#!/bin/bash
# Index matching results into OpenSearch

MATCHES_PATH="${1:-/data/matches.parquet}"
INDEX_NAME="${2:-person_matches}"

echo "Indexing matches to OpenSearch..."
echo "Source: $MATCHES_PATH"
echo "Index: $INDEX_NAME"
echo ""

docker exec -it person-matcher-app python3 /app/index_matches_simple.py \
  --matches "$MATCHES_PATH" \
  --index "$INDEX_NAME" \
  --host opensearch \
  --port 9200 \
  --batch-size 10000

echo ""
echo "✅ Indexing completed!"
