# Data source for Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Use provided AMI or default to latest Amazon Linux 2
locals {
  mlflow_ami = var.mlflow_server_ami != "" ? var.mlflow_server_ami : data.aws_ami.amazon_linux.id
  ssh_ip     = var.your_ip_for_ssh_mlflow != "" ? var.your_ip_for_ssh_mlflow : var.my_ip_address
}

# S3 bucket for data and model artifacts
resource "aws_s3_bucket" "project_bucket" {
  bucket = var.project_bucket_name

  tags = {
    Name        = "${var.project_name}-data-bucket"
    Purpose     = "Data and model artifacts storage"
    Environment = var.environment
  }
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "project_bucket_versioning" {
  bucket = aws_s3_bucket.project_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "project_bucket_encryption" {
  bucket = aws_s3_bucket.project_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "project_bucket_pab" {
  bucket = aws_s3_bucket.project_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Security group for MLflow EC2 instance
resource "aws_security_group" "mlflow_sg" {
  count       = var.create_ec2_instance ? 1 : 0
  name        = "${var.project_name}-mlflow-server-sg"
  description = "Security group for MLflow tracking server"
  vpc_id      = aws_vpc.main.id

  # SSH access from your IP
  ingress {
    description = "SSH from authorized IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.ssh_ip]
  }

  # MLflow UI/API access from your IP
  ingress {
    description = "MLflow UI/API from authorized IP"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = [local.ssh_ip]
  }

  # MLflow access from VPC
  ingress {
    description = "MLflow UI/API from VPC"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  # All outbound traffic allowed
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-mlflow-server-sg"
    Environment = var.environment
    Purpose     = "MLflow tracking server security group"
  }
}

# IAM role for MLflow EC2 instance
resource "aws_iam_role" "ec2_role" {
  count = var.create_ec2_instance ? 1 : 0
  name  = "${var.project_name}-mlflow-server-role"

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

  tags = {
    Name        = "${var.project_name}-mlflow-server-role"
    Environment = var.environment
    Purpose     = "MLflow tracking server IAM role"
  }
}

# IAM policy for MLflow S3 access
resource "aws_iam_role_policy" "ec2_s3_policy" {
  count = var.create_ec2_instance ? 1 : 0
  name  = "${var.project_name}-mlflow-s3-policy"
  role  = aws_iam_role.ec2_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.project_bucket.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.project_bucket.arn}/mlflow-artifacts/*"
      }
    ]
  })
}

# IAM policy for CloudWatch Logs access
resource "aws_iam_role_policy" "ec2_cloudwatch_policy" {
  count = var.create_ec2_instance ? 1 : 0
  name  = "${var.project_name}-mlflow-cloudwatch-policy"
  role  = aws_iam_role.ec2_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}

# IAM instance profile for MLflow server
resource "aws_iam_instance_profile" "ec2_profile" {
  count = var.create_ec2_instance ? 1 : 0
  name  = "${var.project_name}-mlflow-server-profile"
  role  = aws_iam_role.ec2_role[0].name
}

# EC2 instance for MLflow tracking server
resource "aws_instance" "mlflow_instance" {
  count                  = var.create_ec2_instance ? 1 : 0
  ami                    = local.mlflow_ami
  instance_type          = var.ec2_instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.mlflow_sg[0].id]
  subnet_id              = aws_subnet.public[0].id
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile[0].name

  # User data script to set up MLflow server
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    bucket_name = aws_s3_bucket.project_bucket.bucket
    aws_region  = var.aws_region
  }))

  tags = {
    Name        = "${var.project_name}-mlflow-server"
    Environment = var.environment
    Purpose     = "MLflow tracking server"
    Service     = "mlflow"
  }
}

# Elastic IP for MLflow server (for stable public IP)
resource "aws_eip" "mlflow_eip" {
  count    = var.create_ec2_instance ? 1 : 0
  instance = aws_instance.mlflow_instance[0].id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-mlflow-server-eip"
    Environment = var.environment
    Purpose     = "MLflow tracking server static IP"
  }
}
