"""
Shared pytest fixtures for API Contract Validator tests.
"""

import json
from pathlib import Path
from typing import Dict, List

import pytest

from api_contract_validator.config.models import (
    AIAnalysisConfig,
    DriftDetectionConfig,
    ExecutionConfig,
    LoggingConfig,
    ReportingConfig,
    TestGenerationConfig,
)
from api_contract_validator.generation.base import TestCase, TestCaseType
from api_contract_validator.input.normalizer.models import (
    APIMetadata,
    Endpoint,
    FieldConstraint,
    FieldDefinition,
    FieldType,
    HTTPMethod,
    Parameter,
    RequestBody,
    ResponseBody,
    SourceType,
    UnifiedAPISpec,
)
from api_contract_validator.schema.contract.contract_model import APIContract, EndpointContract


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def default_execution_config():
    """Default execution configuration."""
    return ExecutionConfig(
        parallel_workers=5,
        timeout_seconds=10,
        retry_attempts=2,
        retry_delay_seconds=0.5,
    )


@pytest.fixture
def default_test_generation_config():
    """Default test generation configuration."""
    return TestGenerationConfig(
        generate_valid=True,
        generate_invalid=True,
        generate_boundary=True,
        max_tests_per_endpoint=50,
        enable_prioritization=True,
    )


@pytest.fixture
def default_drift_detection_config():
    """Default drift detection configuration."""
    return DriftDetectionConfig(
        detect_contract_drift=True,
        detect_validation_drift=True,
        detect_behavioral_drift=True,
    )


@pytest.fixture
def ai_config_enabled():
    """AI analysis config with enabled flag."""
    return AIAnalysisConfig(
        enabled=True,
        api_key="test-api-key-12345",
        model="claude-3-5-sonnet-20241022",
        enable_root_cause_analysis=True,
        enable_remediation_suggestions=True,
    )


@pytest.fixture
def ai_config_disabled():
    """AI analysis config with disabled flag."""
    return AIAnalysisConfig(enabled=False)


@pytest.fixture
def default_reporting_config(tmp_path):
    """Default reporting configuration."""
    return ReportingConfig(
        output_directory=tmp_path / "output",
        generate_markdown=True,
        generate_json=True,
        generate_cli_summary=True,
    )


# ============================================================================
# Field & Constraint Fixtures
# ============================================================================


@pytest.fixture
def simple_string_constraint():
    """Simple string constraint with length limits."""
    return FieldConstraint(
        required=True, min_length=1, max_length=100, nullable=False
    )


@pytest.fixture
def email_field_constraint():
    """Email field constraint."""
    return FieldConstraint(required=True, format="email", nullable=False)


@pytest.fixture
def integer_constraint():
    """Integer constraint with range."""
    return FieldConstraint(required=True, minimum=1, maximum=1000)


@pytest.fixture
def enum_constraint():
    """Enum constraint."""
    return FieldConstraint(required=True, enum=["active", "inactive", "suspended"])


@pytest.fixture
def simple_field_definition():
    """Simple string field definition."""
    return FieldDefinition(
        name="name",
        type=FieldType.STRING,
        description="User name",
        constraints=FieldConstraint(required=True, min_length=1, max_length=100),
    )


@pytest.fixture
def email_field_definition():
    """Email field definition."""
    return FieldDefinition(
        name="email",
        type=FieldType.STRING,
        description="Email address",
        constraints=FieldConstraint(required=True, format="email"),
    )


@pytest.fixture
def integer_field_definition():
    """Integer field definition."""
    return FieldDefinition(
        name="age",
        type=FieldType.INTEGER,
        description="User age",
        constraints=FieldConstraint(required=False, minimum=0, maximum=150),
    )


@pytest.fixture
def nested_object_field():
    """Nested object field definition."""
    address_fields = {
        "street": FieldDefinition(
            name="street", type=FieldType.STRING, constraints=FieldConstraint(required=True)
        ),
        "city": FieldDefinition(
            name="city", type=FieldType.STRING, constraints=FieldConstraint(required=True)
        ),
        "zipcode": FieldDefinition(
            name="zipcode",
            type=FieldType.STRING,
            constraints=FieldConstraint(required=False, pattern=r"^\d{5}$"),
        ),
    }
    return FieldDefinition(
        name="address", type=FieldType.OBJECT, properties=address_fields
    )


@pytest.fixture
def array_field_definition():
    """Array field definition."""
    item_definition = FieldDefinition(
        name="tag", type=FieldType.STRING, constraints=FieldConstraint(required=False)
    )
    return FieldDefinition(
        name="tags", type=FieldType.ARRAY, items=item_definition
    )


# ============================================================================
# Endpoint Fixtures
# ============================================================================


@pytest.fixture
def simple_get_endpoint():
    """Simple GET endpoint with path parameter."""
    return Endpoint(
        path="/users/{userId}",
        method=HTTPMethod.GET,
        operation_id="getUserById",
        summary="Get user by ID",
        parameters=[
            Parameter(
                name="userId",
                location="path",
                type=FieldType.INTEGER,
                constraints=FieldConstraint(required=True, minimum=1),
            )
        ],
        responses=[
            ResponseBody(
                status_code=200,
                content_type="application/json",
                schema={
                    "id": FieldDefinition(
                        name="id",
                        type=FieldType.INTEGER,
                        constraints=FieldConstraint(required=True),
                    ),
                    "email": FieldDefinition(
                        name="email",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=True, format="email"),
                    ),
                    "name": FieldDefinition(
                        name="name",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=True, min_length=1, max_length=100),
                    ),
                },
            ),
            ResponseBody(
                status_code=404,
                content_type="application/json",
                schema={
                    "error": FieldDefinition(
                        name="error", type=FieldType.STRING, constraints=FieldConstraint(required=True)
                    ),
                    "message": FieldDefinition(
                        name="message", type=FieldType.STRING, constraints=FieldConstraint(required=True)
                    ),
                },
            ),
        ],
    )


@pytest.fixture
def simple_post_endpoint():
    """Simple POST endpoint with request body."""
    return Endpoint(
        path="/users",
        method=HTTPMethod.POST,
        operation_id="createUser",
        summary="Create a new user",
        request_body=RequestBody(
            required=True,
            content_type="application/json",
            schema={
                "email": FieldDefinition(
                    name="email",
                    type=FieldType.STRING,
                    constraints=FieldConstraint(required=True, format="email"),
                ),
                "name": FieldDefinition(
                    name="name",
                    type=FieldType.STRING,
                    constraints=FieldConstraint(required=True, min_length=1, max_length=100),
                ),
                "age": FieldDefinition(
                    name="age",
                    type=FieldType.INTEGER,
                    constraints=FieldConstraint(required=False, minimum=0, maximum=150),
                ),
            },
        ),
        responses=[
            ResponseBody(
                status_code=201,
                content_type="application/json",
                schema={
                    "id": FieldDefinition(
                        name="id", type=FieldType.INTEGER, constraints=FieldConstraint(required=True)
                    ),
                    "email": FieldDefinition(
                        name="email", type=FieldType.STRING, constraints=FieldConstraint(required=True)
                    ),
                    "name": FieldDefinition(
                        name="name", type=FieldType.STRING, constraints=FieldConstraint(required=True)
                    ),
                },
            ),
            ResponseBody(
                status_code=400,
                content_type="application/json",
                schema={
                    "error": FieldDefinition(
                        name="error", type=FieldType.STRING, constraints=FieldConstraint(required=True)
                    ),
                    "message": FieldDefinition(
                        name="message", type=FieldType.STRING, constraints=FieldConstraint(required=True)
                    ),
                },
            ),
        ],
    )


@pytest.fixture
def endpoint_with_query_params():
    """GET endpoint with query parameters."""
    return Endpoint(
        path="/users",
        method=HTTPMethod.GET,
        operation_id="listUsers",
        summary="List all users",
        parameters=[
            Parameter(
                name="limit",
                location="query",
                type=FieldType.INTEGER,
                constraints=FieldConstraint(required=False, minimum=1, maximum=100, default=10),
            ),
            Parameter(
                name="offset",
                location="query",
                type=FieldType.INTEGER,
                constraints=FieldConstraint(required=False, minimum=0, default=0),
            ),
            Parameter(
                name="status",
                location="query",
                type=FieldType.STRING,
                constraints=FieldConstraint(enum=["active", "inactive"]),
            ),
        ],
        responses=[
            ResponseBody(
                status_code=200,
                content_type="application/json",
                schema={},  # Array response
            )
        ],
    )


# ============================================================================
# UnifiedAPISpec Fixtures
# ============================================================================


@pytest.fixture
def sample_api_metadata():
    """Sample API metadata."""
    return APIMetadata(
        title="Sample User API",
        version="1.0.0",
        description="Simple user management API for testing",
        base_url="http://localhost:8000",
    )


@pytest.fixture
def simple_unified_spec(sample_api_metadata, simple_get_endpoint, simple_post_endpoint):
    """Simple UnifiedAPISpec with 2 endpoints."""
    return UnifiedAPISpec(
        source_type=SourceType.OPENAPI,
        source_path="/path/to/spec.yaml",
        metadata=sample_api_metadata,
        endpoints=[simple_get_endpoint, simple_post_endpoint],
        confidence=1.0,
    )


@pytest.fixture
def openapi_spec_path():
    """Path to sample OpenAPI spec file."""
    return Path("examples/openapi/sample_users_api.yaml")


# ============================================================================
# TestCase Fixtures
# ============================================================================


@pytest.fixture
def valid_test_case(simple_get_endpoint):
    """Valid test case for GET /users/{userId}."""
    return TestCase(
        test_id="valid_get_1",
        endpoint=simple_get_endpoint,
        test_type=TestCaseType.VALID,
        description="Valid GET request with existing user ID",
        method=HTTPMethod.GET,
        path="/users/{userId}",
        path_params={"userId": 1},
        expected_status=200,
        should_pass=True,
        priority=1.0,
    )


@pytest.fixture
def invalid_test_case(simple_post_endpoint):
    """Invalid test case for POST /users (missing required field)."""
    return TestCase(
        test_id="invalid_post_1",
        endpoint=simple_post_endpoint,
        test_type=TestCaseType.INVALID,
        description="POST with missing required field: email",
        method=HTTPMethod.POST,
        path="/users",
        request_body={"name": "John Doe"},  # Missing email
        expected_status=400,
        should_pass=False,
        priority=1.2,
    )


@pytest.fixture
def boundary_test_case(simple_post_endpoint):
    """Boundary test case for POST /users (min length string)."""
    return TestCase(
        test_id="boundary_post_1",
        endpoint=simple_post_endpoint,
        test_type=TestCaseType.BOUNDARY,
        description="POST with minimum length name",
        method=HTTPMethod.POST,
        path="/users",
        request_body={"email": "test@example.com", "name": "A"},  # Min length 1
        expected_status=201,
        should_pass=True,
        priority=0.7,
    )


# ============================================================================
# OpenAPI Spec Fixture Data
# ============================================================================


@pytest.fixture
def minimal_openapi_spec_dict():
    """Minimal valid OpenAPI 3.0 spec as dictionary."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0.0"},
        "paths": {
            "/health": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {"status": {"type": "string"}}}
                                }
                            },
                        }
                    }
                }
            }
        },
    }


@pytest.fixture
def complex_openapi_spec_dict():
    """Complex OpenAPI spec with nested schemas, arrays, and constraints."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Complex API", "version": "2.0.0", "description": "API with complex schemas"},
        "servers": [{"url": "https://api.example.com", "description": "Production"}],
        "paths": {
            "/users": {
                "post": {
                    "operationId": "createUser",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserInput"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        },
                        "400": {
                            "description": "Bad Request",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "email", "name"],
                    "properties": {
                        "id": {"type": "integer", "minimum": 1},
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string", "minLength": 1, "maxLength": 100},
                        "age": {"type": "integer", "minimum": 0, "maximum": 150},
                        "status": {"type": "string", "enum": ["active", "inactive", "suspended"]},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "address": {"$ref": "#/components/schemas/Address"},
                    },
                },
                "UserInput": {
                    "type": "object",
                    "required": ["email", "name"],
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string", "minLength": 1, "maxLength": 100},
                        "age": {"type": "integer", "minimum": 0, "maximum": 150},
                    },
                },
                "Address": {
                    "type": "object",
                    "required": ["street", "city"],
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                        "zipcode": {"type": "string", "pattern": r"^\d{5}$"},
                    },
                },
                "Error": {
                    "type": "object",
                    "required": ["error", "message"],
                    "properties": {
                        "error": {"type": "string"},
                        "message": {"type": "string"},
                    },
                },
            }
        },
    }


@pytest.fixture
def invalid_openapi_spec_dict():
    """Invalid OpenAPI spec missing required fields."""
    return {
        "openapi": "3.0.0",
        # Missing required 'info' field
        "paths": {}
    }


# ============================================================================
# HTTP Response Fixtures
# ============================================================================


@pytest.fixture
def mock_user_response():
    """Mock successful user response."""
    return {
        "id": 1,
        "email": "john@example.com",
        "name": "John Doe",
        "age": 30,
        "status": "active",
    }


@pytest.fixture
def mock_users_list_response():
    """Mock list of users response."""
    return [
        {"id": 1, "email": "john@example.com", "name": "John Doe"},
        {"id": 2, "email": "jane@example.com", "name": "Jane Smith"},
    ]


@pytest.fixture
def mock_error_response():
    """Mock error response."""
    return {"error": "validation_error", "message": "Email format is invalid"}


@pytest.fixture
def mock_404_response():
    """Mock not found response."""
    return {"error": "not_found", "message": "User not found"}


# ============================================================================
# Sample OpenAPI File Content
# ============================================================================


@pytest.fixture
def sample_openapi_yaml_content():
    """Sample OpenAPI YAML content as string."""
    return """openapi: 3.0.0
info:
  title: Test User API
  version: 1.0.0
  description: API for testing

servers:
  - url: http://localhost:8000

paths:
  /users:
    get:
      operationId: listUsers
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
    post:
      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserInput'
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '400':
          description: Bad Request

  /users/{userId}:
    get:
      operationId: getUserById
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: integer
            minimum: 1
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '404':
          description: Not Found

components:
  schemas:
    User:
      type: object
      required:
        - id
        - email
        - name
      properties:
        id:
          type: integer
          minimum: 1
        email:
          type: string
          format: email
        name:
          type: string
          minLength: 1
          maxLength: 100
        age:
          type: integer
          minimum: 0
          maximum: 150
        status:
          type: string
          enum: [active, inactive, suspended]

    UserInput:
      type: object
      required:
        - email
        - name
      properties:
        email:
          type: string
          format: email
        name:
          type: string
          minLength: 1
          maxLength: 100
        age:
          type: integer
          minimum: 0
          maximum: 150
"""
