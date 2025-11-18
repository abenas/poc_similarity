"""
Name Similarity Search
Find most similar names given an input using fuzzy matching
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, lit, soundex, levenshtein as spark_levenshtein
from pyspark.sql.types import DoubleType, StructType, StructField, StringType
import Levenshtein
import jellyfish
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NameSearcher:
    """Search for similar names using fuzzy matching algorithms"""
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        
    @staticmethod
    @udf(returnType=DoubleType())
    def combined_similarity(name1: str, name2: str) -> float:
        """Calculate combined similarity score using multiple algorithms"""
        if not name1 or not name2:
            return 0.0
            
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # Exact match
        if name1_lower == name2_lower:
            return 1.0
        
        # Levenshtein (normalized)
        lev_distance = Levenshtein.distance(name1_lower, name2_lower)
        max_len = max(len(name1), len(name2))
        lev_sim = 1.0 - (lev_distance / max_len) if max_len > 0 else 0.0
        
        # Jaro-Winkler
        jaro_sim = jellyfish.jaro_winkler_similarity(name1_lower, name2_lower)
        
        # Combined score (weighted average)
        return (lev_sim * 0.4) + (jaro_sim * 0.6)
    
    def search_similar_names(
        self, 
        input_name: str, 
        dataset_path: str, 
        top_n: int = 10,
        threshold: float = 0.5,
        use_blocking: bool = True
    ):
        """
        Search for similar names in a dataset
        
        Args:
            input_name: Name to search for
            dataset_path: Path to parquet dataset
            top_n: Number of top results to return
            threshold: Minimum similarity threshold (0-1)
            use_blocking: Use phonetic blocking to speed up search
        """
        logger.info(f"Searching for names similar to: '{input_name}'")
        
        # Load dataset
        df = self.spark.read.parquet(dataset_path)
        
        # If using blocking, filter by soundex match first
        if use_blocking:
            input_soundex = soundex(lit(input_name))
            df = df.filter(soundex(col("nome_completo")) == input_soundex)
            logger.info(f"Blocking reduced dataset to {df.count()} candidates")
        
        # Calculate similarity for each record
        df_with_sim = df.withColumn(
            "similarity",
            self.combined_similarity(lit(input_name), col("nome_completo"))
        )
        
        # Filter by threshold and get top N
        results = (df_with_sim
                  .filter(col("similarity") >= threshold)
                  .orderBy(col("similarity").desc())
                  .limit(top_n)
                  .select("nome_completo", "data_nascimento", "nr_documento", "similarity")
                  .collect())
        
        return results
    
    def search_in_matches(
        self,
        input_name: str,
        matches_path: str,
        top_n: int = 10,
        threshold: float = 0.5
    ):
        """
        Search for a name in the matches dataset
        
        Args:
            input_name: Name to search for
            matches_path: Path to matches parquet
            top_n: Number of results
            threshold: Minimum similarity
        """
        logger.info(f"Searching matches for: '{input_name}'")
        
        df = self.spark.read.parquet(matches_path)
        
        # Check both sides of the match
        df_with_sim = df.withColumn(
            "similarity_1",
            self.combined_similarity(lit(input_name), col("nome_completo_1"))
        ).withColumn(
            "similarity_2", 
            self.combined_similarity(lit(input_name), col("nome_completo_2"))
        )
        
        # Get the best match from either side
        from pyspark.sql.functions import greatest, when
        
        df_best = df_with_sim.withColumn(
            "best_similarity",
            greatest(col("similarity_1"), col("similarity_2"))
        ).withColumn(
            "matched_name",
            when(col("similarity_1") >= col("similarity_2"), col("nome_completo_1"))
            .otherwise(col("nome_completo_2"))
        ).withColumn(
            "other_name",
            when(col("similarity_1") >= col("similarity_2"), col("nome_completo_2"))
            .otherwise(col("nome_completo_1"))
        )
        
        results = (df_best
                  .filter(col("best_similarity") >= threshold)
                  .orderBy(col("best_similarity").desc())
                  .limit(top_n)
                  .select("matched_name", "other_name", "similarity_score", "best_similarity")
                  .collect())
        
        return results


def print_results(results, search_type="dataset"):
    """Pretty print search results"""
    if not results:
        print("\n❌ No results found")
        return
    
    print(f"\n✅ Found {len(results)} similar names:\n")
    print("=" * 80)
    
    if search_type == "dataset":
        for i, row in enumerate(results, 1):
            print(f"{i}. {row.nome_completo}")
            print(f"   📅 Birth: {row.data_nascimento}")
            print(f"   🆔 Doc: {row.nr_documento}")
            print(f"   📊 Similarity: {row.similarity:.4f}")
            print("-" * 80)
    else:  # matches
        for i, row in enumerate(results, 1):
            print(f"{i}. {row.matched_name} ↔️ {row.other_name}")
            print(f"   📊 Input Similarity: {row.best_similarity:.4f}")
            print(f"   🔗 Match Score: {row.similarity_score:.4f}")
            print("-" * 80)


def main():
    parser = argparse.ArgumentParser(description="Search for similar names")
    parser.add_argument("--name", required=True, help="Name to search for")
    parser.add_argument("--dataset", help="Path to dataset parquet file")
    parser.add_argument("--matches", help="Path to matches parquet file")
    parser.add_argument("--top", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("--threshold", type=float, default=0.5, help="Similarity threshold (default: 0.5)")
    parser.add_argument("--no-blocking", action="store_true", help="Disable phonetic blocking")
    
    args = parser.parse_args()
    
    if not args.dataset and not args.matches:
        parser.error("Must provide either --dataset or --matches")
    
    # Create Spark session
    spark = (SparkSession.builder
            .appName("NameSearch")
            .config("spark.sql.shuffle.partitions", "10")
            .getOrCreate())
    
    try:
        searcher = NameSearcher(spark)
        
        if args.dataset:
            results = searcher.search_similar_names(
                input_name=args.name,
                dataset_path=args.dataset,
                top_n=args.top,
                threshold=args.threshold,
                use_blocking=not args.no_blocking
            )
            print_results(results, "dataset")
            
        if args.matches:
            results = searcher.search_in_matches(
                input_name=args.name,
                matches_path=args.matches,
                top_n=args.top,
                threshold=args.threshold
            )
            print_results(results, "matches")
            
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
