# DynamoDB Table for State Tracking
resource "aws_dynamodb_table" "state" {
  name           = "${var.project_name}-state"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "dataset_id"

  attribute {
    name = "dataset_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb.arn
  }

  tags = {
    Name = "${var.project_name}-state-table"
  }
}

# DynamoDB Table for Deduplication
resource "aws_dynamodb_table" "dedup" {
  name           = "${var.project_name}-dedup"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "match_key"

  attribute {
    name = "match_key"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb.arn
  }

  tags = {
    Name = "${var.project_name}-dedup-table"
  }
}
