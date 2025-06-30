variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_bucket_name" {
  description = "Name of the S3 bucket for data and model artifacts storage"
  type        = string
  # Example: "fraud-detection-data-artifacts-dev-20241201"
  # Note: S3 bucket names must be globally unique
}

variable "key_pair_name" {
  description = "Name of the AWS key pair for EC2 instance access (must exist in AWS)"
  type        = string
  # Example: "my-fraud-detection-keypair"
}

variable "my_ip_address" {
  description = "Your IP address for SSH access to EC2 instance (CIDR format)"
  type        = string
  # Example: "123.456.789.0/32"
}

variable "create_ec2_instance" {
  description = "Whether to create EC2 instance for MLflow/Bastion host"
  type        = bool
  default     = true
}

variable "ec2_instance_type" {
  description = "EC2 instance type for MLflow server"
  type        = string
  default     = "t2.micro"
}

variable "flink_instance_type" {
  description = "EC2 instance type for Flink streaming job server"
  type        = string
  default     = "t3.medium"
}

variable "monitoring_instance_type" {
  description = "EC2 instance type for monitoring server (Prometheus/Grafana)"
  type        = string
  default     = "t3.medium"
}

variable "project_name" {
  description = "Name of the project for resource naming"
  type        = string
  default     = "fraud-detection"
}

variable "mlflow_server_ami" {
  description = "AMI ID for MLflow server (defaults to latest Amazon Linux 2)"
  type        = string
  default     = ""
}

variable "your_ip_for_ssh_mlflow" {
  description = "Your IP address for SSH access to MLflow server (CIDR format)"
  type        = string
  default     = ""
}

variable "vpc_cidr_block" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "msk_broker_instance_type" {
  description = "MSK broker instance type"
  type        = string
  default     = "kafka.t3.small"
}

variable "msk_broker_count" {
  description = "Number of MSK broker nodes"
  type        = number
  default     = 2
}

variable "msk_storage_size" {
  description = "Storage size in GB for MSK brokers"
  type        = number
  default     = 20
}

variable "ecs_task_cpu" {
  description = "CPU units for ECS task (1024 = 1 vCPU)"
  type        = string
  default     = "512"
}

variable "ecs_task_memory" {
  description = "Memory for ECS task in MiB"
  type        = string
  default     = "1024"
}

variable "ecs_service_desired_count" {
  description = "Desired number of ECS service tasks"
  type        = number
  default     = 2
}

variable "create_monitoring_server" {
  description = "Whether to create monitoring server (Prometheus/Grafana)"
  type        = bool
  default     = true
}

variable "terraform_state_bucket" {
  description = "S3 bucket name for Terraform state storage"
  type        = string
  default     = "your-terraform-state-bucket"
}

variable "terraform_state_key" {
  description = "S3 key for Terraform state file"
  type        = string
  default     = "fraud-detection/terraform.tfstate"
}

variable "terraform_state_region" {
  description = "AWS region for Terraform state bucket"
  type        = string
  default     = "us-east-1"
}

variable "terraform_state_dynamodb_table" {
  description = "DynamoDB table name for Terraform state locking"
  type        = string
  default     = "terraform-state-lock"
}
