#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

check_service() {
    local service=$1
    local health_json=$(curl -s http://localhost:4566/_localstack/health)
    if echo "$health_json" | grep -q "\"$service\": \"running\""; then
        echo -e "${GREEN}✓${NC} $service is running"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not running"
        return 1
    fi
}

# Wait for LocalStack to be available
wait_for_localstack() {
    echo -e "${BLUE}Waiting for LocalStack to be available...${NC}"
    until curl -s http://localhost:4566/_localstack/health > /dev/null; do
        echo "Waiting..."
        sleep 2
    done
}

# Main health check
main() {
    wait_for_localstack

    echo -e "\n${BLUE}Checking LocalStack services...${NC}"
    
    local failed=0
    
    # Check each required service
    services=("s3" "ssm" "ses" "lambda" "logs" "iam")
    for service in "${services[@]}"; do
        check_service "$service" || ((failed++))
    done

    echo ""
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}All services are running!${NC}"
        return 0
    else
        echo -e "${RED}$failed service(s) are not running properly${NC}"
        return 1
    fi
}

main
