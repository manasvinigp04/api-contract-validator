"""
AnyOf Validator

Validates that data matches AT LEAST ONE of the provided schemas.

Example:
    anyOf:
      - type: object
        properties:
          email: { type: string, format: email }
      - type: object
        properties:
          phone: { type: string, pattern: "^\\+[0-9]+" }
"""

from typing import Any, Dict, List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.schema.contract.contract_model import Violation, ViolationType

logger = get_logger(__name__)


class AnyOfValidator:
    """Validates data against anyOf schema composition."""

    def __init__(self, spec_dict: Dict[str, Any]):
        """
        Initialize anyOf validator.

        Args:
            spec_dict: Full OpenAPI spec dictionary
        """
        self.spec_dict = spec_dict

    def validate(
        self,
        data: Dict[str, Any],
        anyof_schemas: List[Dict[str, Any]],
        endpoint_id: str,
        location: str = "response_body",
    ) -> List[Violation]:
        """
        Validate data matches at least one schema.

        Args:
            data: Data to validate
            anyof_schemas: List of schemas (at least one must match)
            endpoint_id: Endpoint identifier
            location: Location in request/response

        Returns:
            List of violations (empty if at least one schema matches)
        """
        from api_contract_validator.schema.contract.rules_engine import RulesEngine

        rules_engine = RulesEngine()

        # Try to validate against each schema
        for idx, schema in enumerate(anyof_schemas):
            # Resolve $ref if present
            if "$ref" in schema:
                schema = self._resolve_ref(schema["$ref"])
                if not schema:
                    continue

            # Validate against this schema
            schema_violations = rules_engine.validate_schema(
                data=data,
                schema=schema,
                endpoint_id=endpoint_id,
                location=location,
                spec_dict=self.spec_dict,
            )

            if not schema_violations:
                # At least one schema matches - success!
                return []

        # No schemas matched
        return [
            Violation(
                endpoint_id=endpoint_id,
                location=location,
                field_path="",
                violation_type=ViolationType.CONSTRAINT_VIOLATION,
                expected="data to match at least one schema",
                actual="no schemas matched",
                message=f"anyOf validation failed: data doesn't match any of {len(anyof_schemas)} schemas",
                severity="error",
            )
        ]

    def _resolve_ref(self, ref: str) -> Dict[str, Any]:
        """Resolve $ref to schema."""
        if not ref.startswith("#/"):
            return {}

        parts = ref[2:].split("/")
        current = self.spec_dict
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return {}
            else:
                return {}

        return current if isinstance(current, dict) else {}
