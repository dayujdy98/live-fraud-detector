#\!/bin/bash
set -e

FLINK_IP=$(terraform output -raw flink_instance_public_ip 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
SSH_KEY="~/.ssh/fraud-detection-keypair-new.pem"
KAFKA_BROKERS=$(terraform output -raw msk_bootstrap_brokers_sasl_iam 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
API_URL=$(terraform output -raw api_url 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')

echo "=== Deploying Flink Job ==="
echo "Flink IP: $FLINK_IP"
echo "SSH Key: $SSH_KEY"

# 1. Copy Flink job to server
echo "Copying flink_job.py to Flink server..."
scp -i $SSH_KEY -o StrictHostKeyChecking=no ../src/deployment/flink_job.py ec2-user@$FLINK_IP:/tmp/
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ec2-user@$FLINK_IP "sudo mkdir -p /opt/flink/usrlib && sudo cp /tmp/flink_job.py /opt/flink/usrlib/ && sudo chown ec2-user:ec2-user /opt/flink/usrlib/flink_job.py"

# 2. Set up environment and run job
echo "Setting up environment and running Flink job..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ec2-user@$FLINK_IP << REMOTE_COMMANDS
cd /opt/flink
export KAFKA_BROKER_ADDRESS="$KAFKA_BROKERS"
export API_ENDPOINT_URL="$API_URL"
export INPUT_TOPIC="transactions"
export OUTPUT_TOPIC="fraud_alerts"
export FRAUD_THRESHOLD="0.8"

echo "Environment variables set:"
echo "KAFKA_BROKER_ADDRESS=\$KAFKA_BROKER_ADDRESS"
echo "API_ENDPOINT_URL=\$API_ENDPOINT_URL"

# Submit the Flink job
echo "Submitting Flink job..."
./bin/flink run usrlib/flink_job.py

# Check job status
echo "Checking job status..."
./bin/flink list
REMOTE_COMMANDS

echo "Flink job deployed\! Web UI: http://$FLINK_IP:8081"
