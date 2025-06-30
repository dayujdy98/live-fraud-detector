#!/bin/bash

echo "Starting Fraud Detection System Services"
echo "==========================================="

# Check if AWS credentials are configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "ERROR: AWS credentials not configured or expired"
    echo "Please run: aws configure"
    echo "Enter your AWS Access Key ID, Secret Access Key, and region (us-east-1)"
    exit 1
fi

echo "SUCCESS: AWS credentials verified"
echo ""

# Get instance IDs from Terraform
echo "Getting infrastructure details..."
cd infra

MLFLOW_INSTANCE_ID=$(terraform output -raw ec2_instance_id 2>/dev/null)
FLINK_INSTANCE_ID=$(terraform output -raw flink_instance_id 2>/dev/null)
MONITORING_INSTANCE_ID=$(terraform output -raw monitoring_server_id 2>/dev/null)

if [ -z "$MLFLOW_INSTANCE_ID" ] || [ -z "$FLINK_INSTANCE_ID" ] || [ -z "$MONITORING_INSTANCE_ID" ]; then
    echo "ERROR: Could not get instance IDs from Terraform"
    echo "Make sure you're in the project directory and Terraform is initialized"
    exit 1
fi

echo "Instance IDs found:"
echo "   MLflow: $MLFLOW_INSTANCE_ID"
echo "   Flink: $FLINK_INSTANCE_ID"
echo "   Monitoring: $MONITORING_INSTANCE_ID"
echo ""

# Check current instance states
echo "Checking current instance states..."
aws ec2 describe-instances \
    --instance-ids $MLFLOW_INSTANCE_ID $FLINK_INSTANCE_ID $MONITORING_INSTANCE_ID \
    --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' \
    --output table

echo ""

# Start EC2 instances if they're stopped
echo "Starting EC2 instances..."
aws ec2 start-instances --instance-ids $MLFLOW_INSTANCE_ID $FLINK_INSTANCE_ID $MONITORING_INSTANCE_ID

echo "Waiting for instances to start (this may take 2-3 minutes)..."
aws ec2 wait instance-running --instance-ids $MLFLOW_INSTANCE_ID $FLINK_INSTANCE_ID $MONITORING_INSTANCE_ID

echo "SUCCESS: EC2 instances are running"
echo ""

# Start ECS service
echo "Starting ECS service..."
aws ecs update-service \
    --cluster fraud-detection-cluster \
    --service fraud-detection-api-service \
    --desired-count 1

echo "Waiting for ECS service to be stable (this may take 2-3 minutes)..."
aws ecs wait services-stable \
    --cluster fraud-detection-cluster \
    --services fraud-detection-api-service

echo "SUCCESS: ECS service is running"
echo ""

# Wait additional time for services to fully initialize
echo "Waiting for services to fully initialize (60 seconds)..."
sleep 60

cd ..

# Test the system
echo "TEST: Running system health check..."
./test-complete-system.sh

echo ""
echo "Service startup complete!"
echo ""
echo "Access URLs:"
echo "   API Documentation: http://fraud-detection-alb-1804403570.us-east-1.elb.amazonaws.com/docs"
echo "   Flink Dashboard: http://13.219.130.248:8081"
echo "   MLflow UI: http://52.203.174.199:5000"
echo "   Grafana Dashboard: http://18.211.164.129:3000 (admin/admin123)"
echo "   Prometheus: http://18.211.164.129:9090"
