#!/bin/bash

# Log all output for debugging
exec > >(tee /var/log/user-data.log) 2>&1

# Update the system
yum update -y

# Install Python 3 and pip
yum install -y python3 python3-pip git unzip

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws/

# Install MLflow and dependencies with specific versions for stability
pip3 install mlflow==2.8.1 boto3 gunicorn psycopg2-binary

# Create MLflow directories
mkdir -p /opt/mlflow/metadata
mkdir -p /home/ec2-user/mlflow
chown -R ec2-user:ec2-user /opt/mlflow
chown -R ec2-user:ec2-user /home/ec2-user/mlflow

# Create systemd service for MLflow
cat > /etc/systemd/system/mlflow.service << EOF
[Unit]
Description=MLflow Tracking Server
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/mlflow
Environment=AWS_DEFAULT_REGION=${aws_region}
Environment=MLFLOW_BACKEND_STORE_URI=sqlite:////opt/mlflow/metadata/mlflow.db
Environment=MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://${bucket_name}/mlflow-artifacts
ExecStart=/usr/local/bin/mlflow server --backend-store-uri sqlite:////opt/mlflow/metadata/mlflow.db --default-artifact-root s3://${bucket_name}/mlflow-artifacts --host 0.0.0.0 --port 5000 --serve-artifacts
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start MLflow service
systemctl daemon-reload
systemctl enable mlflow
systemctl start mlflow

# Install htop for monitoring
yum install -y htop

# Wait for MLflow service to be ready
sleep 30

# Create a welcome message
cat > /etc/motd << EOF

====================================
  Fraud Detection MLflow Server
====================================

This instance is configured with:
- MLflow tracking server running on port 5000
- AWS CLI v2
- Docker
- Python 3 with pip
- SQLite backend store
- S3 artifact storage

MLflow UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000
S3 Bucket: ${bucket_name}
Backend Store: sqlite:////opt/mlflow/metadata/mlflow.db
Artifact Root: s3://${bucket_name}/mlflow-artifacts

Configuration for local development:
export MLFLOW_TRACKING_URI=http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000

====================================

EOF

# Create MLflow configuration info file
cat > /home/ec2-user/mlflow-info.txt << EOF
MLflow Server Configuration
===========================

Tracking URI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000
Backend Store: sqlite:////opt/mlflow/metadata/mlflow.db
Artifact Root: s3://${bucket_name}/mlflow-artifacts
AWS Region: ${aws_region}

Local Environment Setup:
export MLFLOW_TRACKING_URI=http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000

Python Usage:
import mlflow
mlflow.set_tracking_uri("http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000")
EOF

chown ec2-user:ec2-user /home/ec2-user/mlflow-info.txt

# Log the completion
echo "User data script completed successfully at $(date)" >> /var/log/user-data.log
echo "MLflow server setup complete. Service status:" >> /var/log/user-data.log
systemctl status mlflow >> /var/log/user-data.log
