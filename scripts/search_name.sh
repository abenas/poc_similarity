#!/bin/bash
# Search for similar names in datasets or matches

# Usage examples:
# ./search_name.sh "João Silva"
# ./search_name.sh "Maria Santos" --threshold 0.7
# ./search_name.sh "Pedro Oliveira" --top 20 --matches

NAME="${1:-João Silva}"
shift

docker exec -it spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --driver-memory 2g \
  --executor-memory 3g \
  --executor-cores 4 \
  --total-executor-cores 16 \
  /app/name_search.py \
  --name "$NAME" \
  --dataset /data/dataset1.parquet \
  "$@"

echo ""
echo "Search completed for: $NAME"
