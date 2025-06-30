#!/bin/bash
set -e

echo "Stopping AWS Services to Reduce Costs..."
echo "========================================"

# Get resource IDs from terraform outputs
echo "Getting resource IDs..."
CLUSTER_ARN=$(terraform output -raw ecs_cluster_arn 2>/dev/null)
SERVICE_NAME=$(terraform output -raw ecs_service_name 2>/dev/null)
EC2_INSTANCE_ID=$(terraform output -raw ec2_instance_id 2>/dev/null)
FLINK_INSTANCE_ID=$(terraform output -raw flink_instance_id 2>/dev/null)
MONITORING_INSTANCE_ID=$(terraform output -raw monitoring_server_id 2>/dev/null)

echo "Found resources:"
echo "  ECS Cluster: $CLUSTER_ARN"
echo "  ECS Service: $SERVICE_NAME"
echo "  MLflow Instance: $EC2_INSTANCE_ID"
echo "  Flink Instance: $FLINK_INSTANCE_ID"
echo "  Monitoring Instance: $MONITORING_INSTANCE_ID"

echo ""
echo "Stopping ECS service (scale to 0)..."
aws ecs update-service \
  --cluster "$CLUSTER_ARN" \
  --service "$SERVICE_NAME" \
  --desired-count 0

echo "ECS service scaled to 0"

echo ""
echo "Stopping EC2 instances..."

# Stop MLflow server
if [ ! -z "$EC2_INSTANCE_ID" ]; then
    echo "  Stopping MLflow server ($EC2_INSTANCE_ID)..."
    aws ec2 stop-instances --instance-ids "$EC2_INSTANCE_ID"
fi

# Stop Flink server
if [ ! -z "$FLINK_INSTANCE_ID" ]; then
    echo "  Stopping Flink server ($FLINK_INSTANCE_ID)..."
    aws ec2 stop-instances --instance-ids "$FLINK_INSTANCE_ID"
fi

# Stop monitoring server
if [ ! -z "$MONITORING_INSTANCE_ID" ]; then
    echo "  Stopping monitoring server ($MONITORING_INSTANCE_ID)..."
    aws ec2 stop-instances --instance-ids "$MONITORING_INSTANCE_ID"
fi

echo ""
echo "All services stopped successfully!"
echo ""
echo "To restart: Run './start-services.sh'"
echo "To permanently delete: Run 'terraform destroy'"
