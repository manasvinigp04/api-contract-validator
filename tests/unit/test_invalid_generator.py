"""
Unit tests for invalid test generator.
"""

import pytest

from api_contract_validator.generation.base import TestCase, TestCaseType
from api_contract_validator.generation.invalid.generator import InvalidTestGenerator
from api_contract_validator.input.normalizer.models import (
    Endpoint,
    FieldConstraint,
    FieldDefinition,
    FieldType,
    HTTPMethod,
    RequestBody,
    ResponseBody,
)


@pytest.mark.unit
class TestInvalidTestGenerator:
    """Test InvalidTestGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create InvalidTestGenerator instance."""
        return InvalidTestGenerator()

    def test_generate_missing_required_field(self, generator, simple_post_endpoint):
        """Test generating test with missing required field."""
        tests = generator.generate_tests(simple_post_endpoint)

        # Should have tests for missing email and missing name
        missing_tests = [t for t in tests if "missing required field" in t.description.lower()]
        assert len(missing_tests) >= 2

        # Check structure
        for test in missing_tests:
            assert test.test_type == TestCaseType.INVALID
            assert test.should_pass is False
            assert test.expected_status == 400
            assert test.priority >= 1.0

    def test_generate_type_violation(self, generator):
        """Test generating test with wrong data type."""
        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "age": FieldDefinition(
                        name="age",
                        type=FieldType.INTEGER,
                        constraints=FieldConstraint(required=True),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        type_violation_tests = [t for t in tests if "type" in t.description.lower()]
        assert len(type_violation_tests) >= 1

        test = type_violation_tests[0]
        # Age should be sent as wrong type (e.g., string instead of int)
        assert test.request_body is not None
        assert "age" in test.request_body
        # Value should be wrong type
        assert not isinstance(test.request_body["age"], int)

    def test_generate_string_too_short(self, generator):
        """Test generating test with string shorter than minimum."""
        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "username": FieldDefinition(
                        name="username",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=True, min_length=3, max_length=20),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        short_tests = [t for t in tests if "too short" in t.description.lower() or "below minimum" in t.description.lower()]
        assert len(short_tests) >= 1

        test = short_tests[0]
        assert len(test.request_body["username"]) < 3

    def test_generate_string_too_long(self, generator):
        """Test generating test with string longer than maximum."""
        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "bio": FieldDefinition(
                        name="bio",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=True, max_length=100),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        long_tests = [t for t in tests if "too long" in t.description.lower() or "exceeds maximum" in t.description.lower()]
        assert len(long_tests) >= 1

        test = long_tests[0]
        assert len(test.request_body["bio"]) > 100

    def test_generate_value_too_small(self, generator):
        """Test generating test with numeric value below minimum."""
        endpoint = Endpoint(
            path="/products",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "price": FieldDefinition(
                        name="price",
                        type=FieldType.NUMBER,
                        constraints=FieldConstraint(required=True, minimum=0.01, maximum=10000.0),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        small_tests = [t for t in tests if "too small" in t.description.lower() or "below minimum" in t.description.lower()]
        assert len(small_tests) >= 1

        test = small_tests[0]
        assert test.request_body["price"] < 0.01

    def test_generate_value_too_large(self, generator):
        """Test generating test with numeric value above maximum."""
        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "age": FieldDefinition(
                        name="age",
                        type=FieldType.INTEGER,
                        constraints=FieldConstraint(required=True, minimum=0, maximum=150),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        large_tests = [t for t in tests if "too large" in t.description.lower() or "exceeds maximum" in t.description.lower()]
        assert len(large_tests) >= 1

        test = large_tests[0]
        assert test.request_body["age"] > 150

    def test_generate_invalid_enum_value(self, generator):
        """Test generating test with invalid enum value."""
        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "status": FieldDefinition(
                        name="status",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=True, enum=["active", "inactive"]),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        enum_tests = [t for t in tests if "enum" in t.description.lower() or "invalid" in t.description.lower()]
        assert len(enum_tests) >= 1

        test = enum_tests[0]
        assert test.request_body["status"] not in ["active", "inactive"]

    def test_cap_at_max_tests(self, generator):
        """Test that tests are capped at 10 per endpoint."""
        # Create endpoint with many fields to generate many tests
        schema = {}
        for i in range(20):
            schema[f"field{i}"] = FieldDefinition(
                name=f"field{i}",
                type=FieldType.STRING,
                constraints=FieldConstraint(required=True, min_length=1, max_length=100),
            )

        endpoint = Endpoint(
            path="/complex",
            method=HTTPMethod.POST,
            request_body=RequestBody(required=True, schema=schema),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        # Should be capped at 10 tests
        assert len(tests) <= 10

    def test_priority_assignment(self, generator, simple_post_endpoint):
        """Test that priorities are assigned correctly."""
        tests = generator.generate_tests(simple_post_endpoint)

        # Missing field tests should have highest priority (1.2)
        missing_tests = [t for t in tests if "missing" in t.description.lower()]
        if missing_tests:
            assert all(t.priority >= 1.1 for t in missing_tests)

    def test_all_tests_marked_invalid(self, generator, simple_post_endpoint):
        """Test that all generated tests are marked as invalid."""
        tests = generator.generate_tests(simple_post_endpoint)

        assert all(t.test_type == TestCaseType.INVALID for t in tests)
        assert all(t.should_pass is False for t in tests)
        assert all(t.expected_status == 400 for t in tests)

    def test_generate_tests_with_path_params(self, generator):
        """Test generating invalid tests for endpoint with path params."""
        endpoint = Endpoint(
            path="/users/{userId}",
            method=HTTPMethod.PATCH,
            parameters=[
                Parameter(
                    name="userId",
                    location="path",
                    type=FieldType.INTEGER,
                    constraints=FieldConstraint(required=True, minimum=1),
                )
            ],
            request_body=RequestBody(
                required=True,
                schema={
                    "name": FieldDefinition(
                        name="name",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=True),
                    )
                },
            ),
            responses=[ResponseBody(status_code=200, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        # All tests should have valid path params (invalid tests focus on body/query)
        assert all("userId" in t.path_params for t in tests)
        assert all(t.path_params["userId"] >= 1 for t in tests)
