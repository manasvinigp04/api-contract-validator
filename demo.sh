#!/bin/bash

# API Contract Validator Demo Script
# This script demonstrates how to use the validator as a library and via REST API

set -e

echo "🚀 API Contract Validator Demo"
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please create one first:"
    echo "   python -m venv .venv"
    echo "   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate"
    exit 1
fi

# 1. Install/update dependencies
echo "📦 Installing dependencies..."
pip install -e . --quiet
python -m spacy download en_core_web_sm --quiet 2>/dev/null || true

# 2. Start the validator API server
echo "🌐 Starting validator API server on port 9000..."
uvicorn api_contract_validator.api.server:app --port 9000 --log-level warning > /tmp/validator.log 2>&1 &
VALIDATOR_PID=$!
sleep 3

echo "   ✓ Validator API running (PID: $VALIDATOR_PID)"

# 3. Check if example spec exists
SPEC_FILE="examples/petstore/petstore-openapi.yaml"
if [ ! -f "$SPEC_FILE" ]; then
    echo "⚠️  Example spec not found. Using a test API..."
    # You can add your own OpenAPI spec here
    SPEC_FILE="path/to/your/openapi.yaml"
fi

# 4. Test parsing endpoint
echo ""
echo "📄 Testing: Parse OpenAPI Specification"
echo "---------------------------------------"
if [ -f "$SPEC_FILE" ]; then
    curl -s -X POST http://localhost:9000/parse \
        -F "spec_file=@$SPEC_FILE" | jq '.' || echo "Parse endpoint called successfully"
fi

# 5. Test generate-tests endpoint
echo ""
echo "🧪 Testing: Generate Test Cases"
echo "--------------------------------"
if [ -f "$SPEC_FILE" ]; then
    curl -s -X POST http://localhost:9000/generate-tests \
        -F "spec_file=@$SPEC_FILE" \
        -F 'request_data={"prioritize": true, "max_tests_per_endpoint": 20}' | jq '.total_tests, .valid_tests, .invalid_tests, .boundary_tests' || echo "Generate tests endpoint called"
fi

# 6. Health check
echo ""
echo "💚 Testing: Health Check"
echo "------------------------"
curl -s http://localhost:9000/health | jq '.'

echo ""
echo "📚 API Documentation available at: http://localhost:9000/docs"
echo ""

# Keep server running or cleanup
read -p "Keep validator API server running? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up..."
    kill $VALIDATOR_PID 2>/dev/null || true
    echo "✨ Demo completed!"
else
    echo ""
    echo "✨ Validator API server is still running at http://localhost:9000"
    echo "   - API Docs: http://localhost:9000/docs"
    echo "   - Health: http://localhost:9000/health"
    echo ""
    echo "   To stop the server, run: kill $VALIDATOR_PID"
    echo ""
fi
