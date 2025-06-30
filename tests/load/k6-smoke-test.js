/**
 * k6 Smoke Test for Fraud Detection API
 *
 * Quick validation test to ensure API is functioning correctly
 * before running comprehensive load tests.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

export const options = {
  vus: 10, // 10 virtual users
  duration: '30s', // Run for 30 seconds
  thresholds: {
    http_req_duration: ['p(95)<200'], // 95% of requests under 200ms
    http_req_failed: ['rate<0.1'],    // Error rate under 10%
  },
};

// Sample transaction for testing
const sampleTransaction = {
  V1: 0.5, V2: -0.3, V3: 1.2, V4: 0.8, V5: -0.1,
  V6: 0.7, V7: -0.4, V8: 0.9, V9: 0.2, V10: -0.6,
  V11: 0.3, V12: 0.1, V13: -0.8, V14: 0.6, V15: 0.4,
  V16: -0.2, V17: 0.9, V18: -0.5, V19: 0.7, V20: 0.1,
  V21: -0.3, V22: 0.8, V23: 0.2, V24: -0.7, V25: 0.5,
  V26: 0.3, V27: -0.1, V28: 0.6, Amount: 150.75
};

export default function () {
  // Test health endpoint
  const healthResponse = http.get(`${BASE_URL}/health`);
  check(healthResponse, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 100ms': (r) => r.timings.duration < 100,
  });

  // Test prediction endpoint
  const payload = JSON.stringify({ transactions: [sampleTransaction] });
  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  const response = http.post(`${BASE_URL}/predict`, payload, params);

  const isSuccess = check(response, {
    'prediction status is 200': (r) => r.status === 200,
    'prediction response time < 200ms': (r) => r.timings.duration < 200,
    'has valid prediction': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.predictions &&
          Array.isArray(body.predictions) &&
          body.predictions.length === 1 &&
          typeof body.predictions[0] === 'number' &&
          body.predictions[0] >= 0 && body.predictions[0] <= 1;
      } catch (e) {
        return false;
      }
    },
  });

  sleep(1);
}

export function setup() {
  console.log('Starting Smoke Test');
  console.log(`API URL: ${BASE_URL}`);
}

export function teardown(data) {
  console.log('Smoke Test Complete');
}
