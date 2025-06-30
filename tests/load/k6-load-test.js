/**
 * k6 Load Testing Script for Fraud Detection API
 *
 * This script validates the 10K+ TPS claims with realistic load patterns
 * including burst traffic simulation and sustained high throughput testing.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const responseTime = new Trend('response_time', true);
const requestCount = new Counter('requests_total');

// Test configuration
const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

// Load testing scenarios
export const options = {
  scenarios: {
    // Scenario 1: Ramp-up to 10K TPS
    ramp_up_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },   // Ramp up to 100 VUs
        { duration: '5m', target: 500 },   // Ramp up to 500 VUs
        { duration: '10m', target: 1000 }, // Ramp up to 1000 VUs (targeting ~10K TPS)
        { duration: '10m', target: 1000 }, // Stay at 1000 VUs
        { duration: '5m', target: 0 },     // Ramp down
      ],
      gracefulRampDown: '30s',
    },

    // Scenario 2: Burst testing for peak load
    burst_test: {
      executor: 'constant-arrival-rate',
      rate: 12000, // 12K requests per second (20% above target)
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 500,
      maxVUs: 1500,
      startTime: '35m', // Start after ramp-up test
    },

    // Scenario 3: Sustained load test
    sustained_load: {
      executor: 'constant-arrival-rate',
      rate: 10000, // Target 10K TPS
      timeUnit: '1s',
      duration: '30m',
      preAllocatedVUs: 1000,
      maxVUs: 1200,
      startTime: '45m', // Start after burst test
    },
  },

  // Performance thresholds based on SLA requirements
  thresholds: {
    http_req_duration: [
      'p(95)<100',     // 95% of requests under 100ms
      'p(99)<250',     // 99% of requests under 250ms
      'avg<50',        // Average response time under 50ms
    ],
    http_req_failed: ['rate<0.01'], // Error rate under 1%
    errors: ['rate<0.01'],
    checks: ['rate>0.99'], // 99% of checks should pass
  },
};

// Generate realistic transaction data
function generateTransaction() {
  const transaction = {
    V1: (Math.random() - 0.5) * 4,   // Normal distribution ~ N(0,2)
    V2: (Math.random() - 0.5) * 4,
    V3: (Math.random() - 0.5) * 4,
    V4: (Math.random() - 0.5) * 4,
    V5: (Math.random() - 0.5) * 4,
    V6: (Math.random() - 0.5) * 4,
    V7: (Math.random() - 0.5) * 4,
    V8: (Math.random() - 0.5) * 4,
    V9: (Math.random() - 0.5) * 4,
    V10: (Math.random() - 0.5) * 4,
    V11: (Math.random() - 0.5) * 4,
    V12: (Math.random() - 0.5) * 4,
    V13: (Math.random() - 0.5) * 4,
    V14: (Math.random() - 0.5) * 4,
    V15: (Math.random() - 0.5) * 4,
    V16: (Math.random() - 0.5) * 4,
    V17: (Math.random() - 0.5) * 4,
    V18: (Math.random() - 0.5) * 4,
    V19: (Math.random() - 0.5) * 4,
    V20: (Math.random() - 0.5) * 4,
    V21: (Math.random() - 0.5) * 4,
    V22: (Math.random() - 0.5) * 4,
    V23: (Math.random() - 0.5) * 4,
    V24: (Math.random() - 0.5) * 4,
    V25: (Math.random() - 0.5) * 4,
    V26: (Math.random() - 0.5) * 4,
    V27: (Math.random() - 0.5) * 4,
    V28: (Math.random() - 0.5) * 4,
    Amount: Math.random() * 1000, // Transaction amount 0-1000
  };

  return transaction;
}

// Generate batch of transactions for realistic API usage
function generateBatch(size = 5) {
  const transactions = [];
  for (let i = 0; i < size; i++) {
    transactions.push(generateTransaction());
  }
  return { transactions };
}

export default function () {
  // Generate realistic payload
  const payload = JSON.stringify(generateBatch(Math.floor(Math.random() * 10) + 1));

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: '30s', // 30 second timeout
  };

  // Make prediction request
  const startTime = Date.now();
  const response = http.post(`${BASE_URL}/predict`, payload, params);
  const endTime = Date.now();

  // Record custom metrics
  requestCount.add(1);
  responseTime.add(endTime - startTime);

  // Validate response
  const isSuccess = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 100ms': (r) => r.timings.duration < 100,
    'response time < 250ms': (r) => r.timings.duration < 250,
    'has predictions': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.predictions && Array.isArray(body.predictions);
      } catch (e) {
        return false;
      }
    },
    'predictions are numbers': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.predictions.every(p => typeof p === 'number' && p >= 0 && p <= 1);
      } catch (e) {
        return false;
      }
    },
  });

  if (!isSuccess) {
    errorRate.add(1);
  }

  // Small random sleep to simulate realistic user behavior
  sleep(Math.random() * 0.1);
}

// Test lifecycle hooks
export function setup() {
  console.log('Starting Load Test');
  console.log(`Target: 10K+ TPS sustained load`);
  console.log(`SLA: p95 < 100ms, p99 < 250ms`);
  console.log(`API URL: ${BASE_URL}`);

  // Health check before starting load test
  const healthResponse = http.get(`${BASE_URL}/health`);
  if (healthResponse.status !== 200) {
    throw new Error(`Health check failed: ${healthResponse.status}`);
  }

  console.log('Health check passed - starting load test');
}

export function teardown(data) {
  console.log('Load Test Complete');
  console.log('Check the summary for detailed metrics');
}
