"""
OpenAPI Specification Parser

Parses OpenAPI 3.0 specifications and converts them to unified intermediate representation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename

from api_contract_validator.config.exceptions import OpenAPIError
from api_contract_validator.config.logging import get_logger
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
    SecurityScheme,
    SourceType,
    UnifiedAPISpec,
)

logger = get_logger(__name__)


class OpenAPIParser:
    """
    Parses OpenAPI 3.0 specifications into unified intermediate representation.
    """

    def __init__(self):
        self.spec_dict: Dict[str, Any] = {}
        self.schemas: Dict[str, FieldDefinition] = {}

    def parse_file(self, spec_path: Path) -> UnifiedAPISpec:
        """
        Parse an OpenAPI specification file.

        Args:
            spec_path: Path to OpenAPI spec file (YAML or JSON)

        Returns:
            UnifiedAPISpec instance

        Raises:
            OpenAPIError: If parsing or validation fails
        """
        logger.info(f"Parsing OpenAPI specification: {spec_path}")

        try:
            # Read and validate the spec
            spec_dict, spec_url = read_from_filename(str(spec_path))
            validate_spec(spec_dict)
            self.spec_dict = spec_dict

            logger.info("OpenAPI specification validated successfully")

            # Parse components
            metadata = self._parse_metadata()
            security_schemes = self._parse_security_schemes()
            self._parse_schemas()  # Populate self.schemas
            endpoints = self._parse_endpoints()

            unified_spec = UnifiedAPISpec(
                source_type=SourceType.OPENAPI,
                source_path=str(spec_path),
                metadata=metadata,
                endpoints=endpoints,
                security_schemes=security_schemes,
                schemas=self.schemas,
                confidence=1.0,
            )

            logger.info(
                f"Parsed {len(endpoints)} endpoints from OpenAPI specification"
            )
            return unified_spec

        except Exception as e:
            raise OpenAPIError(f"Failed to parse OpenAPI specification: {e}")

    def _parse_metadata(self) -> APIMetadata:
        """Parse API metadata from info section."""
        info = self.spec_dict.get("info", {})
        servers = self.spec_dict.get("servers", [])

        base_url = servers[0].get("url") if servers else None

        return APIMetadata(
            title=info.get("title", "Unknown API"),
            version=info.get("version", "1.0.0"),
            description=info.get("description"),
            base_url=base_url,
            contact=info.get("contact"),
            license=info.get("license"),
            terms_of_service=info.get("termsOfService"),
        )

    def _parse_security_schemes(self) -> List[SecurityScheme]:
        """Parse security schemes from components."""
        components = self.spec_dict.get("components", {})
        security_schemes_dict = components.get("securitySchemes", {})

        schemes = []
        for name, scheme_data in security_schemes_dict.items():
            scheme = SecurityScheme(
                name=name,
                type=scheme_data.get("type", ""),
                scheme=scheme_data.get("scheme"),
                bearer_format=scheme_data.get("bearerFormat"),
                in_location=scheme_data.get("in"),
                description=scheme_data.get("description"),
            )
            schemes.append(scheme)

        return schemes

    def _parse_schemas(self) -> None:
        """Parse reusable schemas from components."""
        components = self.spec_dict.get("components", {})
        schemas_dict = components.get("schemas", {})

        for schema_name, schema_data in schemas_dict.items():
            self.schemas[schema_name] = self._parse_field_definition(
                schema_name, schema_data
            )

    def _parse_endpoints(self) -> List[Endpoint]:
        """Parse all endpoints from paths section."""
        paths = self.spec_dict.get("paths", {})
        endpoints = []

        for path, path_item in paths.items():
            # Path-level parameters
            path_params = path_item.get("parameters", [])

            for method, operation in path_item.items():
                if method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                    try:
                        endpoint = self._parse_endpoint(
                            path, method.upper(), operation, path_params
                        )
                        endpoints.append(endpoint)
                    except Exception as e:
                        logger.warning(f"Failed to parse endpoint {method.upper()} {path}: {e}")

        return endpoints

    def _parse_endpoint(
        self,
        path: str,
        method: str,
        operation: Dict[str, Any],
        path_params: List[Dict[str, Any]],
    ) -> Endpoint:
        """Parse a single endpoint operation."""
        # Parse parameters
        parameters = []
        for param in path_params + operation.get("parameters", []):
            parameters.append(self._parse_parameter(param))

        # Parse request body
        request_body = None
        if "requestBody" in operation:
            request_body = self._parse_request_body(operation["requestBody"])

        # Parse responses
        responses = []
        for status_code, response_data in operation.get("responses", {}).items():
            try:
                status = int(status_code)
                response = self._parse_response(status, response_data)
                responses.append(response)
            except ValueError:
                # Handle 'default' or other non-numeric status codes
                if status_code == "default":
                    response = self._parse_response(200, response_data)
                    responses.append(response)

        # Parse security
        security = None
        if "security" in operation:
            security = [list(s.keys())[0] for s in operation["security"] if s]

        return Endpoint(
            path=path,
            method=HTTPMethod[method],
            operation_id=operation.get("operationId"),
            summary=operation.get("summary"),
            description=operation.get("description"),
            tags=operation.get("tags", []),
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=security,
            deprecated=operation.get("deprecated", False),
            confidence=1.0,
        )

    def _parse_parameter(self, param_data: Dict[str, Any]) -> Parameter:
        """Parse a parameter definition."""
        schema = param_data.get("schema", {})

        return Parameter(
            name=param_data.get("name", "unknown"),
            location=param_data.get("in", "query"),
            type=self._map_type(schema.get("type", "string")),
            description=param_data.get("description"),
            constraints=self._parse_constraints(schema, param_data.get("required", False)),
            confidence=1.0,
        )

    def _parse_request_body(self, body_data: Dict[str, Any]) -> RequestBody:
        """Parse request body definition."""
        content = body_data.get("content", {})

        # Get first content type (usually application/json)
        content_type = list(content.keys())[0] if content else "application/json"
        schema_data = content.get(content_type, {}).get("schema", {})

        schema = self._parse_schema_properties(schema_data)

        return RequestBody(
            content_type=content_type,
            schema=schema,
            required=body_data.get("required", False),
            description=body_data.get("description"),
            confidence=1.0,
        )

    def _parse_response(self, status_code: int, response_data: Dict[str, Any]) -> ResponseBody:
        """Parse response definition."""
        content = response_data.get("content", {})

        # Get first content type
        content_type = list(content.keys())[0] if content else "application/json"
        schema_data = content.get(content_type, {}).get("schema", {})

        schema = self._parse_schema_properties(schema_data)

        return ResponseBody(
            status_code=status_code,
            content_type=content_type,
            schema=schema,
            description=response_data.get("description"),
            confidence=1.0,
        )

    def _parse_schema_properties(self, schema_data: Dict[str, Any]) -> Dict[str, FieldDefinition]:
        """Parse schema properties into field definitions."""
        if "$ref" in schema_data:
            # Handle reference
            ref_name = schema_data["$ref"].split("/")[-1]
            if ref_name in self.schemas:
                # Return the referenced schema's properties
                ref_schema = self.schemas[ref_name]
                return ref_schema.properties or {}
            return {}

        properties = schema_data.get("properties", {})
        required_fields = schema_data.get("required", [])

        fields = {}
        for field_name, field_schema in properties.items():
            is_required = field_name in required_fields
            fields[field_name] = self._parse_field_definition(
                field_name, field_schema, is_required
            )

        return fields

    def _parse_field_definition(
        self, name: str, schema: Dict[str, Any], required: bool = False
    ) -> FieldDefinition:
        """Parse a field definition from schema."""
        field_type = self._map_type(schema.get("type", "string"))

        # Handle $ref
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            if ref_name in self.schemas:
                return self.schemas[ref_name]

        # Handle array type
        items = None
        if field_type == FieldType.ARRAY and "items" in schema:
            items = self._parse_field_definition("item", schema["items"])

        # Handle object type
        properties = None
        if field_type == FieldType.OBJECT and "properties" in schema:
            properties = self._parse_schema_properties(schema)

        return FieldDefinition(
            name=name,
            type=field_type,
            description=schema.get("description"),
            constraints=self._parse_constraints(schema, required),
            items=items,
            properties=properties,
            confidence=1.0,
        )

    def _parse_constraints(
        self, schema: Dict[str, Any], required: bool = False
    ) -> FieldConstraint:
        """Parse validation constraints from schema."""
        return FieldConstraint(
            required=required,
            nullable=schema.get("nullable", False),
            min_length=schema.get("minLength"),
            max_length=schema.get("maxLength"),
            minimum=schema.get("minimum"),
            maximum=schema.get("maximum"),
            pattern=schema.get("pattern"),
            enum=schema.get("enum"),
            format=schema.get("format"),
            default=schema.get("default"),
        )

    def _map_type(self, openapi_type: str) -> FieldType:
        """Map OpenAPI type to FieldType enum."""
        type_mapping = {
            "string": FieldType.STRING,
            "integer": FieldType.INTEGER,
            "number": FieldType.NUMBER,
            "boolean": FieldType.BOOLEAN,
            "array": FieldType.ARRAY,
            "object": FieldType.OBJECT,
            "null": FieldType.NULL,
        }
        return type_mapping.get(openapi_type, FieldType.STRING)


def parse_openapi(spec_path: Path) -> UnifiedAPISpec:
    """
    Convenience function to parse an OpenAPI specification.

    Args:
        spec_path: Path to OpenAPI spec file

    Returns:
        UnifiedAPISpec instance
    """
    parser = OpenAPIParser()
    return parser.parse_file(spec_path)
