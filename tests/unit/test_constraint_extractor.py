"""
Unit tests for constraint extractor.
"""

import pytest

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
from api_contract_validator.schema.contract.constraint_extractor import (
    ConstraintExtractor,
    extract_contract,
)
from api_contract_validator.schema.contract.contract_model import (
    APIContract,
    EndpointContract,
)


@pytest.mark.unit
class TestConstraintExtractor:
    """Test ConstraintExtractor class."""

    def test_extract_contract_basic(self, simple_unified_spec):
        """Test extracting contract from simple spec."""
        extractor = ConstraintExtractor(simple_unified_spec)
        contract = extractor.extract_contract()

        assert isinstance(contract, APIContract)
        assert len(contract.endpoint_contracts) == 2
        assert contract.spec == simple_unified_spec

        # Verify all endpoint IDs are present
        endpoint_ids = set(contract.endpoint_contracts.keys())
        expected_ids = {ep.endpoint_id for ep in simple_unified_spec.endpoints}
        assert endpoint_ids == expected_ids

    def test_extract_parameter_constraints(self, simple_get_endpoint):
        """Test extracting parameter constraints."""
        from api_contract_validator.input.normalizer.models import UnifiedAPISpec, APIMetadata, SourceType

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Test", version="1.0.0"),
            endpoints=[simple_get_endpoint],
        )

        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        endpoint_contract = contract.get_contract(simple_get_endpoint.endpoint_id)
        assert endpoint_contract is not None
        assert len(endpoint_contract.parameter_rules) > 0

        # Find userId parameter rule
        user_id_rules = [r for r in endpoint_contract.parameter_rules if "userId" in r.field_path]
        assert len(user_id_rules) > 0

        # Check constraint rules
        user_id_rule = user_id_rules[0]
        assert user_id_rule.location == "parameter"
        assert len(user_id_rule.constraint_rules) > 0

        # Should have type, required, and minimum constraints
        rule_types = {cr.rule_type for cr in user_id_rule.constraint_rules}
        assert "type" in rule_types
        assert "required" in rule_types
        assert "minimum" in rule_types

    def test_extract_request_body_constraints(self, simple_post_endpoint):
        """Test extracting request body constraints."""
        from api_contract_validator.input.normalizer.models import UnifiedAPISpec, APIMetadata, SourceType

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Test", version="1.0.0"),
            endpoints=[simple_post_endpoint],
        )

        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        endpoint_contract = contract.get_contract(simple_post_endpoint.endpoint_id)
        assert len(endpoint_contract.request_rules) > 0

        # Should have rules for email, name, age fields
        field_paths = {r.field_path for r in endpoint_contract.request_rules}
        assert "request.email" in field_paths
        assert "request.name" in field_paths
        assert "request.age" in field_paths

    def test_extract_response_body_constraints(self, simple_get_endpoint):
        """Test extracting response body constraints."""
        from api_contract_validator.input.normalizer.models import UnifiedAPISpec, APIMetadata, SourceType

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Test", version="1.0.0"),
            endpoints=[simple_get_endpoint],
        )

        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        endpoint_contract = contract.get_contract(simple_get_endpoint.endpoint_id)

        # Should have response rules for status 200 and 404
        assert 200 in endpoint_contract.response_rules
        assert 404 in endpoint_contract.response_rules

        # 200 response should have id, email, name fields
        rules_200 = endpoint_contract.response_rules[200]
        field_paths_200 = {r.field_path for r in rules_200}
        assert "response.200.id" in field_paths_200
        assert "response.200.email" in field_paths_200
        assert "response.200.name" in field_paths_200

    def test_extract_nested_field_rules(self):
        """Test extracting rules from nested object properties."""
        from api_contract_validator.input.normalizer.models import (
            UnifiedAPISpec,
            APIMetadata,
            SourceType,
        )

        # Create endpoint with nested address object
        address_fields = {
            "street": FieldDefinition(
                name="street",
                type=FieldType.STRING,
                constraints=FieldConstraint(required=True),
            ),
            "city": FieldDefinition(
                name="city",
                type=FieldType.STRING,
                constraints=FieldConstraint(required=True, min_length=2),
            ),
        }

        endpoint = Endpoint(
            path="/users",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "address": FieldDefinition(
                        name="address",
                        type=FieldType.OBJECT,
                        properties=address_fields,
                        constraints=FieldConstraint(required=True),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Test", version="1.0.0"),
            endpoints=[endpoint],
        )

        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        endpoint_contract = contract.get_contract(endpoint.endpoint_id)

        # Should have rules for address and nested fields
        field_paths = {r.field_path for r in endpoint_contract.request_rules}
        assert "request.address" in field_paths
        assert "request.address.street" in field_paths
        assert "request.address.city" in field_paths

        # Check nested field constraints
        city_rules = [r for r in endpoint_contract.request_rules if r.field_path == "request.address.city"]
        assert len(city_rules) > 0
        city_rule = city_rules[0]

        # Should have min_length constraint
        constraint_types = {cr.rule_type for cr in city_rule.constraint_rules}
        assert "min_length" in constraint_types

    def test_extract_array_field_rules(self):
        """Test extracting rules from array items."""
        from api_contract_validator.input.normalizer.models import (
            UnifiedAPISpec,
            APIMetadata,
            SourceType,
        )

        # Create endpoint with array of strings
        endpoint = Endpoint(
            path="/items",
            method=HTTPMethod.POST,
            request_body=RequestBody(
                required=True,
                schema={
                    "tags": FieldDefinition(
                        name="tags",
                        type=FieldType.ARRAY,
                        items=FieldDefinition(
                            name="tag",
                            type=FieldType.STRING,
                            constraints=FieldConstraint(min_length=1, max_length=20),
                        ),
                        constraints=FieldConstraint(required=True),
                    )
                },
            ),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Test", version="1.0.0"),
            endpoints=[endpoint],
        )

        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        endpoint_contract = contract.get_contract(endpoint.endpoint_id)

        # Should have rules for tags array and array items
        field_paths = {r.field_path for r in endpoint_contract.request_rules}
        assert "request.tags" in field_paths
        assert "request.tags[]" in field_paths  # Array item notation

    def test_extract_all_constraint_types(self):
        """Test extraction of all constraint types."""
        from api_contract_validator.input.normalizer.models import (
            UnifiedAPISpec,
            APIMetadata,
            SourceType,
        )

        # Create field with all constraints
        field_def = FieldDefinition(
            name="username",
            type=FieldType.STRING,
            constraints=FieldConstraint(
                required=True,
                nullable=False,
                min_length=3,
                max_length=20,
                pattern=r"^[a-zA-Z0-9_]+$",
                enum=None,  # Can't have enum and pattern together typically
                format=None,
            ),
        )

        endpoint = Endpoint(
            path="/register",
            method=HTTPMethod.POST,
            request_body=RequestBody(required=True, schema={"username": field_def}),
            responses=[ResponseBody(status_code=201, schema={})],
        )

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Test", version="1.0.0"),
            endpoints=[endpoint],
        )

        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        endpoint_contract = contract.get_contract(endpoint.endpoint_id)
        username_rules = [r for r in endpoint_contract.request_rules if r.field_path == "request.username"]
        assert len(username_rules) == 1

        constraint_rule = username_rules[0]
        rule_types = {cr.rule_type for cr in constraint_rule.constraint_rules}

        # Should have all constraint types
        assert "type" in rule_types
        assert "required" in rule_types
        assert "min_length" in rule_types
        assert "max_length" in rule_types
        assert "pattern" in rule_types

    def test_extract_endpoint_with_no_body(self, simple_get_endpoint):
        """Test extracting contract for GET endpoint without request body."""
        from api_contract_validator.input.normalizer.models import UnifiedAPISpec, APIMetadata, SourceType

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Test", version="1.0.0"),
            endpoints=[simple_get_endpoint],
        )

        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        endpoint_contract = contract.get_contract(simple_get_endpoint.endpoint_id)

        # Should have parameter rules but no request body rules
        assert len(endpoint_contract.parameter_rules) > 0
        assert len(endpoint_contract.request_rules) == 0

    def test_extract_empty_endpoint(self):
        """Test extracting contract from minimal endpoint."""
        from api_contract_validator.input.normalizer.models import (
            UnifiedAPISpec,
            APIMetadata,
            SourceType,
        )

        # Minimal endpoint - no params, no body
        endpoint = Endpoint(
            path="/health",
            method=HTTPMethod.GET,
            responses=[ResponseBody(status_code=200, schema={})],
        )

        spec = UnifiedAPISpec(
            source_type=SourceType.OPENAPI,
            source_path="/test/spec.yaml",
            metadata=APIMetadata(title="Test", version="1.0.0"),
            endpoints=[endpoint],
        )

        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        endpoint_contract = contract.get_contract(endpoint.endpoint_id)

        # Should have no rules (or minimal rules)
        assert len(endpoint_contract.parameter_rules) == 0
        assert len(endpoint_contract.request_rules) == 0

    def test_rule_id_uniqueness(self, simple_unified_spec):
        """Test that all rule IDs are unique."""
        extractor = ConstraintExtractor(simple_unified_spec)
        contract = extractor.extract_contract()

        all_rule_ids = []
        for endpoint_contract in contract.get_all_contracts():
            for rule in endpoint_contract.get_all_rules():
                all_rule_ids.append(rule.rule_id)

        # Check uniqueness
        assert len(all_rule_ids) == len(set(all_rule_ids))

    def test_get_critical_contracts(self, simple_unified_spec):
        """Test filtering critical endpoint contracts."""
        extractor = ConstraintExtractor(simple_unified_spec)
        contract = extractor.extract_contract()

        critical_contracts = contract.get_critical_contracts()

        # Should only include POST endpoint
        assert len(critical_contracts) == 1
        assert critical_contracts[0].endpoint.method == HTTPMethod.POST

    def test_convenience_function(self, simple_unified_spec):
        """Test the convenience function wrapper."""
        contract = extract_contract(simple_unified_spec)

        assert isinstance(contract, APIContract)
        assert len(contract.endpoint_contracts) > 0
