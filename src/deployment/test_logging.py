#!/usr/bin/env python3
"""
Test script to verify prediction logging functionality.
This script sends test requests to the FastAPI service and checks if predictions are logged.
"""

import requests
import json
import time
import pandas as pd
import os

def test_prediction_logging():
    """Test the prediction logging functionality."""
    
    # API endpoint
    api_url = "http://localhost:8000"
    
    # Test data - mix of normal and potentially fraudulent transactions
    test_transactions = [
        {
            "V1": -1.36, "V2": -0.07, "V3": 2.54, "V4": 1.38, "V5": -0.34,
            "V6": 0.46, "V7": 0.24, "V8": 0.10, "V9": 0.36, "V10": 0.09,
            "V11": -0.55, "V12": -0.62, "V13": -0.99, "V14": -0.31, "V15": 1.47,
            "V16": -0.47, "V17": 0.21, "V18": 0.03, "V19": 0.40, "V20": 0.25,
            "V21": -0.02, "V22": 0.28, "V23": -0.11, "V24": 0.07, "V25": 0.13,
            "V26": -0.19, "V27": 0.13, "V28": -0.02, "Amount": 149.62
        },
        {
            "V1": -4.2, "V2": -3.1, "V3": -2.8, "V4": 3.2, "V5": 2.9,
            "V6": 3.1, "V7": -2.5, "V8": -1.8, "V9": -1.2, "V10": -0.8,
            "V11": -1.5, "V12": -1.2, "V13": -0.9, "V14": -0.6, "V15": -0.3,
            "V16": -0.1, "V17": 0.2, "V18": 0.4, "V19": 0.6, "V20": 0.8,
            "V21": 1.0, "V22": 1.2, "V23": 1.4, "V24": 1.6, "V25": 1.8,
            "V26": 2.0, "V27": 2.2, "V28": 2.4, "Amount": 1850.75
        }
    ]
    
    print("Testing prediction logging functionality...")
    print(f"API URL: {api_url}")
    print(f"Test transactions: {len(test_transactions)}")
    print()
    
    # Check if API is running
    try:
        health_response = requests.get(f"{api_url}/health")
        if health_response.status_code == 200:
            print("✅ API is healthy")
        else:
            print(f"❌ API health check failed: {health_response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the service is running.")
        return
    
    # Send prediction request
    try:
        payload = {"transactions": test_transactions}
        response = requests.post(
            f"{api_url}/predict",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            predictions = response.json()["predictions"]
            print("✅ Prediction request successful")
            print(f"Predictions: {predictions}")
            
            # Check if log file was created
            log_file = "/app/data/inference_log.csv"
            if os.path.exists(log_file):
                print(f"✅ Log file created: {log_file}")
                
                # Read and display the log
                try:
                    log_df = pd.read_csv(log_file)
                    print(f"✅ Log file contains {len(log_df)} records")
                    print("\nLog file contents:")
                    print(log_df.to_string(index=False))
                    
                    # Verify log structure
                    expected_columns = ['V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10',
                                      'V11', 'V12', 'V13', 'V14', 'V15', 'V16', 'V17', 'V18', 'V19', 'V20',
                                      'V21', 'V22', 'V23', 'V24', 'V25', 'V26', 'V27', 'V28', 'Amount',
                                      'prediction', 'prediction_id', 'timestamp', 'fraud_detected']
                    
                    missing_columns = [col for col in expected_columns if col not in log_df.columns]
                    if missing_columns:
                        print(f"❌ Missing columns in log: {missing_columns}")
                    else:
                        print("✅ Log file has all expected columns")
                        
                except Exception as e:
                    print(f"❌ Error reading log file: {e}")
            else:
                print(f"❌ Log file not found: {log_file}")
                
        else:
            print(f"❌ Prediction request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during prediction request: {e}")

if __name__ == "__main__":
    test_prediction_logging() 