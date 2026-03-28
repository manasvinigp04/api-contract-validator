"""
Constraint Extractor

Extracts validation constraints from API specifications and builds contract rules.
"""

from typing import Dict, List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.input.normalizer.models import (
    Endpoint,
    FieldDefinition,
    UnifiedAPISpec,
)
from api_contract_validator.schema.contract.contract_model import (
    APIContract,
    ConstraintRule,
    ContractRule,
    EndpointContract,
)

logger = get_logger(__name__)


class ConstraintExtractor:
    """
    Extracts validation constraints and builds executable contract rules.
    """

    def __init__(self, spec: UnifiedAPISpec):
        self.spec = spec
        self.rule_counter = 0

    def extract_contract(self) -> APIContract:
        """
        Extract complete API contract from specification.

        Returns:
            APIContract with all endpoint contracts and rules
        """
        logger.info("Extracting contract from specification")

        endpoint_contracts = {}
        for endpoint in self.spec.endpoints:
            contract = self._extract_endpoint_contract(endpoint)
            endpoint_contracts[endpoint.endpoint_id] = contract

        api_contract = APIContract(spec=self.spec, endpoint_contracts=endpoint_contracts)

        total_rules = sum(len(c.get_all_rules()) for c in endpoint_contracts.values())
        logger.info(f"Extracted {len(endpoint_contracts)} endpoint contracts with {total_rules} rules")

        return api_contract

    def _extract_endpoint_contract(self, endpoint: Endpoint) -> EndpointContract:
        """Extract contract for a single endpoint."""
        # Extract parameter rules
        parameter_rules = []
        for param in endpoint.parameters:
            rules = self._extract_field_rules(
                endpoint.endpoint_id,
                f"parameter.{param.name}",
                param.name,
                param.type.value,
                param.constraints,
                "parameter",
            )
            parameter_rules.extend(rules)

        # Extract request body rules
        request_rules = []
        if endpoint.request_body:
            for field_name, field_def in endpoint.request_body.schema.items():
                rules = self._extract_field_rules_recursive(
                    endpoint.endpoint_id,
                    f"request.{field_name}",
                    field_def,
                    "request_body",
                )
                request_rules.extend(rules)

        # Extract response rules by status code
        response_rules = {}
        for response in endpoint.responses:
            rules = []
            for field_name, field_def in response.schema.items():
                field_rules = self._extract_field_rules_recursive(
                    endpoint.endpoint_id,
                    f"response.{response.status_code}.{field_name}",
                    field_def,
                    "response_body",
                )
                rules.extend(field_rules)
            response_rules[response.status_code] = rules

        return EndpointContract(
            endpoint=endpoint,
            request_rules=request_rules,
            response_rules=response_rules,
            parameter_rules=parameter_rules,
        )

    def _extract_field_rules_recursive(
        self,
        endpoint_id: str,
        field_path: str,
        field_def: FieldDefinition,
        location: str,
    ) -> List[ContractRule]:
        """Recursively extract rules for a field and its nested fields."""
        rules = self._extract_field_rules(
            endpoint_id,
            field_path,
            field_def.name,
            field_def.type.value,
            field_def.constraints,
            location,
        )

        # Recurse into object properties
        if field_def.properties:
            for prop_name, prop_def in field_def.properties.items():
                nested_rules = self._extract_field_rules_recursive(
                    endpoint_id, f"{field_path}.{prop_name}", prop_def, location
                )
                rules.extend(nested_rules)

        # Recurse into array items
        if field_def.items:
            item_rules = self._extract_field_rules_recursive(
                endpoint_id, f"{field_path}[]", field_def.items, location
            )
            rules.extend(item_rules)

        return rules

    def _extract_field_rules(
        self,
        endpoint_id: str,
        field_path: str,
        field_name: str,
        field_type: str,
        constraints: FieldDefinition,
        location: str,
    ) -> List[ContractRule]:
        """Extract validation rules for a single field."""
        constraint_rules = []

        # Type constraint
        constraint_rules.append(
            ConstraintRule(
                rule_type="type",
                field_path=field_path,
                expected_value=field_type,
                description=f"Field must be of type {field_type}",
            )
        )

        # Required constraint
        if hasattr(constraints, "required") and constraints.required:
            constraint_rules.append(
                ConstraintRule(
                    rule_type="required",
                    field_path=field_path,
                    expected_value=True,
                    description="Field is required",
                )
            )

        # String length constraints
        if hasattr(constraints, "min_length") and constraints.min_length is not None:
            constraint_rules.append(
                ConstraintRule(
                    rule_type="min_length",
                    field_path=field_path,
                    expected_value=constraints.min_length,
                    description=f"Minimum length: {constraints.min_length}",
                )
            )

        if hasattr(constraints, "max_length") and constraints.max_length is not None:
            constraint_rules.append(
                ConstraintRule(
                    rule_type="max_length",
                    field_path=field_path,
                    expected_value=constraints.max_length,
                    description=f"Maximum length: {constraints.max_length}",
                )
            )

        # Numeric range constraints
        if hasattr(constraints, "minimum") and constraints.minimum is not None:
            constraint_rules.append(
                ConstraintRule(
                    rule_type="minimum",
                    field_path=field_path,
                    expected_value=constraints.minimum,
                    description=f"Minimum value: {constraints.minimum}",
                )
            )

        if hasattr(constraints, "maximum") and constraints.maximum is not None:
            constraint_rules.append(
                ConstraintRule(
                    rule_type="maximum",
                    field_path=field_path,
                    expected_value=constraints.maximum,
                    description=f"Maximum value: {constraints.maximum}",
                )
            )

        # Pattern constraint
        if hasattr(constraints, "pattern") and constraints.pattern:
            constraint_rules.append(
                ConstraintRule(
                    rule_type="pattern",
                    field_path=field_path,
                    expected_value=constraints.pattern,
                    description=f"Must match pattern: {constraints.pattern}",
                )
            )

        # Enum constraint
        if hasattr(constraints, "enum") and constraints.enum:
            constraint_rules.append(
                ConstraintRule(
                    rule_type="enum",
                    field_path=field_path,
                    expected_value=constraints.enum,
                    description=f"Must be one of: {constraints.enum}",
                )
            )

        # Format constraint
        if hasattr(constraints, "format") and constraints.format:
            constraint_rules.append(
                ConstraintRule(
                    rule_type="format",
                    field_path=field_path,
                    expected_value=constraints.format,
                    description=f"Must match format: {constraints.format}",
                )
            )

        # Create contract rule
        self.rule_counter += 1
        rule = ContractRule(
            rule_id=f"rule_{self.rule_counter}",
            endpoint_id=endpoint_id,
            location=location,
            field_path=field_path,
            constraint_rules=constraint_rules,
            required=getattr(constraints, "required", False),
            nullable=getattr(constraints, "nullable", False),
        )

        return [rule]


def extract_contract(spec: UnifiedAPISpec) -> APIContract:
    """
    Convenience function to extract contract from specification.

    Args:
        spec: UnifiedAPISpec instance

    Returns:
        APIContract instance
    """
    extractor = ConstraintExtractor(spec)
    return extractor.extract_contract()
