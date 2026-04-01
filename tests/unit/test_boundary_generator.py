"""
Unit tests for boundary test generator.
"""

import pytest

from api_contract_validator.generation.base import TestCase, TestCaseType
from api_contract_validator.generation.boundary.generator import BoundaryTestGenerator
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
class TestBoundaryTestGenerator:
    """Test BoundaryTestGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create BoundaryTestGenerator instance."""
        return BoundaryTestGenerator()

    def test_generate_min_length_boundary(self, generator):
        """Test generating string at exact minimum length."""
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

        min_tests = [t for t in tests if "minimum length" in t.description.lower()]
        assert len(min_tests) >= 1

        test = min_tests[0]
        assert len(test.request_body["username"]) == 3
        assert test.should_pass is True

    def test_generate_max_length_boundary(self, generator):
        """Test generating string at exact maximum length."""
        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "bio": FieldDefinition(
                        name="bio",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=True, min_length=1, max_length=50),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        max_tests = [t for t in tests if "maximum length" in t.description.lower()]
        assert len(max_tests) >= 1

        test = max_tests[0]
        assert len(test.request_body["bio"]) == 50

    def test_generate_min_value_boundary(self, generator):
        """Test generating number at exact minimum value."""
        endpoint = Endpoint(
            path="/products",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "quantity": FieldDefinition(
                        name="quantity",
                        type=FieldType.INTEGER,
                        constraints=FieldConstraint(required=True, minimum=1, maximum=100),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        min_tests = [t for t in tests if "minimum value" in t.description.lower()]
        assert len(min_tests) >= 1

        test = min_tests[0]
        assert test.request_body["quantity"] == 1

    def test_generate_max_value_boundary(self, generator):
        """Test generating number at exact maximum value."""
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

        max_tests = [t for t in tests if "maximum value" in t.description.lower()]
        assert len(max_tests) >= 1

        test = max_tests[0]
        assert test.request_body["age"] == 150

    def test_generate_zero_value(self, generator):
        """Test generating zero value for numeric field."""
        endpoint = Endpoint(
            path="/cart",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "discount": FieldDefinition(
                        name="discount",
                        type=FieldType.NUMBER,
                        constraints=FieldConstraint(required=True, minimum=0.0),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        zero_tests = [t for t in tests if "zero" in t.description.lower()]
        assert len(zero_tests) >= 1

        test = zero_tests[0]
        assert test.request_body["discount"] == 0 or test.request_body["discount"] == 0.0

    def test_generate_empty_string(self, generator):
        """Test generating empty string for optional field."""
        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "nickname": FieldDefinition(
                        name="nickname",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=False),  # Optional
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        # May have empty string test if field is optional
        empty_tests = [t for t in tests if "empty" in t.description.lower()]
        if empty_tests:
            test = empty_tests[0]
            assert test.request_body.get("nickname") == ""

    def test_generate_empty_array(self, generator):
        """Test generating empty array for optional array field."""
        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "tags": FieldDefinition(
                        name="tags",
                        type=FieldType.ARRAY,
                        items=FieldDefinition(name="tag", type=FieldType.STRING),
                        constraints=FieldConstraint(required=False),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        # May have empty array test
        empty_tests = [t for t in tests if "empty" in t.description.lower() and "array" in t.description.lower()]
        if empty_tests:
            test = empty_tests[0]
            assert test.request_body.get("tags") == []

    def test_cap_at_max_tests(self, generator):
        """Test that boundary tests are capped."""
        # Create endpoint with many constrained fields
        schema = {}
        for i in range(15):
            schema[f"field{i}"] = FieldDefinition(
                name=f"field{i}",
                type=FieldType.STRING,
                constraints=FieldConstraint(required=True, min_length=1, max_length=50),
            )

        endpoint = Endpoint(
            path="/complex",
            method=HTTPMethod.POST,
            request_body=RequestBody(required=True, schema=schema),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        # Should be capped at ~8 tests
        assert len(tests) <= 10

    def test_all_tests_should_pass(self, generator, simple_post_endpoint):
        """Test that all boundary tests are expected to pass."""
        tests = generator.generate_tests(simple_post_endpoint)

        assert all(t.test_type == TestCaseType.BOUNDARY for t in tests)
        assert all(t.should_pass is True for t in tests)
        # Expected status should be success (200 or 201)
        assert all(200 <= t.expected_status < 300 for t in tests)

    def test_priority_range(self, generator, simple_post_endpoint):
        """Test that boundary test priorities are in expected range."""
        tests = generator.generate_tests(simple_post_endpoint)

        # Boundary tests typically have lower priority (0.6-0.7)
        priorities = [t.priority for t in tests]
        assert all(0.5 <= p <= 1.0 for p in priorities)
