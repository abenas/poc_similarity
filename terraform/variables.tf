variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "person-matching"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "emr_release_label" {
  description = "EMR release version"
  type        = string
  default     = "emr-7.0.0"
}

variable "emr_master_instance_type" {
  description = "EMR master node instance type"
  type        = string
  default     = "m5.xlarge"
}

variable "emr_core_instance_type" {
  description = "EMR core node instance type"
  type        = string
  default     = "m5.2xlarge"
}

variable "emr_core_instance_count" {
  description = "Number of EMR core nodes"
  type        = number
  default     = 3
}

variable "opensearch_instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "r6g.xlarge.search"
}

variable "opensearch_instance_count" {
  description = "Number of OpenSearch data nodes"
  type        = number
  default     = 3
}

variable "opensearch_ebs_volume_size" {
  description = "EBS volume size for OpenSearch (GB)"
  type        = number
  default     = 100
}

variable "elasticache_node_type" {
  description = "ElastiCache node type for Redis"
  type        = string
  default     = "cache.r6g.xlarge"
}

variable "elasticache_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 2
}

variable "glue_database_name" {
  description = "Glue catalog database name"
  type        = string
  default     = "person_data"
}

variable "lambda_schedule_expression" {
  description = "CloudWatch Events schedule expression for Lambda trigger"
  type        = string
  default     = "rate(6 hours)"  # Run 4 times per day
}

variable "matching_threshold" {
  description = "Similarity threshold for matching (0-1)"
  type        = number
  default     = 0.7
}

variable "enable_emr_autoscaling" {
  description = "Enable EMR autoscaling"
  type        = bool
  default     = true
}

variable "emr_min_capacity" {
  description = "Minimum EMR capacity for autoscaling"
  type        = number
  default     = 2
}

variable "emr_max_capacity" {
  description = "Maximum EMR capacity for autoscaling"
  type        = number
  default     = 10
}
