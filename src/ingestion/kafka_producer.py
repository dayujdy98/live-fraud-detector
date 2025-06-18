#!/usr/bin/env python3
"""
Kafka Producer for Fraud Detection System

This script simulates streaming credit card transactions by reading from a CSV file
and publishing messages to a Kafka topic for real-time fraud detection.
"""

import os
import sys
import json
import time
import logging
import argparse
import signal
from typing import Dict, Any, Optional
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError
from dotenv import load_dotenv


class TransactionProducer:
    """Kafka producer for streaming credit card transactions."""
    
    def __init__(self):
        """Initialize the transaction producer with configuration."""
        self.producer: Optional[KafkaProducer] = None
        self.messages_sent = 0
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Load configuration
        self._load_config()
        
        # Set up logging
        self._setup_logging()
        
    def _load_config(self):
        """Load configuration from environment variables."""
        # Load environment variables from .env file
        load_dotenv()
        
        # Kafka configuration
        self.kafka_broker = os.getenv('KAFKA_BROKER_ADDRESS', 'localhost:9092')
        self.topic_name = os.getenv('KAFKA_TRANSACTIONS_TOPIC', 'transactions')
        
        # Data configuration
        self.data_path = os.getenv('TRANSACTION_DATA_PATH', 'data/raw/transactions.csv')
        
        # Streaming configuration
        self.delay_seconds = float(os.getenv('STREAM_DELAY_SECONDS', '0.1'))
        self.loop_dataset = os.getenv('LOOP_DATASET', 'false').lower() == 'true'
        self.use_time_column = os.getenv('USE_TIME_COLUMN', 'false').lower() == 'true'
        
        # Producer configuration
        self.batch_size = int(os.getenv('KAFKA_BATCH_SIZE', '16384'))
        self.linger_ms = int(os.getenv('KAFKA_LINGER_MS', '10'))
        
    def _setup_logging(self):
        """Set up logging configuration."""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/kafka_producer.log', mode='a')
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        self.running = False
        
    def _create_producer(self) -> KafkaProducer:
        """Create and configure Kafka producer."""
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.kafka_broker.split(','),
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                batch_size=self.batch_size,
                linger_ms=self.linger_ms,
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,
                max_in_flight_requests_per_connection=1,
                enable_idempotence=True
            )
            
            self.logger.info(f"Successfully connected to Kafka broker(s): {self.kafka_broker}")
            return producer
            
        except Exception as e:
            self.logger.error(f"Failed to create Kafka producer: {e}")
            raise
            
    def _load_transaction_data(self) -> pd.DataFrame:
        """Load transaction data from CSV file."""
        try:
            if not os.path.exists(self.data_path):
                raise FileNotFoundError(f"Transaction data file not found: {self.data_path}")
                
            self.logger.info(f"Loading transaction data from: {self.data_path}")
            
            # Read CSV file
            df = pd.read_csv(self.data_path)
            
            # Validate required columns
            required_columns = ['Class']  # 'Class' is the fraud label
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
                
            self.logger.info(f"Loaded {len(df)} transactions from dataset")
            self.logger.info(f"Dataset columns: {list(df.columns)}")
            
            # Sort by Time column if it exists and we want to use it
            if self.use_time_column and 'Time' in df.columns:
                df = df.sort_values('Time').reset_index(drop=True)
                self.logger.info("Sorted transactions by Time column for realistic simulation")
                
            return df
            
        except FileNotFoundError as e:
            self.logger.error(f"Data file not found: {e}")
            self.logger.error("Please ensure the transaction data file exists or download it first")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load transaction data: {e}")
            raise
            
    def _create_transaction_message(self, row: pd.Series, transaction_id: int) -> Dict[str, Any]:
        """Create a transaction message from a DataFrame row."""
        # Convert pandas Series to dictionary
        transaction = row.to_dict()
        
        # Add metadata
        transaction['transaction_id'] = f"txn_{transaction_id:010d}"
        transaction['timestamp'] = int(time.time() * 1000)  # Current timestamp in milliseconds
        transaction['producer_id'] = 'kafka_producer_v1'
        
        # Ensure all values are JSON serializable
        for key, value in transaction.items():
            if pd.isna(value):
                transaction[key] = None
            elif isinstance(value, (pd.Timestamp, pd.NaT.__class__)):
                transaction[key] = str(value)
            elif hasattr(value, 'item'):  # Handle numpy types
                transaction[key] = value.item()
                
        return transaction
        
    def _send_message(self, transaction: Dict[str, Any]) -> bool:
        """Send a single transaction message to Kafka."""
        try:
            # Use transaction_id as the message key for partitioning
            key = transaction.get('transaction_id')
            
            # Send message asynchronously
            future = self.producer.send(
                topic=self.topic_name,
                key=key,
                value=transaction
            )
            
            # Optional: Add callback for monitoring
            future.add_callback(self._on_send_success)
            future.add_errback(self._on_send_error)
            
            self.messages_sent += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
            
    def _on_send_success(self, record_metadata):
        """Callback for successful message delivery."""
        if self.messages_sent % 1000 == 0:  # Log every 1000 messages
            self.logger.debug(
                f"Message sent successfully to topic: {record_metadata.topic}, "
                f"partition: {record_metadata.partition}, "
                f"offset: {record_metadata.offset}"
            )
            
    def _on_send_error(self, exception):
        """Callback for message delivery failure."""
        self.logger.error(f"Failed to send message: {exception}")
        
    def _calculate_delay(self, current_row: pd.Series, next_row: Optional[pd.Series]) -> float:
        """Calculate delay between messages based on Time column or fixed delay."""
        if not self.use_time_column or next_row is None or 'Time' not in current_row:
            return self.delay_seconds
            
        try:
            # Use the time difference from the dataset (scaled down for simulation)
            time_diff = next_row['Time'] - current_row['Time']
            # Scale down by a factor to speed up simulation (e.g., 1 second in data = 0.01 seconds in simulation)
            scaled_delay = max(time_diff * 0.01, 0.001)  # Minimum 1ms delay
            return min(scaled_delay, 1.0)  # Maximum 1 second delay
        except Exception:
            return self.delay_seconds
            
    def start_streaming(self):
        """Start streaming transactions to Kafka."""
        try:
            # Create Kafka producer
            self.producer = self._create_producer()
            
            # Load transaction data
            df = self._load_transaction_data()
            
            self.logger.info(f"Starting to stream transactions to topic: {self.topic_name}")
            self.logger.info(f"Stream delay: {self.delay_seconds} seconds")
            self.logger.info(f"Loop dataset: {self.loop_dataset}")
            
            iteration = 0
            
            while self.running:
                iteration += 1
                self.logger.info(f"Starting dataset iteration {iteration}")
                
                for idx, row in df.iterrows():
                    if not self.running:
                        break
                        
                    # Create transaction message
                    transaction = self._create_transaction_message(row, self.messages_sent + 1)
                    
                    # Send message
                    if self._send_message(transaction):
                        # Log progress periodically
                        if self.messages_sent % 100 == 0:
                            fraud_status = "FRAUD" if transaction.get('Class') == 1 else "NORMAL"
                            self.logger.info(
                                f"Sent {self.messages_sent} messages. "
                                f"Latest: {transaction['transaction_id']} ({fraud_status})"
                            )
                    
                    # Calculate and apply delay
                    if idx < len(df) - 1:
                        delay = self._calculate_delay(row, df.iloc[idx + 1])
                        time.sleep(delay)
                    else:
                        time.sleep(self.delay_seconds)
                        
                # Break if not looping
                if not self.loop_dataset:
                    break
                    
                self.logger.info(f"Completed iteration {iteration}, sent {self.messages_sent} total messages")
                
                if self.loop_dataset and self.running:
                    self.logger.info("Restarting dataset for continuous streaming...")
                    time.sleep(1)  # Brief pause between iterations
                    
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            self.logger.error(f"Error during streaming: {e}")
            raise
        finally:
            self._shutdown()
            
    def _shutdown(self):
        """Gracefully shutdown the producer."""
        self.logger.info("Shutting down Kafka producer...")
        
        if self.producer:
            try:
                # Flush any remaining messages
                self.producer.flush(timeout=10)
                self.producer.close(timeout=10)
                self.logger.info("Kafka producer closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing Kafka producer: {e}")
                
        self.logger.info(f"Total messages sent: {self.messages_sent}")
        self.logger.info("Producer shutdown complete")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Kafka Producer for Credit Card Transactions")
    
    parser.add_argument(
        '--data-path',
        type=str,
        help='Path to the transaction CSV file (overrides environment variable)'
    )
    
    parser.add_argument(
        '--topic',
        type=str,
        help='Kafka topic name (overrides environment variable)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        help='Delay between messages in seconds (overrides environment variable)'
    )
    
    parser.add_argument(
        '--loop',
        action='store_true',
        help='Loop through the dataset continuously'
    )
    
    parser.add_argument(
        '--use-time-column',
        action='store_true',
        help='Use the Time column from dataset for realistic timing'
    )
    
    return parser.parse_args()


def main():
    """Main function to run the transaction producer."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Override environment variables with command line arguments if provided
        if args.data_path:
            os.environ['TRANSACTION_DATA_PATH'] = args.data_path
        if args.topic:
            os.environ['KAFKA_TRANSACTIONS_TOPIC'] = args.topic
        if args.delay:
            os.environ['STREAM_DELAY_SECONDS'] = str(args.delay)
        if args.loop:
            os.environ['LOOP_DATASET'] = 'true'
        if args.use_time_column:
            os.environ['USE_TIME_COLUMN'] = 'true'
            
        # Create and start the producer
        producer = TransactionProducer()
        producer.start_streaming()
        
    except Exception as e:
        logging.error(f"Failed to start transaction producer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 