"""
Invalid Test Generator

Generates invalid test cases that should fail validation.
"""

import random
import string
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


class InvalidTestGenerator(BaseTestGenerator):
    """Generates invalid test cases that should fail validation."""

    def __init__(self):
        super().__init__()
        self.valid_generator = ValidTestGenerator()

    def generate_tests(self, endpoint: Endpoint) -> List[TestCase]:
        """Generate invalid test cases for an endpoint."""
        tests = []

        # Missing required fields
        if endpoint.request_body:
            for field_name, field_def in endpoint.request_body.schema.items():
                if field_def.constraints.required:
                    test = self._generate_missing_field_test(endpoint, field_name)
                    tests.append(test)

        # Type violations
        if endpoint.request_body:
            for field_name, field_def in endpoint.request_body.schema.items():
                test = self._generate_type_violation_test(endpoint, field_name, field_def)
                tests.append(test)

        # Constraint violations
        if endpoint.request_body:
            for field_name, field_def in endpoint.request_body.schema.items():
                constraint_tests = self._generate_constraint_violation_tests(
                    endpoint, field_name, field_def
                )
                tests.extend(constraint_tests)

        # Limit total invalid tests per endpoint
        if len(tests) > 10:
            # Keep high priority ones
            tests = sorted(tests, key=lambda t: t.priority, reverse=True)[:10]

        return tests

    def _generate_missing_field_test(self, endpoint: Endpoint, missing_field: str) -> TestCase:
        """Generate test with a required field missing."""
        # Generate valid body
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        # Remove the required field
        if missing_field in request_body:
            del request_body[missing_field]

        path_params = {}
        for param in endpoint.parameters:
            if param.location == "path":
                path_params[param.name] = self.valid_generator._generate_valid_value(
                    param.type.value, param.constraints
                )

        return TestCase(
            test_id=self.generate_test_id(f"invalid_missing_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.INVALID,
            description=f"Missing required field: {missing_field}",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=400,
            should_pass=False,
            priority=1.2,
        )

    def _generate_type_violation_test(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with wrong data type."""
        # Generate valid body
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        # Replace field with wrong type
        wrong_type_value = self._generate_wrong_type_value(field_def.type)
        request_body[field_name] = wrong_type_value

        path_params = {}
        for param in endpoint.parameters:
            if param.location == "path":
                path_params[param.name] = self.valid_generator._generate_valid_value(
                    param.type.value, param.constraints
                )

        return TestCase(
            test_id=self.generate_test_id(f"invalid_type_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.INVALID,
            description=f"Type violation for field: {field_name}",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=400,
            should_pass=False,
            priority=1.1,
        )

    def _generate_constraint_violation_tests(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> List[TestCase]:
        """Generate tests violating various constraints."""
        tests = []

        # String length violations
        if field_def.type == FieldType.STRING:
            if field_def.constraints.min_length:
                test = self._generate_string_too_short_test(endpoint, field_name, field_def)
                tests.append(test)

            if field_def.constraints.max_length:
                test = self._generate_string_too_long_test(endpoint, field_name, field_def)
                tests.append(test)

        # Numeric range violations
        if field_def.type in [FieldType.INTEGER, FieldType.NUMBER]:
            if field_def.constraints.minimum is not None:
                test = self._generate_value_too_small_test(endpoint, field_name, field_def)
                tests.append(test)

            if field_def.constraints.maximum is not None:
                test = self._generate_value_too_large_test(endpoint, field_name, field_def)
                tests.append(test)

        # Enum violations
        if field_def.constraints.enum:
            test = self._generate_invalid_enum_test(endpoint, field_name, field_def)
            tests.append(test)

        return tests

    def _generate_string_too_short_test(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with string shorter than minimum."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        min_len = field_def.constraints.min_length
        # Generate string one char shorter than minimum
        request_body[field_name] = "x" * max(0, min_len - 1)

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"invalid_short_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.INVALID,
            description=f"String too short for {field_name} (min: {min_len})",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=400,
            should_pass=False,
            priority=0.9,
        )

    def _generate_string_too_long_test(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with string longer than maximum."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        max_len = field_def.constraints.max_length
        # Generate string one char longer than maximum
        request_body[field_name] = "x" * (max_len + 1)

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"invalid_long_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.INVALID,
            description=f"String too long for {field_name} (max: {max_len})",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=400,
            should_pass=False,
            priority=0.9,
        )

    def _generate_value_too_small_test(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with value below minimum."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        minimum = field_def.constraints.minimum
        request_body[field_name] = minimum - 1

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"invalid_small_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.INVALID,
            description=f"Value too small for {field_name} (min: {minimum})",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=400,
            should_pass=False,
            priority=0.9,
        )

    def _generate_value_too_large_test(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with value above maximum."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        maximum = field_def.constraints.maximum
        request_body[field_name] = maximum + 1

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"invalid_large_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.INVALID,
            description=f"Value too large for {field_name} (max: {maximum})",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=400,
            should_pass=False,
            priority=0.9,
        )

    def _generate_invalid_enum_test(
        self, endpoint: Endpoint, field_name: str, field_def: FieldDefinition
    ) -> TestCase:
        """Generate test with invalid enum value."""
        request_body = self.valid_generator._generate_valid_body(endpoint.request_body.schema)

        # Use a value not in the enum
        request_body[field_name] = "INVALID_ENUM_VALUE"

        path_params = self._generate_path_params(endpoint)

        return TestCase(
            test_id=self.generate_test_id(f"invalid_enum_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.INVALID,
            description=f"Invalid enum value for {field_name}",
            method=endpoint.method,
            path=endpoint.path,
            path_params=path_params,
            request_body=request_body,
            expected_status=400,
            should_pass=False,
            priority=1.0,
        )

    def _generate_wrong_type_value(self, correct_type: FieldType) -> Any:
        """Generate a value of wrong type."""
        if correct_type == FieldType.STRING:
            return 12345  # Number instead of string
        elif correct_type in [FieldType.INTEGER, FieldType.NUMBER]:
            return "not_a_number"  # String instead of number
        elif correct_type == FieldType.BOOLEAN:
            return "true"  # String instead of boolean
        elif correct_type == FieldType.ARRAY:
            return "not_an_array"  # String instead of array
        elif correct_type == FieldType.OBJECT:
            return "not_an_object"  # String instead of object
        else:
            return None

    def _generate_path_params(self, endpoint: Endpoint) -> Dict[str, Any]:
        """Generate valid path parameters."""
        path_params = {}
        for param in endpoint.parameters:
            if param.location == "path":
                path_params[param.name] = self.valid_generator._generate_valid_value(
                    param.type.value, param.constraints
                )
        return path_params
