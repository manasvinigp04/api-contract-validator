"""
Contract Rules Engine

Validates data against contract rules and detects violations.
"""

import re
from typing import Any, Dict, List, Optional

from api_contract_validator.config.logging import get_logger
from api_contract_validator.schema.contract.contract_model import (
    ContractRule,
    Violation,
    ViolationType,
)

logger = get_logger(__name__)


class RulesEngine:
    """
    Deterministic rules engine for contract validation.
    """

    def validate_against_rules(
        self,
        data: Dict[str, Any],
        rules: List[ContractRule],
        endpoint_id: str,
        location: str,
    ) -> List[Violation]:
        """
        Validate data against a list of contract rules.

        Args:
            data: Data to validate (dict)
            rules: List of contract rules
            endpoint_id: Endpoint identifier
            location: Location of data ("request_body", "response_body", "parameter")

        Returns:
            List of violations found
        """
        violations = []

        for rule in rules:
            rule_violations = self._validate_rule(data, rule, endpoint_id, location)
            violations.extend(rule_violations)

        return violations

    def _validate_rule(
        self,
        data: Dict[str, Any],
        rule: ContractRule,
        endpoint_id: str,
        location: str,
    ) -> List[Violation]:
        """Validate data against a single contract rule."""
        violations = []

        # Extract field value from data
        field_value = self._get_field_value(data, rule.field_path)

        # Check if field is missing
        if field_value is None:
            if rule.required:
                violations.append(
                    Violation(
                        violation_type=ViolationType.MISSING_FIELD,
                        endpoint_id=endpoint_id,
                        location=location,
                        field_path=rule.field_path,
                        expected="present",
                        actual="missing",
                        message=f"Required field '{rule.field_path}' is missing",
                        severity="error",
                    )
                )
            return violations

        # Check nullable
        if field_value is None and not rule.nullable:
            violations.append(
                Violation(
                    violation_type=ViolationType.CONSTRAINT_VIOLATION,
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=rule.field_path,
                    expected="non-null",
                    actual="null",
                    message=f"Field '{rule.field_path}' cannot be null",
                    severity="error",
                )
            )
            return violations

        # Validate each constraint rule
        for constraint in rule.constraint_rules:
            violation = self._validate_constraint(
                field_value, constraint, endpoint_id, location
            )
            if violation:
                violations.append(violation)

        return violations

    def _validate_constraint(
        self,
        value: Any,
        constraint: ConstraintRule,
        endpoint_id: str,
        location: str,
    ) -> Optional[Violation]:
        """Validate a single constraint."""
        rule_type = constraint.rule_type

        if rule_type == "type":
            return self._validate_type(value, constraint, endpoint_id, location)
        elif rule_type == "min_length":
            return self._validate_min_length(value, constraint, endpoint_id, location)
        elif rule_type == "max_length":
            return self._validate_max_length(value, constraint, endpoint_id, location)
        elif rule_type == "minimum":
            return self._validate_minimum(value, constraint, endpoint_id, location)
        elif rule_type == "maximum":
            return self._validate_maximum(value, constraint, endpoint_id, location)
        elif rule_type == "pattern":
            return self._validate_pattern(value, constraint, endpoint_id, location)
        elif rule_type == "enum":
            return self._validate_enum(value, constraint, endpoint_id, location)
        elif rule_type == "format":
            return self._validate_format(value, constraint, endpoint_id, location)

        return None

    def _validate_type(
        self, value: Any, constraint: ConstraintRule, endpoint_id: str, location: str
    ) -> Optional[Violation]:
        """Validate type constraint."""
        expected_type = constraint.expected_value
        actual_type = self._get_type_string(value)

        if not self._check_type_match(value, expected_type):
            return Violation(
                violation_type=ViolationType.TYPE_MISMATCH,
                endpoint_id=endpoint_id,
                location=location,
                field_path=constraint.field_path,
                expected=expected_type,
                actual=actual_type,
                message=f"Type mismatch: expected {expected_type}, got {actual_type}",
                severity="error",
            )

        return None

    def _validate_min_length(
        self, value: Any, constraint: ConstraintRule, endpoint_id: str, location: str
    ) -> Optional[Violation]:
        """Validate minimum length constraint."""
        if isinstance(value, (str, list)):
            if len(value) < constraint.expected_value:
                return Violation(
                    violation_type=ViolationType.CONSTRAINT_VIOLATION,
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=constraint.field_path,
                    expected=f"length >= {constraint.expected_value}",
                    actual=f"length = {len(value)}",
                    message=f"Length {len(value)} is less than minimum {constraint.expected_value}",
                    severity="error",
                )
        return None

    def _validate_max_length(
        self, value: Any, constraint: ConstraintRule, endpoint_id: str, location: str
    ) -> Optional[Violation]:
        """Validate maximum length constraint."""
        if isinstance(value, (str, list)):
            if len(value) > constraint.expected_value:
                return Violation(
                    violation_type=ViolationType.CONSTRAINT_VIOLATION,
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=constraint.field_path,
                    expected=f"length <= {constraint.expected_value}",
                    actual=f"length = {len(value)}",
                    message=f"Length {len(value)} exceeds maximum {constraint.expected_value}",
                    severity="error",
                )
        return None

    def _validate_minimum(
        self, value: Any, constraint: ConstraintRule, endpoint_id: str, location: str
    ) -> Optional[Violation]:
        """Validate minimum value constraint."""
        if isinstance(value, (int, float)):
            if value < constraint.expected_value:
                return Violation(
                    violation_type=ViolationType.RANGE_VIOLATION,
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=constraint.field_path,
                    expected=f">= {constraint.expected_value}",
                    actual=value,
                    message=f"Value {value} is less than minimum {constraint.expected_value}",
                    severity="error",
                )
        return None

    def _validate_maximum(
        self, value: Any, constraint: ConstraintRule, endpoint_id: str, location: str
    ) -> Optional[Violation]:
        """Validate maximum value constraint."""
        if isinstance(value, (int, float)):
            if value > constraint.expected_value:
                return Violation(
                    violation_type=ViolationType.RANGE_VIOLATION,
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=constraint.field_path,
                    expected=f"<= {constraint.expected_value}",
                    actual=value,
                    message=f"Value {value} exceeds maximum {constraint.expected_value}",
                    severity="error",
                )
        return None

    def _validate_pattern(
        self, value: Any, constraint: ConstraintRule, endpoint_id: str, location: str
    ) -> Optional[Violation]:
        """Validate regex pattern constraint."""
        if isinstance(value, str):
            if not re.match(constraint.expected_value, value):
                return Violation(
                    violation_type=ViolationType.PATTERN_MISMATCH,
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=constraint.field_path,
                    expected=f"pattern: {constraint.expected_value}",
                    actual=value,
                    message=f"Value '{value}' does not match pattern '{constraint.expected_value}'",
                    severity="error",
                )
        return None

    def _validate_enum(
        self, value: Any, constraint: ConstraintRule, endpoint_id: str, location: str
    ) -> Optional[Violation]:
        """Validate enum constraint."""
        if value not in constraint.expected_value:
            return Violation(
                violation_type=ViolationType.INVALID_ENUM,
                endpoint_id=endpoint_id,
                location=location,
                field_path=constraint.field_path,
                expected=constraint.expected_value,
                actual=value,
                message=f"Value '{value}' is not one of allowed values: {constraint.expected_value}",
                severity="error",
            )
        return None

    def _validate_format(
        self, value: Any, constraint: ConstraintRule, endpoint_id: str, location: str
    ) -> Optional[Violation]:
        """Validate format constraint (email, date-time, uuid, etc.)."""
        format_type = constraint.expected_value

        if format_type == "email" and isinstance(value, str):
            if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", value):
                return Violation(
                    violation_type=ViolationType.CONSTRAINT_VIOLATION,
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=constraint.field_path,
                    expected="valid email",
                    actual=value,
                    message=f"Invalid email format: '{value}'",
                    severity="error",
                )

        elif format_type == "uuid" and isinstance(value, str):
            uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
            if not re.match(uuid_pattern, value, re.IGNORECASE):
                return Violation(
                    violation_type=ViolationType.CONSTRAINT_VIOLATION,
                    endpoint_id=endpoint_id,
                    location=location,
                    field_path=constraint.field_path,
                    expected="valid UUID",
                    actual=value,
                    message=f"Invalid UUID format: '{value}'",
                    severity="error",
                )

        return None

    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Extract field value from data using dot notation path."""
        # Remove location prefix (e.g., "request.", "response.200.")
        path_parts = field_path.split(".")
        if path_parts[0] in ["request", "response", "parameter"]:
            path_parts = path_parts[1:]
        # Skip status code if present
        if path_parts and path_parts[0].isdigit():
            path_parts = path_parts[1:]

        current = data
        for part in path_parts:
            if part == "[]":
                # Array indicator - skip for now
                continue

            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            else:
                return None

        return current

    def _check_type_match(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_checks = {
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "array": lambda v: isinstance(v, list),
            "object": lambda v: isinstance(v, dict),
            "null": lambda v: v is None,
        }

        check_func = type_checks.get(expected_type)
        return check_func(value) if check_func else False

    def _get_type_string(self, value: Any) -> str:
        """Get type string for a value."""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        elif value is None:
            return "null"
        else:
            return type(value).__name__
