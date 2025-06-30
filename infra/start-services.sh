#!/bin/bash
set -e

echo "Getting resource IDs..."
CLUSTER_ID=$(terraform output -raw ecs_cluster_id 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
SERVICE_NAME=$(terraform output -raw ecs_service_name 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
INSTANCE_ID=$(terraform output -raw ec2_instance_id 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')

echo "Starting EC2 instance..."
aws ec2 start-instances --instance-ids "$INSTANCE_ID"

echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

echo "Starting ECS service..."
aws ecs update-service \
  --cluster "$CLUSTER_ID" \
  --service "$SERVICE_NAME" \
  --desired-count 2

echo "Services started. API will be available in ~2 minutes."
