#!/bin/bash
# Demo Validation Runner
# Runs ACV validation against mock APIs and saves reports

set -e

DEMO_DIR="/Users/I764709/api-contract-validator/demo"
ACV_CMD="python -m api_contract_validator.cli.main"

echo "=========================================="
echo "ACV Demo Validation Runner"
echo "=========================================="
echo ""

# Check if in correct directory
if [ ! -d "$DEMO_DIR" ]; then
    echo "Error: Demo directory not found at $DEMO_DIR"
    exit 1
fi

cd /Users/I764709/api-contract-validator

# Function to check if server is running
check_server() {
    local url=$1
    local max_attempts=30
    local attempt=1

    echo "Waiting for server at $url..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo "✓ Server is ready"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 1
        ((attempt++))
    done

    echo "✗ Server failed to start"
    return 1
}

# Function to run validation
run_validation() {
    local name=$1
    local spec=$2
    local url=$3
    local output_dir=$4

    echo ""
    echo "=========================================="
    echo "Validating: $name"
    echo "=========================================="
    echo "Spec: $spec"
    echo "API: $url"
    echo "Output: $output_dir"
    echo ""

    $ACV_CMD validate "$spec" \
        --api-url "$url" \
        --output-dir "$output_dir" \
        --parallel 5 \
        --timeout 30 \
        2>&1 | tee "$output_dir/validation.log"

    echo ""
    echo "✓ Validation complete for $name"
    echo "  Reports saved to: $output_dir"
    echo ""
}

# Scenario 1: E-Commerce API
echo "=========================================="
echo "SCENARIO 1: E-Commerce Platform API"
echo "=========================================="
echo ""

echo "Starting e-commerce mock server..."
python "$DEMO_DIR/mock-apis/ecommerce_mock.py" > "$DEMO_DIR/outputs/ecommerce/server.log" 2>&1 &
ECOMMERCE_PID=$!
echo "Server PID: $ECOMMERCE_PID"

# Wait for server to start
if check_server "http://localhost:8080/v2/products"; then
    run_validation \
        "E-Commerce API" \
        "$DEMO_DIR/specs/e-commerce-api.yaml" \
        "http://localhost:8080/v2" \
        "$DEMO_DIR/outputs/ecommerce"

    # Save sample requests
    echo "Saving sample API responses..."
    curl -s http://localhost:8080/v2/products > "$DEMO_DIR/outputs/ecommerce/sample_products.json"
    curl -s http://localhost:8080/v2/cart > "$DEMO_DIR/outputs/ecommerce/sample_cart.json"
else
    echo "Failed to start e-commerce server"
fi

echo "Stopping e-commerce server (PID: $ECOMMERCE_PID)..."
kill $ECOMMERCE_PID 2>/dev/null || true
sleep 2

# Scenario 2: Healthcare API
echo ""
echo "=========================================="
echo "SCENARIO 2: Healthcare API"
echo "=========================================="
echo ""

echo "Starting healthcare mock server..."
python "$DEMO_DIR/mock-apis/healthcare_mock.py" > "$DEMO_DIR/outputs/healthcare/server.log" 2>&1 &
HEALTHCARE_PID=$!
echo "Server PID: $HEALTHCARE_PID"

# Wait for server to start
if check_server "http://localhost:9000/v3/doctors"; then
    run_validation \
        "Healthcare API" \
        "$DEMO_DIR/specs/healthcare-api.yaml" \
        "http://localhost:9000/v3" \
        "$DEMO_DIR/outputs/healthcare"

    # Save sample requests
    echo "Saving sample API responses..."
    curl -s http://localhost:9000/v3/doctors > "$DEMO_DIR/outputs/healthcare/sample_doctors.json"
else
    echo "Failed to start healthcare server"
fi

echo "Stopping healthcare server (PID: $HEALTHCARE_PID)..."
kill $HEALTHCARE_PID 2>/dev/null || true

# Summary
echo ""
echo "=========================================="
echo "VALIDATION COMPLETE"
echo "=========================================="
echo ""
echo "Reports generated:"
echo "  E-Commerce: $DEMO_DIR/outputs/ecommerce/"
echo "  Healthcare: $DEMO_DIR/outputs/healthcare/"
echo ""
echo "View reports:"
echo "  cat $DEMO_DIR/outputs/ecommerce/drift_report_*.md"
echo "  cat $DEMO_DIR/outputs/healthcare/drift_report_*.md"
echo ""
