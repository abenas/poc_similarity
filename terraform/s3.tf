# S3 Buckets
resource "aws_s3_bucket" "data_source1" {
  bucket = "${var.project_name}-data-source1-${var.environment}"

  tags = {
    Name        = "Dataset 1 Source Bucket"
    Description = "Primary dataset for person matching"
  }
}

resource "aws_s3_bucket" "data_source2" {
  bucket = "${var.project_name}-data-source2-${var.environment}"

  tags = {
    Name        = "Dataset 2 Source Bucket"
    Description = "Secondary dataset for person matching"
  }
}

resource "aws_s3_bucket" "results" {
  bucket = "${var.project_name}-results-${var.environment}"

  tags = {
    Name        = "Matching Results Bucket"
    Description = "Stores person matching results"
  }
}

resource "aws_s3_bucket" "scripts" {
  bucket = "${var.project_name}-scripts-${var.environment}"

  tags = {
    Name        = "Scripts Bucket"
    Description = "PySpark scripts and dependencies"
  }
}

resource "aws_s3_bucket" "logs" {
  bucket = "${var.project_name}-logs-${var.environment}"

  tags = {
    Name        = "Logs Bucket"
    Description = "EMR and application logs"
  }
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "data_source1" {
  bucket = aws_s3_bucket.data_source1.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "data_source2" {
  bucket = aws_s3_bucket.data_source2.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "results" {
  bucket = aws_s3_bucket.results.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "scripts" {
  bucket = aws_s3_bucket.scripts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Public Access Block
resource "aws_s3_bucket_public_access_block" "data_source1" {
  bucket = aws_s3_bucket.data_source1.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "data_source2" {
  bucket = aws_s3_bucket.data_source2.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "results" {
  bucket = aws_s3_bucket.results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "scripts" {
  bucket = aws_s3_bucket.scripts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Lifecycle Policies
resource "aws_s3_bucket_lifecycle_configuration" "results" {
  bucket = aws_s3_bucket.results.id

  rule {
    id     = "archive-old-results"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    expiration {
      days = 90
    }
  }
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data_source1" {
  bucket = aws_s3_bucket.data_source1.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_source2" {
  bucket = aws_s3_bucket.data_source2.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "results" {
  bucket = aws_s3_bucket.results.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "scripts" {
  bucket = aws_s3_bucket.scripts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

# S3 Access Logging
resource "aws_s3_bucket_logging" "data_source1" {
  bucket = aws_s3_bucket.data_source1.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access-logs/data-source1/"
}

resource "aws_s3_bucket_logging" "data_source2" {
  bucket = aws_s3_bucket.data_source2.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access-logs/data-source2/"
}

resource "aws_s3_bucket_logging" "results" {
  bucket = aws_s3_bucket.results.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access-logs/results/"
}

resource "aws_s3_bucket_logging" "scripts" {
  bucket = aws_s3_bucket.scripts.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access-logs/scripts/"
}

# S3 Event Notifications
resource "aws_s3_bucket_notification" "data_source1_notification" {
  bucket = aws_s3_bucket.data_source1.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.delta_detector.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = ""
    filter_suffix       = ".parquet"
  }

  depends_on = [aws_lambda_permission.allow_s3_source1]
}

resource "aws_s3_bucket_notification" "data_source2_notification" {
  bucket = aws_s3_bucket.data_source2.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.delta_detector.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = ""
    filter_suffix       = ".parquet"
  }

  depends_on = [aws_lambda_permission.allow_s3_source2]
}
