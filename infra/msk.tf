# WARNING: MSK can be expensive. Use t3.small brokers and tear down after use.

# Security Group for MSK Cluster
resource "aws_security_group" "msk" {
  name_prefix = "${var.project_name}-msk-"
  description = "Security group for MSK cluster"
  vpc_id      = aws_vpc.main.id

  # Kafka broker port
  ingress {
    from_port   = 9092
    to_port     = 9092
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Kafka broker access"
  }

  # Kafka broker TLS port
  ingress {
    from_port   = 9094
    to_port     = 9094
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Kafka broker TLS access"
  }

  # Kafka broker SASL/IAM port
  ingress {
    from_port   = 9098
    to_port     = 9098
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Kafka broker SASL/IAM access"
  }

  # Zookeeper port
  ingress {
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Zookeeper access"
  }

  # JMX port for monitoring
  ingress {
    from_port   = 11001
    to_port     = 11002
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "JMX monitoring"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-msk-sg"
    Environment = var.environment
    Purpose     = "MSK cluster security group"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# CloudWatch Log Group for MSK
resource "aws_cloudwatch_log_group" "msk" {
  name              = "/aws/msk/${var.project_name}-cluster"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-msk-logs"
    Environment = var.environment
  }
}

# MSK Configuration
resource "aws_msk_configuration" "main" {
  kafka_versions = ["3.4.0"]
  name           = "${var.project_name}-msk-config"

  server_properties = <<PROPERTIES
auto.create.topics.enable=true
default.replication.factor=${var.msk_broker_count}
min.insync.replicas=1
num.partitions=3
log.retention.hours=168
log.retention.bytes=1073741824
PROPERTIES

  description = "MSK configuration for ${var.project_name}"
}

# MSK Cluster
resource "aws_msk_cluster" "main" {
  cluster_name           = "${var.project_name}-msk-cluster"
  kafka_version          = "3.4.0"
  number_of_broker_nodes = var.msk_broker_count
  configuration_info {
    arn      = aws_msk_configuration.main.arn
    revision = aws_msk_configuration.main.latest_revision
  }

  broker_node_group_info {
    instance_type   = var.msk_broker_instance_type
    client_subnets  = aws_subnet.private[*].id
    security_groups = [aws_security_group.msk.id]
    storage_info {
      ebs_storage_info {
        volume_size = var.msk_storage_size
      }
    }
  }

  client_authentication {
    sasl {
      iam = true
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk.name
      }
    }
  }

  tags = {
    Name        = "${var.project_name}-msk-cluster"
    Environment = var.environment
    Purpose     = "Kafka cluster for fraud detection streaming"
    # Cost warning tag
    CostOptimization = "Use t3.small instances - tear down after use"
  }
}

# IAM role for MSK client access
resource "aws_iam_role" "msk_client_role" {
  name = "${var.project_name}-msk-client-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "ec2.amazonaws.com",
            "ecs-tasks.amazonaws.com"
          ]
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-msk-client-role"
    Environment = var.environment
  }
}

# IAM policy for MSK client access
resource "aws_iam_role_policy" "msk_client_policy" {
  name = "${var.project_name}-msk-client-policy"
  role = aws_iam_role.msk_client_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kafka-cluster:Connect",
          "kafka-cluster:AlterCluster",
          "kafka-cluster:DescribeCluster"
        ]
        Resource = aws_msk_cluster.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kafka-cluster:*Topic*",
          "kafka-cluster:WriteData",
          "kafka-cluster:ReadData"
        ]
        Resource = "${aws_msk_cluster.main.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kafka-cluster:AlterGroup",
          "kafka-cluster:DescribeGroup"
        ]
        Resource = "${aws_msk_cluster.main.arn}/*"
      }
    ]
  })
}
