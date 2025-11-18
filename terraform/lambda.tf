# Lambda Execution Role
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_source1.arn,
          "${aws_s3_bucket.data_source1.arn}/*",
          aws_s3_bucket.data_source2.arn,
          "${aws_s3_bucket.data_source2.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.state.arn
      },
      {
        Effect = "Allow"
        Action = [
          "elasticmapreduce:AddJobFlowSteps",
          "elasticmapreduce:DescribeCluster",
          "elasticmapreduce:ListSteps"
        ]
        Resource = aws_emr_cluster.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda Function for Delta Detection
resource "aws_lambda_function" "delta_detector" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-delta-detector"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "delta_detector.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 300
  memory_size     = 512

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DATASET1_BUCKET  = aws_s3_bucket.data_source1.id
      DATASET1_PREFIX  = ""
      DATASET2_BUCKET  = aws_s3_bucket.data_source2.id
      DATASET2_PREFIX  = ""
      STATE_TABLE      = aws_dynamodb_table.state.name
      EMR_CLUSTER_ID   = aws_emr_cluster.main.id
      SCRIPT_PATH      = "s3://${aws_s3_bucket.scripts.id}/person_matcher.py"
      OUTPUT_BUCKET    = aws_s3_bucket.results.id
      GLUE_DATABASE    = aws_glue_catalog_database.main.name
      TABLE1_NAME      = "dataset1"
      TABLE2_NAME      = "dataset2"
    }
  }

  tags = {
    Name = "${var.project_name}-delta-detector"
  }
}

# Archive Lambda code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambdas/delta_detector.py"
  output_path = "${path.module}/lambda_function.zip"
}

# Security Group for Lambda
resource "aws_security_group" "lambda" {
  name_prefix = "${var.project_name}-lambda-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for Lambda functions"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-lambda-sg"
  }
}

# CloudWatch Event Rule for scheduled execution
resource "aws_cloudwatch_event_rule" "lambda_schedule" {
  name                = "${var.project_name}-lambda-schedule"
  description         = "Trigger Lambda function on schedule"
  schedule_expression = var.lambda_schedule_expression

  tags = {
    Name = "${var.project_name}-lambda-schedule"
  }
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.lambda_schedule.name
  target_id = "DeltaDetectorLambda"
  arn       = aws_lambda_function.delta_detector.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delta_detector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedule.arn
}

# Lambda permissions for S3
resource "aws_lambda_permission" "allow_s3_source1" {
  statement_id  = "AllowExecutionFromS3Source1"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delta_detector.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_source1.arn
}

resource "aws_lambda_permission" "allow_s3_source2" {
  statement_id  = "AllowExecutionFromS3Source2"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delta_detector.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_source2.arn
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.delta_detector.function_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-lambda-logs"
  }
}
