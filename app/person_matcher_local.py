"""
Distributed Person Matching using PySpark - Local Version
Compares two datasets using blocking strategies and fuzzy matching
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, udf, lit, concat_ws, soundex, substring, year, abs as spark_abs
from pyspark.sql.types import DoubleType
import Levenshtein
import jellyfish
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersonMatcher:
    """Scalable person matching engine using distributed computing"""
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        
    def create_blocking_key(self, df: DataFrame) -> DataFrame:
        """Create blocking keys to reduce comparison space using Soundex + Year-Month"""
        return df.withColumn(
            "blocking_key",
            concat_ws("_", 
                     soundex(col("nome_completo")),
                     substring(col("data_nascimento"), 1, 7)  # YYYY-MM
            )
        )
    
    @staticmethod
    @udf(returnType=DoubleType())
    def levenshtein_similarity(s1: str, s2: str) -> float:
        """Calculate normalized Levenshtein similarity (0-1)"""
        if not s1 or not s2:
            return 0.0
        distance = Levenshtein.distance(s1.lower(), s2.lower())
        max_len = max(len(s1), len(s2))
        return 1.0 - (distance / max_len) if max_len > 0 else 1.0
    
    @staticmethod
    @udf(returnType=DoubleType())
    def jaro_winkler_similarity(s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity"""
        if not s1 or not s2:
            return 0.0
        return jellyfish.jaro_winkler_similarity(s1.lower(), s2.lower())
    
    @staticmethod
    @udf(returnType=DoubleType())
    def soundex_match(s1: str, s2: str) -> float:
        """Phonetic matching using Soundex"""
        if not s1 or not s2:
            return 0.0
        try:
            return 1.0 if jellyfish.soundex(s1) == jellyfish.soundex(s2) else 0.0
        except:
            return 0.0
    
    @staticmethod
    @udf(returnType=DoubleType())
    def date_similarity(d1: str, d2: str) -> float:
        """Date similarity - exact match or close dates"""
        if not d1 or not d2:
            return 0.0
        if d1 == d2:
            return 1.0
        if d1[:7] == d2[:7]:  # YYYY-MM
            return 0.8
        if d1[:4] == d2[:4]:  # YYYY
            return 0.5
        return 0.0
    
    def compute_similarity_score(self, df: DataFrame) -> DataFrame:
        """Compute composite similarity score using multiple algorithms"""
        df = df.withColumn(
            "name_lev_score",
            self.levenshtein_similarity(col("nome_completo_1"), col("nome_completo_2"))
        )
        
        df = df.withColumn(
            "name_jaro_score",
            self.jaro_winkler_similarity(col("nome_completo_1"), col("nome_completo_2"))
        )
        
        df = df.withColumn(
            "name_soundex_score",
            self.soundex_match(col("nome_completo_1"), col("nome_completo_2"))
        )
        
        df = df.withColumn(
            "date_score",
            self.date_similarity(col("data_nascimento_1"), col("data_nascimento_2"))
        )
        
        df = df.withColumn(
            "doc_match",
            (col("nr_documento_1") == col("nr_documento_2")).cast("double")
        )
        
        df = df.withColumn(
            "similarity_score",
            (
                col("name_lev_score") * 0.25 +
                col("name_jaro_score") * 0.25 +
                col("name_soundex_score") * 0.15 +
                col("date_score") * 0.25 +
                col("doc_match") * 0.10
            )
        )
        
        return df
    
    def match_datasets(self, df1: DataFrame, df2: DataFrame, threshold: float = 0.7) -> DataFrame:
        """Match two datasets using blocking and fuzzy matching"""
        # Avoid expensive count operations in production
        # logger.info(f"Dataset 1 count: {df1.count()}")
        # logger.info(f"Dataset 2 count: {df2.count()}")
        
        # Create blocking keys and repartition for better parallelism
        df1_blocked = self.create_blocking_key(df1) \
            .repartition(200, "blocking_key") \
            .cache()
        df2_blocked = self.create_blocking_key(df2) \
            .repartition(200, "blocking_key") \
            .cache()
        
        # Force materialization
        df1_blocked.count()
        df2_blocked.count()
        
        # Join on blocking key with broadcast hint for smaller dataset
        logger.info("Performing blocked join...")
        joined = df1_blocked.alias("d1").join(
            df2_blocked.alias("d2"),
            col("d1.blocking_key") == col("d2.blocking_key"),
            "inner"
        )
        
        # Rename columns
        joined = joined.select(
            col("d1.nome_completo").alias("nome_completo_1"),
            col("d1.data_nascimento").alias("data_nascimento_1"),
            col("d1.nr_documento").alias("nr_documento_1"),
            col("d1.status").alias("status_1"),
            col("d2.nome_completo").alias("nome_completo_2"),
            col("d2.data_nascimento").alias("data_nascimento_2"),
            col("d2.nr_documento").alias("nr_documento_2"),
            col("d2.status").alias("status_2"),
            col("d1.blocking_key")
        )
        
        # Pre-filter: eliminate pairs with age difference > 5 years
        joined = joined.filter(
            spark_abs(year(col("data_nascimento_1")) - year(col("data_nascimento_2"))) <= 5
        )
        
        logger.info(f"Blocked pairs count: {joined.count()}")
        
        # Compute similarity scores with optimized operations
        logger.info("Computing similarity scores...")
        scored = self.compute_similarity_score(joined)
        
        # Filter by threshold - push down predicate early
        matches = scored.filter(col("similarity_score") >= threshold)
        
        result = matches.select(
            col("nr_documento_1"),
            col("nome_completo_1"),
            col("data_nascimento_1"),
            col("status_1"),
            col("nr_documento_2"),
            col("nome_completo_2"),
            col("data_nascimento_2"),
            col("status_2"),
            col("similarity_score"),
            col("name_lev_score"),
            col("name_jaro_score"),
            col("date_score")
        ).repartition(10)  # Consolidate partitions for efficient writing
        
        # Avoid expensive count in production - comment out for performance
        # logger.info(f"Matches found: {result.count()}")
        
        return result


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Person Matcher with Fuzzy Algorithms')
    parser.add_argument('--dataset1', required=True, help='Path to dataset 1')
    parser.add_argument('--dataset2', required=True, help='Path to dataset 2')
    parser.add_argument('--output', required=True, help='Output path for results')
    parser.add_argument('--threshold', type=float, default=0.7, help='Similarity threshold (default: 0.7)')
    parser.add_argument('--max-matches', type=int, default=5, help='Max matches per record (default: 5)')
    
    args = parser.parse_args()
    
    # Initialize Spark with optimized configurations
    spark = SparkSession.builder \
        .appName("PersonMatcher") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.sql.adaptive.skewJoin.enabled", "true") \
        .config("spark.sql.adaptive.autoBroadcastJoinThreshold", "10MB") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.shuffle.partitions", "200") \
        .config("spark.default.parallelism", "200") \
        .config("spark.sql.files.maxPartitionBytes", "128MB") \
        .config("spark.sql.inMemoryColumnarStorage.compressed", "true") \
        .config("spark.sql.inMemoryColumnarStorage.batchSize", "10000") \
        .config("spark.memory.fraction", "0.8") \
        .config("spark.memory.storageFraction", "0.3") \
        .getOrCreate()
    
    logger.info(f"Reading datasets from {args.dataset1} and {args.dataset2}")
    
    # Read datasets
    df1 = spark.read.parquet(args.dataset1)
    df2 = spark.read.parquet(args.dataset2)
    
    # Initialize matcher
    matcher = PersonMatcher(spark)
    
    # Perform matching
    matches = matcher.match_datasets(df1, df2, args.threshold)
    
    # Write results
    logger.info(f"Writing results to {args.output}")
    matches.write \
        .mode("overwrite") \
        .parquet(args.output)
    
    logger.info("Job completed successfully")
    
    spark.stop()


if __name__ == "__main__":
    main()
