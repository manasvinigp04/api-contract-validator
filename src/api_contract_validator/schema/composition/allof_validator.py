"""
AllOf Validator

Validates that data matches ALL of the provided schemas (schema merging).

Example:
    allOf:
      - $ref: "#/components/schemas/BaseDataDestination"
      - type: object
        properties:
          type: { type: string, enum: [HDL] }
"""

from typing import Any, Dict, List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.schema.contract.contract_model import Violation

logger = get_logger(__name__)


class AllOfValidator:
    """Validates data against allOf schema composition."""

    def __init__(self, spec_dict: Dict[str, Any]):
        """
        Initialize allOf validator.

        Args:
            spec_dict: Full OpenAPI spec dictionary
        """
        self.spec_dict = spec_dict

    def validate(
        self,
        data: Dict[str, Any],
        allof_schemas: List[Dict[str, Any]],
        endpoint_id: str,
        location: str = "response_body",
    ) -> List[Violation]:
        """
        Validate data matches all schemas.

        Strategy: Merge all schemas into one and validate once.

        Args:
            data: Data to validate
            allof_schemas: List of schemas (all must match)
            endpoint_id: Endpoint identifier
            location: Location in request/response

        Returns:
            List of violations
        """
        from api_contract_validator.schema.contract.rules_engine import RulesEngine

        # Resolve all $refs first
        resolved_schemas = []
        for schema in allof_schemas:
            if "$ref" in schema:
                resolved = self._resolve_ref(schema["$ref"])
                if resolved:
                    resolved_schemas.append(resolved)
            else:
                resolved_schemas.append(schema)

        # Merge all schemas
        merged_schema = self._merge_schemas(resolved_schemas)

        # Validate against merged schema
        rules_engine = RulesEngine()
        return rules_engine.validate_schema(
            data=data,
            schema=merged_schema,
            endpoint_id=endpoint_id,
            location=location,
            spec_dict=self.spec_dict,
        )

    def _merge_schemas(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple schemas into one.

        Merges properties, required fields, and constraints.
        """
        merged = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for schema in schemas:
            # Merge properties
            if "properties" in schema:
                merged["properties"].update(schema["properties"])

            # Merge required fields
            if "required" in schema:
                for field in schema["required"]:
                    if field not in merged["required"]:
                        merged["required"].append(field)

            # Merge other constraints
            for key in ["additionalProperties", "minProperties", "maxProperties"]:
                if key in schema:
                    # Take most restrictive constraint
                    if key == "additionalProperties":
                        # false is more restrictive than true
                        if schema[key] is False:
                            merged[key] = False
                    elif key == "minProperties":
                        merged[key] = max(merged.get(key, 0), schema[key])
                    elif key == "maxProperties":
                        if key not in merged:
                            merged[key] = schema[key]
                        else:
                            merged[key] = min(merged[key], schema[key])

        return merged

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
