#\!/bin/bash
set -e

MLFLOW_IP=$(terraform output -raw mlflow_server_public_ip 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
SSH_KEY="~/.ssh/fraud-detection-keypair-new.pem"
KAFKA_BROKERS=$(terraform output -raw msk_bootstrap_brokers_sasl_iam 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')

echo "=== Creating Kafka Topics ==="
echo "MLflow IP: $MLFLOW_IP"
echo "Kafka Brokers: $KAFKA_BROKERS"

# SSH to MLflow server and create topics
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ec2-user@$MLFLOW_IP << REMOTE_COMMANDS
# Create transactions topic
echo "Creating 'transactions' topic..."
kafka-topics.sh --create \
  --bootstrap-server $KAFKA_BROKERS \
  --topic transactions \
  --partitions 3 \
  --replication-factor 2

# Create fraud_alerts topic
echo "Creating 'fraud_alerts' topic..."
kafka-topics.sh --create \
  --bootstrap-server $KAFKA_BROKERS \
  --topic fraud_alerts \
  --partitions 3 \
  --replication-factor 2

# List topics to verify
echo "Listing all topics:"
kafka-topics.sh --list --bootstrap-server $KAFKA_BROKERS
REMOTE_COMMANDS

echo "Kafka topics created successfully\!"
