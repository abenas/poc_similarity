#!/bin/bash

###############################################################################
# Benchmark Script for Person Matching Pipeline
# 
# Measures execution time, resource usage, and matching results
# Compares performance across different configurations
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DATA_DIR="/data"
OUTPUT_DIR="/data/results"
BENCHMARK_DIR="./benchmark_results"
LOG_FILE="${BENCHMARK_DIR}/benchmark_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "${BENCHMARK_DIR}"
# OUTPUT_DIR is inside container, no need to create locally

# Helper functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "${LOG_FILE}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "${LOG_FILE}"
}

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "${LOG_FILE}"
}

# Display banner
banner() {
    echo -e "${BLUE}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Person Matching Pipeline - Performance Benchmark"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Get Docker container stats
get_container_stats() {
    local container_name=$1
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" "${container_name}" 2>/dev/null || echo "N/A"
}

# Monitor resource usage during execution
monitor_resources() {
    local interval=${1:-5}
    local output_file="${BENCHMARK_DIR}/resource_usage_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "Monitoring resource usage (saving to ${output_file})..."
    
    while true; do
        {
            echo "=== $(date +'%Y-%m-%d %H:%M:%S') ==="
            docker stats --no-stream \
                spark-master \
                spark-worker-1 \
                spark-worker-2 \
                spark-worker-3 \
                spark-worker-4 2>/dev/null || true
            echo ""
        } >> "${output_file}"
        sleep "${interval}"
    done
}

# Run matching pipeline
run_matching() {
    local threshold=${1:-0.7}
    local max_matches=${2:-5}
    
    log "Running matching pipeline (threshold=${threshold}, max_matches=${max_matches})..."
    
    # Start resource monitoring in background
    monitor_resources 5 &
    MONITOR_PID=$!
    
    # Measure execution time
    START_TIME=$(date +%s)
    
    # Execute matching
    docker exec spark-master bash -c "
        cd /app && \
        /opt/spark/bin/spark-submit \
            --master spark://spark-master:7077 \
            --driver-memory 2g \
            --executor-memory 3g \
            --conf spark.executor.cores=4 \
            --conf spark.sql.shuffle.partitions=200 \
            --conf spark.default.parallelism=200 \
            --conf spark.sql.adaptive.enabled=true \
            --conf spark.sql.adaptive.coalescePartitions.enabled=true \
            --conf spark.sql.adaptive.skewJoin.enabled=true \
            --conf spark.sql.adaptive.autoBroadcastJoinThreshold=10m \
            --conf spark.speculation=true \
            --conf spark.speculation.multiplier=2 \
            --conf spark.speculation.quantile=0.75 \
            --conf spark.memory.fraction=0.8 \
            --conf spark.memory.storageFraction=0.3 \
            --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
            --conf spark.kryo.registrationRequired=false \
            person_matcher_local.py \
                --dataset1 /data/dataset1.parquet \
                --dataset2 /data/dataset2.parquet \
                --output /data/results \
                --threshold ${threshold} \
                --max-matches ${max_matches}
    " 2>&1 | tee -a "${LOG_FILE}"
    
    EXECUTION_STATUS=${PIPESTATUS[0]}
    
    # Stop resource monitoring
    kill "${MONITOR_PID}" 2>/dev/null || true
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    if [ ${EXECUTION_STATUS} -eq 0 ]; then
        log "✅ Matching completed successfully in ${ELAPSED} seconds"
    else
        log_error "❌ Matching failed with status ${EXECUTION_STATUS}"
        return ${EXECUTION_STATUS}
    fi
    
    return 0
}

# Analyze results
analyze_results() {
    log "Analyzing matching results..."
    
    # Count matches
    MATCH_COUNT=$(docker exec spark-master bash -c "
        python3 -c \"
import pandas as pd
import glob
files = glob.glob('/data/results/*.parquet')
if files:
    df = pd.read_parquet(files[0])
    print(len(df))
else:
    print(0)
\"
    " 2>/dev/null || echo "0")
    
    log_info "Total matches found: ${MATCH_COUNT}"
    
    # Show sample of top matches
    log_info "Top 10 matches:"
    docker exec spark-master bash -c "
        python3 -c \"
import pandas as pd
import glob
files = glob.glob('/data/results/*.parquet')
if files:
    df = pd.read_parquet(files[0])
    df_sorted = df.sort_values('similarity_score', ascending=False).head(10)
    print(df_sorted[['nome_completo_1', 'nome_completo_2', 'similarity_score']].to_string())
\"
    " 2>&1 | tee -a "${LOG_FILE}"
}

# Generate benchmark report
generate_report() {
    local elapsed=$1
    local threshold=$2
    local match_count=$3
    
    REPORT_FILE="${BENCHMARK_DIR}/report_$(date +%Y%m%d_%H%M%S).md"
    
    log "Generating benchmark report: ${REPORT_FILE}"
    
    cat > "${REPORT_FILE}" <<EOF
# Person Matching Benchmark Report

**Date:** $(date +'%Y-%m-%d %H:%M:%S')

## Configuration

- **Threshold:** ${threshold}
- **Data Directory:** ${DATA_DIR}
- **Output Directory:** ${OUTPUT_DIR}
- **Spark Cluster:** 1 master + 4 workers (6GB RAM, 4 cores each)

## Performance Metrics

- **Execution Time:** ${elapsed} seconds
- **Total Matches Found:** ${match_count}
- **Throughput:** $((match_count / elapsed)) matches/second

## Resource Usage

### Spark Master
\`\`\`
$(get_container_stats spark-master)
\`\`\`

### Spark Worker 1
\`\`\`
$(get_container_stats spark-worker-1)
\`\`\`

### Spark Worker 2
\`\`\`
$(get_container_stats spark-worker-2)
\`\`\`

### Spark Worker 3
\`\`\`
$(get_container_stats spark-worker-3)
\`\`\`

### Spark Worker 4
\`\`\`
$(get_container_stats spark-worker-4)
\`\`\`

## Spark Configuration

- Driver Memory: 2g
- Executor Memory: 3g
- Executor Cores: 4
- Shuffle Partitions: 200
- Adaptive Query Execution: Enabled
- Speculation: Enabled
- Kryo Serialization: Enabled

## Data Statistics

### Dataset 1
\`\`\`
$(docker exec spark-master bash -c "ls -lh /data/dataset1.parquet" 2>/dev/null || echo "N/A")
\`\`\`

### Dataset 2
\`\`\`
$(docker exec spark-master bash -c "ls -lh /data/dataset2.parquet" 2>/dev/null || echo "N/A")
\`\`\`

## Optimization Notes

- Blocking strategy: Soundex + Year-Month (improved from first 3 letters + year)
- Age pre-filter: Eliminates pairs with >5 years difference
- Partitioning: Data partitioned by blocking_key
- Cache materialization: Forced with count() before expensive operations
- Output consolidation: 10 partitions for final results

## Recommendations

1. Monitor memory usage - adjust executor memory if seeing OOM errors
2. Check skew in blocking keys - redistribute if necessary
3. Tune threshold based on precision/recall requirements
4. Scale workers horizontally for larger datasets

---
*Generated by benchmark.sh*
EOF
    
    log "✅ Report saved to ${REPORT_FILE}"
}

# Main execution
main() {
    banner
    
    # Parse arguments
    THRESHOLD=${1:-0.7}
    MAX_MATCHES=${2:-5}
    
    log "Starting benchmark with threshold=${THRESHOLD}, max_matches=${MAX_MATCHES}"
    
    # Check if containers are running
    log_info "Checking Docker containers..."
    if ! docker ps | grep -q "spark-master"; then
        log_error "Spark containers not running. Start with: docker-compose up -d"
        exit 1
    fi
    
    # Clean previous results
    log_info "Cleaning previous results..."
    docker exec spark-master bash -c "rm -rf /data/results/*" 2>/dev/null || true
    
    # Run benchmark
    START_TIME=$(date +%s)
    
    if run_matching "${THRESHOLD}" "${MAX_MATCHES}"; then
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        
        # Analyze results
        analyze_results
        
        # Get match count for report
        MATCH_COUNT=$(docker exec spark-master bash -c "
            python3 -c \"
import pandas as pd
import glob
files = glob.glob('/data/results/*.parquet')
if files:
    df = pd.read_parquet(files[0])
    print(len(df))
else:
    print(0)
\"
        " 2>/dev/null || echo "0")
        
        # Generate report
        generate_report "${ELAPSED}" "${THRESHOLD}" "${MATCH_COUNT}"
        
        log "🎉 Benchmark completed successfully!"
        log "📊 Check results at: ${BENCHMARK_DIR}"
    else
        log_error "Benchmark failed"
        exit 1
    fi
}

# Execute main function
main "$@"
