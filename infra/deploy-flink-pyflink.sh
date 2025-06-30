#!/bin/bash
set -e

FLINK_IP=$(terraform output -raw flink_instance_public_ip 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
SSH_KEY="~/.ssh/fraud-detection-keypair-new.pem"
KAFKA_BROKERS=$(terraform output -raw msk_bootstrap_brokers_sasl_iam 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
API_URL=$(terraform output -raw api_url 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')

echo "=== Deploying Flink Job with PyFlink (Memory Optimized) ==="
echo "Flink IP: $FLINK_IP"
echo "SSH Key: $SSH_KEY"

# 1. Copy Flink job to server
echo "Copying flink_job.py to Flink server..."
scp -i $SSH_KEY -o StrictHostKeyChecking=no ../src/deployment/flink_job.py ec2-user@$FLINK_IP:/tmp/

# 2. Set up PyFlink environment with memory optimizations
echo "Setting up PyFlink environment with memory optimizations..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ec2-user@$FLINK_IP << REMOTE_COMMANDS
# Install Python dependencies with compatible versions for older OpenSSL
if ! python3 -c "import pyflink" 2>/dev/null; then
    echo "Installing PyFlink with compatible dependencies..."
    # Install urllib3 1.x for OpenSSL 1.0.2 compatibility
    pip3 install --user "urllib3<2.0" "requests<2.29"
    # Install PyFlink without apache-beam to avoid conflicts
    pip3 install --user "apache-flink==1.18.1" --no-deps
    # Install only essential PyFlink dependencies
    pip3 install --user py4j cloudpickle typing-extensions
fi

# Set up environment variables
export KAFKA_BROKER_ADDRESS="$KAFKA_BROKERS"
export API_ENDPOINT_URL="$API_URL"
export INPUT_TOPIC="transactions"
export OUTPUT_TOPIC="fraud_alerts"
export FRAUD_THRESHOLD="0.8"

# Memory optimization for Python process
export PYTHONHASHSEED=0
export MALLOC_ARENA_MAX=2

echo "Environment variables set:"
echo "KAFKA_BROKER_ADDRESS=\$KAFKA_BROKER_ADDRESS"
echo "API_ENDPOINT_URL=\$API_ENDPOINT_URL"

# Create a wrapper script to run with reduced memory usage
cat > /tmp/run_flink_job.py << 'PYTHON_SCRIPT'
import os
import gc
import sys

# Optimize memory usage
gc.set_threshold(700, 10, 10)  # Reduce GC frequency

# Set JVM options for lower memory usage
os.environ['FLINK_ENV_JAVA_OPTS'] = '-Xmx512m -Xms256m'

# Import and run the job
sys.path.insert(0, '/tmp')
from flink_job import run_flink_job

if __name__ == "__main__":
    run_flink_job()
PYTHON_SCRIPT

# Run the job with memory optimizations
echo "Running Flink job with PyFlink..."
cd /opt/flink
python3 -O /tmp/run_flink_job.py

REMOTE_COMMANDS

echo "Flink job deployed with PyFlink! Web UI: http://$FLINK_IP:8081"
