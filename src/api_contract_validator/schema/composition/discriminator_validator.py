"""
Discriminator Validator

Validates polymorphic schemas using OpenAPI discriminator property.

Example:
    discriminator:
      propertyName: type
      mapping:
        HDL: "#/components/schemas/HDLDataDestination"
        S3: "#/components/schemas/S3DataDestination"
"""

from typing import Any, Dict, List, Optional

from api_contract_validator.config.logging import get_logger
from api_contract_validator.schema.contract.contract_model import Violation, ViolationType

logger = get_logger(__name__)


class DiscriminatorValidator:
    """Validates data against discriminated union schemas."""

    def __init__(self, spec_dict: Dict[str, Any]):
        """
        Initialize discriminator validator.

        Args:
            spec_dict: Full OpenAPI spec dictionary for $ref resolution
        """
        self.spec_dict = spec_dict
        self.components = spec_dict.get("components", {})
        self.schemas = self.components.get("schemas", {})

    def validate(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any],
        endpoint_id: str,
        location: str = "response_body",
    ) -> List[Violation]:
        """
        Validate data against discriminated schema.

        Args:
            data: Response data to validate
            schema: Schema with discriminator
            endpoint_id: Endpoint identifier
            location: Location in request/response

        Returns:
            List of contract violations
        """
        discriminator = schema.get("discriminator")
        if not discriminator:
            return []

        violations = []

        # Extract discriminator configuration
        property_name = discriminator.get("propertyName")
        mapping = discriminator.get("mapping", {})

        if not property_name:
            logger.warning(f"Discriminator missing propertyName in {endpoint_id}")
            return []

        # Check if discriminator property exists in data
        discriminator_value = data.get(property_name)
        if discriminator_value is None:
            violations.append(
                Violation(
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=property_name,
                    violation_type=ViolationType.MISSING_FIELD,
                    expected=f"discriminator property '{property_name}'",
                    actual="missing",
                    message=f"Missing discriminator field: {property_name}",
                    severity="error",
                )
            )
            return violations

        # Resolve sub-schema from mapping
        sub_schema_ref = mapping.get(discriminator_value)
        if not sub_schema_ref:
            # Try to find schema by implicit naming (e.g., type: "HDL" -> HDLDataDestination)
            sub_schema_ref = self._find_implicit_schema(discriminator_value, schema)

        if not sub_schema_ref:
            violations.append(
                Violation(
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=property_name,
                    violation_type=ViolationType.INVALID_ENUM,
                    expected=f"one of {list(mapping.keys())}",
                    actual=discriminator_value,
                    message=f"Unknown discriminator value: {discriminator_value}",
                    severity="error",
                )
            )
            return violations

        # Resolve $ref and validate against sub-schema
        sub_schema = self._resolve_ref(sub_schema_ref)
        if sub_schema:
            # Import here to avoid circular dependency
            from api_contract_validator.schema.contract.rules_engine import RulesEngine

            rules_engine = RulesEngine()
            # Recursively validate against resolved schema
            sub_violations = rules_engine.validate_schema(
                data=data,
                schema=sub_schema,
                endpoint_id=endpoint_id,
                location=location,
                spec_dict=self.spec_dict,
            )
            violations.extend(sub_violations)

        return violations

    def _find_implicit_schema(
        self, discriminator_value: str, parent_schema: Dict[str, Any]
    ) -> Optional[str]:
        """
        Find schema by implicit naming when mapping is missing.

        Checks oneOf/anyOf in parent schema for matching schemas.
        """
        for key in ["oneOf", "anyOf"]:
            if key in parent_schema:
                for item in parent_schema[key]:
                    if "$ref" in item:
                        return item["$ref"]
        return None

    def _resolve_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        """
        Resolve OpenAPI $ref to actual schema.

        Args:
            ref: Reference string like "#/components/schemas/HDLDataDestination"

        Returns:
            Resolved schema dictionary or None
        """
        if not ref.startswith("#/"):
            logger.warning(f"External refs not supported: {ref}")
            return None

        # Parse ref path
        parts = ref[2:].split("/")  # Remove "#/" prefix

        # Navigate spec dict
        current = self.spec_dict
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    logger.warning(f"Could not resolve ref: {ref}")
                    return None
            else:
                return None

        return current
