output "emr_cluster_id" {
  description = "EMR cluster ID"
  value       = aws_emr_cluster.main.id
}

output "emr_master_public_dns" {
  description = "EMR master node public DNS"
  value       = aws_emr_cluster.main.master_public_dns
}

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint"
  value       = aws_opensearch_domain.main.endpoint
}

output "opensearch_kibana_endpoint" {
  description = "OpenSearch Dashboards endpoint"
  value       = aws_opensearch_domain.main.dashboard_endpoint
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "s3_bucket_data_source1" {
  description = "S3 bucket for dataset 1"
  value       = aws_s3_bucket.data_source1.id
}

output "s3_bucket_data_source2" {
  description = "S3 bucket for dataset 2"
  value       = aws_s3_bucket.data_source2.id
}

output "s3_bucket_results" {
  description = "S3 bucket for results"
  value       = aws_s3_bucket.results.id
}

output "s3_bucket_scripts" {
  description = "S3 bucket for scripts"
  value       = aws_s3_bucket.scripts.id
}

output "glue_database_name" {
  description = "Glue catalog database name"
  value       = aws_glue_catalog_database.main.name
}

output "dynamodb_state_table" {
  description = "DynamoDB state tracking table"
  value       = aws_dynamodb_table.state.name
}

output "lambda_function_name" {
  description = "Lambda function name for delta detection"
  value       = aws_lambda_function.delta_detector.function_name
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}
