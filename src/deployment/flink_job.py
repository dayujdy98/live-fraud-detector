#!/usr/bin/env python3
"""
Real-time Fraud Detection Flink Streaming Job

This job consumes transaction data from Kafka, processes it through the fraud detection API,
and produces fraud alerts for high-probability fraud cases.
"""

import json
import logging
import os

import requests
from pyflink.common.serialization import (
    JsonRowDeserializationSchema,
    SimpleStringSchema,
)
from pyflink.common.typeinfo import Types
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer, FlinkKafkaProducer
from pyflink.datastream.functions import MapFunction

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FraudDetector(MapFunction):
    """
    Map function that processes transactions through the fraud detection API.

    Takes a transaction Row from Kafka, calls the fraud detection API,
    and returns the enriched transaction with fraud probability.
    """

    def __init__(self):
        self.api_endpoint = os.getenv("API_ENDPOINT_URL")
        if not self.api_endpoint:
            raise ValueError("API_ENDPOINT_URL environment variable is required")

        # Remove trailing slash if present
        self.api_endpoint = self.api_endpoint.rstrip("/")
        self.predict_url = f"{self.api_endpoint}/predict"

        logger.info(f"Initialized FraudDetector with API endpoint: {self.api_endpoint}")

    def map(self, value):
        """
        Process a transaction through the fraud detection API.

        Args:
            value: Flink Row object containing transaction data

        Returns:
            JSON string with enriched transaction data including fraud probability
        """
        try:
            # Convert Flink Row to dictionary
            tx_dict = value.as_dict()

            # Prepare request payload for the API
            request_payload = {"transactions": [tx_dict]}

            # Make API call to fraud detection service
            response = requests.post(
                self.predict_url,
                json=request_payload,
                headers={"Content-Type": "application/json"},
                timeout=10,  # 10 second timeout
            )

            if response.status_code == 200:
                # Parse response to get fraud probability
                response_data = response.json()
                fraud_probability = response_data.get("predictions", [0.0])[0]

                # Add fraud probability to transaction data
                tx_dict["fraud_probability"] = fraud_probability
                tx_dict["fraud_detected"] = fraud_probability > 0.5

                logger.debug(
                    f"Transaction processed successfully. Fraud probability: {fraud_probability:.4f}"
                )

            else:
                # API call failed, set default values
                tx_dict["fraud_probability"] = -1.0
                tx_dict["fraud_detected"] = False
                tx_dict["error"] = f"API call failed with status {response.status_code}"

                logger.warning(
                    f"API call failed for transaction. Status: {response.status_code}, Response: {response.text}"
                )

        except requests.exceptions.RequestException as e:
            # Network or request error
            tx_dict["fraud_probability"] = -1.0
            tx_dict["fraud_detected"] = False
            tx_dict["error"] = f"Request error: {str(e)}"

            logger.error(f"Request error processing transaction: {e}")

        except Exception as e:
            # Any other error
            tx_dict["fraud_probability"] = -1.0
            tx_dict["fraud_detected"] = False
            tx_dict["error"] = f"Processing error: {str(e)}"

            logger.error(f"Error processing transaction: {e}")

        # Return enriched transaction as JSON string
        return json.dumps(tx_dict)


def run_flink_job():
    """
    Main function to set up and execute the Flink streaming job.
    """
    # Set up the streaming execution environment
    env = StreamExecutionEnvironment.get_execution_environment()

    # Get configuration from environment variables
    kafka_broker = os.getenv("KAFKA_BROKER_ADDRESS")
    if not kafka_broker:
        raise ValueError("KAFKA_BROKER_ADDRESS environment variable is required")

    # Kafka topic names
    input_topic = os.getenv("INPUT_TOPIC", "transactions")
    output_topic = os.getenv("OUTPUT_TOPIC", "fraud_alerts")

    # Fraud probability threshold for alerts (configurable)
    fraud_threshold = float(os.getenv("FRAUD_THRESHOLD", "0.8"))

    logger.info(f"Starting Flink job with broker: {kafka_broker}")
    logger.info(f"Input topic: {input_topic}, Output topic: {output_topic}")
    logger.info(f"Fraud threshold: {fraud_threshold}")

    # Define the schema for incoming transaction data
    # This should match the structure of your transaction JSON
    transaction_schema = Types.ROW(
        [
            Types.FIELD("V1", Types.FLOAT()),
            Types.FIELD("V2", Types.FLOAT()),
            Types.FIELD("V3", Types.FLOAT()),
            Types.FIELD("V4", Types.FLOAT()),
            Types.FIELD("V5", Types.FLOAT()),
            Types.FIELD("V6", Types.FLOAT()),
            Types.FIELD("V7", Types.FLOAT()),
            Types.FIELD("V8", Types.FLOAT()),
            Types.FIELD("V9", Types.FLOAT()),
            Types.FIELD("V10", Types.FLOAT()),
            Types.FIELD("V11", Types.FLOAT()),
            Types.FIELD("V12", Types.FLOAT()),
            Types.FIELD("V13", Types.FLOAT()),
            Types.FIELD("V14", Types.FLOAT()),
            Types.FIELD("V15", Types.FLOAT()),
            Types.FIELD("V16", Types.FLOAT()),
            Types.FIELD("V17", Types.FLOAT()),
            Types.FIELD("V18", Types.FLOAT()),
            Types.FIELD("V19", Types.FLOAT()),
            Types.FIELD("V20", Types.FLOAT()),
            Types.FIELD("V21", Types.FLOAT()),
            Types.FIELD("V22", Types.FLOAT()),
            Types.FIELD("V23", Types.FLOAT()),
            Types.FIELD("V24", Types.FLOAT()),
            Types.FIELD("V25", Types.FLOAT()),
            Types.FIELD("V26", Types.FLOAT()),
            Types.FIELD("V27", Types.FLOAT()),
            Types.FIELD("V28", Types.FLOAT()),
            Types.FIELD("Amount", Types.FLOAT()),
            Types.FIELD("transaction_id", Types.STRING()),
            Types.FIELD("timestamp", Types.STRING()),
        ]
    )

    # Create JSON deserialization schema for Kafka source
    json_deserializer = (
        JsonRowDeserializationSchema.builder().type_info(transaction_schema).build()
    )

    # Create Kafka consumer for input topic
    kafka_source = FlinkKafkaConsumer(
        topics=input_topic,
        deserializer=json_deserializer,
        properties={
            "bootstrap.servers": kafka_broker,
            "group.id": "fraud-detection-group",
            "auto.offset.reset": "latest",
            "enable.auto.commit": "true",
        },
    )

    # Create Kafka producer for output topic
    kafka_sink = FlinkKafkaProducer(
        topic=output_topic,
        serialization_schema=SimpleStringSchema(),
        producer_config={
            "bootstrap.servers": kafka_broker,
            "transaction.timeout.ms": "900000",  # 15 minutes
        },
    )

    # Build the streaming pipeline
    stream = env.add_source(kafka_source)

    # Process transactions through fraud detection API
    enriched_stream = stream.map(FraudDetector(), output_type=Types.STRING())

    # Filter for high-probability fraud cases
    fraud_alerts = enriched_stream.filter(
        lambda record: json.loads(record).get("fraud_probability", -1) > fraud_threshold
    )

    # Send fraud alerts to output topic
    fraud_alerts.add_sink(kafka_sink)

    # Execute the job
    logger.info("Executing Flink job: Real-time Fraud Detection")
    env.execute("Real-time Fraud Detection")


if __name__ == "__main__":
    run_flink_job()
