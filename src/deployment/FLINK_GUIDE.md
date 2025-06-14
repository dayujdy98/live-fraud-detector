# Flink Streaming Job Guide

This guide provides detailed information about the Flink streaming job for real-time fraud detection.

## Overview

The Flink job (`flink_job.py`) implements a real-time fraud detection pipeline that:

1. **Consumes** transaction data from Kafka
2. **Processes** each transaction through the fraud detection API
3. **Filters** high-probability fraud cases
4. **Produces** fraud alerts to another Kafka topic

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Kafka Source  │    │   FraudDetector │    │   Kafka Sink    │
│   (transactions)│───▶│   (MapFunction) │───▶│   (fraud_alerts)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   FastAPI       │
                       │   /predict      │
                       └─────────────────┘
```

## Job Components

### 1. FraudDetector MapFunction

The core processing logic is implemented in the `FraudDetector` class:

```python
class FraudDetector(MapFunction):
    def __init__(self):
        # Initialize API endpoint from environment variable
        self.api_endpoint = os.getenv('API_ENDPOINT_URL')
        self.predict_url = f"{self.api_endpoint}/predict"

    def map(self, value):
        # Convert Flink Row to dictionary
        tx_dict = value.as_dict()

        # Call fraud detection API
        response = requests.post(self.predict_url, json={"transactions": [tx_dict]})

        # Add fraud probability to transaction
        fraud_probability = response.json()['predictions'][0]
        tx_dict['fraud_probability'] = fraud_probability
        tx_dict['fraud_detected'] = fraud_probability > 0.5

        return json.dumps(tx_dict)
```

**Key Features:**

- **Error Handling**: Graceful handling of API failures
- **Timeout Management**: 10-second timeout for API calls
- **Logging**: Structured logging for monitoring
- **Flexible Output**: Returns JSON string for Kafka sink

### 2. Data Schema

The job expects transaction data with the following schema:

```python
transaction_schema = Types.ROW([
    Types.FIELD("V1", Types.FLOAT()),
    Types.FIELD("V2", Types.FLOAT()),
    # ... V3-V28
    Types.FIELD("V28", Types.FLOAT()),
    Types.FIELD("Amount", Types.FLOAT()),
    Types.FIELD("transaction_id", Types.STRING()),
    Types.FIELD("timestamp", Types.STRING())
])
```

### 3. Kafka Configuration

#### Source Configuration

```python
kafka_source = FlinkKafkaConsumer(
    topics=input_topic,
    deserializer=json_deserializer,
    properties={
        'bootstrap.servers': kafka_broker,
        'group.id': 'fraud-detection-group',
        'auto.offset.reset': 'latest',
        'enable.auto.commit': 'true'
    }
)
```

#### Sink Configuration

```python
kafka_sink = FlinkKafkaProducer(
    topic=output_topic,
    serialization_schema=SimpleStringSchema(),
    producer_config={
        'bootstrap.servers': kafka_broker,
        'transaction.timeout.ms': '900000'  # 15 minutes
    }
)
```

## Environment Variables

### Required Variables

| Variable               | Description             | Example                 |
| ---------------------- | ----------------------- | ----------------------- |
| `KAFKA_BROKER_ADDRESS` | Kafka bootstrap servers | `localhost:9092`        |
| `API_ENDPOINT_URL`     | FastAPI service URL     | `http://localhost:8000` |

### Optional Variables

| Variable          | Description                 | Default        |
| ----------------- | --------------------------- | -------------- |
| `INPUT_TOPIC`     | Input Kafka topic           | `transactions` |
| `OUTPUT_TOPIC`    | Output Kafka topic          | `fraud_alerts` |
| `FRAUD_THRESHOLD` | Fraud probability threshold | `0.8`          |

## Deployment Options

### 1. Local Development

```bash
# Install dependencies
pip install -r flink_requirements.txt

# Set environment variables
export KAFKA_BROKER_ADDRESS="localhost:9092"
export API_ENDPOINT_URL="http://localhost:8000"

# Run job
python flink_job.py
```

### 2. Docker Deployment

```bash
# Build image
docker build -t fraud-detection-flink -f Dockerfile.flink .

# Run container
docker run \
  -e KAFKA_BROKER_ADDRESS="kafka:9092" \
  -e API_ENDPOINT_URL="http://api:8000" \
  fraud-detection-flink
```

### 3. Flink Cluster Submission

#### Using Submission Script

```bash
# Make executable
chmod +x submit_flink_job.sh

# Submit job
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

### 4. AWS EMR Flink

```bash
# Create EMR cluster with Flink
aws emr create-cluster \
  --name "Fraud Detection Flink" \
  --release-label emr-6.10.0 \
  --applications Name=Flink \
  --ec2-attributes KeyName=your-key-pair \
  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m5.xlarge \
  InstanceGroupType=CORE,InstanceCount=2,InstanceType=m5.xlarge \
  --use-default-roles

# Submit job to EMR
aws emr add-steps \
  --cluster-id j-XXXXXXXXX \
  --steps Type=CUSTOM_JAR,Name="Flink Fraud Detection",Jar="command-runner.jar",Args=["flink-yarn-session","-d","-n","2","-jm","1024m","-tm","2048m"]
```

## Testing

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

### 2. Monitor Output

```bash
# Consume fraud alerts
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic fraud_alerts \
  --from-beginning
```

### 3. Check Job Status

```bash
# List running jobs
flink list

# Check job details
flink info <job-id>
```

## Performance Tuning

### 1. Parallelism

Adjust parallelism based on throughput requirements:

```python
# In flink_job.py
env.set_parallelism(4)  # Set default parallelism
```

### 2. Checkpointing

Enable checkpointing for fault tolerance:

```python
# Enable checkpointing
env.enable_checkpointing(60000)  # Checkpoint every 60 seconds
```

### 3. Backpressure Handling

Monitor backpressure in Flink Web UI and adjust:

- Increase parallelism
- Optimize API response times
- Add buffering if needed

## Monitoring

### 1. Flink Web UI

Access at `http://localhost:8081` to monitor:

- Job status and metrics
- Task manager health
- Checkpoint status
- Backpressure indicators

### 2. Metrics

Key metrics to monitor:

- **Throughput**: Records processed per second
- **Latency**: End-to-end processing time
- **Error Rate**: Failed API calls
- **Backpressure**: Processing bottlenecks

### 3. Logs

Monitor logs for:

- API call failures
- Kafka connectivity issues
- Processing errors
- Performance warnings

## Troubleshooting

### Common Issues

#### 1. Job Fails to Start

**Symptoms**: Job fails during initialization

**Causes**:

- Missing environment variables
- Kafka connectivity issues
- API endpoint not accessible

**Solutions**:

```bash
# Check environment variables
echo $KAFKA_BROKER_ADDRESS
echo $API_ENDPOINT_URL

# Test Kafka connectivity
kafka-console-consumer --bootstrap-server $KAFKA_BROKER_ADDRESS --topic transactions --max-messages 1

# Test API connectivity
curl $API_ENDPOINT_URL/health
```

#### 2. High API Latency

**Symptoms**: Slow processing, backpressure

**Causes**:

- API server overload
- Network latency
- Large request volume

**Solutions**:

- Scale API instances
- Implement API caching
- Add request batching
- Optimize model inference

#### 3. No Fraud Alerts

**Symptoms**: No output in fraud_alerts topic

**Causes**:

- Fraud threshold too high
- API returning low probabilities
- Filtering logic issues

**Solutions**:

```bash
# Check fraud threshold
echo $FRAUD_THRESHOLD

# Test API with known fraudulent data
curl -X POST $API_ENDPOINT_URL/predict \
  -H "Content-Type: application/json" \
  -d '{"transactions":[{"V1":-4.0,"V2":-3.0,"V3":-2.0,"Amount":1500.0}]}'
```

#### 4. Memory Issues

**Symptoms**: OutOfMemoryError, task manager failures

**Causes**:

- Insufficient memory allocation
- Memory leaks in processing
- Large state size

**Solutions**:

- Increase task manager memory
- Enable garbage collection monitoring
- Optimize state management

## Production Considerations

### 1. High Availability

- Use Flink HA mode with multiple JobManagers
- Enable checkpointing with external storage
- Deploy across multiple availability zones

### 2. Scaling

- Horizontal scaling: Add more TaskManagers
- Vertical scaling: Increase memory/CPU per task
- Auto-scaling: Use Kubernetes or EMR auto-scaling

### 3. Security

- Enable SSL/TLS for Kafka connections
- Implement API authentication
- Use VPC and security groups
- Encrypt data in transit and at rest

### 4. Monitoring

- Set up CloudWatch alarms
- Use Flink metrics with Prometheus
- Implement custom metrics
- Set up alerting for failures

## Cost Optimization

### 1. Resource Allocation

- Right-size TaskManager memory and CPU
- Use spot instances for development
- Implement auto-scaling based on load

### 2. Storage

- Use cost-effective checkpoint storage
- Implement data retention policies
- Compress Kafka messages

### 3. Network

- Minimize cross-AZ data transfer
- Use VPC endpoints for AWS services
- Optimize API call patterns

## Integration with AWS

### 1. Amazon MSK

```bash
# Get MSK bootstrap brokers
aws kafka get-bootstrap-brokers --cluster-arn <cluster-arn>

# Use SASL/IAM authentication
export KAFKA_BROKER_ADDRESS="<bootstrap-brokers-sasl-iam>"
```

### 2. ECS Fargate API

```bash
# Get API endpoint from ALB
export API_ENDPOINT_URL="http://<alb-dns-name>"
```

### 3. CloudWatch Logs

```python
# Configure logging to CloudWatch
import boto3
import logging
from pythonjsonlogger import jsonlogger

# Set up CloudWatch logger
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

## Best Practices

### 1. Error Handling

- Implement retry logic for API calls
- Use dead letter queues for failed records
- Log errors with context information

### 2. Performance

- Use async HTTP clients for API calls
- Implement connection pooling
- Batch API requests when possible

### 3. Monitoring

- Set up comprehensive metrics
- Implement health checks
- Use distributed tracing

### 4. Testing

- Unit test individual components
- Integration test with real Kafka
- Load test with realistic data volumes

## Example Configurations

### Development

```bash
export KAFKA_BROKER_ADDRESS="localhost:9092"
export API_ENDPOINT_URL="http://localhost:8000"
export FRAUD_THRESHOLD="0.8"
export INPUT_TOPIC="transactions"
export OUTPUT_TOPIC="fraud_alerts"
```

### Production

```bash
export KAFKA_BROKER_ADDRESS="b-1.fraud-detection-msk.abc123.c2.kafka.us-east-1.amazonaws.com:9098"
export API_ENDPOINT_URL="https://fraud-detection-api.example.com"
export FRAUD_THRESHOLD="0.9"
export INPUT_TOPIC="production-transactions"
export OUTPUT_TOPIC="production-fraud-alerts"
```
