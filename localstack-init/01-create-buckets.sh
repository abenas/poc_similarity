#!/bin/bash

# Create S3 buckets for local testing
awslocal s3 mb s3://person-matching-data-source1-dev
awslocal s3 mb s3://person-matching-data-source2-dev
awslocal s3 mb s3://person-matching-results-dev
awslocal s3 mb s3://person-matching-scripts-dev

# Create DynamoDB table for state tracking
awslocal dynamodb create-table \
    --table-name person-matching-state \
    --attribute-definitions \
        AttributeName=dataset_id,AttributeType=S \
    --key-schema \
        AttributeName=dataset_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST

echo "LocalStack initialization complete!"
