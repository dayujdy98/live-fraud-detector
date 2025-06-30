# Example Terraform variables file

# AWS Configuration
aws_region  = "us-east-1"
environment = "dev"

# Project Configuration
project_name = "fraud-detection"

# S3 Bucket Name
# Add a timestamp or random suffix to ensure uniqueness
project_bucket_name = "live-fraud-detector-terraform-state-1750547046"

# EC2 Configuration
create_ec2_instance      = true
ec2_instance_type        = "t2.micro"
flink_instance_type      = "t3.medium"
monitoring_instance_type = "t3.medium"

# AWS Key Pair
# Create this in the AWS Console or via CLI before running terraform
key_pair_name = "fraud-detection-keypair-new"

# Your IP address for SSH access
# Format: "xxx.xxx.xxx.xxx/32" (the /32 means only your exact IP)
my_ip_address = "151.205.96.121/32"

# Networking Configuration
vpc_cidr_block       = "10.0.0.0/16"
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]

# MSK Configuration
msk_broker_instance_type = "kafka.t3.small"
msk_broker_count         = 2
msk_storage_size         = 20

# ECS Configuration
ecs_task_cpu              = "512"
ecs_task_memory           = "1024"
ecs_service_desired_count = 2

# Monitoring Configuration
create_monitoring_server = true

# Terraform State Configuration
terraform_state_bucket         = "live-fraud-detector-terraform-state-1750547046"
terraform_state_key            = "fraud-detection/terraform.tfstate"
terraform_state_region         = "us-east-1"
terraform_state_dynamodb_table = "terraform-state-lock"
