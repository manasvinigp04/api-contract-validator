"""
Unit tests for valid test generator.
"""

import pytest

from api_contract_validator.generation.base import TestCase, TestCaseType
from api_contract_validator.generation.valid.generator import ValidTestGenerator
from api_contract_validator.input.normalizer.models import (
    Endpoint,
    FieldConstraint,
    FieldDefinition,
    FieldType,
    HTTPMethod,
    Parameter,
    RequestBody,
    ResponseBody,
)


@pytest.mark.unit
class TestValidTestGenerator:
    """Test ValidTestGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create ValidTestGenerator instance."""
        return ValidTestGenerator()

    def test_generate_happy_path_test(self, generator, simple_post_endpoint):
        """Test generating primary happy path test."""
        tests = generator.generate_tests(simple_post_endpoint)

        assert len(tests) >= 1
        test = tests[0]

        assert isinstance(test, TestCase)
        assert test.test_type == TestCaseType.VALID
        assert test.should_pass is True
        assert test.method == HTTPMethod.POST
        assert test.path == "/users"
        assert test.priority == 1.0
        assert test.expected_status == 201

        # Should have request body with required fields
        assert test.request_body is not None
        assert "email" in test.request_body
        assert "name" in test.request_body

    def test_generate_minimal_valid_test(self, generator):
        """Test generating minimal test with only required fields."""
        # Create endpoint with many optional fields
        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "email": FieldDefinition(
                        name="email",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=True, format="email"),
                    ),
                    "name": FieldDefinition(
                        name="name",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=True),
                    ),
                    "age": FieldDefinition(
                        name="age",
                        type=FieldType.INTEGER,
                        constraints=FieldConstraint(required=False),
                    ),
                    "phone": FieldDefinition(
                        name="phone",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=False),
                    ),
                    "address": FieldDefinition(
                        name="address",
                        type=FieldType.STRING,
                        constraints=FieldConstraint(required=False),
                    ),
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        tests = generator.generate_tests(endpoint)

        # Should generate 2 tests (happy path + minimal) due to >3 fields
        assert len(tests) == 2

        minimal_test = tests[1]
        assert minimal_test.test_type == TestCaseType.VALID
        assert minimal_test.priority == 0.8
        assert "email" in minimal_test.request_body
        assert "name" in minimal_test.request_body
        # Optional fields should not be present
        assert "age" not in minimal_test.request_body
        assert "phone" not in minimal_test.request_body

    def test_generate_valid_string_with_email_format(self, generator):
        """Test generating valid email string."""
        field_def = FieldDefinition(
            name="email",
            type=FieldType.STRING,
            constraints=FieldConstraint(format="email"),
        )

        value = generator._generate_valid_field_value(field_def)

        assert isinstance(value, str)
        assert "@" in value
        assert "." in value

    def test_generate_valid_string_with_uuid_format(self, generator):
        """Test generating valid UUID string."""
        field_def = FieldDefinition(
            name="id",
            type=FieldType.STRING,
            constraints=FieldConstraint(format="uuid"),
        )

        value = generator._generate_valid_field_value(field_def)

        assert isinstance(value, str)
        # UUID format: 8-4-4-4-12 hex chars
        parts = value.split("-")
        assert len(parts) == 5

    def test_generate_valid_string_with_datetime_format(self, generator):
        """Test generating valid date-time string."""
        field_def = FieldDefinition(
            name="created_at",
            type=FieldType.STRING,
            constraints=FieldConstraint(format="date-time"),
        )

        value = generator._generate_valid_field_value(field_def)

        assert isinstance(value, str)
        assert "T" in value  # ISO format separator

    def test_generate_valid_integer_with_constraints(self, generator):
        """Test generating valid integer within bounds."""
        field_def = FieldDefinition(
            name="age",
            type=FieldType.INTEGER,
            constraints=FieldConstraint(minimum=18, maximum=65),
        )

        value = generator._generate_valid_field_value(field_def)

        assert isinstance(value, int)
        assert 18 <= value <= 65

    def test_generate_valid_number_with_constraints(self, generator):
        """Test generating valid number/float within bounds."""
        field_def = FieldDefinition(
            name="price",
            type=FieldType.NUMBER,
            constraints=FieldConstraint(minimum=0.0, maximum=1000.0),
        )

        value = generator._generate_valid_field_value(field_def)

        assert isinstance(value, (int, float))
        assert 0.0 <= value <= 1000.0

    def test_generate_valid_enum_value(self, generator):
        """Test generating valid value from enum."""
        field_def = FieldDefinition(
            name="status",
            type=FieldType.STRING,
            constraints=FieldConstraint(enum=["active", "inactive", "suspended"]),
        )

        value = generator._generate_valid_field_value(field_def)

        assert value in ["active", "inactive", "suspended"]

    def test_generate_valid_boolean(self, generator):
        """Test generating valid boolean value."""
        field_def = FieldDefinition(
            name="is_active",
            type=FieldType.BOOLEAN,
        )

        value = generator._generate_valid_field_value(field_def)

        assert isinstance(value, bool)

    def test_generate_valid_array(self, generator):
        """Test generating valid array."""
        field_def = FieldDefinition(
            name="tags",
            type=FieldType.ARRAY,
            items=FieldDefinition(
                name="tag",
                type=FieldType.STRING,
            ),
        )

        value = generator._generate_valid_field_value(field_def)

        assert isinstance(value, list)
        assert len(value) >= 1
        assert all(isinstance(item, str) for item in value)

    def test_generate_valid_nested_object(self, generator):
        """Test generating valid nested object."""
        field_def = FieldDefinition(
            name="address",
            type=FieldType.OBJECT,
            properties={
                "street": FieldDefinition(
                    name="street",
                    type=FieldType.STRING,
                    constraints=FieldConstraint(required=True),
                ),
                "city": FieldDefinition(
                    name="city",
                    type=FieldType.STRING,
                    constraints=FieldConstraint(required=True),
                ),
            },
        )

        value = generator._generate_valid_field_value(field_def)

        assert isinstance(value, dict)
        assert "street" in value
        assert "city" in value

    def test_generate_path_params_substitution(self, generator, simple_get_endpoint):
        """Test generating path parameters."""
        tests = generator.generate_tests(simple_get_endpoint)

        test = tests[0]
        assert "userId" in test.path_params
        assert isinstance(test.path_params["userId"], int)
        assert test.path_params["userId"] >= 1  # minimum constraint

        # Test full_path property
        full_path = test.full_path
        assert "{userId}" not in full_path
        assert f"/{test.path_params['userId']}" in full_path

    def test_expected_status_selection(self, generator):
        """Test selection of expected status code."""
        # Endpoint with multiple success responses
        endpoint = Endpoint(
            path="/test",
            method=HTTPMethod.POST,
            responses=[
                ResponseBody(status_code=200, schema={}),
                ResponseBody(status_code=201, schema={}),
                ResponseBody(status_code=400, schema={}),
            ],
        )

        tests = generator.generate_tests(endpoint)

        # Should pick first 2xx status (200)
        assert tests[0].expected_status == 200

    def test_generate_tests_returns_list(self, generator, simple_get_endpoint):
        """Test that generate_tests returns a list."""
        tests = generator.generate_tests(simple_get_endpoint)

        assert isinstance(tests, list)
        assert len(tests) >= 1
        assert all(isinstance(t, TestCase) for t in tests)

    def test_test_id_uniqueness(self, generator, simple_get_endpoint):
        """Test that generated test IDs are unique."""
        tests1 = generator.generate_tests(simple_get_endpoint)
        tests2 = generator.generate_tests(simple_get_endpoint)

        test_ids = [t.test_id for t in tests1 + tests2]
        assert len(test_ids) == len(set(test_ids))
