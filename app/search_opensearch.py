"""
Search matches in OpenSearch using various query patterns
"""

from opensearchpy import OpenSearch
import argparse
import json
from datetime import datetime


class MatchSearcher:
    """Search person matches in OpenSearch"""
    
    def __init__(self, opensearch_host="opensearch", opensearch_port=9200):
        self.client = OpenSearch(
            hosts=[{'host': opensearch_host, 'port': opensearch_port}],
            http_auth=('admin', 'Admin@123'),
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False
        )
        
    def search_by_document(self, nr_documento, index_name="person_matches", top_n=10, min_score=None):
        """Find all matches for a specific document number"""
        
        bool_query = {
            "should": [
                {"term": {"nr_documento_1": nr_documento}},
                {"term": {"nr_documento_2": nr_documento}}
            ],
            "minimum_should_match": 1
        }
        
        if min_score is not None:
            bool_query["filter"] = {"range": {"similarity_score": {"gte": min_score}}}
        
        query = {
            "query": {"bool": bool_query},
            "sort": [{"similarity_score": "desc"}],
            "size": top_n
        }
        
        return self.client.search(index=index_name, body=query)
    
    def search_by_name(self, name, index_name="person_matches", top_n=10, fuzzy=True, min_score=None):
        """Search matches by person name (fuzzy or exact)"""
        
        if fuzzy:
            bool_query = {
                "should": [
                    {
                        "match": {
                            "nome_completo_1": {
                                "query": name,
                                "fuzziness": "AUTO"
                            }
                        }
                    },
                    {
                        "match": {
                            "nome_completo_2": {
                                "query": name,
                                "fuzziness": "AUTO"
                            }
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        else:
            bool_query = {
                "should": [
                    {"match_phrase": {"nome_completo_1": name}},
                    {"match_phrase": {"nome_completo_2": name}}
                ],
                "minimum_should_match": 1
            }
        
        if min_score is not None:
            bool_query["filter"] = {"range": {"similarity_score": {"gte": min_score}}}
        
        query = {
            "query": {"bool": bool_query},
            "sort": [{"similarity_score": "desc"}],
            "size": top_n
        }
        
        return self.client.search(index=index_name, body=query)
    
    def search_high_quality_matches(self, min_score=0.8, index_name="person_matches", top_n=100):
        """Find high-quality matches above a similarity threshold"""
        
        query = {
            "query": {
                "range": {
                    "similarity_score": {"gte": min_score}
                }
            },
            "sort": [{"similarity_score": "desc"}],
            "size": top_n
        }
        
        return self.client.search(index=index_name, body=query)
    
    def search_by_age_range(self, min_age, max_age, index_name="person_matches", top_n=50):
        """Find matches where both persons are within an age range"""
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"idade_1": {"gte": min_age, "lte": max_age}}},
                        {"range": {"idade_2": {"gte": min_age, "lte": max_age}}}
                    ]
                }
            },
            "sort": [{"similarity_score": "desc"}],
            "size": top_n
        }
        
        return self.client.search(index=index_name, body=query)
    
    def aggregate_stats(self, index_name="person_matches"):
        """Get statistics about matches"""
        
        query = {
            "size": 0,
            "aggs": {
                "avg_similarity": {"avg": {"field": "similarity_score"}},
                "max_similarity": {"max": {"field": "similarity_score"}},
                "min_similarity": {"min": {"field": "similarity_score"}},
                "similarity_distribution": {
                    "histogram": {
                        "field": "similarity_score",
                        "interval": 0.1
                    }
                },
                "age_diff_stats": {
                    "stats": {"field": "idade_diff"}
                }
            }
        }
        
        return self.client.search(index=index_name, body=query)


def print_results(response, search_type="default"):
    """Pretty print search results"""
    
    hits = response['hits']['hits']
    total = response['hits']['total']['value']
    
    print(f"\n{'='*80}")
    print(f"🔍 Found {total} total matches (showing {len(hits)})")
    print(f"{'='*80}\n")
    
    for i, hit in enumerate(hits, 1):
        source = hit['_source']
        score = hit.get('_score')
        
        # Handle None values for formatting
        similarity_score = source.get('similarity_score')
        levenshtein = source.get('levenshtein_sim')
        jaro_winkler = source.get('jaro_winkler_sim')
        idade_diff = source.get('idade_diff')
        
        score_str = f"{score:.4f}" if score is not None else "N/A"
        similarity_str = f"{similarity_score:.4f}" if similarity_score is not None else "N/A"
        levenshtein_str = f"{levenshtein:.4f}" if levenshtein is not None else "N/A"
        jaro_winkler_str = f"{jaro_winkler:.4f}" if jaro_winkler is not None else "N/A"
        idade_diff_str = f"{idade_diff}" if idade_diff is not None else "N/A"
        
        print(f"{i}. Match ID: {source.get('match_id', 'N/A')}")
        print(f"   👤 Person 1: {source['nome_completo_1']}")
        print(f"      📅 Birth: {source['data_nascimento_1']} | 🆔 Doc: {source['nr_documento_1']} | Age: {source.get('idade_1', 'N/A')}")
        print(f"   👤 Person 2: {source['nome_completo_2']}")
        print(f"      📅 Birth: {source['data_nascimento_2']} | 🆔 Doc: {source['nr_documento_2']} | Age: {source.get('idade_2', 'N/A')}")
        print(f"   📊 Similarity: {similarity_str} | Search Score: {score_str}")
        print(f"   📏 Levenshtein: {levenshtein_str} | Jaro-Winkler: {jaro_winkler_str}")
        print(f"   🔢 Age Difference: {idade_diff_str} years")
        print(f"{'-'*80}")


def print_stats(response):
    """Print aggregation statistics"""
    
    aggs = response['aggregations']
    
    print(f"\n{'='*80}")
    print(f"📊 Match Statistics")
    print(f"{'='*80}\n")
    
    print(f"Similarity Scores:")
    print(f"  Average: {aggs['avg_similarity']['value']:.4f}")
    print(f"  Maximum: {aggs['max_similarity']['value']:.4f}")
    print(f"  Minimum: {aggs['min_similarity']['value']:.4f}\n")
    
    print(f"Age Difference Statistics:")
    age_stats = aggs['age_diff_stats']
    print(f"  Average: {age_stats['avg']:.2f} years")
    print(f"  Maximum: {age_stats['max']:.0f} years")
    print(f"  Minimum: {age_stats['min']:.0f} years\n")
    
    print(f"Similarity Distribution:")
    for bucket in aggs['similarity_distribution']['buckets']:
        key = bucket['key']
        count = bucket['doc_count']
        print(f"  {key:.1f}-{key+0.1:.1f}: {count} matches")
    
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description="Search matches in OpenSearch")
    parser.add_argument("--index", default="person_matches", help="Index name")
    parser.add_argument("--host", default="opensearch", help="OpenSearch host")
    parser.add_argument("--port", type=int, default=9200, help="OpenSearch port")
    
    # Search options
    parser.add_argument("--document", help="Search by document number")
    parser.add_argument("--name", help="Search by person name")
    parser.add_argument("--fuzzy", action="store_true", help="Use fuzzy name search")
    parser.add_argument("--min-score", type=float, help="Minimum similarity score")
    parser.add_argument("--age-min", type=int, help="Minimum age")
    parser.add_argument("--age-max", type=int, help="Maximum age")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--top", type=int, default=10, help="Number of results")
    
    args = parser.parse_args()
    
    searcher = MatchSearcher(opensearch_host=args.host, opensearch_port=args.port)
    
    try:
        if args.stats:
            response = searcher.aggregate_stats(index_name=args.index)
            print_stats(response)
        elif args.document:
            response = searcher.search_by_document(
                args.document, args.index, args.top, min_score=args.min_score
            )
            print_results(response, "document")
        elif args.name:
            response = searcher.search_by_name(
                args.name, args.index, args.top, args.fuzzy, min_score=args.min_score
            )
            print_results(response, "name")
        elif args.min_score:
            response = searcher.search_high_quality_matches(args.min_score, args.index, args.top)
            print_results(response, "score")
        elif args.age_min and args.age_max:
            response = searcher.search_by_age_range(args.age_min, args.age_max, args.index, args.top)
            print_results(response, "age")
        else:
            parser.error("Must specify at least one search criteria")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
