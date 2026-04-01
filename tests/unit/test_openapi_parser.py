"""
Unit tests for OpenAPI parser.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from api_contract_validator.config.exceptions import OpenAPIError
from api_contract_validator.input.normalizer.models import (
    FieldType,
    HTTPMethod,
    SourceType,
    UnifiedAPISpec,
)
from api_contract_validator.input.openapi.parser import OpenAPIParser, parse_openapi


@pytest.mark.unit
class TestOpenAPIParser:
    """Test OpenAPIParser class."""

    @pytest.fixture
    def parser(self):
        """Create OpenAPIParser instance."""
        return OpenAPIParser()

    @pytest.fixture
    def temp_spec_file(self, tmp_path, sample_openapi_yaml_content):
        """Create temporary OpenAPI spec file."""
        spec_file = tmp_path / "test_spec.yaml"
        spec_file.write_text(sample_openapi_yaml_content)
        return spec_file

    @pytest.fixture
    def complex_spec_file(self, tmp_path, complex_openapi_spec_dict):
        """Create temporary complex OpenAPI spec file."""
        spec_file = tmp_path / "complex_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(complex_openapi_spec_dict, f)
        return spec_file

    @pytest.fixture
    def invalid_spec_file(self, tmp_path, invalid_openapi_spec_dict):
        """Create temporary invalid OpenAPI spec file."""
        spec_file = tmp_path / "invalid_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(invalid_openapi_spec_dict, f)
        return spec_file

    # ========================================================================
    # Basic Parsing Tests
    # ========================================================================

    def test_parse_simple_spec_success(self, parser, openapi_spec_path):
        """Test parsing the sample users API spec."""
        result = parser.parse_file(openapi_spec_path)

        assert isinstance(result, UnifiedAPISpec)
        assert result.source_type == SourceType.OPENAPI
        assert result.metadata.title == "Sample User API"
        assert result.metadata.version == "1.0.0"
        assert len(result.endpoints) == 3
        assert result.confidence == 1.0

    def test_parse_metadata_extraction(self, parser, temp_spec_file):
        """Test metadata extraction from info section."""
        result = parser.parse_file(temp_spec_file)

        assert result.metadata.title == "Test User API"
        assert result.metadata.version == "1.0.0"
        assert result.metadata.description == "API for testing"
        assert result.metadata.base_url == "http://localhost:8000"

    def test_parse_metadata_with_contact_and_license(self, parser, tmp_path):
        """Test parsing metadata with contact and license info."""
        spec_dict = {
            "openapi": "3.0.0",
            "info": {
                "title": "API with Metadata",
                "version": "1.0.0",
                "contact": {"name": "API Team", "email": "api@example.com"},
                "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
                "termsOfService": "https://example.com/terms",
            },
            "paths": {},
        }
        spec_file = tmp_path / "metadata_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec_dict, f)

        result = parser.parse_file(spec_file)

        assert result.metadata.contact == {"name": "API Team", "email": "api@example.com"}
        assert result.metadata.license == {"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
        assert result.metadata.terms_of_service == "https://example.com/terms"

    def test_parse_endpoints_all_methods(self, parser, tmp_path):
        """Test parsing endpoints with different HTTP methods."""
        spec_dict = {
            "openapi": "3.0.0",
            "info": {"title": "Methods API", "version": "1.0.0"},
            "paths": {
                "/resource": {
                    "get": {"responses": {"200": {"description": "OK"}}},
                    "post": {"responses": {"201": {"description": "Created"}}},
                    "put": {"responses": {"200": {"description": "Updated"}}},
                    "patch": {"responses": {"200": {"description": "Patched"}}},
                    "delete": {"responses": {"204": {"description": "Deleted"}}},
                }
            },
        }
        spec_file = tmp_path / "methods_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec_dict, f)

        result = parser.parse_file(spec_file)

        assert len(result.endpoints) == 5
        methods = {ep.method for ep in result.endpoints}
        assert methods == {HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH, HTTPMethod.DELETE}

    # ========================================================================
    # Parameter Parsing Tests
    # ========================================================================

    def test_parse_path_parameters(self, parser, openapi_spec_path):
        """Test parsing path parameters with constraints."""
        result = parser.parse_file(openapi_spec_path)

        # GET /users/{userId} has path parameter
        get_user_endpoint = next((e for e in result.endpoints if e.path == "/users/{userId}"), None)
        assert get_user_endpoint is not None

        path_params = [p for p in get_user_endpoint.parameters if p.location == "path"]
        assert len(path_params) == 1
        assert path_params[0].name == "userId"
        assert path_params[0].type == FieldType.INTEGER
        assert path_params[0].constraints.required is True
        assert path_params[0].constraints.minimum == 1

    def test_parse_query_parameters(self, parser, tmp_path):
        """Test parsing query parameters."""
        spec_dict = {
            "openapi": "3.0.0",
            "info": {"title": "Query API", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                            },
                            {
                                "name": "filter",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string", "enum": ["all", "active"]},
                            },
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        spec_file = tmp_path / "query_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec_dict, f)

        result = parser.parse_file(spec_file)

        endpoint = result.endpoints[0]
        query_params = [p for p in endpoint.parameters if p.location == "query"]
        assert len(query_params) == 2

        limit_param = next(p for p in query_params if p.name == "limit")
        assert limit_param.type == FieldType.INTEGER
        assert limit_param.constraints.minimum == 1
        assert limit_param.constraints.maximum == 100
        assert limit_param.constraints.default == 10

        filter_param = next(p for p in query_params if p.name == "filter")
        assert filter_param.constraints.enum == ["all", "active"]

    # ========================================================================
    # Request Body Parsing Tests
    # ========================================================================

    def test_parse_request_body_schema(self, parser, openapi_spec_path):
        """Test parsing request body with nested schema."""
        result = parser.parse_file(openapi_spec_path)

        # POST /users has request body
        post_endpoint = next((e for e in result.endpoints if e.method == HTTPMethod.POST), None)
        assert post_endpoint is not None
        assert post_endpoint.request_body is not None

        body = post_endpoint.request_body
        assert body.required is True
        assert body.content_type == "application/json"
        assert "email" in body.schema
        assert "name" in body.schema

        email_field = body.schema["email"]
        assert email_field.type == FieldType.STRING
        assert email_field.constraints.required is True
        assert email_field.constraints.format == "email"

        name_field = body.schema["name"]
        assert name_field.constraints.min_length == 1
        assert name_field.constraints.max_length == 100

    # ========================================================================
    # Response Parsing Tests
    # ========================================================================

    def test_parse_response_body_multiple_status(self, parser, openapi_spec_path):
        """Test parsing multiple response status codes."""
        result = parser.parse_file(openapi_spec_path)

        # POST /users has 201 and 400 responses
        post_endpoint = next((e for e in result.endpoints if e.method == HTTPMethod.POST), None)
        assert len(post_endpoint.responses) == 2

        status_codes = {r.status_code for r in post_endpoint.responses}
        assert status_codes == {201, 400}

        success_response = next((r for r in post_endpoint.responses if r.status_code == 201), None)
        assert success_response is not None
        assert "id" in success_response.schema
        assert "email" in success_response.schema

        error_response = next((r for r in post_endpoint.responses if r.status_code == 400), None)
        assert error_response is not None
        assert "error" in error_response.schema
        assert "message" in error_response.schema

    def test_parse_default_status_code_handling(self, parser, tmp_path):
        """Test handling of 'default' status code."""
        spec_dict = {
            "openapi": "3.0.0",
            "info": {"title": "Default Response API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "responses": {
                            "default": {
                                "description": "Default response",
                                "content": {"application/json": {"schema": {"type": "object"}}},
                            }
                        }
                    }
                }
            },
        }
        spec_file = tmp_path / "default_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec_dict, f)

        result = parser.parse_file(spec_file)

        endpoint = result.endpoints[0]
        assert len(endpoint.responses) == 1
        # 'default' should map to 200
        assert endpoint.responses[0].status_code == 200

    # ========================================================================
    # Constraint Parsing Tests
    # ========================================================================

    def test_parse_field_constraints(self, parser, openapi_spec_path):
        """Test parsing all constraint types."""
        result = parser.parse_file(openapi_spec_path)

        # Find User schema
        user_schema = result.schemas.get("User")
        assert user_schema is not None
        assert user_schema.properties is not None

        # Check integer constraints
        age_field = user_schema.properties.get("age")
        assert age_field is not None
        assert age_field.constraints.minimum == 0
        assert age_field.constraints.maximum == 150

        # Check enum constraint
        status_field = user_schema.properties.get("status")
        assert status_field is not None
        assert status_field.constraints.enum == ["active", "inactive", "suspended"]

        # Check string length constraints
        name_field = user_schema.properties.get("name")
        assert name_field is not None
        assert name_field.constraints.min_length == 1
        assert name_field.constraints.max_length == 100

        # Check format constraint
        email_field = user_schema.properties.get("email")
        assert email_field is not None
        assert email_field.constraints.format == "email"

    # ========================================================================
    # $ref Resolution Tests
    # ========================================================================

    def test_parse_ref_resolution(self, parser, openapi_spec_path):
        """Test resolution of $ref to component schemas."""
        result = parser.parse_file(openapi_spec_path)

        # POST /users request body references UserInput schema
        post_endpoint = next((e for e in result.endpoints if e.method == HTTPMethod.POST), None)
        assert post_endpoint.request_body is not None

        # Should have resolved schema fields
        assert "email" in post_endpoint.request_body.schema
        assert "name" in post_endpoint.request_body.schema

    def test_parse_nested_ref_in_properties(self, parser, complex_spec_file):
        """Test parsing nested $ref in object properties."""
        result = parser.parse_file(complex_spec_file)

        # User schema has address field that references Address schema
        user_schema = result.schemas.get("User")
        assert user_schema is not None
        assert user_schema.properties is not None

        address_field = user_schema.properties.get("address")
        assert address_field is not None
        # The $ref should be resolved to Address schema
        assert address_field.properties is not None
        assert "street" in address_field.properties
        assert "city" in address_field.properties

    # ========================================================================
    # Nested Structure Tests
    # ========================================================================

    def test_parse_nested_objects(self, parser, complex_spec_file):
        """Test parsing nested object properties."""
        result = parser.parse_file(complex_spec_file)

        # Address schema has nested properties
        address_schema = result.schemas.get("Address")
        assert address_schema is not None
        assert address_schema.type == FieldType.OBJECT
        assert address_schema.properties is not None
        assert len(address_schema.properties) == 3

        zipcode = address_schema.properties.get("zipcode")
        assert zipcode.constraints.pattern == r"^\d{5}$"

    def test_parse_array_items(self, parser, complex_spec_file):
        """Test parsing array with item schema."""
        result = parser.parse_file(complex_spec_file)

        # User schema has tags array
        user_schema = result.schemas.get("User")
        tags_field = user_schema.properties.get("tags")

        assert tags_field is not None
        assert tags_field.type == FieldType.ARRAY
        assert tags_field.items is not None
        assert tags_field.items.type == FieldType.STRING

    # ========================================================================
    # Security Scheme Tests
    # ========================================================================

    def test_parse_security_schemes(self, parser, tmp_path):
        """Test parsing security schemes."""
        spec_dict = {
            "openapi": "3.0.0",
            "info": {"title": "Secure API", "version": "1.0.0"},
            "paths": {},
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "JWT authentication",
                    },
                    "apiKey": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    },
                }
            },
        }
        spec_file = tmp_path / "secure_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec_dict, f)

        result = parser.parse_file(spec_file)

        assert len(result.security_schemes) == 2
        bearer_scheme = next((s for s in result.security_schemes if s.name == "bearerAuth"), None)
        assert bearer_scheme is not None
        assert bearer_scheme.type == "http"
        assert bearer_scheme.scheme == "bearer"
        assert bearer_scheme.bearer_format == "JWT"

        api_key_scheme = next((s for s in result.security_schemes if s.name == "apiKey"), None)
        assert api_key_scheme is not None
        assert api_key_scheme.type == "apiKey"
        assert api_key_scheme.in_location == "header"

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    def test_parse_invalid_spec_raises_error(self, parser, invalid_spec_file):
        """Test that invalid OpenAPI spec raises OpenAPIError."""
        with pytest.raises(OpenAPIError) as exc_info:
            parser.parse_file(invalid_spec_file)

        assert "Failed to parse OpenAPI specification" in str(exc_info.value)

    def test_parse_nonexistent_file_raises_error(self, parser):
        """Test parsing nonexistent file raises error."""
        with pytest.raises(OpenAPIError):
            parser.parse_file(Path("/nonexistent/spec.yaml"))

    def test_parse_empty_paths_returns_no_endpoints(self, parser, tmp_path):
        """Test spec with empty paths returns no endpoints."""
        spec_dict = {
            "openapi": "3.0.0",
            "info": {"title": "Empty API", "version": "1.0.0"},
            "paths": {},
        }
        spec_file = tmp_path / "empty_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec_dict, f)

        result = parser.parse_file(spec_file)

        assert len(result.endpoints) == 0

    # ========================================================================
    # Edge Cases Tests
    # ========================================================================

    def test_parse_spec_with_no_servers(self, parser, tmp_path):
        """Test parsing spec without servers section."""
        spec_dict = {
            "openapi": "3.0.0",
            "info": {"title": "No Servers API", "version": "1.0.0"},
            "paths": {
                "/test": {"get": {"responses": {"200": {"description": "OK"}}}}
            },
        }
        spec_file = tmp_path / "no_servers_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec_dict, f)

        result = parser.parse_file(spec_file)

        assert result.metadata.base_url is None

    def test_parse_endpoint_without_operation_id(self, parser, tmp_path):
        """Test parsing endpoint without operationId."""
        spec_dict = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Test endpoint",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        spec_file = tmp_path / "no_opid_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec_dict, f)

        result = parser.parse_file(spec_file)

        endpoint = result.endpoints[0]
        assert endpoint.operation_id is None
        assert endpoint.summary == "Test endpoint"

    def test_parse_response_without_content(self, parser, tmp_path):
        """Test parsing response without content/schema."""
        spec_dict = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "delete": {
                        "responses": {
                            "204": {"description": "No Content"}  # No content body
                        }
                    }
                }
            },
        }
        spec_file = tmp_path / "no_content_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec_dict, f)

        result = parser.parse_file(spec_file)

        endpoint = result.endpoints[0]
        assert len(endpoint.responses) == 1
        assert endpoint.responses[0].status_code == 204
        # Schema should be empty dict
        assert endpoint.responses[0].schema == {}

    def test_parse_optional_fields_omitted(self, parser, minimal_openapi_spec_dict, tmp_path):
        """Test parsing spec with minimal/optional fields omitted."""
        spec_file = tmp_path / "minimal_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(minimal_openapi_spec_dict, f)

        result = parser.parse_file(spec_file)

        assert result.metadata.title == "Minimal API"
        assert result.metadata.description is None
        assert result.metadata.base_url is None
        assert len(result.security_schemes) == 0

    # ========================================================================
    # Type Mapping Tests
    # ========================================================================

    def test_map_type_all_types(self, parser):
        """Test type mapping for all OpenAPI types."""
        assert parser._map_type("string") == FieldType.STRING
        assert parser._map_type("integer") == FieldType.INTEGER
        assert parser._map_type("number") == FieldType.NUMBER
        assert parser._map_type("boolean") == FieldType.BOOLEAN
        assert parser._map_type("array") == FieldType.ARRAY
        assert parser._map_type("object") == FieldType.OBJECT
        assert parser._map_type("null") == FieldType.NULL

    def test_map_type_unknown_defaults_to_string(self, parser):
        """Test unknown type defaults to STRING."""
        assert parser._map_type("unknown_type") == FieldType.STRING

    # ========================================================================
    # Convenience Function Test
    # ========================================================================

    def test_parse_openapi_convenience_function(self, openapi_spec_path):
        """Test the convenience function wrapper."""
        result = parse_openapi(openapi_spec_path)

        assert isinstance(result, UnifiedAPISpec)
        assert result.metadata.title == "Sample User API"
        assert len(result.endpoints) == 3

    # ========================================================================
    # Integration - Full Spec Parse
    # ========================================================================

    def test_parse_complex_spec_end_to_end(self, parser, complex_spec_file):
        """Test parsing complex spec with all features."""
        result = parser.parse_file(complex_spec_file)

        assert result.metadata.title == "Complex API"
        assert result.metadata.version == "2.0.0"
        assert result.metadata.base_url == "https://api.example.com"

        # Should have parsed schemas
        assert "User" in result.schemas
        assert "UserInput" in result.schemas
        assert "Address" in result.schemas
        assert "Error" in result.schemas

        # Should have parsed endpoint
        assert len(result.endpoints) >= 1

        # User schema should have all fields
        user_schema = result.schemas["User"]
        assert user_schema.properties is not None
        assert "email" in user_schema.properties
        assert "address" in user_schema.properties
        assert "tags" in user_schema.properties
