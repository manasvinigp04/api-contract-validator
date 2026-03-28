"""
Boundary Test Generator

Generates boundary and edge case test cases.
"""

import sys
from typing import Any, Dict, List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.generation.base import BaseTestGenerator, TestCase, TestCaseType
from api_contract_validator.generation.valid.generator import ValidTestGenerator
from api_contract_validator.input.normalizer.models import (
    Endpoint,
    FieldDefinition,
    FieldType,
)

logger = get_logger(__name__)


class BoundaryTestGenerator(BaseTestGenerator):
    """Generates boundary and edge case test cases."""

    def __init__(self):
        super().__init__()
        self.valid_generator = ValidTestGenerator()

    def generate_tests(self, endpoint: Endpoint) -> List[TestCase]:
        """Generate boundary test cases for an endpoint."""
        tests = []

        if endpoint.request_body:
            for field_name, field_def in endpoint.request_body.schema.items():
                boundary_tests = self._generate_field_boundary_tests(
                    endpoint, field_name, field_def
                )
                tests.extend(boundary_tests)

        # Limit tests
        if len(tests) > 8:
            tests = tests[:8]

        return tests

    def _generate_field_boundary_tests(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> List[TestCase]:
        """Generate boundary tests for a specific field."""
        tests = []

        if field_def.type == FieldType.STRING:
            # Minimum length boundary
            if field_def.constraints.min_length:
                test = self._generate_min_length_boundary(endpoint, field_name, field_def)
                tests.append(test)

            # Maximum length boundary
            if field_def.constraints.max_length:
                test = self._generate_max_length_boundary(endpoint, field_name, field_def)
                tests.append(test)

            # Empty string (if not required)
            if not field_def.constraints.required:
                test = self._generate_empty_string_test(endpoint, field_name, field_def)
                tests.append(test)

        elif field_def.type in [FieldType.INTEGER, FieldType.NUMBER]:
            # Minimum value boundary
            if field_def.constraints.minimum is not None:
                test = self._generate_min_value_boundary(endpoint, field_name, field_def)
                tests.append(test)

            # Maximum value boundary
            if field_def.constraints.maximum is not None:
                test = self._generate_max_value_boundary(endpoint, field_name, field_def)
                tests.append(test)

            # Zero
            test = self._generate_zero_value_test(endpoint, field_name, field_def)
            tests.append(test)

        elif field_def.type == FieldType.ARRAY:
            # Empty array (if not required)
            if not field_def.constraints.required:
                test = self._generate_empty_array_test(endpoint, field_name, field_def)
                tests.append(test)

        return tests

    def _generate_min_length_boundary(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with string at minimum length."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        min_len = field_def.constraints.min_length
        request_body[field_name] = "x" * min_len

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"boundary_minlen_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.BOUNDARY,
            description=f"Boundary: {field_name} at minimum length {min_len}",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=200,
            should_pass=True,
            priority=0.7,
        )

    def _generate_max_length_boundary(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with string at maximum length."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        max_len = field_def.constraints.max_length
        request_body[field_name] = "x" * max_len

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"boundary_maxlen_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.BOUNDARY,
            description=f"Boundary: {field_name} at maximum length {max_len}",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=200,
            should_pass=True,
            priority=0.7,
        )

    def _generate_empty_string_test(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with empty string."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)
        request_body[field_name] = ""

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"boundary_empty_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.BOUNDARY,
            description=f"Boundary: {field_name} with empty string",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=200,
            should_pass=True,
            priority=0.6,
        )

    def _generate_min_value_boundary(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with value at minimum."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        minimum = field_def.constraints.minimum
        request_body[field_name] = minimum

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"boundary_minval_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.BOUNDARY,
            description=f"Boundary: {field_name} at minimum value {minimum}",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=200,
            should_pass=True,
            priority=0.7,
        )

    def _generate_max_value_boundary(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with value at maximum."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        maximum = field_def.constraints.maximum
        request_body[field_name] = maximum

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"boundary_maxval_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.BOUNDARY,
            description=f"Boundary: {field_name} at maximum value {maximum}",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=200,
            should_pass=True,
            priority=0.7,
        )

    def _generate_zero_value_test(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with zero value."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)
        request_body[field_name] = 0

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"boundary_zero_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.BOUNDARY,
            description=f"Boundary: {field_name} with zero value",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=200,
            should_pass=True,
            priority=0.6,
        )

    def _generate_empty_array_test(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with empty array."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)
        request_body[field_name] = []

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"boundary_emptyarray_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.BOUNDARY,
            description=f"Boundary: {field_name} with empty array",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=200,
            should_pass=True,
            priority=0.6,
        )

    def _generate_path_params(self, endpoint: Endpoint) -> Dict[str, Any]:
        """Generate valid path parameters."""
        path_params = {}
        for param in endpoint.parameters:
            if param.location == "path":
                path_params[param.name] = self.valid_generator._generate_valid_value(
                    param.type.value, param.constraints
                )
        return path_params
