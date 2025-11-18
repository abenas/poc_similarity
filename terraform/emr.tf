# Security Group for EMR
resource "aws_security_group" "emr_master" {
  name_prefix = "${var.project_name}-emr-master-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for EMR master node"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-emr-master-sg"
  }
}

resource "aws_security_group" "emr_slave" {
  name_prefix = "${var.project_name}-emr-slave-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for EMR slave nodes"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-emr-slave-sg"
  }
}

# EMR Service Role
resource "aws_iam_role" "emr_service_role" {
  name = "${var.project_name}-emr-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "elasticmapreduce.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "emr_service_policy" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEMRServicePolicy_v2"
}

# EMR EC2 Instance Profile
resource "aws_iam_role" "emr_ec2_role" {
  name = "${var.project_name}-emr-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "emr_ec2_policy" {
  name = "${var.project_name}-emr-ec2-policy"
  role = aws_iam_role.emr_ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_source1.arn,
          "${aws_s3_bucket.data_source1.arn}/*",
          aws_s3_bucket.data_source2.arn,
          "${aws_s3_bucket.data_source2.arn}/*",
          aws_s3_bucket.results.arn,
          "${aws_s3_bucket.results.arn}/*",
          aws_s3_bucket.scripts.arn,
          "${aws_s3_bucket.scripts.arn}/*",
          aws_s3_bucket.logs.arn,
          "${aws_s3_bucket.logs.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions",
          "glue:GetPartition",
          "glue:GetDatabases",
          "glue:GetTables"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.state.arn
      },
      {
        Effect = "Allow"
        Action = [
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpGet"
        ]
        Resource = "${aws_opensearch_domain.main.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "emr_ec2_profile" {
  name = "${var.project_name}-emr-ec2-profile"
  role = aws_iam_role.emr_ec2_role.name
}

# EMR Auto Scaling Role
resource "aws_iam_role" "emr_autoscaling_role" {
  name = "${var.project_name}-emr-autoscaling-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "elasticmapreduce.amazonaws.com",
            "application-autoscaling.amazonaws.com"
          ]
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "emr_autoscaling_policy" {
  role       = aws_iam_role.emr_autoscaling_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforAutoScalingRole"
}

# EMR Cluster
resource "aws_emr_cluster" "main" {
  name          = "${var.project_name}-cluster"
  release_label = var.emr_release_label
  applications  = ["Spark", "Hadoop", "Hive", "Livy"]

  ec2_attributes {
    subnet_id                         = aws_subnet.private[0].id
    emr_managed_master_security_group = aws_security_group.emr_master.id
    emr_managed_slave_security_group  = aws_security_group.emr_slave.id
    instance_profile                  = aws_iam_instance_profile.emr_ec2_profile.arn
  }

  master_instance_group {
    instance_type  = var.emr_master_instance_type
    instance_count = 1

    ebs_config {
      size                 = 100
      type                 = "gp3"
      volumes_per_instance = 1
    }
  }

  core_instance_group {
    instance_type  = var.emr_core_instance_type
    instance_count = var.emr_core_instance_count

    ebs_config {
      size                 = 500
      type                 = "gp3"
      volumes_per_instance = 2
    }

    autoscaling_policy = var.enable_emr_autoscaling ? jsonencode({
      Constraints = {
        MinCapacity = var.emr_min_capacity
        MaxCapacity = var.emr_max_capacity
      }
      Rules = [
        {
          Name        = "ScaleUpOnYARNMemory"
          Description = "Scale up when YARN memory utilization is high"
          Action = {
            SimpleScalingPolicyConfiguration = {
              AdjustmentType         = "CHANGE_IN_CAPACITY"
              ScalingAdjustment      = 1
              CoolDown               = 300
            }
          }
          Trigger = {
            CloudWatchAlarmDefinition = {
              ComparisonOperator = "LESS_THAN"
              EvaluationPeriods  = 1
              MetricName         = "YARNMemoryAvailablePercentage"
              Namespace          = "AWS/ElasticMapReduce"
              Period             = 300
              Statistic          = "AVERAGE"
              Threshold          = 15.0
              Unit               = "PERCENT"
            }
          }
        },
        {
          Name        = "ScaleDownOnYARNMemory"
          Description = "Scale down when YARN memory utilization is low"
          Action = {
            SimpleScalingPolicyConfiguration = {
              AdjustmentType         = "CHANGE_IN_CAPACITY"
              ScalingAdjustment      = -1
              CoolDown               = 300
            }
          }
          Trigger = {
            CloudWatchAlarmDefinition = {
              ComparisonOperator = "GREATER_THAN"
              EvaluationPeriods  = 1
              MetricName         = "YARNMemoryAvailablePercentage"
              Namespace          = "AWS/ElasticMapReduce"
              Period             = 300
              Statistic          = "AVERAGE"
              Threshold          = 75.0
              Unit               = "PERCENT"
            }
          }
        }
      ]
    }) : null
  }

  configurations_json = jsonencode([
    {
      Classification = "spark"
      Properties = {
        "maximizeResourceAllocation" = "true"
      }
    },
    {
      Classification = "spark-defaults"
      Properties = {
        "spark.dynamicAllocation.enabled"          = "true"
        "spark.shuffle.service.enabled"            = "true"
        "spark.serializer"                         = "org.apache.spark.serializer.KryoSerializer"
        "spark.sql.adaptive.enabled"               = "true"
        "spark.sql.adaptive.coalescePartitions.enabled" = "true"
        "spark.speculation"                        = "true"
        "spark.sql.files.maxPartitionBytes"        = "134217728" # 128 MB
      }
    },
    {
      Classification = "spark-hive-site"
      Properties = {
        "hive.metastore.client.factory.class" = "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
      }
    }
  ])

  service_role     = aws_iam_role.emr_service_role.arn
  autoscaling_role = var.enable_emr_autoscaling ? aws_iam_role.emr_autoscaling_role.arn : null

  log_uri = "s3://${aws_s3_bucket.logs.id}/emr-logs/"

  keep_job_flow_alive_when_no_steps = true
  termination_protection            = false

  tags = {
    Name = "${var.project_name}-emr-cluster"
  }
}
