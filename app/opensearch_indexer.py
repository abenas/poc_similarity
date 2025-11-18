"""
OpenSearch Indexer for Person Matches
Indexes matching results for fast retrieval by nr_documento
"""

from opensearchpy import OpenSearch, helpers
from pyspark.sql import SparkSession, DataFrame
import boto3
import json
import logging
from typing import Iterator, Dict, Any
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenSearchIndexer:
    """
    Handles indexing of person matches to OpenSearch
    """
    
    def __init__(
        self,
        host: str,
        port: int = 443,
        use_ssl: bool = True,
        region: str = "us-east-1"
    ):
        """
        Initialize OpenSearch client
        
        Args:
            host: OpenSearch endpoint
            port: Port number
            use_ssl: Use SSL connection
            region: AWS region
        """
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=self._get_aws_auth(region),
            use_ssl=use_ssl,
            verify_certs=True,
            connection_class=self._get_connection_class()
        )
        
        self.index_name = "person-matches"
    
    def _get_aws_auth(self, region: str):
        """Get AWS authentication for OpenSearch"""
        from opensearchpy import RequestsHttpConnection, AWSV4SignerAuth
        
        credentials = boto3.Session().get_credentials()
        return AWSV4SignerAuth(credentials, region, 'es')
    
    def _get_connection_class(self):
        """Get connection class for OpenSearch"""
        from opensearchpy import RequestsHttpConnection
        return RequestsHttpConnection
    
    def create_index(self):
        """
        Create index with optimized mapping for person matches
        """
        index_body = {
            "settings": {
                "number_of_shards": 5,
                "number_of_replicas": 1,
                "refresh_interval": "30s",
                "analysis": {
                    "analyzer": {
                        "name_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "nr_documento_1": {
                        "type": "keyword"
                    },
                    "nome_completo_1": {
                        "type": "text",
                        "analyzer": "name_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "data_nascimento_1": {
                        "type": "date",
                        "format": "yyyy-MM-dd"
                    },
                    "status_1": {
                        "type": "keyword"
                    },
                    "nr_documento_2": {
                        "type": "keyword"
                    },
                    "nome_completo_2": {
                        "type": "text",
                        "analyzer": "name_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "data_nascimento_2": {
                        "type": "date",
                        "format": "yyyy-MM-dd"
                    },
                    "status_2": {
                        "type": "keyword"
                    },
                    "similarity_score": {
                        "type": "float"
                    },
                    "name_lev_score": {
                        "type": "float"
                    },
                    "name_jaro_score": {
                        "type": "float"
                    },
                    "date_score": {
                        "type": "float"
                    },
                    "indexed_at": {
                        "type": "date"
                    }
                }
            }
        }
        
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(index=self.index_name, body=index_body)
            logger.info(f"Created index: {self.index_name}")
        else:
            logger.info(f"Index already exists: {self.index_name}")
    
    def bulk_index_from_spark(self, df: DataFrame, batch_size: int = 1000):
        """
        Index data from Spark DataFrame using bulk API
        
        Args:
            df: Spark DataFrame with match results
            batch_size: Number of documents per bulk request
        """
        def generate_actions(partition: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
            """Generate bulk index actions"""
            from datetime import datetime
            
            for row in partition:
                doc = {
                    '_index': self.index_name,
                    '_source': {
                        **row,
                        'indexed_at': datetime.utcnow().isoformat()
                    }
                }
                yield doc
        
        # Convert to pandas and iterate
        logger.info("Starting bulk indexing...")
        
        total_docs = 0
        for batch in df.toLocalIterator():
            actions = []
            for _ in range(batch_size):
                try:
                    row = next(batch)
                    actions.append({
                        '_index': self.index_name,
                        '_source': row.asDict()
                    })
                except StopIteration:
                    break
            
            if actions:
                success, failed = helpers.bulk(
                    self.client,
                    actions,
                    chunk_size=batch_size,
                    raise_on_error=False
                )
                total_docs += success
                
                if failed:
                    logger.warning(f"Failed to index {len(failed)} documents")
        
        logger.info(f"Indexed {total_docs} documents")
    
    def search_by_document(self, nr_documento: str, limit: int = 10) -> list:
        """
        Search matches by document number
        
        Args:
            nr_documento: Document number to search
            limit: Maximum number of results
            
        Returns:
            List of matching records
        """
        query = {
            "query": {
                "bool": {
                    "should": [
                        {"term": {"nr_documento_1": nr_documento}},
                        {"term": {"nr_documento_2": nr_documento}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "sort": [
                {"similarity_score": {"order": "desc"}}
            ],
            "size": limit
        }
        
        response = self.client.search(index=self.index_name, body=query)
        
        return [hit['_source'] for hit in response['hits']['hits']]


def index_from_s3(
    spark: SparkSession,
    input_path: str,
    opensearch_endpoint: str,
    region: str = "us-east-1"
):
    """
    Read matches from S3 and index to OpenSearch
    
    Args:
        spark: SparkSession
        input_path: S3 path to parquet files
        opensearch_endpoint: OpenSearch domain endpoint
        region: AWS region
    """
    logger.info(f"Reading matches from {input_path}")
    
    df = spark.read.parquet(input_path)
    
    # Initialize indexer
    indexer = OpenSearchIndexer(opensearch_endpoint, region=region)
    indexer.create_index()
    
    # Convert to JSON and write to temporary location
    temp_path = f"{input_path.rstrip('/')}_json"
    df.write.mode("overwrite").json(temp_path)
    
    # Read JSON and index
    import awswrangler as wr
    
    json_files = wr.s3.list_objects(temp_path)
    
    for json_file in json_files:
        if json_file.endswith('.json'):
            data = wr.s3.read_json(json_file)
            
            actions = []
            for _, row in data.iterrows():
                actions.append({
                    '_index': indexer.index_name,
                    '_source': row.to_dict()
                })
            
            if actions:
                helpers.bulk(indexer.client, actions, chunk_size=1000)
    
    logger.info("Indexing completed")


def main():
    """
    Main function for indexing job
    """
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: opensearch_indexer.py <input_s3_path> <opensearch_endpoint> [region]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    opensearch_endpoint = sys.argv[2]
    region = sys.argv[3] if len(sys.argv) > 3 else "us-east-1"
    
    spark = SparkSession.builder \
        .appName("OpenSearchIndexer") \
        .getOrCreate()
    
    index_from_s3(spark, input_path, opensearch_endpoint, region)
    
    spark.stop()


if __name__ == "__main__":
    main()
