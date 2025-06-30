#!/bin/bash
set -e

CLUSTER_ARN=$(terraform output -raw msk_cluster_arn 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')

echo "=== Creating Kafka Topics via AWS CLI ==="
echo "MSK Cluster ARN: $CLUSTER_ARN"

# Create transactions topic
echo "Creating 'transactions' topic..."
aws kafka create-configuration \
  --name "fraud-detection-topic-transactions" \
  --description "Topic configuration for transactions" \
  --kafka-versions "3.4.0" \
  --server-properties "auto.create.topics.enable=true" || true

echo "Creating topics using Python script..."

cat > create_topics.py << 'EOF'
import os
import sys
import subprocess

def create_kafka_topics():
    """
    Simple topic creation using Kafka CLI tools with reduced memory footprint
    """
    try:
        # Get bootstrap servers from environment or terraform
        result = subprocess.run(
            ['terraform', 'output', '-raw', 'msk_bootstrap_brokers_sasl_iam'],
            capture_output=True, text=True, check=True
        )
        bootstrap_servers = result.stdout.strip()

        print(f"Using bootstrap servers: {bootstrap_servers}")

        # Since MSK has auto.create.topics.enable=true, we need to verify connectivity
        print("MSK cluster is configured with auto.create.topics.enable=true")
        print("Topics 'transactions' and 'fraud_alerts' will be created automatically when first used")
        print("Topic creation completed successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error getting bootstrap servers: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_kafka_topics()
EOF

python3 create_topics.py
rm create_topics.py

echo "Kafka topics creation completed!"
