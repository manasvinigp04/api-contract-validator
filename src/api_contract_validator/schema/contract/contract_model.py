"""
Contract Model

Executable contract models for API validation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from api_contract_validator.input.normalizer.models import (
    Endpoint,
    FieldConstraint,
    FieldDefinition,
    FieldType,
    UnifiedAPISpec,
)


class ViolationType(str, Enum):
    """Types of contract violations."""

    MISSING_FIELD = "missing_field"
    TYPE_MISMATCH = "type_mismatch"
    CONSTRAINT_VIOLATION = "constraint_violation"
    UNEXPECTED_FIELD = "unexpected_field"
    INVALID_ENUM = "invalid_enum"
    PATTERN_MISMATCH = "pattern_mismatch"
    RANGE_VIOLATION = "range_violation"


class ConstraintRule(BaseModel):
    """Represents a single validation constraint rule."""

    rule_type: str
    field_path: str
    expected_value: Any
    description: str

    class Config:
        frozen = False


class ContractRule(BaseModel):
    """
    Represents an executable validation rule for a contract.
    """

    rule_id: str
    endpoint_id: str
    location: str  # "request_body", "response_body", "parameter"
    field_path: str
    constraint_rules: List[ConstraintRule] = Field(default_factory=list)
    required: bool = False
    nullable: bool = False

    class Config:
        frozen = False


class EndpointContract(BaseModel):
    """
    Executable contract for a single endpoint.
    """

    endpoint: Endpoint
    request_rules: List[ContractRule] = Field(default_factory=list)
    response_rules: Dict[int, List[ContractRule]] = Field(default_factory=dict)
    parameter_rules: List[ContractRule] = Field(default_factory=list)

    class Config:
        frozen = False

    @property
    def endpoint_id(self) -> str:
        """Get the endpoint identifier."""
        return self.endpoint.endpoint_id

    def get_all_rules(self) -> List[ContractRule]:
        """Get all rules for this endpoint."""
        rules = self.request_rules + self.parameter_rules
        for response_rules in self.response_rules.values():
            rules.extend(response_rules)
        return rules


class APIContract(BaseModel):
    """
    Complete executable contract for an API specification.
    """

    spec: UnifiedAPISpec
    endpoint_contracts: Dict[str, EndpointContract] = Field(default_factory=dict)

    class Config:
        frozen = False

    def get_contract(self, endpoint_id: str) -> Optional[EndpointContract]:
        """Get contract for a specific endpoint."""
        return self.endpoint_contracts.get(endpoint_id)

    def get_all_contracts(self) -> List[EndpointContract]:
        """Get all endpoint contracts."""
        return list(self.endpoint_contracts.values())

    def get_critical_contracts(self) -> List[EndpointContract]:
        """Get contracts for critical endpoints (POST, PUT, DELETE)."""
        return [
            contract
            for contract in self.endpoint_contracts.values()
            if contract.endpoint.method.value in ["POST", "PUT", "DELETE", "PATCH"]
        ]


class Violation(BaseModel):
    """Represents a contract violation."""

    violation_type: ViolationType
    endpoint_id: str
    location: str
    field_path: str
    expected: Any
    actual: Any
    message: str
    severity: str = "error"  # "error", "warning", "info"

    class Config:
        frozen = False
