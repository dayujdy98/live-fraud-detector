#!/bin/bash

# Submit Flink Job Script
# This script helps submit the fraud detection Flink job to a Flink cluster

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "flink_job.py" ]; then
    print_error "Please run this script from the src/deployment/ directory"
    exit 1
fi

# Get configuration from environment variables or prompt user
FLINK_JOBMANAGER_HOST=${FLINK_JOBMANAGER_HOST:-"localhost"}
FLINK_JOBMANAGER_PORT=${FLINK_JOBMANAGER_PORT:-"8081"}
KAFKA_BROKER_ADDRESS=${KAFKA_BROKER_ADDRESS:-""}
API_ENDPOINT_URL=${API_ENDPOINT_URL:-""}

# Prompt for missing required variables
if [ -z "$KAFKA_BROKER_ADDRESS" ]; then
    echo -n "Enter Kafka broker address (e.g., localhost:9092): "
    read KAFKA_BROKER_ADDRESS
fi

if [ -z "$API_ENDPOINT_URL" ]; then
    echo -n "Enter API endpoint URL (e.g., http://localhost:8000): "
    read API_ENDPOINT_URL
fi

# Validate inputs
if [ -z "$KAFKA_BROKER_ADDRESS" ] || [ -z "$API_ENDPOINT_URL" ]; then
    print_error "Kafka broker address and API endpoint URL are required"
    exit 1
fi

print_status "Submitting Flink job with configuration:"
echo "  Flink JobManager: ${FLINK_JOBMANAGER_HOST}:${FLINK_JOBMANAGER_PORT}"
echo "  Kafka Broker: $KAFKA_BROKER_ADDRESS"
echo "  API Endpoint: $API_ENDPOINT_URL"

# Set additional environment variables
export INPUT_TOPIC=${INPUT_TOPIC:-"transactions"}
export OUTPUT_TOPIC=${OUTPUT_TOPIC:-"fraud_alerts"}
export FRAUD_THRESHOLD=${FRAUD_THRESHOLD:-"0.8"}

print_status "Using topics: $INPUT_TOPIC -> $OUTPUT_TOPIC"
print_status "Fraud threshold: $FRAUD_THRESHOLD"

# Check if Flink is accessible
print_status "Checking Flink cluster connectivity..."
if ! curl -s "http://${FLINK_JOBMANAGER_HOST}:${FLINK_JOBMANAGER_PORT}" > /dev/null; then
    print_error "Cannot connect to Flink JobManager at ${FLINK_JOBMANAGER_HOST}:${FLINK_JOBMANAGER_PORT}"
    print_error "Make sure Flink is running and accessible"
    exit 1
fi

# Submit the job using Flink CLI
print_status "Submitting Flink job..."

# Create a temporary properties file for the job
PROPERTIES_FILE=$(mktemp)
cat > "$PROPERTIES_FILE" << EOF
# Flink Job Properties
jobmanager.rpc.address: ${FLINK_JOBMANAGER_HOST}
jobmanager.rpc.port: ${FLINK_JOBMANAGER_PORT}
parallelism.default: 2
taskmanager.numberOfTaskSlots: 2
EOF

# Submit the job
flink run \
    --jobmanager ${FLINK_JOBMANAGER_HOST}:${FLINK_JOBMANAGER_PORT} \
    --python flink_job.py \
    --properties "$PROPERTIES_FILE" \
    --env KAFKA_BROKER_ADDRESS="$KAFKA_BROKER_ADDRESS" \
    --env API_ENDPOINT_URL="$API_ENDPOINT_URL" \
    --env INPUT_TOPIC="$INPUT_TOPIC" \
    --env OUTPUT_TOPIC="$OUTPUT_TOPIC" \
    --env FRAUD_THRESHOLD="$FRAUD_THRESHOLD"

# Clean up
rm -f "$PROPERTIES_FILE"

print_status "Flink job submitted successfully!"
print_status "Monitor the job at: http://${FLINK_JOBMANAGER_HOST}:${FLINK_JOBMANAGER_PORT}"
