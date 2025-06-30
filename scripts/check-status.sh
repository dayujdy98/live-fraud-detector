#!/bin/bash

echo "Fraud Detection System Status Check"
echo "======================================"

# Check if AWS credentials are configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "ERROR: AWS credentials not configured or expired"
    echo "Please run: aws configure"
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
    exit 1
fi

# Check EC2 instance states
echo "EC2 Instance States:"
aws ec2 describe-instances \
    --instance-ids $MLFLOW_INSTANCE_ID $FLINK_INSTANCE_ID $MONITORING_INSTANCE_ID \
    --query 'Reservations[].Instances[].[Tags[?Key==`Name`].Value|[0],State.Name,InstanceId]' \
    --output table

echo ""

# Check ECS service status
echo "ECS Service Status:"
aws ecs describe-services \
    --cluster fraud-detection-cluster \
    --services fraud-detection-api-service \
    --query 'services[0].[serviceName,status,runningCount,desiredCount]' \
    --output table

echo ""

# Check target group health
echo "Load Balancer Target Health:"
TARGET_GROUP_ARN=$(terraform output -raw target_group_arn 2>/dev/null)
if [ ! -z "$TARGET_GROUP_ARN" ]; then
    aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN \
        --query 'TargetHealthDescriptions[].[Target.Id,TargetHealth.State,TargetHealth.Description]' \
        --output table
else
    echo "Could not get target group ARN"
fi

cd ..

echo ""
echo "TEST: Quick Service Test:"
./test-complete-system.sh

echo ""
echo "Management Commands:"
echo "   Start all services: ./start-services.sh"
echo "   Stop all services: ./stop-services.sh"
echo "   Check status: ./check-status.sh"
