"""
Index matching results into OpenSearch for fast querying
"""

from opensearchpy import OpenSearch, helpers
from pyspark.sql import SparkSession
import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_age(birth_date_str):
    """Calculate age from birth date string (yyyy-MM-dd)"""
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except:
        return 0


class MatchIndexer:
    """Index person matches into OpenSearch"""
    
    def __init__(self, opensearch_host="opensearch", opensearch_port=9200):
        self.client = OpenSearch(
            hosts=[{'host': opensearch_host, 'port': opensearch_port}],
            http_auth=('admin', 'Admin@123'),
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False
        )
        
    def create_index(self, index_name="person_matches"):
        """Create OpenSearch index with proper mappings"""
        
        mapping = {
            "settings": {
                "number_of_shards": 2,
                "number_of_replicas": 1,
                "index": {
                    "refresh_interval": "5s"
                }
            },
            "mappings": {
                "properties": {
                    "nome_completo_1": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "nome_completo_2": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "data_nascimento_1": {"type": "date", "format": "yyyy-MM-dd"},
                    "data_nascimento_2": {"type": "date", "format": "yyyy-MM-dd"},
                    "nr_documento_1": {"type": "keyword"},
                    "nr_documento_2": {"type": "keyword"},
                    "similarity_score": {"type": "float"},
                    "levenshtein_sim": {"type": "float"},
                    "jaro_winkler_sim": {"type": "float"},
                    "idade_1": {"type": "integer"},
                    "idade_2": {"type": "integer"},
                    "idade_diff": {"type": "integer"},
                    "match_id": {"type": "keyword"},
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        # Delete if exists
        if self.client.indices.exists(index=index_name):
            logger.info(f"Deleting existing index: {index_name}")
            self.client.indices.delete(index=index_name)
        
        # Create new index
        logger.info(f"Creating index: {index_name}")
        self.client.indices.create(index=index_name, body=mapping)
        
    def index_matches(self, matches_path, index_name="person_matches", batch_size=1000):
        """Index matches from parquet into OpenSearch"""
        
        logger.info(f"Loading matches from: {matches_path}")
        
        # Create Spark session
        spark = SparkSession.builder.appName("MatchIndexer").getOrCreate()
        
        try:
            # Read matches
            df = spark.read.parquet(matches_path)
            total_matches = df.count()
            logger.info(f"Found {total_matches} matches to index")
            
            # Convert to pandas for easier OpenSearch indexing
            pdf = df.toPandas()
            
            # Prepare documents for bulk indexing
            def doc_generator():
                indexed_at = datetime.utcnow().isoformat()
                for idx, row in pdf.iterrows():
                    # Calculate ages
                    idade_1 = calculate_age(row['data_nascimento_1'])
                    idade_2 = calculate_age(row['data_nascimento_2'])
                    
                    # Map correct column names from parquet
                    levenshtein_sim = float(row.get('name_lev_score', row.get('levenshtein_sim', 0)))
                    jaro_winkler_sim = float(row.get('name_jaro_score', row.get('jaro_winkler_sim', 0)))
                    
                    doc = {
                        "_index": index_name,
                        "_id": f"{row['nr_documento_1']}_{row['nr_documento_2']}",
                        "_source": {
                            "nome_completo_1": row['nome_completo_1'],
                            "nome_completo_2": row['nome_completo_2'],
                            "data_nascimento_1": row['data_nascimento_1'],
                            "data_nascimento_2": row['data_nascimento_2'],
                            "nr_documento_1": row['nr_documento_1'],
                            "nr_documento_2": row['nr_documento_2'],
                            "similarity_score": float(row['similarity_score']),
                            "levenshtein_sim": levenshtein_sim,
                            "jaro_winkler_sim": jaro_winkler_sim,
                            "idade_1": idade_1,
                            "idade_2": idade_2,
                            "idade_diff": abs(idade_1 - idade_2),
                            "match_id": f"{row['nr_documento_1']}_{row['nr_documento_2']}",
                            "indexed_at": indexed_at
                        }
                    }
                    yield doc
            
            # Bulk index
            logger.info(f"Starting bulk indexing in batches of {batch_size}...")
            success, failed = helpers.bulk(
                self.client,
                doc_generator(),
                chunk_size=batch_size,
                raise_on_error=False
            )
            
            logger.info(f"✅ Indexed {success} documents")
            if failed:
                logger.warning(f"⚠️ Failed to index {len(failed)} documents")
            
            # Refresh index
            self.client.indices.refresh(index=index_name)
            
            return success, failed
            
        finally:
            spark.stop()


def main():
    parser = argparse.ArgumentParser(description="Index matches into OpenSearch")
    parser.add_argument("--matches", required=True, help="Path to matches parquet file")
    parser.add_argument("--index", default="person_matches", help="OpenSearch index name")
    parser.add_argument("--host", default="opensearch", help="OpenSearch host")
    parser.add_argument("--port", type=int, default=9200, help="OpenSearch port")
    parser.add_argument("--batch-size", type=int, default=1000, help="Bulk indexing batch size")
    
    args = parser.parse_args()
    
    indexer = MatchIndexer(opensearch_host=args.host, opensearch_port=args.port)
    
    # Create index
    indexer.create_index(index_name=args.index)
    
    # Index matches
    success, failed = indexer.index_matches(
        matches_path=args.matches,
        index_name=args.index,
        batch_size=args.batch_size
    )
    
    print(f"\n{'='*60}")
    print(f"✅ Indexing Complete!")
    print(f"{'='*60}")
    print(f"Index: {args.index}")
    print(f"Successful: {success}")
    print(f"Failed: {len(failed) if failed else 0}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
