"""
Valid Test Generator

Generates valid test cases (happy paths) from API contracts.
"""

import random
import string
import uuid
from datetime import datetime
from typing import Any, Dict, List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.generation.base import BaseTestGenerator, TestCase, TestCaseType
from api_contract_validator.input.normalizer.models import (
    Endpoint,
    FieldDefinition,
    FieldType,
)

logger = get_logger(__name__)


class ValidTestGenerator(BaseTestGenerator):
    """Generates valid test cases that should pass validation."""

    def generate_tests(self, endpoint: Endpoint) -> List[TestCase]:
        """Generate valid test cases for an endpoint."""
        tests = []

        # Generate primary happy path test
        test = self._generate_happy_path(endpoint)
        tests.append(test)

        # Generate additional valid variations if request body has optional fields
        if endpoint.request_body and len(endpoint.request_body.schema) > 3:
            # Generate test with only required fields
            test_minimal = self._generate_minimal_valid(endpoint)
            tests.append(test_minimal)

        return tests

    def _generate_happy_path(self, endpoint: Endpoint) -> TestCase:
        """Generate a primary happy path test case."""
        # Generate path parameters
        path_params = {}
        for param in endpoint.parameters:
            if param.location == "path":
                path_params[param.name] = self._generate_valid_value(
                    param.type.value, param.constraints
                )

        # Generate query parameters
        query_params = {}
        for param in endpoint.parameters:
            if param.location == "query" and param.constraints.required:
                query_params[param.name] = self._generate_valid_value(
                    param.type.value, param.constraints
                )

        # Generate request body
        request_body = None
        if endpoint.request_body:
            request_body = self._generate_valid_body(endpoint.request_body.schema)

        # Expected status (first success response)
        expected_status = 200
        for response in endpoint.responses:
            if 200 <= response.status_code < 300:
                expected_status = response.status_code
                break

        return TestCase(
            test_id=self.generate_test_id(f"valid_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.VALID,
            description=f"Valid {endpoint.method.value} request to {endpoint.path}",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            query_params=query_params,
            request_body=request_body,
            expected_status=expected_status,
            should_pass=True,
            priority=1.0,
        )

    def _generate_minimal_valid(self, endpoint: Endpoint) -> TestCase:
        """Generate a test with only required fields."""
        # Generate path parameters
        path_params = {}
        for param in endpoint.parameters:
            if param.location == "path":
                path_params[param.name] = self._generate_valid_value(
                    param.type.value, param.constraints
                )

        # Generate only required query parameters
        query_params = {}
        for param in endpoint.parameters:
            if param.location == "query" and param.constraints.required:
                query_params[param.name] = self._generate_valid_value(
                    param.type.value, param.constraints
                )

        # Generate request body with only required fields
        request_body = None
        if endpoint.request_body:
            request_body = self._generate_minimal_body(endpoint.request_body.schema)

        expected_status = 200
        for response in endpoint.responses:
            if 200 <= response.status_code < 300:
                expected_status = response.status_code
                break

        return TestCase(
            test_id=self.generate_test_id(f"valid_minimal_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.VALID,
            description=f"Valid {endpoint.method.value} with minimal required fields",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            query_params=query_params,
            request_body=request_body,
            expected_status=expected_status,
            should_pass=True,
            priority=0.8,
        )

    def _generate_valid_body(self, schema: Dict[str, FieldDefinition]) -> Dict[str, Any]:
        """Generate a valid request body from schema."""
        body = {}
        for field_name, field_def in schema.items():
            # Always include required fields, optionally include others
            if field_def.constraints.required or random.random() > 0.3:
                body[field_name] = self._generate_valid_field_value(field_def)
        return body

    def _generate_minimal_body(self, schema: Dict[str, FieldDefinition]) -> Dict[str, Any]:
        """Generate request body with only required fields."""
        body = {}
        for field_name, field_def in schema.items():
            if field_def.constraints.required:
                body[field_name] = self._generate_valid_field_value(field_def)
        return body

    def _generate_valid_field_value(self, field_def: FieldDefinition) -> Any:
        """Generate a valid value for a field."""
        if field_def.constraints.default is not None:
            return field_def.constraints.default

        if field_def.constraints.enum:
            return random.choice(field_def.constraints.enum)

        if field_def.type == FieldType.OBJECT and field_def.properties:
            return self._generate_valid_body(field_def.properties)

        if field_def.type == FieldType.ARRAY:
            # Generate 1-3 items
            count = random.randint(1, 3)
            if field_def.items:
                return [self._generate_valid_field_value(field_def.items) for _ in range(count)]
            return ["item1", "item2"]

        return self._generate_valid_value(field_def.type.value, field_def.constraints)

    def _generate_valid_value(self, field_type: str, constraints: Any) -> Any:
        """Generate a valid value for a given type and constraints."""
        if field_type == "string":
            return self._generate_valid_string(constraints)
        elif field_type == "integer":
            return self._generate_valid_integer(constraints)
        elif field_type == "number":
            return self._generate_valid_number(constraints)
        elif field_type == "boolean":
            return random.choice([True, False])
        elif field_type == "array":
            return ["item1", "item2"]
        elif field_type == "object":
            return {"key": "value"}
        else:
            return "default_value"

    def _generate_valid_string(self, constraints: Any) -> str:
        """Generate a valid string value."""
        # Check format first
        if hasattr(constraints, "format"):
            format_type = constraints.format
            if format_type == "email":
                return f"user{random.randint(1, 1000)}@example.com"
            elif format_type == "date-time":
                return datetime.utcnow().isoformat() + "Z"
            elif format_type == "date":
                return datetime.utcnow().strftime("%Y-%m-%d")
            elif format_type == "uuid":
                return str(uuid.uuid4())
            elif format_type == "uri":
                return "https://example.com/resource"

        # Check enum
        if hasattr(constraints, "enum") and constraints.enum:
            return random.choice(constraints.enum)

        # Generate string respecting length constraints
        min_len = getattr(constraints, "min_length", 1)
        max_len = getattr(constraints, "max_length", 50)

        # Ensure min_len is at least 1
        min_len = max(1, min_len)
        target_len = random.randint(min_len, min(max_len, min_len + 10))

        return "".join(random.choices(string.ascii_letters + string.digits, k=target_len))

    def _generate_valid_integer(self, constraints: Any) -> int:
        """Generate a valid integer value."""
        minimum = getattr(constraints, "minimum", 0)
        maximum = getattr(constraints, "maximum", 1000)

        return random.randint(int(minimum), int(maximum))

    def _generate_valid_number(self, constraints: Any) -> float:
        """Generate a valid number value."""
        minimum = getattr(constraints, "minimum", 0.0)
        maximum = getattr(constraints, "maximum", 1000.0)

        return round(random.uniform(float(minimum), float(maximum)), 2)
