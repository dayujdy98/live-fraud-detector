# Data Ingestion Module

This module contains scripts for data ingestion and streaming in the fraud detection system.

## Components

### 1. Kafka Producer (`kafka_producer.py`)

Streams credit card transactions from a CSV file to a Kafka topic for real-time processing.

#### Features:

- **Configurable via Environment Variables**: Kafka brokers, topics, delays, etc.
- **Multiple Data Sources**: Local CSV files, S3 downloads
- **Realistic Simulation**: Uses Time column from dataset for realistic timing
- **Robust Error Handling**: Graceful shutdown, connection retries
- **Comprehensive Logging**: Detailed logging with configurable levels
- **Command Line Interface**: Override environment variables via CLI arguments

#### Usage:

```bash
# Basic usage with default configuration
python src/ingestion/kafka_producer.py

# With custom parameters
python src/ingestion/kafka_producer.py \
  --data-path data/raw/transactions.csv \
  --topic fraud-transactions \
  --delay 0.05 \
  --loop \
  --use-time-column

# Background streaming
nohup python src/ingestion/kafka_producer.py --loop > producer.log 2>&1 &
```

#### Configuration:

Create a `.env` file in the project root:

```bash
# Copy the example file
cp env.example .env

# Edit with your settings
nano .env
```

Key environment variables:

- `KAFKA_BROKER_ADDRESS`: Kafka broker addresses (default: localhost:9092)
- `KAFKA_TRANSACTIONS_TOPIC`: Kafka topic name (default: transactions)
- `TRANSACTION_DATA_PATH`: Path to CSV file (default: data/raw/transactions.csv)
- `STREAM_DELAY_SECONDS`: Delay between messages (default: 0.1)
- `LOOP_DATASET`: Loop through dataset continuously (default: false)
- `USE_TIME_COLUMN`: Use Time column for realistic timing (default: false)

### 2. Data Downloader (`download_data.py`)

Downloads the Credit Card Fraud Detection dataset from various sources.

#### Features:

- **Multiple Sources**: S3, public URLs, sample data generation
- **Automatic Fallback**: Tries S3 → Public URL → Sample data
- **S3 Integration**: Downloads from configured S3 bucket
- **Sample Data**: Creates synthetic data for testing

#### Usage:

```bash
# Download dataset (tries all methods)
python src/ingestion/download_data.py

# The script will:
# 1. Try downloading from S3 (if S3_BUCKET_NAME is configured)
# 2. Try downloading from public URL
# 3. Create sample data for testing
```

#### Configuration for S3:

```bash
# In .env file
S3_BUCKET_NAME=your-fraud-detection-bucket
S3_DATA_KEY=raw/creditcard.csv
AWS_REGION=us-east-1
```

## Quick Start

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Environment**:

   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start Kafka** (if running locally):

   ```bash
   # Using Docker Compose
   docker-compose up kafka zookeeper

   # Or using Confluent Platform
   confluent local services start
   ```

4. **Download Data**:

   ```bash
   python src/ingestion/download_data.py
   ```

5. **Start Producer**:
   ```bash
   python src/ingestion/kafka_producer.py
   ```

## Kafka Setup

### Local Kafka with Docker

Create a `docker-compose.yml` file:

```yaml
version: "3.8"
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

Start with:

```bash
docker-compose up -d
```

### Create Topic

```bash
# Create the transactions topic
kafka-topics --create --topic transactions --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

# List topics
kafka-topics --list --bootstrap-server localhost:9092

# Monitor messages
kafka-console-consumer --topic transactions --bootstrap-server localhost:9092 --from-beginning
```

## Monitoring

### Producer Metrics

The producer logs key metrics:

- Messages sent per second
- Connection status
- Error rates
- Fraud transaction detection

### Kafka Monitoring

```bash
# Check topic details
kafka-topics --describe --topic transactions --bootstrap-server localhost:9092

# Monitor consumer lag
kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group fraud-detection-group

# View recent messages
kafka-console-consumer --topic transactions --bootstrap-server localhost:9092 --max-messages 10
```

## Message Format

Each transaction message contains:

```json
{
  "transaction_id": "txn_0000000001",
  "timestamp": 1701234567890,
  "producer_id": "kafka_producer_v1",
  "Time": 0.0,
  "V1": -1.359807134,
  "V2": -0.072781173,
  "V3": 2.536346738,
  // ... V4-V28 (PCA components)
  "Amount": 149.62,
  "Class": 0
}
```

Where:

- `transaction_id`: Unique identifier for the transaction
- `timestamp`: Current timestamp when message was sent
- `producer_id`: Identifier for the producer instance
- `Time`: Original time from dataset (seconds elapsed)
- `V1-V28`: PCA-transformed features (anonymized)
- `Amount`: Transaction amount
- `Class`: Fraud label (0=normal, 1=fraud)

## Troubleshooting

### Common Issues

1. **Kafka Connection Failed**:

   - Check if Kafka is running: `docker ps` or `jps -l`
   - Verify broker address in `.env` file
   - Check network connectivity

2. **File Not Found**:

   - Run the download script: `python src/ingestion/download_data.py`
   - Check file path in `TRANSACTION_DATA_PATH`
   - Verify file permissions

3. **Import Errors**:

   - Install dependencies: `pip install -r requirements.txt`
   - Check Python version (requires 3.7+)

4. **AWS/S3 Errors**:
   - Configure AWS credentials: `aws configure`
   - Check bucket permissions
   - Verify bucket name and region

### Logs

Check logs for detailed error information:

- Producer logs: `logs/kafka_producer.log`
- Console output for real-time monitoring

### Performance Tuning

For high throughput:

```bash
# In .env file
KAFKA_BATCH_SIZE=32768
KAFKA_LINGER_MS=5
STREAM_DELAY_SECONDS=0.01
```

For realistic simulation:

```bash
USE_TIME_COLUMN=true
STREAM_DELAY_SECONDS=0.1
```

## Next Steps

After setting up the producer:

1. Set up Kafka consumers for real-time processing
2. Implement fraud detection models
3. Add monitoring and alerting
4. Scale to multiple producers/consumers
