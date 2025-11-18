# Security Group for OpenSearch
resource "aws_security_group" "opensearch" {
  name_prefix = "${var.project_name}-opensearch-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for OpenSearch domain"

  ingress {
    from_port = 443
    to_port   = 443
    protocol  = "tcp"
    cidr_blocks = [
      var.vpc_cidr
    ]
    description = "HTTPS from VPC"
  }

  egress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    cidr_blocks     = [var.vpc_cidr]
    description     = "HTTPS to VPC"
  }

  tags = {
    Name = "${var.project_name}-opensearch-sg"
  }
}

# Generate random password for OpenSearch master user
resource "random_password" "opensearch_master_password" {
  length  = 32
  special = true
}

# Store OpenSearch password in Secrets Manager
resource "aws_secretsmanager_secret" "opensearch_master_password" {
  name                    = "${var.project_name}-opensearch-master-password"
  kms_key_id              = aws_kms_key.secrets.arn
  recovery_window_in_days = 30
  
  tags = {
    Name = "${var.project_name}-opensearch-master-password"
  }
}

resource "aws_secretsmanager_secret_version" "opensearch_master_password" {
  secret_id     = aws_secretsmanager_secret.opensearch_master_password.id
  secret_string = random_password.opensearch_master_password.result
}

# Note: Automatic rotation requires implementing a Lambda function
# Uncomment after implementing rotation Lambda
# resource "aws_secretsmanager_secret_rotation" "opensearch_master_password" {
#   secret_id           = aws_secretsmanager_secret.opensearch_master_password.id
#   rotation_lambda_arn = aws_lambda_function.rotate_opensearch_secret.arn
#
#   rotation_rules {
#     automatically_after_days = 30
#   }
# }

# OpenSearch Service-Linked Role
data "aws_iam_policy_document" "opensearch_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["es.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# OpenSearch Domain
resource "aws_opensearch_domain" "main" {
  domain_name    = "${var.project_name}-${var.environment}"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type          = var.opensearch_instance_type
    instance_count         = var.opensearch_instance_count
    zone_awareness_enabled = true

    zone_awareness_config {
      availability_zone_count = 2
    }

    dedicated_master_enabled = true
    dedicated_master_type    = "r6g.large.search"
    dedicated_master_count   = 3
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.opensearch_ebs_volume_size
    iops        = 3000
    throughput  = 125
  }

  vpc_options {
    subnet_ids = [
      aws_subnet.private[0].id,
      aws_subnet.private[1].id
    ]
    security_group_ids = [aws_security_group.opensearch.id]
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = aws_kms_key.opensearch.arn
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = "admin"
      master_user_password = random_password.opensearch_master_password.result
    }
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_index_slow_logs.arn
    log_type                 = "INDEX_SLOW_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_search_slow_logs.arn
    log_type                 = "SEARCH_SLOW_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_application_logs.arn
    log_type                 = "ES_APPLICATION_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_audit_logs.arn
    log_type                 = "AUDIT_LOGS"
    enabled                  = true
  }

  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
    "override_main_response_version"         = "false"
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action   = "es:*"
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-${var.environment}/*"
        Condition = {
          IpAddress = {
            "aws:SourceIp" = [var.vpc_cidr]
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-opensearch"
  }
}

# CloudWatch Log Groups for OpenSearch
resource "aws_cloudwatch_log_group" "opensearch_index_slow_logs" {
  name              = "/aws/opensearch/${var.project_name}-${var.environment}/index-slow-logs"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.logs.arn

  tags = {
    Name = "${var.project_name}-opensearch-index-slow-logs"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_search_slow_logs" {
  name              = "/aws/opensearch/${var.project_name}-${var.environment}/search-slow-logs"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.logs.arn

  tags = {
    Name = "${var.project_name}-opensearch-search-slow-logs"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_application_logs" {
  name              = "/aws/opensearch/${var.project_name}-${var.environment}/application-logs"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.logs.arn

  tags = {
    Name = "${var.project_name}-opensearch-application-logs"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_audit_logs" {
  name              = "/aws/opensearch/${var.project_name}-${var.environment}/audit-logs"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.logs.arn

  tags = {
    Name = "${var.project_name}-opensearch-audit-logs"
  }
}
