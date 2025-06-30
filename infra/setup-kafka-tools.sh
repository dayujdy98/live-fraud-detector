#!/bin/bash
set -e

MLFLOW_IP=$(terraform output -raw mlflow_server_public_ip 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
SSH_KEY="~/.ssh/fraud-detection-keypair-new.pem"
KAFKA_BROKERS=$(terraform output -raw msk_bootstrap_brokers_sasl_iam 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')

echo "=== Installing Kafka Tools and Creating Topics ==="
echo "MLflow IP: $MLFLOW_IP"
echo "Kafka Brokers: $KAFKA_BROKERS"

# SSH to MLflow server, install Kafka tools, and create topics
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ec2-user@$MLFLOW_IP << REMOTE_COMMANDS
# Install Java
if ! java -version 2>/dev/null; then
    echo "Installing Java..."
    sudo yum install -y java-11-amazon-corretto-headless
fi

# Download and install Kafka
if [ ! -d "/opt/kafka" ]; then
    echo "Installing Kafka tools..."
    cd /tmp
    curl -L -o kafka.tgz https://archive.apache.org/dist/kafka/2.8.2/kafka_2.13-2.8.2.tgz
    sudo mkdir -p /opt/kafka
    sudo tar -xzf kafka.tgz -C /opt/kafka --strip-components=1
    sudo chown -R ec2-user:ec2-user /opt/kafka
    rm kafka.tgz

    # Add kafka to PATH
    echo 'export PATH=/opt/kafka/bin:\$PATH' >> ~/.bashrc
    export PATH=/opt/kafka/bin:\$PATH
fi

# Ensure PATH is set
export PATH=/opt/kafka/bin:\$PATH

# Create transactions topic
echo "Creating 'transactions' topic..."
/opt/kafka/bin/kafka-topics.sh --create \
  --bootstrap-server $KAFKA_BROKERS \
  --topic transactions \
  --partitions 3 \
  --replication-factor 2 \
  --if-not-exists

# Create fraud_alerts topic
echo "Creating 'fraud_alerts' topic..."
/opt/kafka/bin/kafka-topics.sh --create \
  --bootstrap-server $KAFKA_BROKERS \
  --topic fraud_alerts \
  --partitions 3 \
  --replication-factor 2 \
  --if-not-exists

# List topics to verify
echo "Listing all topics:"
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server $KAFKA_BROKERS

REMOTE_COMMANDS

echo "Kafka tools installed and topics created successfully!"
