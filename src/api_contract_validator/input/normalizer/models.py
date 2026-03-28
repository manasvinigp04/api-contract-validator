"""
Unified Intermediate Representation Models

These Pydantic models provide a normalized representation for API specifications
that can be derived from both OpenAPI specs and PRD documents.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class HTTPMethod(str, Enum):
    """HTTP methods supported by the API."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class FieldType(str, Enum):
    """Field data types in the schema."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


class SourceType(str, Enum):
    """Type of specification source."""

    OPENAPI = "openapi"
    PRD = "prd"
    MANUAL = "manual"


class FieldConstraint(BaseModel):
    """
    Represents validation constraints on a field.
    """

    required: bool = False
    nullable: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    enum: Optional[List[Any]] = None
    format: Optional[str] = None  # e.g., "email", "date-time", "uuid"
    default: Optional[Any] = None

    class Config:
        frozen = False


class FieldDefinition(BaseModel):
    """
    Represents a field in a schema (request/response body or parameter).
    """

    name: str
    type: FieldType
    description: Optional[str] = None
    constraints: FieldConstraint = Field(default_factory=FieldConstraint)
    items: Optional["FieldDefinition"] = None  # For array types
    properties: Optional[Dict[str, "FieldDefinition"]] = None  # For object types
    confidence: float = 1.0  # Confidence score (1.0 = certain, <1.0 = inferred from PRD)

    class Config:
        frozen = False


class Parameter(BaseModel):
    """
    Represents an API parameter (path, query, header, or cookie).
    """

    name: str
    location: str  # "path", "query", "header", "cookie"
    type: FieldType
    description: Optional[str] = None
    constraints: FieldConstraint = Field(default_factory=FieldConstraint)
    confidence: float = 1.0

    class Config:
        frozen = False


class RequestBody(BaseModel):
    """
    Represents a request body schema.
    """

    content_type: str = "application/json"
    schema: Dict[str, FieldDefinition] = Field(default_factory=dict)
    required: bool = False
    description: Optional[str] = None
    confidence: float = 1.0

    class Config:
        frozen = False


class ResponseBody(BaseModel):
    """
    Represents a response body schema.
    """

    status_code: int
    content_type: str = "application/json"
    schema: Dict[str, FieldDefinition] = Field(default_factory=dict)
    description: Optional[str] = None
    confidence: float = 1.0

    class Config:
        frozen = False


class Endpoint(BaseModel):
    """
    Represents an API endpoint with its methods and schemas.
    """

    path: str
    method: HTTPMethod
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    parameters: List[Parameter] = Field(default_factory=list)
    request_body: Optional[RequestBody] = None
    responses: List[ResponseBody] = Field(default_factory=list)
    security: Optional[List[str]] = None
    deprecated: bool = False
    confidence: float = 1.0  # For PRD-derived endpoints

    class Config:
        frozen = False

    @property
    def endpoint_id(self) -> str:
        """Generate a unique identifier for this endpoint."""
        return f"{self.method.value}:{self.path}"


class SecurityScheme(BaseModel):
    """
    Represents an API security scheme.
    """

    name: str
    type: str  # "apiKey", "http", "oauth2", "openIdConnect"
    scheme: Optional[str] = None  # For http type: "basic", "bearer"
    bearer_format: Optional[str] = None
    in_location: Optional[str] = None  # For apiKey: "query", "header", "cookie"
    description: Optional[str] = None

    class Config:
        frozen = False


class APIMetadata(BaseModel):
    """
    Represents API metadata (title, version, etc.).
    """

    title: str
    version: str
    description: Optional[str] = None
    base_url: Optional[str] = None
    contact: Optional[Dict[str, str]] = None
    license: Optional[Dict[str, str]] = None
    terms_of_service: Optional[str] = None

    class Config:
        frozen = False


class UnifiedAPISpec(BaseModel):
    """
    Unified intermediate representation of an API specification.

    This model can represent both OpenAPI specs and PRD-derived specifications
    in a normalized format suitable for contract validation and test generation.
    """

    source_type: SourceType
    source_path: Optional[str] = None
    metadata: APIMetadata
    endpoints: List[Endpoint] = Field(default_factory=list)
    security_schemes: List[SecurityScheme] = Field(default_factory=list)
    global_parameters: List[Parameter] = Field(default_factory=list)
    schemas: Dict[str, FieldDefinition] = Field(
        default_factory=dict
    )  # Reusable schema definitions
    confidence: float = 1.0  # Overall confidence (lower for PRD-derived specs)

    class Config:
        frozen = False

    def get_endpoint(self, path: str, method: HTTPMethod) -> Optional[Endpoint]:
        """Get a specific endpoint by path and method."""
        for endpoint in self.endpoints:
            if endpoint.path == path and endpoint.method == method:
                return endpoint
        return None

    def get_endpoints_by_tag(self, tag: str) -> List[Endpoint]:
        """Get all endpoints with a specific tag."""
        return [ep for ep in self.endpoints if tag in ep.tags]

    def get_critical_endpoints(self) -> List[Endpoint]:
        """
        Get endpoints that are considered critical.
        Critical endpoints typically include POST, PUT, DELETE methods.
        """
        critical_methods = {HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.DELETE}
        return [ep for ep in self.endpoints if ep.method in critical_methods]


# Update forward references
FieldDefinition.model_rebuild()
