# FastAPI Server for API Contract Validator

This module provides a REST API server for the API Contract Validator using FastAPI and Uvicorn.

## Quick Start

### Install Dependencies

```bash
pip install -e .
python -m spacy download en_core_web_sm
```

### Start Server

#### Development Mode (with auto-reload)
```bash
uvicorn api_contract_validator.api.server:app --reload --host 0.0.0.0 --port 8000
```

#### Production Mode
```bash
uvicorn api_contract_validator.api.server:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Direct Python Execution
```bash
python -m api_contract_validator.api.server
# or
python src/api_contract_validator/api/server.py
```

### Debugging in VS Code

1. Open the project in VS Code
2. Press `F5` or go to "Run and Debug"
3. Select **"FastAPI: Uvicorn Server (Development)"**
4. The server starts with breakpoint support

The debugger configuration is in `.vscode/launch.json`.

## API Documentation

Once the server is running, visit:
- **Interactive API docs (Swagger)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/validate` | POST | Validate API against spec (async job) |
| `/parse` | POST | Parse OpenAPI specification |
| `/generate-tests` | POST | Generate test cases |
| `/status/{job_id}` | GET | Get validation job status |
| `/report/{job_id}/{format}` | GET | Download validation report |

### Usage Examples

#### Parse OpenAPI Spec
```bash
curl -X POST http://localhost:8000/parse \
  -F "spec_file=@path/to/openapi.yaml"
```

#### Generate Tests
```bash
curl -X POST http://localhost:8000/generate-tests \
  -F "spec_file=@openapi.yaml" \
  -F 'request_data={"prioritize": true, "max_tests_per_endpoint": 50}'
```

#### Full Validation Workflow
```bash
# 1. Submit validation job
curl -X POST http://localhost:8000/validate \
  -F "spec_file=@openapi.yaml" \
  -F 'validation_request={"api_url": "https://api.example.com", "parallel_workers": 10, "timeout_seconds": 30, "enable_ai_analysis": true}' \
  > job.json

# 2. Check status
JOB_ID=$(cat job.json | jq -r '.job_id')
curl http://localhost:8000/status/$JOB_ID

# 3. Download reports (when completed)
curl http://localhost:8000/report/$JOB_ID/json -o report.json
curl http://localhost:8000/report/$JOB_ID/markdown -o report.md
```

## Configuration

Configure via environment variables:

```bash
export ANTHROPIC_API_KEY="your-api-key"
export AI_ANALYSIS_ENABLED="true"
export PARALLEL_WORKERS="10"
export TIMEOUT_SECONDS="30"
export OUTPUT_DIRECTORY="./reports"
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Server                    │
│                  (api/server.py)                    │
└─────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────┐    ┌──────────┐
   │  Parse  │    │ Generate │    │ Validate │
   │  Spec   │    │  Tests   │    │   API    │
   └─────────┘    └──────────┘    └──────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
   ┌────────────┐                  ┌─────────────┐
   │   Parser   │                  │  Executor   │
   │   Engine   │                  │   Engine    │
   └────────────┘                  └─────────────┘
                                           │
        ┌──────────────────────────────────┤
        │                                  │
        ▼                                  ▼
   ┌────────────┐                  ┌─────────────┐
   │   Drift    │                  │     AI      │
   │  Detector  │                  │  Analyzer   │
   └────────────┘                  └─────────────┘
```

## Features

- **Async Job Processing**: Long-running validations run in background
- **Interactive Documentation**: Auto-generated Swagger UI
- **File Upload Support**: Upload OpenAPI specs via multipart/form-data
- **Flexible Output**: JSON and Markdown reports
- **RESTful Design**: Standard HTTP methods and status codes
- **Health Monitoring**: Built-in health check endpoint
- **Debug Support**: VS Code launch configurations included

## Deployment

### Docker (Recommended for Production)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

COPY . .
RUN pip install -e .

EXPOSE 8000

CMD ["uvicorn", "api_contract_validator.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t api-contract-validator .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY api-contract-validator
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-contract-validator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-contract-validator
  template:
    metadata:
      labels:
        app: api-contract-validator
    spec:
      containers:
      - name: api-contract-validator
        image: api-contract-validator:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: anthropic-api-key
---
apiVersion: v1
kind: Service
metadata:
  name: api-contract-validator
spec:
  selector:
    app: api-contract-validator
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Security Considerations

- Always use HTTPS in production
- Implement authentication/authorization for production deployments
- Use API keys for AI analysis (ANTHROPIC_API_KEY)
- Limit file upload sizes
- Validate and sanitize all inputs
- Use rate limiting to prevent abuse

## Performance Tips

- Use multiple workers in production: `--workers 4`
- Enable connection pooling for httpx
- Use Redis for job storage instead of in-memory dict
- Cache parsed specifications
- Set appropriate timeouts

## Troubleshooting

### Import Errors
```bash
# Ensure package is installed
pip install -e .

# Verify PYTHONPATH includes src directory
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

### Port Already in Use
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn api_contract_validator.api.server:app --port 8001
```

### AI Analysis Fails
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Or disable AI analysis
curl ... -F 'validation_request={"...", "enable_ai_analysis": false}'
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

### Adding New Endpoints

1. Add endpoint function to `server.py`
2. Define request/response models with Pydantic
3. Add route decorator with proper method and path
4. Update this README with endpoint documentation
5. Test via `/docs` interface

## License

MIT License - See LICENSE file for details
