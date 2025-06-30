#!/bin/bash

API_URL="http://fraud-detection-alb-1804403570.us-east-1.elb.amazonaws.com"

echo "Testing Fraud Detection API..."
echo "=================================="

# Test 1: Health Check
echo "1. Health Check:"
curl -s "${API_URL}/health" | jq . 2>/dev/null || curl -s "${API_URL}/health"
echo ""

# Test 2: Normal Transaction (should have low fraud probability)
echo "2. Testing Normal Transaction:"
curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [{
      "V1": -1.5, "V2": 1.5, "V3": -0.8, "V4": 0.3, "V5": -1.2,
      "V6": 0.5, "V7": -0.9, "V8": 0.2, "V9": -1.0, "V10": -0.7,
      "V11": 1.1, "V12": -1.3, "V13": 0.4, "V14": -0.6, "V15": 0.8,
      "V16": -0.2, "V17": 1.0, "V18": -0.5, "V19": 0.7, "V20": -0.3,
      "V21": 0.6, "V22": -0.4, "V23": 0.1, "V24": -0.1, "V25": 0.9,
      "V26": -0.8, "V27": 0.3, "V28": -0.2, "Amount": 67.88
    }]
  }' | jq . 2>/dev/null || curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [{
      "V1": -1.5, "V2": 1.5, "V3": -0.8, "V4": 0.3, "V5": -1.2,
      "V6": 0.5, "V7": -0.9, "V8": 0.2, "V9": -1.0, "V10": -0.7,
      "V11": 1.1, "V12": -1.3, "V13": 0.4, "V14": -0.6, "V15": 0.8,
      "V16": -0.2, "V17": 1.0, "V18": -0.5, "V19": 0.7, "V20": -0.3,
      "V21": 0.6, "V22": -0.4, "V23": 0.1, "V24": -0.1, "V25": 0.9,
      "V26": -0.8, "V27": 0.3, "V28": -0.2, "Amount": 67.88
    }]
  }'
echo ""

# Test 3: Suspicious Transaction (larger amount, different pattern)
echo "3. Testing Suspicious Transaction:"
curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [{
      "V1": 2.5, "V2": -3.2, "V3": 4.1, "V4": -2.8, "V5": 3.7,
      "V6": -4.5, "V7": 2.9, "V8": -3.1, "V9": 4.2, "V10": -2.7,
      "V11": 3.8, "V12": -4.3, "V13": 2.6, "V14": -3.9, "V15": 4.4,
      "V16": -2.2, "V17": 3.5, "V18": -4.1, "V19": 2.7, "V20": -3.3,
      "V21": 4.6, "V22": -2.4, "V23": 3.1, "V24": -3.8, "V25": 4.9,
      "V26": -2.8, "V27": 3.3, "V28": -4.2, "Amount": 2847.77
    }]
  }' | jq . 2>/dev/null || curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [{
      "V1": 2.5, "V2": -3.2, "V3": 4.1, "V4": -2.8, "V5": 3.7,
      "V6": -4.5, "V7": 2.9, "V8": -3.1, "V9": 4.2, "V10": -2.7,
      "V11": 3.8, "V12": -4.3, "V13": 2.6, "V14": -3.9, "V15": 4.4,
      "V16": -2.2, "V17": 3.5, "V18": -4.1, "V19": 2.7, "V20": -3.3,
      "V21": 4.6, "V22": -2.4, "V23": 3.1, "V24": -3.8, "V25": 4.9,
      "V26": -2.8, "V27": 3.3, "V28": -4.2, "Amount": 2847.77
    }]
  }'
echo ""

# Test 4: Batch of Multiple Transactions
echo "4. Testing Batch Processing:"
curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {
        "V1": -0.5, "V2": 0.8, "V3": -0.3, "V4": 0.2, "V5": -0.7,
        "V6": 0.4, "V7": -0.6, "V8": 0.1, "V9": -0.4, "V10": -0.2,
        "V11": 0.6, "V12": -0.8, "V13": 0.3, "V14": -0.5, "V15": 0.7,
        "V16": -0.1, "V17": 0.9, "V18": -0.4, "V19": 0.5, "V20": -0.2,
        "V21": 0.3, "V22": -0.6, "V23": 0.2, "V24": -0.1, "V25": 0.8,
        "V26": -0.7, "V27": 0.4, "V28": -0.3, "Amount": 125.50
      },
      {
        "V1": 1.8, "V2": -2.5, "V3": 3.2, "V4": -1.9, "V5": 2.7,
        "V6": -3.1, "V7": 2.3, "V8": -2.8, "V9": 3.5, "V10": -1.7,
        "V11": 2.9, "V12": -3.4, "V13": 1.6, "V14": -2.2, "V15": 3.8,
        "V16": -1.4, "V17": 2.6, "V18": -3.7, "V19": 1.9, "V20": -2.3,
        "V21": 3.1, "V22": -1.8, "V23": 2.4, "V24": -3.2, "V25": 3.9,
        "V26": -1.5, "V27": 2.7, "V28": -3.6, "Amount": 1893.45
      }
    ]
  }' | jq . 2>/dev/null || curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {
        "V1": -0.5, "V2": 0.8, "V3": -0.3, "V4": 0.2, "V5": -0.7,
        "V6": 0.4, "V7": -0.6, "V8": 0.1, "V9": -0.4, "V10": -0.2,
        "V11": 0.6, "V12": -0.8, "V13": 0.3, "V14": -0.5, "V15": 0.7,
        "V16": -0.1, "V17": 0.9, "V18": -0.4, "V19": 0.5, "V20": -0.2,
        "V21": 0.3, "V22": -0.6, "V23": 0.2, "V24": -0.1, "V25": 0.8,
        "V26": -0.7, "V27": 0.4, "V28": -0.3, "Amount": 125.50
      },
      {
        "V1": 1.8, "V2": -2.5, "V3": 3.2, "V4": -1.9, "V5": 2.7,
        "V6": -3.1, "V7": 2.3, "V8": -2.8, "V9": 3.5, "V10": -1.7,
        "V11": 2.9, "V12": -3.4, "V13": 1.6, "V14": -2.2, "V15": 3.8,
        "V16": -1.4, "V17": 2.6, "V18": -3.7, "V19": 1.9, "V20": -2.3,
        "V21": 3.1, "V22": -1.8, "V23": 2.4, "V24": -3.2, "V25": 3.9,
        "V26": -1.5, "V27": 2.7, "V28": -3.6, "Amount": 1893.45
      }
    ]
  }'
echo ""

echo "COMPLETED: API Testing Complete!"
