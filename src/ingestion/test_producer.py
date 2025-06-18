#!/usr/bin/env python3
"""
Test script for Kafka Producer

This script tests the Kafka producer functionality with a small sample dataset.
"""

import os
import sys
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from ingestion.kafka_producer import TransactionProducer


def create_test_data(file_path: str, num_transactions: int = 50):
    """Create a small test dataset for testing the producer."""
    print(f"Creating test dataset with {num_transactions} transactions...")
    
    # Generate sample data similar to credit card fraud dataset
    np.random.seed(42)
    
    data = {
        'Time': np.sort(np.random.exponential(10, num_transactions)),
        'Amount': np.random.lognormal(3, 1, num_transactions)
    }
    
    # Add V1-V28 features (PCA components)
    for i in range(1, 29):
        data[f'V{i}'] = np.random.normal(0, 1, num_transactions)
    
    # Add fraud labels (highly imbalanced)
    fraud_count = max(1, int(num_transactions * 0.02))  # 2% fraud rate
    fraud_indices = np.random.choice(num_transactions, fraud_count, replace=False)
    data['Class'] = np.zeros(num_transactions)
    data['Class'][fraud_indices] = 1
    
    # Create DataFrame and save
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    
    print(f"Test dataset created:")
    print(f"- Total transactions: {num_transactions}")
    print(f"- Fraud transactions: {fraud_count} ({fraud_count/num_transactions*100:.1f}%)")
    print(f"- Saved to: {file_path}")
    
    return file_path


def test_producer_basic():
    """Test basic producer functionality."""
    print("\n" + "="*50)
    print("Testing Basic Producer Functionality")
    print("="*50)
    
    # Create temporary test data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_file = f.name
    
    try:
        # Create test dataset
        create_test_data(test_file, 10)
        
        # Set test environment variables
        os.environ['TRANSACTION_DATA_PATH'] = test_file
        os.environ['KAFKA_TRANSACTIONS_TOPIC'] = 'test-transactions'
        os.environ['STREAM_DELAY_SECONDS'] = '0.01'  # Fast for testing
        os.environ['LOOP_DATASET'] = 'false'
        os.environ['LOG_LEVEL'] = 'INFO'
        
        print("\nInitializing producer...")
        producer = TransactionProducer()
        
        print("Configuration loaded:")
        print(f"- Data path: {producer.data_path}")
        print(f"- Topic: {producer.topic_name}")
        print(f"- Delay: {producer.delay_seconds}s")
        print(f"- Kafka broker: {producer.kafka_broker}")
        
        print("\nTesting data loading...")
        df = producer._load_transaction_data()
        print(f"Loaded {len(df)} transactions successfully")
        
        print("\nTesting message creation...")
        sample_row = df.iloc[0]
        message = producer._create_transaction_message(sample_row, 1)
        
        print("Sample message created:")
        print(f"- Transaction ID: {message['transaction_id']}")
        print(f"- Amount: {message['Amount']}")
        print(f"- Class: {message['Class']}")
        print(f"- Timestamp: {message['timestamp']}")
        
        print("\n✅ Basic functionality test passed!")
        
    except Exception as e:
        print(f"\n❌ Basic functionality test failed: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
    
    return True


def test_producer_with_kafka():
    """Test producer with actual Kafka connection (requires Kafka to be running)."""
    print("\n" + "="*50)
    print("Testing Producer with Kafka Connection")
    print("="*50)
    
    # Create temporary test data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_file = f.name
    
    try:
        # Create test dataset
        create_test_data(test_file, 5)
        
        # Set test environment variables
        os.environ['TRANSACTION_DATA_PATH'] = test_file
        os.environ['KAFKA_TRANSACTIONS_TOPIC'] = 'test-transactions'
        os.environ['STREAM_DELAY_SECONDS'] = '0.1'
        os.environ['LOOP_DATASET'] = 'false'
        os.environ['LOG_LEVEL'] = 'INFO'
        
        print("\nInitializing producer...")
        producer = TransactionProducer()
        
        print("Testing Kafka connection...")
        kafka_producer = producer._create_producer()
        
        print("✅ Kafka connection successful!")
        
        print("\nSending test messages...")
        # Override the running flag to stop after a few messages
        original_start_streaming = producer.start_streaming
        
        def limited_streaming():
            try:
                producer.producer = kafka_producer
                df = producer._load_transaction_data()
                
                # Send only first 3 messages
                for idx, row in df.head(3).iterrows():
                    transaction = producer._create_transaction_message(row, idx + 1)
                    success = producer._send_message(transaction)
                    
                    if success:
                        fraud_status = "FRAUD" if transaction.get('Class') == 1 else "NORMAL"
                        print(f"✅ Sent: {transaction['transaction_id']} ({fraud_status})")
                    else:
                        print(f"❌ Failed to send message {idx + 1}")
                        
                # Flush messages
                producer.producer.flush(timeout=5)
                print(f"\n✅ Successfully sent {producer.messages_sent} test messages!")
                
            except Exception as e:
                print(f"❌ Error during streaming: {e}")
                raise
            finally:
                producer._shutdown()
        
        # Run limited streaming test
        limited_streaming()
        
        print("\n✅ Kafka integration test passed!")
        
    except Exception as e:
        print(f"\n❌ Kafka integration test failed: {e}")
        print("Note: This test requires Kafka to be running on localhost:9092")
        print("Start Kafka with: docker-compose up -d kafka")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
    
    return True


def main():
    """Run all tests."""
    print("Kafka Producer Test Suite")
    print("=" * 50)
    
    # Test 1: Basic functionality (no Kafka required)
    success_basic = test_producer_basic()
    
    # Test 2: Kafka integration (requires running Kafka)
    success_kafka = test_producer_with_kafka()
    
    # Summary
    print("\n" + "="*50)
    print("Test Results Summary")
    print("="*50)
    print(f"Basic Functionality: {'✅ PASSED' if success_basic else '❌ FAILED'}")
    print(f"Kafka Integration:   {'✅ PASSED' if success_kafka else '❌ FAILED'}")
    
    if success_basic and success_kafka:
        print("\n🎉 All tests passed! Producer is ready for use.")
        return 0
    elif success_basic:
        print("\n⚠️  Basic tests passed, but Kafka integration failed.")
        print("   Make sure Kafka is running: docker-compose up -d kafka")
        return 1
    else:
        print("\n❌ Basic tests failed. Check your environment setup.")
        return 2


if __name__ == "__main__":
    sys.exit(main()) 