"""
Custom Exception Classes

Defines custom exceptions for the API Contract Validator.
"""


class ACVException(Exception):
    """Base exception for all API Contract Validator errors."""

    pass


class ConfigurationError(ACVException):
    """Raised when there's a configuration error."""

    pass


class SpecificationError(ACVException):
    """Raised when there's an error parsing or validating a specification."""

    pass


class OpenAPIError(SpecificationError):
    """Raised when there's an error with an OpenAPI specification."""

    pass


class PRDParsingError(SpecificationError):
    """Raised when there's an error parsing a PRD document."""

    pass


class ContractViolation(ACVException):
    """Raised when a contract violation is detected."""

    def __init__(self, endpoint: str, violation_type: str, message: str):
        self.endpoint = endpoint
        self.violation_type = violation_type
        super().__init__(f"Contract violation in {endpoint}: {message}")


class ValidationError(ACVException):
    """Raised when validation fails."""

    pass


class TestGenerationError(ACVException):
    """Raised when test generation fails."""

    pass


class ExecutionError(ACVException):
    """Raised when test execution fails."""

    pass


class DriftDetectionError(ACVException):
    """Raised when drift detection fails."""

    pass


class AnalysisError(ACVException):
    """Raised when AI analysis fails."""

    pass


class ReportingError(ACVException):
    """Raised when report generation fails."""

    pass


class StorageError(ACVException):
    """Raised when storage operations fail."""

    pass
