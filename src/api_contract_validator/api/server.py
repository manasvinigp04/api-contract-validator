"""
FastAPI Server for API Contract Validator

Provides REST endpoints for API validation, drift detection, and test generation.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Annotated
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl
import uvicorn
import aiofiles
import aiofiles.tempfile

from api_contract_validator import __version__
from api_contract_validator.config.loader import ConfigLoader, set_config
from api_contract_validator.config.logging import LoggerSetup
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.schema.contract.constraint_extractor import ConstraintExtractor
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.execution.runner.executor import TestExecutor
from api_contract_validator.execution.collector.result_collector import ResultCollector
from api_contract_validator.analysis.drift.detector import DriftDetector
from api_contract_validator.analysis.reasoning.analyzer import AIAnalyzer
from api_contract_validator.reporting.generator import ReportGenerator
from api_contract_validator.config.exceptions import ACVException

# Constants
SPEC_FILE_DESCRIPTION = "OpenAPI specification file (YAML or JSON)"
DEFAULT_SPEC_SUFFIX = ".yaml"

# Initialize FastAPI app
app = FastAPI(
    title="API Contract Validator",
    description="Multi-dimensional API contract validation system with intelligent drift detection",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure logging
logger = logging.getLogger("api_contract_validator.api")

# In-memory job storage (in production, use Redis or database)
validation_jobs: Dict[str, Dict[str, Any]] = {}


# Request/Response Models
class ValidationRequest(BaseModel):
    """Request model for API validation."""
    api_url: HttpUrl = Field(..., description="Base URL of the API to validate")
    parallel_workers: int = Field(default=10, ge=1, le=50, description="Number of parallel test executions")
    timeout_seconds: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    enable_ai_analysis: bool = Field(default=True, description="Enable AI-assisted analysis")
    output_format: str = Field(default="all", description="Output format: markdown, json, cli, or all")


class ValidationResponse(BaseModel):
    """Response model for validation request."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status: pending, running, completed, failed")
    message: str = Field(..., description="Status message")


class ValidationStatus(BaseModel):
    """Status model for validation job."""
    job_id: str
    status: str
    message: str
    progress: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class TestGenerationRequest(BaseModel):
    """Request model for test generation."""
    prioritize: bool = Field(default=True, description="Apply risk-based prioritization")
    max_tests_per_endpoint: int = Field(default=50, ge=1, le=500, description="Maximum tests per endpoint")


class ParsedSpec(BaseModel):
    """Response model for parsed specification."""
    title: str
    version: str
    description: Optional[str] = None
    base_url: Optional[str] = None
    endpoints_count: int
    endpoints: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime


# Endpoints

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "API Contract Validator",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "validate": "/validate",
            "parse": "/parse",
            "generate_tests": "/generate-tests",
            "status": "/status/{job_id}",
            "report": "/report/{job_id}/{format}",
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now(timezone.utc)
    )


@app.post("/validate", response_model=ValidationResponse, status_code=202, responses={
    400: {"description": "Invalid request or specification format"},
    500: {"description": "Internal server error during validation job creation"}
})
async def validate_api(
    spec_file: Annotated[UploadFile, File(description=SPEC_FILE_DESCRIPTION)],
    validation_request: Annotated[str, Form(description="JSON-encoded ValidationRequest")],
    background_tasks: Annotated[BackgroundTasks, BackgroundTasks()]
):
    """
    Validate an API against its specification.

    Returns a job ID that can be used to check status and retrieve results.
    """
    import json
    import uuid

    try:
        # Parse validation request
        request_data = json.loads(validation_request)
        request = ValidationRequest(**request_data)

        # Save uploaded file temporarily using async file operations
        content = await spec_file.read()
        suffix = Path(spec_file.filename).suffix if spec_file.filename else DEFAULT_SPEC_SUFFIX
        async with aiofiles.tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=suffix) as tmp_file:
            await tmp_file.write(content)
            tmp_file_name = str(tmp_file.name)

        tmp_path = Path(tmp_file_name)

        # Create job
        job_id = str(uuid.uuid4())
        validation_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "message": "Validation job created",
            "started_at": datetime.now(timezone.utc),
            "completed_at": None,
            "spec_path": tmp_path,
            "request": request,
            "result": None,
        }

        # Run validation in background
        background_tasks.add_task(run_validation, job_id, tmp_path, request)

        return ValidationResponse(
            job_id=job_id,
            status="pending",
            message="Validation job created and queued"
        )

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid validation request JSON: {e}")
    except Exception as e:
        logger.exception("Failed to create validation job")
        raise HTTPException(status_code=500, detail=f"Failed to create validation job: {str(e)}")


@app.post("/parse", response_model=ParsedSpec, responses={
    400: {"description": "Invalid specification format or parsing error"},
    500: {"description": "Internal server error during parsing"}
})
async def parse_specification(
    spec_file: Annotated[UploadFile, File(description=SPEC_FILE_DESCRIPTION)]
):
    """
    Parse and analyze an OpenAPI specification.

    Returns structured information about the API endpoints and schemas.
    """
    try:
        # Save uploaded file temporarily using async file operations
        content = await spec_file.read()
        suffix = Path(spec_file.filename).suffix if spec_file.filename else DEFAULT_SPEC_SUFFIX
        async with aiofiles.tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=suffix) as tmp_file:
            await tmp_file.write(content)
            tmp_file_name = str(tmp_file.name)

        tmp_path = Path(tmp_file_name)

        # Parse specification
        parser = OpenAPIParser()
        spec = parser.parse_file(tmp_path)

        # Clean up temp file
        tmp_path.unlink()

        # Build response
        endpoints_data = []
        for endpoint in spec.endpoints:
            endpoints_data.append({
                "method": endpoint.method.value,
                "path": endpoint.path,
                "operation_id": endpoint.operation_id,
                "summary": endpoint.summary,
                "parameters_count": len(endpoint.parameters) if endpoint.parameters else 0,
                "has_request_body": endpoint.request_body is not None,
                "responses": [r.status_code for r in endpoint.responses],
            })

        return ParsedSpec(
            title=spec.metadata.title,
            version=spec.metadata.version,
            description=spec.metadata.description,
            base_url=spec.metadata.base_url,
            endpoints_count=len(spec.endpoints),
            endpoints=endpoints_data
        )

    except ACVException as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse specification: {str(e)}")
    except Exception as e:
        logger.exception("Failed to parse specification")
        raise HTTPException(status_code=500, detail=f"Failed to parse specification: {str(e)}")


@app.post("/generate-tests", responses={
    400: {"description": "Invalid request or specification format"},
    500: {"description": "Internal server error during test generation"}
})
async def generate_tests(
    spec_file: Annotated[UploadFile, File(description=SPEC_FILE_DESCRIPTION)],
    request_data: Annotated[str, Form(description="JSON-encoded TestGenerationRequest")] = '{"prioritize": true, "max_tests_per_endpoint": 50}'
):
    """
    Generate test cases from an OpenAPI specification.

    Returns a comprehensive test suite with valid, invalid, and boundary test cases.
    """
    import json

    try:
        # Parse request
        req_dict = json.loads(request_data)
        request = TestGenerationRequest(**req_dict)

        # Save uploaded file temporarily using async file operations
        content = await spec_file.read()
        suffix = Path(spec_file.filename).suffix if spec_file.filename else DEFAULT_SPEC_SUFFIX
        async with aiofiles.tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=suffix) as tmp_file:
            await tmp_file.write(content)
            tmp_file_name = str(tmp_file.name)

        tmp_path = Path(tmp_file_name)

        # Parse specification
        parser = OpenAPIParser()
        spec = parser.parse_file(tmp_path)

        # Generate tests
        from api_contract_validator.config.models import TestGenerationConfig
        gen_config = TestGenerationConfig(
            enable_prioritization=request.prioritize,
            max_tests_per_endpoint=request.max_tests_per_endpoint,
        )
        generator = MasterTestGenerator(gen_config)
        test_suite = generator.generate_test_suite(spec)

        # Clean up temp file
        tmp_path.unlink()

        # Return test suite
        return JSONResponse(
            content={
                "total_tests": len(test_suite.test_cases),
                "valid_tests": len(test_suite.get_valid_tests()),
                "invalid_tests": len(test_suite.get_invalid_tests()),
                "boundary_tests": len(test_suite.get_boundary_tests()),
                "high_priority_tests": len(test_suite.get_high_priority_tests()) if request.prioritize else 0,
                "test_suite": test_suite.model_dump(mode="json")
            }
        )

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request JSON: {e}")
    except ACVException as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate tests: {str(e)}")
    except Exception as e:
        logger.exception("Failed to generate tests")
        raise HTTPException(status_code=500, detail=f"Failed to generate tests: {str(e)}")


@app.get("/status/{job_id}", response_model=ValidationStatus, responses={
    404: {"description": "Validation job not found"}
})
async def get_validation_status(job_id: str):
    """
    Get the status of a validation job.
    """
    if job_id not in validation_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = validation_jobs[job_id]
    return ValidationStatus(**job)


@app.get("/report/{job_id}/{format}", responses={
    400: {"description": "Job not completed or invalid format"},
    404: {"description": "Job or report not found"}
})
async def get_report(job_id: str, format: str):
    """
    Download a validation report in the specified format.

    Supported formats: json, markdown
    """
    if job_id not in validation_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = validation_jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not completed yet")

    if "report_paths" not in job:
        raise HTTPException(status_code=404, detail=f"Reports not available for job {job_id}")

    report_paths = job["report_paths"]

    if format not in report_paths:
        raise HTTPException(status_code=404, detail=f"Report format '{format}' not available. Available: {list(report_paths.keys())}")

    report_path = report_paths[format]

    if not Path(report_path).exists():
        raise HTTPException(status_code=404, detail=f"Report file not found: {report_path}")

    return FileResponse(
        path=report_path,
        filename=f"validation_report_{job_id}.{format}",
        media_type="application/json" if format == "json" else "text/markdown"
    )


# Background task for validation
def run_validation(job_id: str, spec_path: Path, request: ValidationRequest):
    """
    Background task to run validation.
    """
    job = validation_jobs[job_id]

    try:
        job["status"] = "running"
        job["message"] = "Validation in progress"

        # Load configuration
        config = ConfigLoader.load()
        config.execution.parallel_workers = request.parallel_workers
        config.execution.timeout_seconds = request.timeout_seconds
        config.ai_analysis.enabled = request.enable_ai_analysis
        set_config(config)
        LoggerSetup.setup(config.logging)

        # Parse specification
        parser = OpenAPIParser()
        unified_spec = parser.parse_file(spec_path)

        # Extract contract rules
        extractor = ConstraintExtractor(unified_spec)
        api_contract = extractor.extract_contract()

        # Generate test cases
        generator = MasterTestGenerator(config.test_generation)
        test_suite = generator.generate_test_suite(unified_spec)

        # Execute tests
        executor = TestExecutor(str(request.api_url), config.execution)
        test_results = executor.execute_tests_sync(test_suite.test_cases)

        collector = ResultCollector()
        collector.add_results(test_results)
        execution_summary = collector.get_summary()

        # Detect drift
        drift_detector = DriftDetector(api_contract, config.drift_detection)
        drift_report = drift_detector.detect_drift(execution_summary)
        drift_report.api_url = str(request.api_url)

        # AI-assisted analysis
        analysis_result = None
        if config.ai_analysis.enabled and request.enable_ai_analysis:
            try:
                ai_analyzer = AIAnalyzer(config.ai_analysis)
                analysis_result = ai_analyzer.analyze_drift(drift_report)
            except Exception as e:
                logger.warning(f"AI analysis failed: {e}")

        # Generate reports
        output_dir = Path(config.reporting.output_directory)
        from rich.console import Console
        report_generator = ReportGenerator(config, Console())
        report_paths = report_generator.generate_reports(
            drift_report=drift_report,
            analysis_result=analysis_result,
            output_format=request.output_format,
            output_dir=output_dir,
        )

        # Update job status
        job["status"] = "completed"
        job["message"] = "Validation completed successfully"
        job["completed_at"] = datetime.now(timezone.utc)
        job["result"] = {
            "total_tests": execution_summary.total,
            "passed": execution_summary.passed,
            "failed": execution_summary.failed,
            "total_drift_issues": drift_report.summary.total_issues,
            "critical_issues": drift_report.summary.critical_count,
            "has_critical_issues": drift_report.has_critical_issues(),
        }
        job["report_paths"] = {k: str(v) for k, v in report_paths.items()}

        # Clean up temp file
        spec_path.unlink(missing_ok=True)

    except Exception as e:
        logger.exception(f"Validation job {job_id} failed")
        job["status"] = "failed"
        job["message"] = f"Validation failed: {str(e)}"
        job["completed_at"] = datetime.now(timezone.utc)

        # Clean up temp file
        spec_path.unlink(missing_ok=True)


def create_app() -> FastAPI:
    """Factory function to create FastAPI app."""
    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info"
):
    """
    Run the FastAPI server with uvicorn.

    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
        log_level: Log level (debug, info, warning, error)
    """
    uvicorn.run(
        "api_contract_validator.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    run_server(reload=True)
