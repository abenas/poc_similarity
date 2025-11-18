# Security Group for ElastiCache
resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-redis-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for Redis cluster"

  ingress {
    from_port = 6379
    to_port   = 6379
    protocol  = "tcp"
    cidr_blocks = [
      var.vpc_cidr
    ]
    description = "Redis from VPC"
  }

  egress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    cidr_blocks     = [var.vpc_cidr]
    description     = "Redis to VPC"
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}

# Generate random password for Redis auth token
resource "random_password" "redis_auth_token" {
  length  = 32
  special = true
}

# Store auth token in Secrets Manager
resource "aws_secretsmanager_secret" "redis_auth_token" {
  name                    = "${var.project_name}-redis-auth-token"
  kms_key_id              = aws_kms_key.secrets.arn
  recovery_window_in_days = 30
  
  tags = {
    Name = "${var.project_name}-redis-auth-token"
  }
}

resource "aws_secretsmanager_secret_version" "redis_auth_token" {
  secret_id     = aws_secretsmanager_secret.redis_auth_token.id
  secret_string = random_password.redis_auth_token.result
}

# Note: Automatic rotation requires implementing a Lambda function
# Uncomment after implementing rotation Lambda
# resource "aws_secretsmanager_secret_rotation" "redis_auth_token" {
#   secret_id           = aws_secretsmanager_secret.redis_auth_token.id
#   rotation_lambda_arn = aws_lambda_function.rotate_redis_secret.arn
#
#   rotation_rules {
#     automatically_after_days = 30
#   }
# }

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

# ElastiCache Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  name   = "${var.project_name}-redis-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = {
    Name = "${var.project_name}-redis-params"
  }
}

# ElastiCache Replication Group (Redis Cluster)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${var.project_name}-redis"
  description                = "Redis cluster for person matching cache"
  engine                     = "redis"
  engine_version             = "7.0"
  node_type                  = var.elasticache_node_type
  num_cache_clusters         = var.elasticache_num_cache_nodes
  parameter_group_name       = aws_elasticache_parameter_group.main.name
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.redis.id]
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  at_rest_encryption_enabled = true
  kms_key_id                = aws_kms_key.elasticache.arn
  transit_encryption_enabled = true
  auth_token                = random_password.redis_auth_token.result

  snapshot_retention_limit = 5
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"

  auto_minor_version_upgrade = true

  tags = {
    Name = "${var.project_name}-redis-cluster"
  }
}
