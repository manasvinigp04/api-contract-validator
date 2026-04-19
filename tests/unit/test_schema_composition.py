"""
Tests for Schema Composition Validators

Tests discriminator, oneOf, anyOf, allOf validation
"""

import pytest

from api_contract_validator.schema.composition.discriminator_validator import DiscriminatorValidator
from api_contract_validator.schema.composition.oneof_validator import OneOfValidator
from api_contract_validator.schema.composition.anyof_validator import AnyOfValidator
from api_contract_validator.schema.composition.allof_validator import AllOfValidator


class TestDiscriminatorValidator:
    """Test discriminator validation for polymorphic types."""

    @pytest.fixture
    def spec_dict(self):
        """OpenAPI spec with discriminator schemas."""
        return {
            "components": {
                "schemas": {
                    "DataDestination": {
                        "discriminator": {
                            "propertyName": "type",
                            "mapping": {
                                "HDL": "#/components/schemas/HDLDataDestination",
                                "S3": "#/components/schemas/S3DataDestination",
                            },
                        },
                        "oneOf": [
                            {"$ref": "#/components/schemas/HDLDataDestination"},
                            {"$ref": "#/components/schemas/S3DataDestination"},
                        ],
                    },
                    "HDLDataDestination": {
                        "type": "object",
                        "required": ["type", "host"],
                        "properties": {
                            "type": {"type": "string", "enum": ["HDL"]},
                            "host": {"type": "string"},
                        },
                    },
                    "S3DataDestination": {
                        "type": "object",
                        "required": ["type", "bucket"],
                        "properties": {
                            "type": {"type": "string", "enum": ["S3"]},
                            "bucket": {"type": "string"},
                        },
                    },
                }
            }
        }

    def test_valid_hdl_discriminator(self, spec_dict):
        """Test valid HDL type validates correctly."""
        validator = DiscriminatorValidator(spec_dict)
        schema = spec_dict["components"]["schemas"]["DataDestination"]

        data = {"type": "HDL", "host": "example.com"}

        violations = validator.validate(data, schema, "POST:/destinations", "response_body")

        assert len(violations) == 0

    def test_missing_discriminator_field(self, spec_dict):
        """Test missing discriminator field is detected."""
        validator = DiscriminatorValidator(spec_dict)
        schema = spec_dict["components"]["schemas"]["DataDestination"]

        data = {"host": "example.com"}  # Missing 'type'

        violations = validator.validate(data, schema, "POST:/destinations", "response_body")

        assert len(violations) > 0
        assert any("discriminator" in v.message.lower() for v in violations)

    def test_unknown_discriminator_value(self, spec_dict):
        """Test unknown discriminator value is detected."""
        validator = DiscriminatorValidator(spec_dict)
        schema = spec_dict["components"]["schemas"]["DataDestination"]

        data = {"type": "AZURE", "host": "example.com"}  # Unknown type

        violations = validator.validate(data, schema, "POST:/destinations", "response_body")

        assert len(violations) > 0
        assert any("unknown discriminator" in v.message.lower() for v in violations)


class TestOneOfValidator:
    """Test oneOf schema composition."""

    @pytest.fixture
    def spec_dict(self):
        return {
            "components": {
                "schemas": {
                    "EmailContact": {
                        "type": "object",
                        "required": ["email"],
                        "properties": {"email": {"type": "string", "format": "email"}},
                    },
                    "PhoneContact": {
                        "type": "object",
                        "required": ["phone"],
                        "properties": {"phone": {"type": "string"}},
                    },
                }
            }
        }

    def test_matches_one_schema(self, spec_dict):
        """Test data matching exactly one schema passes."""
        validator = OneOfValidator(spec_dict)
        oneof_schemas = [
            {"$ref": "#/components/schemas/EmailContact"},
            {"$ref": "#/components/schemas/PhoneContact"},
        ]

        data = {"email": "test@example.com"}

        violations = validator.validate(data, oneof_schemas, "POST:/contact", "request_body")

        assert len(violations) == 0

    def test_matches_no_schema(self, spec_dict):
        """Test data matching no schemas fails."""
        validator = OneOfValidator(spec_dict)
        oneof_schemas = [
            {"$ref": "#/components/schemas/EmailContact"},
            {"$ref": "#/components/schemas/PhoneContact"},
        ]

        data = {}  # No required fields

        violations = validator.validate(data, oneof_schemas, "POST:/contact", "request_body")

        assert len(violations) > 0
        assert any("doesn't match any" in v.message.lower() for v in violations)

    def test_matches_multiple_schemas(self, spec_dict):
        """Test data matching multiple schemas fails."""
        validator = OneOfValidator(spec_dict)
        oneof_schemas = [
            {"$ref": "#/components/schemas/EmailContact"},
            {"$ref": "#/components/schemas/PhoneContact"},
        ]

        data = {"email": "test@example.com", "phone": "+1234567890"}

        violations = validator.validate(data, oneof_schemas, "POST:/contact", "request_body")

        # Should fail because both schemas match
        assert len(violations) > 0
        assert any("matches 2 schemas" in v.message.lower() for v in violations)


class TestAnyOfValidator:
    """Test anyOf schema composition."""

    @pytest.fixture
    def spec_dict(self):
        return {
            "components": {
                "schemas": {
                    "EmailContact": {
                        "type": "object",
                        "required": ["email"],
                        "properties": {"email": {"type": "string"}},
                    },
                    "PhoneContact": {
                        "type": "object",
                        "required": ["phone"],
                        "properties": {"phone": {"type": "string"}},
                    },
                }
            }
        }

    def test_matches_one_schema(self, spec_dict):
        """Test data matching at least one schema passes."""
        validator = AnyOfValidator(spec_dict)
        anyof_schemas = [
            {"$ref": "#/components/schemas/EmailContact"},
            {"$ref": "#/components/schemas/PhoneContact"},
        ]

        data = {"email": "test@example.com"}

        violations = validator.validate(data, anyof_schemas, "POST:/contact", "request_body")

        assert len(violations) == 0

    def test_matches_no_schema(self, spec_dict):
        """Test data matching no schemas fails."""
        validator = AnyOfValidator(spec_dict)
        anyof_schemas = [
            {"$ref": "#/components/schemas/EmailContact"},
            {"$ref": "#/components/schemas/PhoneContact"},
        ]

        data = {}  # No required fields

        violations = validator.validate(data, anyof_schemas, "POST:/contact", "request_body")

        assert len(violations) > 0
        assert any("doesn't match any" in v.message.lower() for v in violations)


class TestAllOfValidator:
    """Test allOf schema composition."""

    @pytest.fixture
    def spec_dict(self):
        return {
            "components": {
                "schemas": {
                    "BaseEntity": {
                        "type": "object",
                        "required": ["id", "createdAt"],
                        "properties": {
                            "id": {"type": "string"},
                            "createdAt": {"type": "string", "format": "date-time"},
                        },
                    },
                    "NamedEntity": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {"name": {"type": "string"}},
                    },
                }
            }
        }

    def test_merges_all_schemas(self, spec_dict):
        """Test data must satisfy all schemas."""
        validator = AllOfValidator(spec_dict)
        allof_schemas = [
            {"$ref": "#/components/schemas/BaseEntity"},
            {"$ref": "#/components/schemas/NamedEntity"},
        ]

        # Valid: has all required fields from both schemas
        data = {"id": "123", "createdAt": "2024-01-01T00:00:00Z", "name": "Test"}

        violations = validator.validate(data, allof_schemas, "GET:/entities", "response_body")

        assert len(violations) == 0

    def test_missing_field_from_merged_schema(self, spec_dict):
        """Test missing field from merged schema is detected."""
        validator = AllOfValidator(spec_dict)
        allof_schemas = [
            {"$ref": "#/components/schemas/BaseEntity"},
            {"$ref": "#/components/schemas/NamedEntity"},
        ]

        # Invalid: missing 'name' from NamedEntity schema
        data = {"id": "123", "createdAt": "2024-01-01T00:00:00Z"}

        violations = validator.validate(data, allof_schemas, "GET:/entities", "response_body")

        assert len(violations) > 0
