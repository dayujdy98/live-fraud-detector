#!/bin/bash

echo "STOPPING: Fraud Detection System Services"
echo "==========================================="

# Check if AWS credentials are configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "ERROR: AWS credentials not configured or expired"
    echo "Run: aws configure"
    exit 1
fi

echo "SUCCESS: AWS credentials verified"
echo ""

# Get instance IDs from Terraform
echo "Getting infrastructure details..."
cd infra

MLFLOW_INSTANCE_ID=$(terraform output -raw mlflow_instance_id 2>/dev/null)
FLINK_INSTANCE_ID=$(terraform output -raw flink_instance_id 2>/dev/null)
MONITORING_INSTANCE_ID=$(terraform output -raw monitoring_instance_id 2>/dev/null)

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

# Stop ECS service first
echo "Stopping ECS service..."
aws ecs update-service \
    --cluster fraud-detection-cluster \
    --service fraud-detection-api-service \
    --desired-count 0

echo "SUCCESS: ECS service stopped"
echo ""

# Stop EC2 instances
echo "Stopping EC2 instances..."
aws ec2 stop-instances --instance-ids $MLFLOW_INSTANCE_ID $FLINK_INSTANCE_ID $MONITORING_INSTANCE_ID

echo "Waiting for instances to stop..."
aws ec2 wait instance-stopped --instance-ids $MLFLOW_INSTANCE_ID $FLINK_INSTANCE_ID $MONITORING_INSTANCE_ID

echo "SUCCESS: EC2 instances stopped"
echo ""

# Show final status
echo "Final instance states:"
aws ec2 describe-instances \
    --instance-ids $MLFLOW_INSTANCE_ID $FLINK_INSTANCE_ID $MONITORING_INSTANCE_ID \
    --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' \
    --output table

cd ..

echo ""
echo "Services stopped to save costs!"
echo "Run './start-services.sh' when you need to use the system again"
