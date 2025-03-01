#!/bin/bash

# Simple script to run tests in each service directory separately

SERVICES_DIR="services"
SERVICES=("arxiv_mailer" "data_layer" "arxiv_processor" "nvd_checker")

echo "===================================="
echo "Running tests for each service"
echo "===================================="

# Track overall exit status
OVERALL_STATUS=0

# Run tests for each service in their own directory
for SERVICE in "${SERVICES[@]}"; do
    SERVICE_PATH="${SERVICES_DIR}/${SERVICE}"
    
    # Check if service directory exists
    if [ -d "$SERVICE_PATH" ]; then
        echo ""
        echo "===================================="
        echo "Running tests for $SERVICE"
        echo "===================================="
        
        # Change to service directory and run tests
        pushd "$SERVICE_PATH" > /dev/null
        
        if [ -d "tests" ]; then
            # Use a temporary file to store output
            TEMP_OUTPUT=$(mktemp)
            
            # First run tests in quiet mode to check for failures
            python -m pytest tests -q --cov=src "$@" > "$TEMP_OUTPUT" 2>&1
            STATUS=$?
            
            # Only show the coverage report section
            sed -n '/^---------- coverage:/,/^$/p' "$TEMP_OUTPUT"
            
            # If tests failed, run again with verbose mode to get detailed error info
            if [ $STATUS -ne 0 ]; then
                echo ""
                echo "FAILURES:"
                
                # Run the failing tests with verbose output
                python -m pytest tests -v --no-header --tb=native --cov=src --no-cov-on-fail "$@"
                
                OVERALL_STATUS=1
                echo "Tests for $SERVICE FAILED with status $STATUS"
            else
                echo "Tests for $SERVICE PASSED"
            fi
            
            # Clean up
            rm "$TEMP_OUTPUT"
        else
            echo "No tests directory found for $SERVICE"
        fi
        
        # Return to original directory
        popd > /dev/null
    else
        echo "Service directory $SERVICE_PATH not found, skipping..."
    fi
done

echo ""
echo "===================================="
echo "Test run complete"
echo "===================================="

exit $OVERALL_STATUS 