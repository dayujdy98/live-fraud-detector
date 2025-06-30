#\!/bin/bash

echo "=== ECS Service Status ==="
aws ecs describe-services \
  --cluster $(terraform output -raw ecs_cluster_id 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g') \
  --services $(terraform output -raw ecs_service_name 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g') \
  --query 'services[0].{RunningCount:runningCount,DesiredCount:desiredCount,Status:status}' \
  --output table

echo "=== EC2 Instance Status ==="
aws ec2 describe-instances \
  --instance-ids $(terraform output -raw ec2_instance_id 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g') \
  --query 'Reservations[0].Instances[0].{State:State.Name,InstanceType:InstanceType}' \
  --output table
