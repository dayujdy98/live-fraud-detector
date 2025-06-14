# Fraud Detection System Deployment

This directory contains the complete fraud detection system including the FastAPI application and Flink streaming job for real-time fraud detection.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Transaction   │    │   Flink Job     │    │   Fraud Alerts  │
│   Generator     │───▶│   (Streaming)   │───▶│   (Kafka Topic) │
│   (Kafka Prod)  │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   FastAPI       │
                       │   (ML Model)    │
                       │                 │
                       └─────────────────┘
```

## Files

### API Components

- `app.py` - Main FastAPI application
- `deployment_requirements.txt` - Production dependencies
- `Dockerfile` - Container configuration for API
- `example_usage.py` - Example API usage script
- `.dockerignore` - Docker build exclusions

### Streaming Components

- `flink_job.py` - Flink streaming job for real-time processing
- `flink_requirements.txt` - Flink job dependencies
- `Dockerfile.flink` - Container configuration for Flink job
- `submit_flink_job.sh` - Script to submit Flink job to cluster
- `generate_test_data.py` - Test data generator for Kafka

## Quick Start

### 1. Local Development

#### API Setup

```bash
# Install dependencies
pip install -r deployment_requirements.txt

# Set environment variables
export MLFLOW_TRACKING_URI="your_mlflow_tracking_uri"

# Run the application
python app.py
```

#### Flink Job Setup

```bash
# Install Flink dependencies
pip install -r flink_requirements.txt

# Set environment variables
export KAFKA_BROKER_ADDRESS="localhost:9092"
export API_ENDPOINT_URL="http://localhost:8000"

# Run Flink job locally
python flink_job.py
```

### 2. Docker Deployment

#### API Deployment

```bash
# Build the Docker image
docker build -t fraud-detection-api -f src/deployment/Dockerfile .

# Run the container
docker run -p 8000:8000 \
  -e MLFLOW_TRACKING_URI="your_mlflow_tracking_uri" \
  fraud-detection-api
```

#### Flink Job Deployment

```bash
# Build Flink job image
docker build -t fraud-detection-flink -f src/deployment/Dockerfile.flink .

# Run Flink job container
docker run \
  -e KAFKA_BROKER_ADDRESS="kafka:9092" \
  -e API_ENDPOINT_URL="http://api:8000" \
  fraud-detection-flink
```

### 3. Complete System with Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: "3.8"
services:
  # FastAPI Service
  fraud-detection-api:
    build:
      context: .
      dockerfile: src/deployment/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - MLFLOW_TRACKING_URI=http://mlflow:5000
    depends_on:
      - mlflow
    restart: unless-stopped

  # Flink Job
  fraud-detection-flink:
    build:
      context: .
      dockerfile: src/deployment/Dockerfile.flink
    environment:
      - KAFKA_BROKER_ADDRESS=kafka:9092
      - API_ENDPOINT_URL=http://fraud-detection-api:8000
      - INPUT_TOPIC=transactions
      - OUTPUT_TOPIC=fraud_alerts
      - FRAUD_THRESHOLD=0.8
    depends_on:
      - fraud-detection-api
      - kafka
    restart: unless-stopped

  # Kafka
  kafka:
    image: confluentinc/cp-kafka:7.3.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    depends_on:
      - zookeeper

  # Zookeeper
  zookeeper:
    image: confluentinc/cp-zookeeper:7.3.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  # MLflow
  mlflow:
    image: python:3.9-slim
    command: >
      bash -c "pip install mlflow boto3 &&
               mlflow server --host 0.0.0.0 --port 5000"
    ports:
      - "5000:5000"
    volumes:
      - mlflow_data:/mlflow
    restart: unless-stopped

volumes:
  mlflow_data:
```

## Flink Streaming Job

### Job Overview

The Flink job (`flink_job.py`) implements a real-time fraud detection pipeline:

1. **Kafka Source**: Consumes transaction data from `transactions` topic
2. **Fraud Detection**: Calls FastAPI to get fraud probability
3. **Filtering**: Filters transactions above fraud threshold
4. **Kafka Sink**: Produces fraud alerts to `fraud_alerts` topic

### Environment Variables

#### Required

- `KAFKA_BROKER_ADDRESS` - Kafka bootstrap servers (e.g., "localhost:9092")
- `API_ENDPOINT_URL` - FastAPI service URL (e.g., "http://localhost:8000")

#### Optional

- `INPUT_TOPIC` - Input Kafka topic (default: "transactions")
- `OUTPUT_TOPIC` - Output Kafka topic (default: "fraud_alerts")
- `FRAUD_THRESHOLD` - Fraud probability threshold (default: 0.8)

### Submitting to Flink Cluster

#### Using the Submission Script

```bash
# Make script executable
chmod +x submit_flink_job.sh

# Submit job with environment variables
export KAFKA_BROKER_ADDRESS="localhost:9092"
export API_ENDPOINT_URL="http://localhost:8000"
./submit_flink_job.sh
```

#### Manual Submission

```bash
# Set environment variables
export KAFKA_BROKER_ADDRESS="localhost:9092"
export API_ENDPOINT_URL="http://localhost:8000"
export INPUT_TOPIC="transactions"
export OUTPUT_TOPIC="fraud_alerts"
export FRAUD_THRESHOLD="0.8"

# Submit to Flink cluster
flink run \
  --jobmanager localhost:8081 \
  --python flink_job.py \
  --env KAFKA_BROKER_ADDRESS="$KAFKA_BROKER_ADDRESS" \
  --env API_ENDPOINT_URL="$API_ENDPOINT_URL" \
  --env INPUT_TOPIC="$INPUT_TOPIC" \
  --env OUTPUT_TOPIC="$OUTPUT_TOPIC" \
  --env FRAUD_THRESHOLD="$FRAUD_THRESHOLD"
```

### Job Configuration

The Flink job includes:

- **Parallelism**: Default 2 (configurable)
- **Checkpointing**: Enabled for fault tolerance
- **Error Handling**: Graceful handling of API failures
- **Logging**: Structured logging for monitoring

## Testing the System

### 1. Generate Test Data

```bash
# Generate 100 transactions with 10% fraud ratio
python generate_test_data.py \
  --bootstrap-servers localhost:9092 \
  --topic transactions \
  --count 100 \
  --interval 1.0 \
  --fraud-ratio 0.1
```

### 2. Monitor Fraud Alerts

```bash
# Consume fraud alerts from Kafka
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic fraud_alerts \
  --from-beginning
```

### 3. Test API Directly

```bash
# Test the API with sample data
python example_usage.py
```

## API Endpoints

### Health Check

- `GET /` - Basic status check
- `GET /health` - Detailed health information

### Prediction

- `POST /predict` - Predict fraud probability for transactions

#### Request Format

```json
{
  "transactions": [
    {
      "V1": -1.36, "V2": -0.07, ..., "V28": -0.02,
      "Amount": 149.62
    }
  ]
}
```

#### Response Format

```json
{
  "predictions": [0.1234]
}
```

## Data Flow

### Transaction Processing Pipeline

1. **Input**: Transaction data arrives in Kafka `transactions` topic
2. **Processing**: Flink job consumes and processes each transaction
3. **ML Prediction**: FastAPI returns fraud probability
4. **Filtering**: High-probability fraud cases are filtered
5. **Output**: Fraud alerts sent to Kafka `fraud_alerts` topic

### Data Schema

#### Input Transaction Schema

```json
{
  "V1": -1.36, "V2": -0.07, ..., "V28": -0.02,
  "Amount": 149.62,
  "transaction_id": "uuid-string",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### Output Fraud Alert Schema

```json
{
  "V1": -1.36, "V2": -0.07, ..., "V28": -0.02,
  "Amount": 149.62,
  "transaction_id": "uuid-string",
  "timestamp": "2024-01-01T12:00:00",
  "fraud_probability": 0.95,
  "fraud_detected": true
}
```

## Monitoring and Troubleshooting

### Flink Job Monitoring

1. **Flink Web UI**: Access at `http://localhost:8081`
2. **Job Metrics**: Monitor throughput, latency, and error rates
3. **Logs**: Check Flink task manager logs for errors

### API Monitoring

1. **Health Checks**: Use `/health` endpoint
2. **Logs**: Monitor application logs for API errors
3. **Metrics**: Track request latency and success rates

### Common Issues

#### Flink Job Fails to Start

- Check Kafka connectivity
- Verify API endpoint is accessible
- Ensure all environment variables are set

#### High API Latency

- Check MLflow model loading
- Monitor API server resources
- Consider scaling API instances

#### No Fraud Alerts

- Verify fraud threshold setting
- Check if transactions are being processed
- Monitor API response times

## Production Deployment

### AWS Infrastructure

Use the Terraform configuration in `../infra/` to deploy:

1. **ECR Repository**: Store Docker images
2. **ECS Fargate**: Run FastAPI service
3. **Amazon MSK**: Kafka cluster for streaming
4. **Application Load Balancer**: Public API endpoint

### Deployment Steps

1. **Deploy Infrastructure**:

   ```bash
   cd ../infra/
   terraform apply
   ```

2. **Deploy API**:

   ```bash
   ./deploy-api.sh
   ```

3. **Deploy Flink Job**:
   ```bash
   # Submit to EMR Flink or standalone Flink cluster
   ./submit_flink_job.sh
   ```

### Scaling Considerations

1. **API Scaling**: Use ECS auto-scaling based on CPU/memory
2. **Flink Scaling**: Adjust parallelism based on throughput
3. **Kafka Scaling**: Add more brokers for higher throughput
4. **Monitoring**: Set up CloudWatch alarms and dashboards

## Security

1. **Network Security**: Use VPC and security groups
2. **Authentication**: Implement API authentication
3. **Encryption**: Enable TLS for all communications
4. **IAM**: Use least privilege access policies

## Cost Optimization

1. **MSK**: Use t3.small instances for development
2. **ECS**: Right-size CPU and memory allocation
3. **Flink**: Use spot instances where possible
4. **Monitoring**: Set up cost alerts and budgets
