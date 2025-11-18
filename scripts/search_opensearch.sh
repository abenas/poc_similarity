#!/bin/bash
# Search matches in OpenSearch

INDEX_NAME="${INDEX_NAME:-person_matches}"

# Default to showing help if no args
if [ $# -eq 0 ]; then
    cat << 'EOF'
OpenSearch Match Search Examples:

# Search by document number
./search_opensearch.sh --document "12345678900"

# Search by name (exact)
./search_opensearch.sh --name "João Silva"

# Search by name (fuzzy)
./search_opensearch.sh --name "Joao Silva" --fuzzy

# High quality matches (similarity >= 0.8)
./search_opensearch.sh --min-score 0.8 --top 20

# Matches by age range (both persons between 30-40 years)
./search_opensearch.sh --age-min 30 --age-max 40

# Get statistics
./search_opensearch.sh --stats

# Change index
INDEX_NAME=my_matches ./search_opensearch.sh --stats

EOF
    exit 0
fi

docker exec -it person-matcher-app python3 /app/search_opensearch.py \
  --index "$INDEX_NAME" \
  --host opensearch \
  --port 9200 \
  "$@"
