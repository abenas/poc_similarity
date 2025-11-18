"""
Distributed Person Matching using PySpark
Compares two datasets of millions of records using blocking strategies and fuzzy matching
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, udf, lit, broadcast, hash, abs as spark_abs, concat_ws, coalesce
from pyspark.sql.types import DoubleType, StructType, StructField, StringType, IntegerType
import Levenshtein
import jellyfish
from typing import List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersonMatcher:
    """
    Scalable person matching engine using distributed computing
    """
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        
    def create_blocking_key(self, df: DataFrame) -> DataFrame:
        """
        Create blocking keys to reduce comparison space
        Uses first 3 chars of name + birth year
        """
        return df.withColumn(
            "blocking_key",
            concat_ws("_", 
                     col("nome_completo").substr(1, 3),
                     col("data_nascimento").substr(1, 4)  # Year
            )
        )
    
    @staticmethod
    @udf(returnType=DoubleType())
    def levenshtein_similarity(s1: str, s2: str) -> float:
        """
        Calculate normalized Levenshtein similarity (0-1)
        """
        if not s1 or not s2:
            return 0.0
        
        distance = Levenshtein.distance(s1.lower(), s2.lower())
        max_len = max(len(s1), len(s2))
        
        if max_len == 0:
            return 1.0
            
        return 1.0 - (distance / max_len)
    
    @staticmethod
    @udf(returnType=DoubleType())
    def jaro_winkler_similarity(s1: str, s2: str) -> float:
        """
        Calculate Jaro-Winkler similarity (better for names)
        """
        if not s1 or not s2:
            return 0.0
        
        return jellyfish.jaro_winkler_similarity(s1.lower(), s2.lower())
    
    @staticmethod
    @udf(returnType=DoubleType())
    def soundex_match(s1: str, s2: str) -> float:
        """
        Phonetic matching using Soundex
        """
        if not s1 or not s2:
            return 0.0
        
        try:
            return 1.0 if jellyfish.soundex(s1) == jellyfish.soundex(s2) else 0.0
        except:
            return 0.0
    
    @staticmethod
    @udf(returnType=DoubleType())
    def date_similarity(d1: str, d2: str) -> float:
        """
        Date similarity - exact match or close dates
        """
        if not d1 or not d2:
            return 0.0
        
        if d1 == d2:
            return 1.0
        
        # Check if year and month match
        if d1[:7] == d2[:7]:  # YYYY-MM
            return 0.8
        
        # Check if year matches
        if d1[:4] == d2[:4]:  # YYYY
            return 0.5
        
        return 0.0
    
    def compute_similarity_score(self, df: DataFrame) -> DataFrame:
        """
        Compute composite similarity score using multiple algorithms
        """
        # Name similarity (weighted average of Levenshtein and Jaro-Winkler)
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
        
        # Date similarity
        df = df.withColumn(
            "date_score",
            self.date_similarity(col("data_nascimento_1"), col("data_nascimento_2"))
        )
        
        # Document exact match
        df = df.withColumn(
            "doc_match",
            (col("nr_documento_1") == col("nr_documento_2")).cast("double")
        )
        
        # Composite score (weighted)
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
    
    def match_datasets(
        self, 
        df1: DataFrame, 
        df2: DataFrame,
        threshold: float = 0.7
    ) -> DataFrame:
        """
        Match two datasets using blocking and fuzzy matching
        
        Args:
            df1: First dataset
            df2: Second dataset
            threshold: Minimum similarity score to consider a match
            
        Returns:
            DataFrame with matches and similarity scores
        """
        logger.info(f"Dataset 1 count: {df1.count()}")
        logger.info(f"Dataset 2 count: {df2.count()}")
        
        # Create blocking keys
        df1_blocked = self.create_blocking_key(df1).cache()
        df2_blocked = self.create_blocking_key(df2).cache()
        
        # Get distinct blocking keys from smaller dataset for broadcast
        blocking_keys = df1_blocked.select("blocking_key").distinct()
        
        # Join on blocking key (reduces cartesian product)
        logger.info("Performing blocked join...")
        joined = df1_blocked.alias("d1").join(
            df2_blocked.alias("d2"),
            col("d1.blocking_key") == col("d2.blocking_key"),
            "inner"
        )
        
        # Rename columns for clarity
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
        
        logger.info(f"Blocked pairs count: {joined.count()}")
        
        # Compute similarity scores
        logger.info("Computing similarity scores...")
        scored = self.compute_similarity_score(joined)
        
        # Filter by threshold
        matches = scored.filter(col("similarity_score") >= threshold)
        
        # Select final columns
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
        ).orderBy(col("similarity_score").desc())
        
        logger.info(f"Matches found: {result.count()}")
        
        return result


def read_from_glue_catalog(
    spark: SparkSession,
    database: str,
    table: str,
    partition_filter: str = None
) -> DataFrame:
    """
    Read data from AWS Glue Data Catalog
    
    Args:
        spark: SparkSession
        database: Glue database name
        table: Glue table name
        partition_filter: Optional partition filter
        
    Returns:
        DataFrame
    """
    df = spark.read \
        .format("parquet") \
        .option("catalog", "glue") \
        .option("database", database) \
        .option("table", table)
    
    if partition_filter:
        df = df.option("partitionFilter", partition_filter)
    
    return df.load()


def main():
    """
    Main execution function for EMR
    """
    import sys
    
    if len(sys.argv) < 5:
        print("Usage: person_matcher.py <glue_db> <table1> <table2> <output_path> [threshold]")
        sys.exit(1)
    
    glue_database = sys.argv[1]
    table1 = sys.argv[2]
    table2 = sys.argv[3]
    output_path = sys.argv[4]
    threshold = float(sys.argv[5]) if len(sys.argv) > 5 else 0.7
    
    # Initialize Spark
    spark = SparkSession.builder \
        .appName("PersonMatcher") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .getOrCreate()
    
    logger.info(f"Reading from Glue catalog: {glue_database}.{table1} and {glue_database}.{table2}")
    
    # Read datasets
    df1 = read_from_glue_catalog(spark, glue_database, table1)
    df2 = read_from_glue_catalog(spark, glue_database, table2)
    
    # Initialize matcher
    matcher = PersonMatcher(spark)
    
    # Perform matching
    matches = matcher.match_datasets(df1, df2, threshold)
    
    # Write results to S3
    logger.info(f"Writing results to {output_path}")
    matches.write \
        .mode("overwrite") \
        .partitionBy("similarity_score") \
        .parquet(output_path)
    
    logger.info("Job completed successfully")
    
    spark.stop()


if __name__ == "__main__":
    main()
