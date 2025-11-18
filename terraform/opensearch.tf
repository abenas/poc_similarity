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
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-opensearch-sg"
  }
}

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
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
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
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-opensearch-index-slow-logs"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_search_slow_logs" {
  name              = "/aws/opensearch/${var.project_name}-${var.environment}/search-slow-logs"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-opensearch-search-slow-logs"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_application_logs" {
  name              = "/aws/opensearch/${var.project_name}-${var.environment}/application-logs"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-opensearch-application-logs"
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
