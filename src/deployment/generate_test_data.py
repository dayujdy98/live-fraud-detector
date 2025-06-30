#!/usr/bin/env python3
"""
Test Data Generator for Fraud Detection Flink Job

This script generates sample transaction data and sends it to Kafka
for testing the fraud detection streaming pipeline.
"""

import argparse
import json
import logging
import random
import time
import uuid
from datetime import datetime

from kafka import KafkaProducer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_transaction():
    """
    Generate a sample transaction with realistic feature values.

    Returns:
        dict: Transaction data with V1-V28 features and Amount
    """
    # Generate realistic feature values (based on typical credit card transaction patterns)
    transaction = {}

    # V1-V28 features (anonymized credit card transaction features)
    for i in range(1, 29):
        # Generate values that mimic real transaction features
        # Some features have different distributions to simulate real patterns
        if i in [1, 2, 3, 4, 5]:  # First few features often have higher variance
            transaction[f"V{i}"] = round(random.uniform(-3, 3), 6)
        elif i in [6, 7, 8, 9, 10]:  # Middle features
            transaction[f"V{i}"] = round(random.uniform(-2, 2), 6)
        elif i in [11, 12, 13, 14, 15]:  # Features that might indicate fraud
            transaction[f"V{i}"] = round(random.uniform(-1.5, 1.5), 6)
        else:  # Remaining features
            transaction[f"V{i}"] = round(random.uniform(-1, 1), 6)

    # Amount (realistic transaction amounts)
    # Most transactions are small, some are larger
    if random.random() < 0.8:  # 80% small transactions
        transaction["Amount"] = round(random.uniform(1, 100), 2)
    else:  # 20% larger transactions
        transaction["Amount"] = round(random.uniform(100, 1000), 2)

    # Add metadata
    transaction["transaction_id"] = str(uuid.uuid4())
    transaction["timestamp"] = datetime.now().isoformat()

    return transaction


def generate_fraudulent_transaction():
    """
    Generate a transaction that is likely to be flagged as fraudulent.

    Returns:
        dict: Transaction data with suspicious patterns
    """
    transaction = {}

    # Generate features that might indicate fraud
    # High values in certain features that are often associated with fraud
    for i in range(1, 29):
        if i in [1, 2, 3]:  # Features often associated with fraud
            transaction[f"V{i}"] = round(random.uniform(-4, -2), 6)  # Negative values
        elif i in [4, 5, 6]:  # More suspicious patterns
            transaction[f"V{i}"] = round(
                random.uniform(2, 4), 6
            )  # High positive values
        elif i in [7, 8, 9, 10]:  # Unusual patterns
            transaction[f"V{i}"] = round(random.uniform(-3, -1), 6)
        else:
            transaction[f"V{i}"] = round(random.uniform(-2, 2), 6)

    # Large amount (often associated with fraud)
    transaction["Amount"] = round(random.uniform(500, 2000), 2)

    # Add metadata
    transaction["transaction_id"] = str(uuid.uuid4())
    transaction["timestamp"] = datetime.now().isoformat()

    return transaction


def send_to_kafka(producer, topic, transaction):
    """
    Send transaction data to Kafka topic.

    Args:
        producer: KafkaProducer instance
        topic: Kafka topic name
        transaction: Transaction data dictionary
    """
    try:
        # Convert transaction to JSON string
        message = json.dumps(transaction)

        # Send to Kafka
        producer.send(topic, message.encode("utf-8"))
        producer.flush()

        logger.info(
            f"Sent transaction {transaction['transaction_id']} to topic {topic}"
        )

    except Exception as e:
        logger.error(f"Error sending transaction to Kafka: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate test transaction data for Kafka"
    )
    parser.add_argument(
        "--bootstrap-servers",
        default="localhost:9092",
        help="Kafka bootstrap servers (default: localhost:9092)",
    )
    parser.add_argument(
        "--topic",
        default="transactions",
        help="Kafka topic name (default: transactions)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of transactions to generate (default: 100)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Interval between transactions in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--fraud-ratio",
        type=float,
        default=0.1,
        help="Ratio of fraudulent transactions (default: 0.1)",
    )

    args = parser.parse_args()

    logger.info("Starting test data generation:")
    logger.info(f"  Kafka servers: {args.bootstrap_servers}")
    logger.info(f"  Topic: {args.topic}")
    logger.info(f"  Count: {args.count}")
    logger.info(f"  Interval: {args.interval}s")
    logger.info(f"  Fraud ratio: {args.fraud_ratio}")

    # Create Kafka producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=args.bootstrap_servers,
            value_serializer=lambda v: v.encode("utf-8"),
            acks="all",
            retries=3,
        )
        logger.info("Connected to Kafka")
    except Exception as e:
        logger.error(f"Failed to connect to Kafka: {e}")
        return

    # Generate and send transactions
    fraud_count = 0
    legitimate_count = 0

    for i in range(args.count):
        # Decide if this should be a fraudulent transaction
        if random.random() < args.fraud_ratio:
            transaction = generate_fraudulent_transaction()
            fraud_count += 1
            logger.info(f"Generated fraudulent transaction {i+1}/{args.count}")
        else:
            transaction = generate_transaction()
            legitimate_count += 1
            logger.info(f"Generated legitimate transaction {i+1}/{args.count}")

        # Send to Kafka
        send_to_kafka(producer, args.topic, transaction)

        # Wait before next transaction
        if i < args.count - 1:  # Don't wait after the last transaction
            time.sleep(args.interval)

    # Close producer
    producer.close()

    logger.info("Test data generation completed!")
    logger.info(f"  Total transactions: {args.count}")
    logger.info(f"  Legitimate transactions: {legitimate_count}")
    logger.info(f"  Fraudulent transactions: {fraud_count}")


if __name__ == "__main__":
    main()
