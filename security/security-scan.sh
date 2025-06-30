#!/bin/bash

# Comprehensive Security Scanning Suite for Fraud Detection System
# This script runs multiple security scanners and generates a consolidated report

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="${SCRIPT_DIR}/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}MLOps Security Scanning Suite${NC}"
echo -e "${BLUE}=============================${NC}"

# Create reports directory
mkdir -p "${REPORTS_DIR}"

# Check and install security tools
install_security_tools() {
    echo -e "${YELLOW}Installing/updating security scanning tools...${NC}"

    # Install Python security tools
    pip install bandit safety semgrep pip-audit

    # Install additional security tools if not present
    if ! command -v trivy &> /dev/null; then
        echo -e "${YELLOW}Installing Trivy container scanner...${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install trivy
        else
            # Linux installation
            curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
        fi
    fi

    echo -e "${GREEN}Security tools installation complete${NC}"
}

# Python code security scanning with Bandit
run_bandit_scan() {
    echo -e "${YELLOW}Running Bandit Python security scan...${NC}"

    bandit -r "${PROJECT_ROOT}/src" \
        -f json \
        -o "${REPORTS_DIR}/bandit_report_${TIMESTAMP}.json" \
        -ll \
        --exclude "${PROJECT_ROOT}/src/training/test_*" \
        || true

    bandit -r "${PROJECT_ROOT}/src" \
        -f txt \
        -o "${REPORTS_DIR}/bandit_report_${TIMESTAMP}.txt" \
        -ll \
        --exclude "${PROJECT_ROOT}/src/training/test_*" \
        || true

    # Generate summary
    echo -e "${GREEN}Bandit scan complete${NC}"
    if [ -f "${REPORTS_DIR}/bandit_report_${TIMESTAMP}.json" ]; then
        BANDIT_ISSUES=$(cat "${REPORTS_DIR}/bandit_report_${TIMESTAMP}.json" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    high = len([r for r in data.get('results', []) if r.get('issue_severity') == 'HIGH'])
    medium = len([r for r in data.get('results', []) if r.get('issue_severity') == 'MEDIUM'])
    low = len([r for r in data.get('results', []) if r.get('issue_severity') == 'LOW'])
    print(f'High: {high}, Medium: {medium}, Low: {low}')
except:
    print('0, 0, 0')
" 2>/dev/null || echo "0, 0, 0")
        echo -e "${BLUE}Bandit Results: ${BANDIT_ISSUES}${NC}"
    fi
}

# Python dependency vulnerability scanning with Safety
run_safety_scan() {
    echo -e "${YELLOW}Running Safety dependency vulnerability scan...${NC}"

    # Generate requirements for scanning
    pip freeze > "${REPORTS_DIR}/current_requirements.txt"

    safety check \
        --json \
        --output "${REPORTS_DIR}/safety_report_${TIMESTAMP}.json" \
        || true

    safety check \
        --output "${REPORTS_DIR}/safety_report_${TIMESTAMP}.txt" \
        || true

    echo -e "${GREEN} Safety scan complete${NC}"
    if [ -f "${REPORTS_DIR}/safety_report_${TIMESTAMP}.json" ]; then
        SAFETY_VULNS=$(cat "${REPORTS_DIR}/safety_report_${TIMESTAMP}.json" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data.get('vulnerabilities', [])))
except:
    print('0')
" 2>/dev/null || echo "0")
        echo -e "${BLUE} Safety Results: ${SAFETY_VULNS} vulnerabilities found${NC}"
    fi
}

# Advanced Python security scanning with Semgrep
run_semgrep_scan() {
    echo -e "${YELLOW} Running Semgrep advanced security scan...${NC}"

    semgrep \
        --config=auto \
        --json \
        --output="${REPORTS_DIR}/semgrep_report_${TIMESTAMP}.json" \
        "${PROJECT_ROOT}/src" \
        || true

    semgrep \
        --config=auto \
        --output="${REPORTS_DIR}/semgrep_report_${TIMESTAMP}.txt" \
        "${PROJECT_ROOT}/src" \
        || true

    echo -e "${GREEN} Semgrep scan complete${NC}"
}

# Python package audit
run_pip_audit() {
    echo -e "${YELLOW} Running pip-audit for known vulnerabilities...${NC}"

    pip-audit \
        --format=json \
        --output="${REPORTS_DIR}/pip_audit_${TIMESTAMP}.json" \
        || true

    pip-audit \
        --output="${REPORTS_DIR}/pip_audit_${TIMESTAMP}.txt" \
        || true

    echo -e "${GREEN} pip-audit scan complete${NC}"
}

# Container security scanning with Trivy
run_trivy_scan() {
    echo -e "${YELLOW} Running Trivy container security scan...${NC}"

    # Scan the Dockerfile and requirements
    trivy fs \
        --format json \
        --output "${REPORTS_DIR}/trivy_fs_${TIMESTAMP}.json" \
        "${PROJECT_ROOT}" \
        || true

    trivy fs \
        --format table \
        --output "${REPORTS_DIR}/trivy_fs_${TIMESTAMP}.txt" \
        "${PROJECT_ROOT}" \
        || true

    # If Docker image exists, scan it
    if docker images | grep -q "fraud-detection-api"; then
        echo -e "${YELLOW}Scanning Docker image...${NC}"
        trivy image \
            --format json \
            --output "${REPORTS_DIR}/trivy_image_${TIMESTAMP}.json" \
            fraud-detection-api:latest \
            || true

        trivy image \
            --format table \
            --output "${REPORTS_DIR}/trivy_image_${TIMESTAMP}.txt" \
            fraud-detection-api:latest \
            || true
    fi

    echo -e "${GREEN} Trivy scan complete${NC}"
}

# Infrastructure security scanning
run_infrastructure_scan() {
    echo -e "${YELLOW}  Running infrastructure security scan...${NC}"

    # Scan Terraform files if tfsec is available
    if command -v tfsec &> /dev/null; then
        tfsec \
            --format json \
            --out "${REPORTS_DIR}/tfsec_${TIMESTAMP}.json" \
            "${PROJECT_ROOT}/infra" \
            || true

        tfsec \
            --out "${REPORTS_DIR}/tfsec_${TIMESTAMP}.txt" \
            "${PROJECT_ROOT}/infra" \
            || true
    else
        echo -e "${YELLOW}  tfsec not found, skipping Terraform security scan${NC}"
        echo "Install with: brew install tfsec (macOS) or see https://github.com/aquasecurity/tfsec"
    fi

    # Scan for secrets in codebase
    if command -v gitleaks &> /dev/null; then
        gitleaks detect \
            --source "${PROJECT_ROOT}" \
            --report-format json \
            --report-path "${REPORTS_DIR}/gitleaks_${TIMESTAMP}.json" \
            || true
    else
        echo -e "${YELLOW}  gitleaks not found, skipping secrets scan${NC}"
        echo "Install with: brew install gitleaks (macOS) or see https://github.com/zricethezav/gitleaks"
    fi

    echo -e "${GREEN} Infrastructure scan complete${NC}"
}

# Generate consolidated security report
generate_security_report() {
    echo -e "${YELLOW} Generating consolidated security report...${NC}"

    REPORT_FILE="${REPORTS_DIR}/security_report_${TIMESTAMP}.md"

    cat > "${REPORT_FILE}" << EOF
# Security Scan Report

**Scan Date:** $(date)
**Project:** Live Fraud Detection System
**Scan ID:** ${TIMESTAMP}

## Executive Summary

This report provides a comprehensive security assessment of the MLOps fraud detection system, covering:
- Python code security vulnerabilities
- Dependency vulnerabilities
- Container security issues
- Infrastructure configuration security
- Secrets and credential exposure

## Detailed Findings

### 1. Python Code Security (Bandit)

**Purpose:** Identifies common security issues in Python code including:
- SQL injection vulnerabilities
- Shell injection risks
- Hardcoded passwords/secrets
- Insecure random number generation
- Unsafe deserialization

**Results:**
$(if [ -f "${REPORTS_DIR}/bandit_report_${TIMESTAMP}.txt" ]; then
    echo "\`\`\`"
    head -20 "${REPORTS_DIR}/bandit_report_${TIMESTAMP}.txt" || echo "Bandit scan results available in detailed report"
    echo "\`\`\`"
else
    echo "Bandit scan not completed"
fi)

### 2. Dependency Vulnerabilities (Safety)

**Purpose:** Scans Python dependencies for known security vulnerabilities

**Results:**
$(if [ -f "${REPORTS_DIR}/safety_report_${TIMESTAMP}.txt" ]; then
    echo "\`\`\`"
    head -20 "${REPORTS_DIR}/safety_report_${TIMESTAMP}.txt" || echo "Safety scan results available in detailed report"
    echo "\`\`\`"
else
    echo "Safety scan not completed"
fi)

### 3. Container Security (Trivy)

**Purpose:** Scans container images and filesystem for vulnerabilities

**Results:**
$(if [ -f "${REPORTS_DIR}/trivy_fs_${TIMESTAMP}.txt" ]; then
    echo "\`\`\`"
    head -20 "${REPORTS_DIR}/trivy_fs_${TIMESTAMP}.txt" || echo "Trivy scan results available in detailed report"
    echo "\`\`\`"
else
    echo "Trivy scan not completed"
fi)

### 4. Infrastructure Security (tfsec)

**Purpose:** Analyzes Terraform configurations for security misconfigurations

**Results:**
$(if [ -f "${REPORTS_DIR}/tfsec_${TIMESTAMP}.txt" ]; then
    echo "\`\`\`"
    head -20 "${REPORTS_DIR}/tfsec_${TIMESTAMP}.txt" || echo "tfsec scan results available in detailed report"
    echo "\`\`\`"
else
    echo "tfsec scan not completed - install tfsec for infrastructure security scanning"
fi)

EOF
}

# Main execution
main() {
    echo -e "${BLUE}Starting comprehensive security scan...${NC}"
    echo "Project: ${PROJECT_ROOT}"
    echo "Reports: ${REPORTS_DIR}"
    echo "Timestamp: ${TIMESTAMP}"
    echo ""

    install_security_tools
    run_bandit_scan
    run_safety_scan
    run_semgrep_scan
    run_pip_audit
    run_trivy_scan
    run_infrastructure_scan
    generate_security_report

    echo ""
    echo -e "${GREEN} Security scanning complete!${NC}"
    echo -e "${BLUE} Reports available in: ${REPORTS_DIR}${NC}"
    echo -e "${BLUE}Consolidated report: ${REPORTS_DIR}/security_report_${TIMESTAMP}.md${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Review the consolidated security report"
    echo "2. Address any high-severity findings"
    echo "3. Integrate security scanning into CI/CD pipeline"
    echo "4. Schedule regular security assessments"
}

# Handle script arguments
case "${1:-}" in
    "quick")
        echo -e "${YELLOW} Running quick security scan...${NC}"
        mkdir -p "${REPORTS_DIR}"
        run_bandit_scan
        run_safety_scan
        echo -e "${GREEN} Quick scan complete${NC}"
        ;;
    "deps")
        echo -e "${YELLOW} Scanning dependencies only...${NC}"
        mkdir -p "${REPORTS_DIR}"
        run_safety_scan
        run_pip_audit
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [quick|deps|help]"
        echo ""
        echo "Options:"
        echo "  quick    Run quick scan (Bandit + Safety only)"
        echo "  deps     Scan dependencies only (Safety + pip-audit)"
        echo "  help     Show this help message"
        echo "  (no args) Run comprehensive security scan suite"
        ;;
    *)
        main
        ;;
esac
