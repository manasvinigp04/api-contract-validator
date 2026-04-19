"""
OneOf Validator

Validates that data matches EXACTLY ONE of the provided schemas.

Example:
    oneOf:
      - $ref: "#/components/schemas/HDLDataDestination"
      - $ref: "#/components/schemas/S3DataDestination"
"""

from typing import Any, Dict, List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.schema.contract.contract_model import Violation, ViolationType

logger = get_logger(__name__)


class OneOfValidator:
    """Validates data against oneOf schema composition."""

    def __init__(self, spec_dict: Dict[str, Any]):
        """
        Initialize oneOf validator.

        Args:
            spec_dict: Full OpenAPI spec dictionary
        """
        self.spec_dict = spec_dict

    def validate(
        self,
        data: Dict[str, Any],
        oneof_schemas: List[Dict[str, Any]],
        endpoint_id: str,
        location: str = "response_body",
    ) -> List[Violation]:
        """
        Validate data matches exactly one schema.

        Args:
            data: Data to validate
            oneof_schemas: List of schemas (one must match)
            endpoint_id: Endpoint identifier
            location: Location in request/response

        Returns:
            List of violations
        """
        from api_contract_validator.schema.contract.rules_engine import RulesEngine

        violations = []
        rules_engine = RulesEngine()

        # Try to validate against each schema
        matched_indices = []
        all_schema_violations = []

        for idx, schema in enumerate(oneof_schemas):
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
                # This schema matches
                matched_indices.append(idx)
            else:
                all_schema_violations.append((idx, schema_violations))

        # Evaluate results
        if len(matched_indices) == 1:
            # Success: exactly one match
            return []
        elif len(matched_indices) == 0:
            # No schemas matched
            violations.append(
                Violation(
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path="",
                    violation_type=ViolationType.CONSTRAINT_VIOLATION,
                    expected="data to match one of the schemas",
                    actual="no schemas matched",
                    message=f"oneOf validation failed: data doesn't match any of {len(oneof_schemas)} schemas",
                    severity="error",
                )
            )
        else:
            # Multiple schemas matched
            violations.append(
                Violation(
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path="",
                    violation_type=ViolationType.CONSTRAINT_VIOLATION,
                    expected="data to match exactly one schema",
                    actual=f"matched {len(matched_indices)} schemas",
                    message=f"oneOf validation failed: data matches {len(matched_indices)} schemas (indices: {matched_indices}), expected exactly 1",
                    severity="error",
                )
            )

        return violations

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
