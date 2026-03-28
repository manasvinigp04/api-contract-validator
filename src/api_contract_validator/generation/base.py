"""
Test Generation Base

Base classes and models for test case generation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from api_contract_validator.input.normalizer.models import Endpoint, HTTPMethod


class TestCaseType(str, Enum):
    """Type of test case."""

    VALID = "valid"
    INVALID = "invalid"
    BOUNDARY = "boundary"
    EDGE = "edge"


class TestCase(BaseModel):
    """Represents a single API test case."""

    test_id: str
    endpoint: Endpoint
    test_type: TestCaseType
    description: str
    method: HTTPMethod
    path: str
    path_params: Dict[str, Any] = Field(default_factory=dict)
    query_params: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    request_body: Optional[Dict[str, Any]] = None
    expected_status: int
    expected_response_schema: Optional[Dict[str, Any]] = None
    should_pass: bool = True  # True for valid tests, False for invalid
    priority: float = 1.0  # Higher = more important

    class Config:
        frozen = False

    @property
    def full_path(self) -> str:
        """Get the full path with path parameters substituted."""
        path = self.path
        for param_name, param_value in self.path_params.items():
            path = path.replace(f"{{{param_name}}}", str(param_value))
        return path


class TestSuite(BaseModel):
    """Collection of test cases for an endpoint or API."""

    name: str
    description: Optional[str] = None
    test_cases: List[TestCase] = Field(default_factory=list)

    class Config:
        frozen = False

    def add_test(self, test_case: TestCase) -> None:
        """Add a test case to the suite."""
        self.test_cases.append(test_case)

    def get_valid_tests(self) -> List[TestCase]:
        """Get all valid test cases."""
        return [tc for tc in self.test_cases if tc.test_type == TestCaseType.VALID]

    def get_invalid_tests(self) -> List[TestCase]:
        """Get all invalid test cases."""
        return [tc for tc in self.test_cases if tc.test_type == TestCaseType.INVALID]

    def get_boundary_tests(self) -> List[TestCase]:
        """Get all boundary test cases."""
        return [tc for tc in self.test_cases if tc.test_type == TestCaseType.BOUNDARY]

    def get_high_priority_tests(self, threshold: float = 1.5) -> List[TestCase]:
        """Get high-priority test cases."""
        return [tc for tc in self.test_cases if tc.priority >= threshold]


class BaseTestGenerator:
    """Base class for test generators."""

    def __init__(self):
        self.test_counter = 0

    def generate_test_id(self, prefix: str) -> str:
        """Generate a unique test ID."""
        self.test_counter += 1
        return f"{prefix}_{self.test_counter}"

    def generate_tests(self, endpoint: Endpoint) -> List[TestCase]:
        """
        Generate test cases for an endpoint.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement generate_tests")
