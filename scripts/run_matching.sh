#!/bin/bash
set -e

echo "🚀 Iniciando pipeline de matching..."

# 1. Submeter job Spark com configurações otimizadas
echo "📊 Submetendo job de matching ao Spark..."
docker-compose exec -T spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  --driver-memory 2g \
  --executor-memory 3g \
  --executor-cores 4 \
  --total-executor-cores 16 \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.sql.adaptive.coalescePartitions.enabled=true \
  --conf spark.sql.adaptive.skewJoin.enabled=true \
  --conf spark.sql.adaptive.autoBroadcastJoinThreshold=10485760 \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --conf spark.sql.shuffle.partitions=200 \
  --conf spark.default.parallelism=200 \
  --conf spark.sql.files.maxPartitionBytes=134217728 \
  --conf spark.memory.fraction=0.8 \
  --conf spark.memory.storageFraction=0.3 \
  --conf spark.sql.inMemoryColumnarStorage.compressed=true \
  --conf spark.sql.inMemoryColumnarStorage.batchSize=10000 \
  --conf spark.locality.wait=3s \
  --conf spark.speculation=true \
  --conf spark.speculation.multiplier=2 \
  --conf spark.speculation.quantile=0.75 \
  /app/person_matcher_local.py \
  --dataset1 /data/dataset1.parquet \
  --dataset2 /data/dataset2.parquet \
  --output /data/matches.parquet \
  --threshold 0.7 \
  --max-matches 5

echo ""
echo "✅ Pipeline concluída!"
echo "📊 Resultados salvos em: ./data/matches.parquet"
echo ""
echo "Para visualizar os resultados:"
echo "  python -c \"import pandas as pd; df = pd.read_parquet('data/matches.parquet'); print(df.head(10))\""
