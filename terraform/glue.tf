# Glue Catalog Database
resource "aws_glue_catalog_database" "main" {
  name        = var.glue_database_name
  description = "Person data catalog for matching pipeline"

  tags = {
    Name = "${var.project_name}-glue-database"
  }
}

# Glue Crawler IAM Role
resource "aws_iam_role" "glue_crawler" {
  name = "${var.project_name}-glue-crawler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service_policy" {
  role       = aws_iam_role.glue_crawler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_access" {
  name = "${var.project_name}-glue-s3-policy"
  role = aws_iam_role.glue_crawler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_source1.arn,
          "${aws_s3_bucket.data_source1.arn}/*",
          aws_s3_bucket.data_source2.arn,
          "${aws_s3_bucket.data_source2.arn}/*",
          aws_s3_bucket.results.arn,
          "${aws_s3_bucket.results.arn}/*"
        ]
      }
    ]
  })
}

# Glue Security Configuration
resource "aws_glue_security_configuration" "main" {
  name = "${var.project_name}-glue-security-config"

  encryption_configuration {
    cloudwatch_encryption {
      cloudwatch_encryption_mode = "SSE-KMS"
      kms_key_arn                = aws_kms_key.logs.arn
    }

    job_bookmarks_encryption {
      job_bookmarks_encryption_mode = "CSE-KMS"
      kms_key_arn                   = aws_kms_key.s3.arn
    }

    s3_encryption {
      s3_encryption_mode = "SSE-KMS"
      kms_key_arn        = aws_kms_key.s3.arn
    }
  }
}

# Glue Crawler for Dataset 1
resource "aws_glue_crawler" "dataset1" {
  name               = "${var.project_name}-dataset1-crawler"
  role               = aws_iam_role.glue_crawler.arn
  database_name      = aws_glue_catalog_database.main.name
  security_configuration = aws_glue_security_configuration.main.name

  s3_target {
    path = "s3://${aws_s3_bucket.data_source1.id}/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
  })

  tags = {
    Name = "${var.project_name}-dataset1-crawler"
  }
}

# Glue Crawler for Dataset 2
resource "aws_glue_crawler" "dataset2" {
  name               = "${var.project_name}-dataset2-crawler"
  role               = aws_iam_role.glue_crawler.arn
  database_name      = aws_glue_catalog_database.main.name
  security_configuration = aws_glue_security_configuration.main.name

  s3_target {
    path = "s3://${aws_s3_bucket.data_source2.id}/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
  })

  tags = {
    Name = "${var.project_name}-dataset2-crawler"
  }
}

# Glue Crawler for Results
resource "aws_glue_crawler" "results" {
  name               = "${var.project_name}-results-crawler"
  role               = aws_iam_role.glue_crawler.arn
  database_name      = aws_glue_catalog_database.main.name
  security_configuration = aws_glue_security_configuration.main.name

  s3_target {
    path = "s3://${aws_s3_bucket.results.id}/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
  })

  tags = {
    Name = "${var.project_name}-results-crawler"
  }
}
