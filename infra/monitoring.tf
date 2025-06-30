# Security Group for Monitoring Server
resource "aws_security_group" "monitoring_sg" {
  count       = var.create_monitoring_server ? 1 : 0
  name        = "${var.project_name}-monitoring-sg"
  description = "Security group for Prometheus and Grafana monitoring server"
  vpc_id      = aws_vpc.main.id

  # SSH access from your IP
  ingress {
    description = "SSH from authorized IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_address]
  }

  # Prometheus UI access from your IP
  ingress {
    description = "Prometheus UI from authorized IP"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_address]
  }

  # Grafana UI access from your IP
  ingress {
    description = "Grafana UI from authorized IP"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_address]
  }

  # Allow outbound traffic to ECS tasks for scraping
  egress {
    description     = "Access to ECS tasks for metrics scraping"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  # All other outbound traffic allowed
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-monitoring-sg"
    Environment = var.environment
    Purpose     = "Prometheus and Grafana monitoring server"
  }
}

# Generate random password for Grafana admin
resource "random_password" "grafana_admin_password" {
  count   = var.create_monitoring_server ? 1 : 0
  length  = 16
  special = true
}

# Store Grafana password in Systems Manager Parameter Store
resource "aws_ssm_parameter" "grafana_admin_password" {
  count = var.create_monitoring_server ? 1 : 0
  name  = "/${var.project_name}/monitoring/grafana_admin_password"
  type  = "SecureString"
  value = random_password.grafana_admin_password[0].result

  tags = {
    Name        = "${var.project_name}-grafana-admin-password"
    Environment = var.environment
    Purpose     = "Grafana admin password"
  }
}

# User data script for monitoring server
locals {
  monitoring_user_data = <<-EOF
#!/bin/bash
# Update system and install Docker and AWS CLI
yum update -y
yum install -y docker awscli
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Retrieve Grafana admin password from Parameter Store
GRAFANA_PASSWORD=$(aws ssm get-parameter --name "/${var.project_name}/monitoring/grafana_admin_password" --with-decryption --region ${var.aws_region} --query "Parameter.Value" --output text)

# Create Prometheus config directory and file
mkdir -p /etc/prometheus
cat <<'PROMETHEUS_CONFIG' > /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'fastapi_service'
    static_configs:
      - targets: ['<MANUALLY_UPDATE_FASTAPI_IP>:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
PROMETHEUS_CONFIG

# Create Prometheus data directory
mkdir -p /opt/prometheus/data

# Run Prometheus container
docker run -d \
  --name prometheus \
  --restart unless-stopped \
  -p 9090:9090 \
  -v /etc/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
  -v /opt/prometheus/data:/prometheus \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.console.libraries=/etc/prometheus/console_libraries \
  --web.console.templates=/etc/prometheus/consoles \
  --storage.tsdb.retention.time=200h \
  --web.enable-lifecycle

# Create Grafana data directory
mkdir -p /opt/grafana/data

# Run Grafana container with secure password from Parameter Store
docker run -d \
  --name grafana \
  --restart unless-stopped \
  -p 3000:3000 \
  -v /opt/grafana/data:/var/lib/grafana \
  -e "GF_SECURITY_ADMIN_PASSWORD=$GRAFANA_PASSWORD" \
  -e "GF_USERS_ALLOW_SIGN_UP=false" \
  grafana/grafana:latest

# Create a script to update Prometheus configuration
cat <<'UPDATE_SCRIPT' > /home/ec2-user/update_prometheus_config.sh
#!/bin/bash
if [ $# -eq 0 ]; then
    echo "Usage: $0 <fastapi_private_ip>"
    echo "Example: $0 10.0.1.100"
    exit 1
fi

FASTAPI_IP=$1
echo "Updating Prometheus configuration with FastAPI IP: $FASTAPI_IP"

# Update the prometheus.yml file
sed -i "s/<MANUALLY_UPDATE_FASTAPI_IP>/$FASTAPI_IP/g" /etc/prometheus/prometheus.yml

# Reload Prometheus configuration
curl -X POST http://localhost:9090/-/reload

echo "Prometheus configuration updated and reloaded successfully!"
echo "Verify target status at: http://localhost:9090/targets"
UPDATE_SCRIPT

chmod +x /home/ec2-user/update_prometheus_config.sh

# Set up basic firewall rules
systemctl enable firewalld
systemctl start firewalld
firewall-cmd --permanent --add-port=22/tcp
firewall-cmd --permanent --add-port=9090/tcp
firewall-cmd --permanent --add-port=3000/tcp
firewall-cmd --reload

echo "Monitoring server setup completed!"
echo "Prometheus UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):9090"
echo "Grafana UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):3000"
echo "Grafana credentials: admin/[password stored in AWS Parameter Store]"
echo "To retrieve Grafana password: aws ssm get-parameter --name '/${var.project_name}/monitoring/grafana_admin_password' --with-decryption --region ${var.aws_region} --query 'Parameter.Value' --output text"
echo ""
EOF
}

# IAM role for monitoring server
resource "aws_iam_role" "monitoring_server_role" {
  count = var.create_monitoring_server ? 1 : 0
  name  = "${var.project_name}-monitoring-server-role"

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
    Name        = "${var.project_name}-monitoring-server-role"
    Environment = var.environment
  }
}

# IAM policy for monitoring server to access SSM Parameter Store
resource "aws_iam_role_policy" "monitoring_server_policy" {
  count = var.create_monitoring_server ? 1 : 0
  name  = "${var.project_name}-monitoring-server-policy"
  role  = aws_iam_role.monitoring_server_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/monitoring/*"
      }
    ]
  })
}

# IAM instance profile for monitoring server
resource "aws_iam_instance_profile" "monitoring_server_profile" {
  count = var.create_monitoring_server ? 1 : 0
  name  = "${var.project_name}-monitoring-server-profile"
  role  = aws_iam_role.monitoring_server_role[0].name

  tags = {
    Name        = "${var.project_name}-monitoring-server-profile"
    Environment = var.environment
  }
}

# EC2 instance for monitoring server
resource "aws_instance" "monitoring_server" {
  count                  = var.create_monitoring_server ? 1 : 0
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.monitoring_instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.monitoring_sg[0].id]
  subnet_id              = aws_subnet.public[0].id
  iam_instance_profile   = aws_iam_instance_profile.monitoring_server_profile[0].name
  user_data              = local.monitoring_user_data

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name        = "${var.project_name}-monitoring-server"
    Environment = var.environment
    Purpose     = "Prometheus and Grafana monitoring"
  }

  depends_on = [
    aws_security_group.monitoring_sg,
    aws_security_group.ecs_tasks
  ]
}

# Elastic IP for monitoring server
resource "aws_eip" "monitoring_eip" {
  count    = var.create_monitoring_server ? 1 : 0
  instance = aws_instance.monitoring_server[0].id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-monitoring-eip"
    Environment = var.environment
  }
}
