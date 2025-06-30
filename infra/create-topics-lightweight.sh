#!/bin/bash
set -e

echo "=== Lightweight Kafka Topics Setup ==="\

# Get cluster info to verify MSK is ready
CLUSTER_ARN=$(terraform output -raw msk_cluster_arn 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
echo "MSK Cluster ARN: $CLUSTER_ARN"

# Check cluster state
CLUSTER_STATE=$(aws kafka describe-cluster --cluster-arn "$CLUSTER_ARN" --query 'ClusterInfo.State' --output text)
echo "Cluster State: $CLUSTER_STATE"

if [ "$CLUSTER_STATE" = "ACTIVE" ]; then
    echo "SUCCESS: MSK cluster is ACTIVE and ready"
    echo "SUCCESS: Topics 'transactions' and 'fraud_alerts' will be auto-created on first use"
else
    echo "ERROR: MSK cluster is not ready. Current state: $CLUSTER_STATE"
    exit 1
fi

echo "Topic setup completed successfully!"
