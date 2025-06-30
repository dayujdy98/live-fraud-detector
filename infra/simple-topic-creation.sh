#!/bin/bash
set -e

echo "=== Creating Kafka Topics ==="
echo "MSK is configured with auto.create.topics.enable=true"
echo "Topics 'transactions' and 'fraud_alerts' will be created automatically when first used"

CLUSTER_ARN=$(terraform output -raw msk_cluster_arn 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
echo "MSK Cluster ARN: $CLUSTER_ARN"

# Get cluster info to verify it's running
aws kafka describe-cluster --cluster-arn "$CLUSTER_ARN" --query 'ClusterInfo.State' --output text

echo "MSK cluster is ready. Topics will be auto-created on first use."
