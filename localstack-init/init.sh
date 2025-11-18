#!/bin/bash

# Initialize LocalStack S3 buckets and Glue catalog

echo "Initializing LocalStack resources..."

# Wait for LocalStack to be ready
sleep 10

# Create S3 buckets
awslocal s3 mb s3://person-data-source1
awslocal s3 mb s3://person-data-source2
awslocal s3 mb s3://person-matching-results
awslocal s3 mb s3://person-matching-scripts

# Create Glue database
awslocal glue create-database --database-input '{"Name": "person_data"}'

# Create sample Glue tables
awslocal glue create-table --database-name person_data \
  --table-input '{
    "Name": "dataset1",
    "StorageDescriptor": {
      "Columns": [
        {"Name": "nome_completo", "Type": "string"},
        {"Name": "data_nascimento", "Type": "string"},
        {"Name": "nr_documento", "Type": "string"},
        {"Name": "status", "Type": "string"}
      ],
      "Location": "s3://person-data-source1/",
      "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
      "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
      "SerdeInfo": {
        "SerializationLibrary": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
      }
    }
  }'

awslocal glue create-table --database-name person_data \
  --table-input '{
    "Name": "dataset2",
    "StorageDescriptor": {
      "Columns": [
        {"Name": "nome_completo", "Type": "string"},
        {"Name": "data_nascimento", "Type": "string"},
        {"Name": "nr_documento", "Type": "string"},
        {"Name": "status", "Type": "string"}
      ],
      "Location": "s3://person-data-source2/",
      "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
      "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
      "SerdeInfo": {
        "SerializationLibrary": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
      }
    }
  }'

# Create DynamoDB table for state tracking
awslocal dynamodb create-table \
  --table-name person-matching-state \
  --attribute-definitions \
    AttributeName=dataset_id,AttributeType=S \
  --key-schema \
    AttributeName=dataset_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

echo "LocalStack initialization complete!"
