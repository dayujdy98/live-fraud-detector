output "s3_project_bucket_name" {
  description = "Name of the S3 bucket for data and model artifacts"
  value       = aws_s3_bucket.project_bucket.bucket
}

output "s3_project_bucket_arn" {
  description = "ARN of the S3 bucket for data and model artifacts"
  value       = aws_s3_bucket.project_bucket.arn
}

output "s3_project_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.project_bucket.bucket_domain_name
}

output "ec2_instance_id" {
  description = "ID of the EC2 instance (if created)"
  value       = var.create_ec2_instance ? aws_instance.mlflow_instance[0].id : null
}

output "ec2_instance_public_ip" {
  description = "Public IP address of the EC2 instance (if created)"
  value       = var.create_ec2_instance ? aws_eip.mlflow_eip[0].public_ip : null
}

output "ec2_instance_public_dns" {
  description = "Public DNS name of the EC2 instance (if created)"
  value       = var.create_ec2_instance ? aws_instance.mlflow_instance[0].public_dns : null
}

output "ec2_security_group_id" {
  description = "ID of the security group for EC2 instance (if created)"
  value       = var.create_ec2_instance ? aws_security_group.mlflow_sg[0].id : null
}

output "mlflow_tracking_uri" {
  description = "MLflow tracking URI for connecting to the MLflow server"
  value       = var.create_ec2_instance ? "http://${aws_eip.mlflow_eip[0].public_ip}:5000" : null
}

output "mlflow_ui_url" {
  description = "URL to access MLflow UI (if EC2 instance is created)"
  value       = var.create_ec2_instance ? "http://${aws_eip.mlflow_eip[0].public_ip}:5000" : null
}

output "mlflow_server_public_ip" {
  description = "Public IP address of the MLflow server"
  value       = var.create_ec2_instance ? aws_eip.mlflow_eip[0].public_ip : null
}

output "mlflow_server_public_dns" {
  description = "Public DNS name of the MLflow server"
  value       = var.create_ec2_instance ? aws_instance.mlflow_instance[0].public_dns : null
}

output "ssh_command" {
  description = "SSH command to connect to the MLflow server (if created)"
  value       = var.create_ec2_instance ? "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_eip.mlflow_eip[0].public_ip}" : null
}

output "mlflow_environment_setup" {
  description = "Environment variable to set MLFLOW_TRACKING_URI locally"
  value       = var.create_ec2_instance ? "export MLFLOW_TRACKING_URI=http://${aws_eip.mlflow_eip[0].public_ip}:5000" : null
}

# VPC and Networking Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

# ECR Outputs
output "ecr_repository_url" {
  description = "URL of the ECR repository for fraud detection API"
  value       = aws_ecr_repository.fraud_detection_api.repository_url
}

output "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.fraud_detection_api.arn
}

# MSK Outputs
output "msk_cluster_arn" {
  description = "ARN of the MSK cluster"
  value       = aws_msk_cluster.main.arn
}

output "msk_bootstrap_brokers_sasl_iam" {
  description = "Bootstrap brokers string for SASL/IAM authentication"
  value       = aws_msk_cluster.main.bootstrap_brokers_sasl_iam
}

output "msk_zookeeper_connect_string" {
  description = "Zookeeper connection string"
  value       = aws_msk_cluster.main.zookeeper_connect_string
}

# ECS Outputs
output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.fraud_detection_api.name
}

# Load Balancer Outputs
output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "api_url" {
  description = "URL to access the fraud detection API"
  value       = "http://${aws_lb.main.dns_name}"
}

# Docker Build and Push Instructions
output "docker_build_instructions" {
  description = "Instructions for building and pushing Docker image to ECR"
  value       = <<-EOT
    # Authenticate Docker to ECR
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.fraud_detection_api.repository_url}

    # Build Docker image
    docker build -t fraud-detection-api -f src/deployment/Dockerfile .

    # Tag the image
    docker tag fraud-detection-api:latest ${aws_ecr_repository.fraud_detection_api.repository_url}:latest

    # Push to ECR
    docker push ${aws_ecr_repository.fraud_detection_api.repository_url}:latest
  EOT
}

# Monitoring Server Outputs
output "monitoring_server_id" {
  description = "ID of the monitoring server EC2 instance"
  value       = var.create_monitoring_server ? aws_instance.monitoring_server[0].id : null
}

output "monitoring_server_public_ip" {
  description = "Public IP address of the monitoring server"
  value       = var.create_monitoring_server ? aws_eip.monitoring_eip[0].public_ip : null
}

output "monitoring_server_public_dns" {
  description = "Public DNS name of the monitoring server"
  value       = var.create_monitoring_server ? aws_instance.monitoring_server[0].public_dns : null
}

output "prometheus_ui_url" {
  description = "URL to access Prometheus UI"
  value       = var.create_monitoring_server ? "http://${aws_eip.monitoring_eip[0].public_ip}:9090" : null
}

output "grafana_ui_url" {
  description = "URL to access Grafana UI"
  value       = var.create_monitoring_server ? "http://${aws_eip.monitoring_eip[0].public_ip}:3000" : null
}

output "monitoring_ssh_command" {
  description = "SSH command to connect to the monitoring server"
  value       = var.create_monitoring_server ? "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_eip.monitoring_eip[0].public_ip}" : null
}

output "monitoring_setup_instructions" {
  description = "Instructions for setting up monitoring after deployment"
  value       = <<-EOT
    # Monitoring Server Setup Instructions

    ## Access URLs:
    - Prometheus UI: http://${var.create_monitoring_server ? aws_eip.monitoring_eip[0].public_ip : "N/A"}:9090
    - Grafana UI: http://${var.create_monitoring_server ? aws_eip.monitoring_eip[0].public_ip : "N/A"}:3000 (admin/admin123)

    ## SSH Access:
    ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${var.create_monitoring_server ? aws_eip.monitoring_eip[0].public_ip : "N/A"}
  EOT
}

# Flink Server Outputs
output "flink_instance_id" {
  description = "ID of the Flink EC2 instance"
  value       = aws_instance.flink_instance.id
}

output "flink_instance_public_ip" {
  description = "Public IP address of the Flink server"
  value       = aws_eip.flink_eip.public_ip
}

output "flink_instance_public_dns" {
  description = "Public DNS name of the Flink server"
  value       = aws_instance.flink_instance.public_dns
}

output "flink_web_ui_url" {
  description = "URL to access Flink Web UI"
  value       = "http://${aws_eip.flink_eip.public_ip}:8081"
}

output "flink_ssh_command" {
  description = "SSH command to connect to the Flink server"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_eip.flink_eip.public_ip}"
}

output "flink_setup_instructions" {
  description = "Instructions for setting up Flink after deployment"
  value       = <<-EOT
    # Flink Server Setup Instructions

    ## Access URLs:
    - Flink Web UI: http://${aws_eip.flink_eip.public_ip}:8081

    ## SSH Access:
    ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_eip.flink_eip.public_ip}
  EOT
}
