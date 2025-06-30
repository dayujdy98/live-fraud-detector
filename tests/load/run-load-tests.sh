#!/bin/bash

# Load Testing Automation Script for Fraud Detection API
# This script runs comprehensive load tests and generates performance reports

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_URL="${API_URL:-http://localhost:8000}"
RESULTS_DIR="${SCRIPT_DIR}/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE} Fraud Detection API Load Testing Suite${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW} Checking prerequisites...${NC}"

    if ! command -v k6 &> /dev/null; then
        echo -e "${RED} k6 is not installed. Please install from: https://k6.io/docs/get-started/installation/${NC}"
        exit 1
    fi

    if ! command -v curl &> /dev/null; then
        echo -e "${RED} curl is not installed${NC}"
        exit 1
    fi

    echo -e "${GREEN} Prerequisites check passed${NC}"
}

# Health check
health_check() {
    echo -e "${YELLOW} Performing API health check...${NC}"

    if curl -s --max-time 10 "${API_URL}/health" > /dev/null; then
        echo -e "${GREEN} API is healthy and responsive${NC}"
    else
        echo -e "${RED} API health check failed. Please ensure the API is running at ${API_URL}${NC}"
        exit 1
    fi
}

# Create results directory
setup_results_dir() {
    mkdir -p "${RESULTS_DIR}"
    echo -e "${GREEN}Results will be saved to: ${RESULTS_DIR}${NC}"
}

# Run load tests
run_load_tests() {
    echo -e "${YELLOW} Running comprehensive load tests...${NC}"

    # Quick smoke test first
    echo -e "${BLUE} Running smoke test (100 requests)...${NC}"
    k6 run \
        --vus 10 \
        --duration 10s \
        --env API_URL="${API_URL}" \
        --summary-export="${RESULTS_DIR}/smoke_test_${TIMESTAMP}.json" \
        "${SCRIPT_DIR}/k6-smoke-test.js"

    if [ $? -ne 0 ]; then
        echo -e "${RED} Smoke test failed. Aborting load tests.${NC}"
        exit 1
    fi

    echo -e "${GREEN} Smoke test passed${NC}"

    # Main load test
    echo -e "${BLUE} Running main load test (targeting 10K+ TPS)...${NC}"
    k6 run \
        --env API_URL="${API_URL}" \
        --summary-export="${RESULTS_DIR}/load_test_${TIMESTAMP}.json" \
        --out csv="${RESULTS_DIR}/load_test_${TIMESTAMP}.csv" \
        "${SCRIPT_DIR}/k6-load-test.js"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN} Load test completed successfully${NC}"
    else
        echo -e "${YELLOW}Load test completed with some threshold violations${NC}"
    fi
}

# Generate performance report
generate_report() {
    echo -e "${YELLOW} Generating performance report...${NC}"

    REPORT_FILE="${RESULTS_DIR}/performance_report_${TIMESTAMP}.md"

    cat > "${REPORT_FILE}" << EOF
# Performance Test Report

**Test Date:** $(date)
**API Endpoint:** ${API_URL}
**Test Duration:** ~75 minutes (including ramp-up, burst, and sustained load)


## Key Findings

$(if [ -f "${RESULTS_DIR}/load_test_${TIMESTAMP}.json" ]; then
    echo "### Load Test Results"
    echo "\`\`\`json"
    cat "${RESULTS_DIR}/load_test_${TIMESTAMP}.json" | jq '.metrics' 2>/dev/null || echo "Raw JSON data available in results file"
    echo "\`\`\`"
else
    echo "Load test results not found. Check test execution logs."
fi)


# Main execution
main() {
    echo -e "${BLUE}Starting load test execution...${NC}"
    echo "API URL: ${API_URL}"
    echo "Timestamp: ${TIMESTAMP}"
    echo ""

    check_prerequisites
    health_check
    setup_results_dir
    run_load_tests
    generate_report

    echo ""
    echo -e "${GREEN} Load testing complete!${NC}"
    echo -e "${BLUE} Results available in: ${RESULTS_DIR}${NC}"
    echo -e "${BLUE} Report: ${RESULTS_DIR}/performance_report_${TIMESTAMP}.md${NC}"
}

# Handle script arguments
case "${1:-}" in
    "smoke")
        echo -e "${YELLOW} Running smoke test only...${NC}"
        check_prerequisites
        health_check
        setup_results_dir
        k6 run --vus 10 --duration 30s --env API_URL="${API_URL}" "${SCRIPT_DIR}/k6-smoke-test.js"
        ;;
    "quick")
        echo -e "${YELLOW} Running quick load test (5 minutes)...${NC}"
        check_prerequisites
        health_check
        setup_results_dir
        k6 run --vus 100 --duration 5m --env API_URL="${API_URL}" "${SCRIPT_DIR}/k6-load-test.js"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [smoke|quick|help]"
        echo ""
        echo "Options:"
        echo "  smoke    Run smoke test only (30 seconds, 10 VUs)"
        echo "  quick    Run quick load test (5 minutes, 100 VUs)"
        echo "  help     Show this help message"
        echo "  (no args) Run full comprehensive load test suite"
        ;;
    *)
        main
        ;;
esac
