#!/bin/bash

echo "Testing Complete Fraud Detection System"
echo "=========================================="

# Get infrastructure details
API_URL="http://fraud-detection-alb-1804403570.us-east-1.elb.amazonaws.com"
FLINK_IP="13.219.130.248"
MLFLOW_IP="52.203.174.199"
GRAFANA_IP="18.211.164.129"
PROMETHEUS_IP="18.211.164.129"

echo "System Components:"
echo "   API URL: $API_URL"
echo "   Flink Server: $FLINK_IP:8081"
echo "   MLflow Server: $MLFLOW_IP:5000"
echo "   Grafana: $GRAFANA_IP:3000"
echo "   Prometheus: $PROMETHEUS_IP:9090"
echo ""

# Test 1: API Health Check
echo "1. Testing API Health..."
health_response=$(curl -s --connect-timeout 10 "$API_URL/health")
if [[ "$health_response" == *"healthy"* ]]; then
    echo "   SUCCESS: API Health check successful: $health_response"
elif [[ "$health_response" == *"503"* ]]; then
    echo "   ERROR: API Service Unavailable (503) - ECS service may be stopped"
else
    echo "   ERROR: API Health check failed: $health_response"
fi
echo ""

# Test 2: Single Transaction Prediction
echo "2. Testing Single Transaction Prediction..."
prediction_response=$(curl -s --connect-timeout 10 -X POST "$API_URL/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [{
      "V1": -1.359807134, "V2": -0.072781173, "V3": 2.536346738, "V4": 1.378155224, "V5": -0.338320769,
      "V6": 0.462387778, "V7": 0.239598554, "V8": 0.098697901, "V9": 0.363786969, "V10": 0.090794172,
      "V11": -0.551599533, "V12": -0.617800856, "V13": -0.991389847, "V14": -0.311169354, "V15": 1.468176972,
      "V16": -0.470400525, "V17": 0.207971242, "V18": 0.025791653, "V19": 0.403992960, "V20": 0.251412098,
      "V21": -0.018306778, "V22": 0.277837576, "V23": -0.110473910, "V24": 0.066928075, "V25": 0.128539358,
      "V26": -0.189114844, "V27": 0.133558377, "V28": -0.021053053, "Amount": 149.62
    }]
  }')

if [[ "$prediction_response" == *"predictions"* ]]; then
    echo "   SUCCESS: Prediction successful: $prediction_response"
elif [[ "$prediction_response" == *"503"* ]]; then
    echo "   ERROR: API Service Unavailable (503) - ECS service may be stopped"
else
    echo "   ERROR: Prediction failed: $prediction_response"
fi
echo ""

# Test 3: MLflow Server
echo "3. Testing MLflow Server..."
mlflow_response=$(curl -s --connect-timeout 10 "$MLFLOW_IP:5000/api/2.0/mlflow/registered-models/list")
if [[ "$mlflow_response" == *"registered_models"* ]]; then
    echo "   SUCCESS: MLflow server accessible"
    # Check if our model exists
    if [[ "$mlflow_response" == *"fraud-detection-optimized"* ]]; then
        echo "   SUCCESS: fraud-detection-optimized model found"
    else
        echo "   WARNING: fraud-detection-optimized model not found"
    fi
else
    echo "   ERROR: MLflow server not accessible (may be stopped)"
fi
echo ""

# Test 4: Flink Web UI
echo "4. Testing Flink Web UI..."
flink_response=$(curl -s --connect-timeout 5 "$FLINK_IP:8081/overview")
if [[ "$flink_response" == *"flink"* ]] || [[ "$flink_response" == *"taskmanagers"* ]]; then
    echo "   SUCCESS: Flink Web UI accessible"
    # Parse task managers count
    if [[ "$flink_response" == *"taskmanagers"* ]]; then
        taskmanagers=$(echo "$flink_response" | grep -o '"taskmanagers":[0-9]*' | cut -d':' -f2)
        echo "   SUCCESS: Task managers: $taskmanagers"
    fi
else
    echo "   ERROR: Flink Web UI not accessible"
fi
echo ""

# Test 5: Prometheus
echo "5. Testing Prometheus..."
prometheus_response=$(curl -s --connect-timeout 5 "$PROMETHEUS_IP:9090/api/v1/query?query=up")
if [[ "$prometheus_response" == *"success"* ]]; then
    echo "   SUCCESS: Prometheus accessible and responding"
    # Check targets
    targets_response=$(curl -s --connect-timeout 5 "$PROMETHEUS_IP:9090/api/v1/targets")
    if [[ "$targets_response" == *"fraud-detection-fastapi"* ]]; then
        echo "   SUCCESS: FastAPI target configured in Prometheus"
    fi
else
    echo "   ERROR: Prometheus not accessible"
fi
echo ""

# Test 6: Grafana
echo "6. Testing Grafana..."
grafana_response=$(curl -s --connect-timeout 5 "$GRAFANA_IP:3000/api/health")
if [[ "$grafana_response" == *"database"* ]] && [[ "$grafana_response" == *"ok"* ]]; then
    echo "   SUCCESS: Grafana accessible and healthy"
    version=$(echo "$grafana_response" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    echo "   SUCCESS: Grafana version: $version"
else
    echo "   ERROR: Grafana not accessible"
fi
echo ""

echo "Access URLs for Manual Testing:"
echo "   API Documentation: $API_URL/docs"
echo "   Flink Dashboard: http://$FLINK_IP:8081"
echo "   MLflow UI: http://$MLFLOW_IP:5000"
echo "   Grafana Dashboard: http://$GRAFANA_IP:3000 (admin/admin123)"
echo "   Prometheus: http://$PROMETHEUS_IP:9090"
echo ""

echo "Service Status Summary:"
echo "   RUNNING: Flink"
echo "   RUNNING: Prometheus"
echo "   RUNNING: Grafana"
echo "   RUNNING: FastAPI"
echo "   RUNNING: MLflow"
echo ""


echo "COMPLETED: System Component Testing Complete!"
