"""
Delta Detection Lambda Function
Detects changes in S3 datasets and triggers incremental processing
"""

import boto3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
emr_client = boto3.client('emr')


def get_s3_file_metadata(bucket: str, prefix: str) -> Dict[str, Any]:
    """
    Get metadata for files in S3 bucket
    
    Args:
        bucket: S3 bucket name
        prefix: S3 prefix/path
        
    Returns:
        Dictionary with file metadata
    """
    files_metadata = {}
    
    paginator = s3_client.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                files_metadata[obj['Key']] = {
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag']
                }
    
    return files_metadata


def compute_dataset_hash(metadata: Dict[str, Any]) -> str:
    """
    Compute hash of dataset metadata for change detection
    
    Args:
        metadata: File metadata dictionary
        
    Returns:
        Hash string
    """
    # Sort by key for consistent hashing
    sorted_items = sorted(metadata.items())
    
    hash_input = json.dumps(sorted_items, sort_keys=True)
    
    return hashlib.sha256(hash_input.encode()).hexdigest()


def get_previous_state(table_name: str, dataset_id: str) -> Dict[str, Any]:
    """
    Get previous processing state from DynamoDB
    
    Args:
        table_name: DynamoDB table name
        dataset_id: Dataset identifier
        
    Returns:
        Previous state dictionary
    """
    table = dynamodb.Table(table_name)
    
    try:
        response = table.get_item(Key={'dataset_id': dataset_id})
        return response.get('Item', {})
    except Exception as e:
        print(f"Error getting previous state: {e}")
        return {}


def save_current_state(
    table_name: str,
    dataset_id: str,
    metadata_hash: str,
    metadata: Dict[str, Any]
):
    """
    Save current processing state to DynamoDB
    
    Args:
        table_name: DynamoDB table name
        dataset_id: Dataset identifier
        metadata_hash: Hash of current metadata
        metadata: Current metadata
    """
    table = dynamodb.Table(table_name)
    
    table.put_item(
        Item={
            'dataset_id': dataset_id,
            'metadata_hash': metadata_hash,
            'last_processed': datetime.utcnow().isoformat(),
            'file_count': len(metadata),
            'metadata': json.dumps(metadata)
        }
    )


def get_changed_files(
    current_metadata: Dict[str, Any],
    previous_metadata: Dict[str, Any]
) -> List[str]:
    """
    Identify changed files between current and previous state
    
    Args:
        current_metadata: Current file metadata
        previous_metadata: Previous file metadata
        
    Returns:
        List of changed file keys
    """
    changed_files = []
    
    # New or modified files
    for key, current in current_metadata.items():
        if key not in previous_metadata:
            changed_files.append(key)
        elif previous_metadata[key].get('etag') != current.get('etag'):
            changed_files.append(key)
    
    return changed_files


def trigger_emr_job(
    cluster_id: str,
    script_path: str,
    args: List[str]
) -> str:
    """
    Trigger EMR step for processing
    
    Args:
        cluster_id: EMR cluster ID
        script_path: S3 path to PySpark script
        args: Script arguments
        
    Returns:
        Step ID
    """
    step = {
        'Name': f'PersonMatching-{datetime.utcnow().isoformat()}',
        'ActionOnFailure': 'CONTINUE',
        'HadoopJarStep': {
            'Jar': 'command-runner.jar',
            'Args': [
                'spark-submit',
                '--deploy-mode', 'cluster',
                '--master', 'yarn',
                '--conf', 'spark.dynamicAllocation.enabled=true',
                '--conf', 'spark.shuffle.service.enabled=true',
                script_path
            ] + args
        }
    }
    
    response = emr_client.add_job_flow_steps(
        JobFlowId=cluster_id,
        Steps=[step]
    )
    
    return response['StepIds'][0]


def lambda_handler(event, context):
    """
    Lambda handler for delta detection and processing
    
    Expected environment variables:
        - DATASET1_BUCKET: S3 bucket for dataset 1
        - DATASET1_PREFIX: S3 prefix for dataset 1
        - DATASET2_BUCKET: S3 bucket for dataset 2
        - DATASET2_PREFIX: S3 prefix for dataset 2
        - STATE_TABLE: DynamoDB table for state tracking
        - EMR_CLUSTER_ID: EMR cluster ID
        - SCRIPT_PATH: S3 path to person_matcher.py
        - OUTPUT_BUCKET: S3 bucket for output
        - GLUE_DATABASE: Glue catalog database
        - TABLE1_NAME: Glue table name for dataset 1
        - TABLE2_NAME: Glue table name for dataset 2
    """
    
    # Get configuration from environment
    dataset1_bucket = os.environ['DATASET1_BUCKET']
    dataset1_prefix = os.environ['DATASET1_PREFIX']
    dataset2_bucket = os.environ['DATASET2_BUCKET']
    dataset2_prefix = os.environ['DATASET2_PREFIX']
    state_table = os.environ['STATE_TABLE']
    emr_cluster_id = os.environ['EMR_CLUSTER_ID']
    script_path = os.environ['SCRIPT_PATH']
    output_bucket = os.environ['OUTPUT_BUCKET']
    glue_database = os.environ['GLUE_DATABASE']
    table1_name = os.environ['TABLE1_NAME']
    table2_name = os.environ['TABLE2_NAME']
    
    print(f"Checking for changes in datasets...")
    
    # Get current metadata for both datasets
    dataset1_metadata = get_s3_file_metadata(dataset1_bucket, dataset1_prefix)
    dataset2_metadata = get_s3_file_metadata(dataset2_bucket, dataset2_prefix)
    
    # Compute hashes
    dataset1_hash = compute_dataset_hash(dataset1_metadata)
    dataset2_hash = compute_dataset_hash(dataset2_metadata)
    
    # Get previous states
    dataset1_prev = get_previous_state(state_table, 'dataset1')
    dataset2_prev = get_previous_state(state_table, 'dataset2')
    
    # Check for changes
    dataset1_changed = dataset1_hash != dataset1_prev.get('metadata_hash')
    dataset2_changed = dataset2_hash != dataset2_prev.get('metadata_hash')
    
    if not dataset1_changed and not dataset2_changed:
        print("No changes detected. Skipping processing.")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'No changes detected',
                'dataset1_hash': dataset1_hash,
                'dataset2_hash': dataset2_hash
            })
        }
    
    print(f"Changes detected - Dataset1: {dataset1_changed}, Dataset2: {dataset2_changed}")
    
    # Identify changed files
    if dataset1_changed:
        changed_files_1 = get_changed_files(
            dataset1_metadata,
            json.loads(dataset1_prev.get('metadata', '{}'))
        )
        print(f"Dataset 1 changed files: {len(changed_files_1)}")
    
    if dataset2_changed:
        changed_files_2 = get_changed_files(
            dataset2_metadata,
            json.loads(dataset2_prev.get('metadata', '{}'))
        )
        print(f"Dataset 2 changed files: {len(changed_files_2)}")
    
    # Trigger EMR job
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_path = f"s3://{output_bucket}/matches/{timestamp}/"
    
    job_args = [
        glue_database,
        table1_name,
        table2_name,
        output_path,
        '0.7'  # threshold
    ]
    
    step_id = trigger_emr_job(emr_cluster_id, script_path, job_args)
    
    print(f"Triggered EMR step: {step_id}")
    
    # Save current states
    save_current_state(state_table, 'dataset1', dataset1_hash, dataset1_metadata)
    save_current_state(state_table, 'dataset2', dataset2_hash, dataset2_metadata)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Processing triggered',
            'step_id': step_id,
            'output_path': output_path,
            'dataset1_changed': dataset1_changed,
            'dataset2_changed': dataset2_changed
        })
    }
