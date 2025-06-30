#!/bin/bash

echo "Configuring Grafana Dashboard for Fraud Detection System"
echo "========================================================"

GRAFANA_URL="http://18.211.164.129:3000"
PROMETHEUS_URL="http://18.211.164.129:9090"

# Wait for Grafana to be ready
echo "Waiting for Grafana to be ready..."
while ! curl -s ${GRAFANA_URL}/api/health > /dev/null; do
    echo "   Still waiting for Grafana..."
    sleep 5
done
echo "SUCCESS: Grafana is ready!"

# Add Prometheus as a data source
echo "Adding Prometheus data source..."
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "'${PROMETHEUS_URL}'",
    "access": "proxy",
    "isDefault": true
  }' \
  http://admin:admin123@18.211.164.129:3000/api/datasources

echo ""
echo "Creating Fraud Detection Dashboard..."

# Create a fraud detection dashboard
DASHBOARD_JSON='{
  "dashboard": {
    "id": null,
    "title": "Fraud Detection System",
    "uid": "fraud-detection",
    "tags": ["fraud", "detection", "api"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Health Status",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"fraud-detection-api\"}",
            "legendFormat": "API Status"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "green", "value": 1}
              ]
            }
          }
        }
      },
      {
        "id": 2,
        "title": "Total Fraud Predictions",
        "type": "stat",
        "targets": [
          {
            "expr": "fraud_predictions_total",
            "legendFormat": "Fraud Predictions"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            }
          }
        }
      },
      {
        "id": 3,
        "title": "HTTP Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Request Rate"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "5s"
  },
  "overwrite": true
}'

curl -X POST \
  -H "Content-Type: application/json" \
  -d "${DASHBOARD_JSON}" \
  http://admin:admin123@18.211.164.129:3000/api/dashboards/db

echo ""
echo "SUCCESS: Grafana Configuration Complete!"
echo ""
echo "Access URLs:"
echo "   Grafana Dashboard: http://18.211.164.129:3000"
echo "   Prometheus: http://18.211.164.129:9090"
echo ""
echo "Grafana Login:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
