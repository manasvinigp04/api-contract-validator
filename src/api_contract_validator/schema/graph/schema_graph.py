"""
Schema Graph Builder

Builds a graph representation of API schemas showing dependencies and relationships.
"""

from typing import Dict, List, Set

from api_contract_validator.config.logging import get_logger
from api_contract_validator.input.normalizer.models import (
    Endpoint,
    FieldDefinition,
    UnifiedAPISpec,
)

logger = get_logger(__name__)


class SchemaNode:
    """Represents a node in the schema graph."""

    def __init__(self, name: str, schema: FieldDefinition):
        self.name = name
        self.schema = schema
        self.dependencies: Set[str] = set()
        self.dependents: Set[str] = set()

    def add_dependency(self, dependency: str) -> None:
        """Add a schema that this node depends on."""
        self.dependencies.add(dependency)

    def add_dependent(self, dependent: str) -> None:
        """Add a schema that depends on this node."""
        self.dependents.add(dependent)


class SchemaGraph:
    """
    Graph representation of API schemas showing dependencies.
    """

    def __init__(self, spec: UnifiedAPISpec):
        self.spec = spec
        self.nodes: Dict[str, SchemaNode] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """Build the schema dependency graph."""
        # Create nodes for all schemas
        for schema_name, schema_def in self.spec.schemas.items():
            self.nodes[schema_name] = SchemaNode(schema_name, schema_def)

        # Build dependency relationships
        for schema_name, node in self.nodes.items():
            self._extract_dependencies(schema_name, node.schema)

    def _extract_dependencies(self, parent_name: str, field_def: FieldDefinition) -> None:
        """Extract dependencies from a field definition."""
        if field_def.properties:
            for prop_name, prop_def in field_def.properties.items():
                # Check if this property references another schema
                if prop_def.type.value == "object" and prop_def.name in self.nodes:
                    self._add_dependency(parent_name, prop_def.name)

                # Recurse into nested properties
                self._extract_dependencies(parent_name, prop_def)

        if field_def.items:
            self._extract_dependencies(parent_name, field_def.items)

    def _add_dependency(self, from_schema: str, to_schema: str) -> None:
        """Add a dependency relationship between schemas."""
        if from_schema in self.nodes and to_schema in self.nodes:
            self.nodes[from_schema].add_dependency(to_schema)
            self.nodes[to_schema].add_dependent(from_schema)

    def get_dependencies(self, schema_name: str) -> Set[str]:
        """Get all schemas that the given schema depends on."""
        if schema_name not in self.nodes:
            return set()
        return self.nodes[schema_name].dependencies.copy()

    def get_dependents(self, schema_name: str) -> Set[str]:
        """Get all schemas that depend on the given schema."""
        if schema_name not in self.nodes:
            return set()
        return self.nodes[schema_name].dependents.copy()

    def get_transitive_dependencies(self, schema_name: str) -> Set[str]:
        """Get all transitive dependencies of a schema."""
        if schema_name not in self.nodes:
            return set()

        visited = set()
        to_visit = [schema_name]

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue

            visited.add(current)
            if current in self.nodes:
                for dep in self.nodes[current].dependencies:
                    if dep not in visited:
                        to_visit.append(dep)

        visited.discard(schema_name)
        return visited

    def get_endpoint_complexity(self, endpoint: Endpoint) -> int:
        """
        Calculate complexity score for an endpoint based on schema dependencies.
        """
        complexity = 0

        # Count parameters
        complexity += len(endpoint.parameters)

        # Count request body fields
        if endpoint.request_body:
            complexity += len(endpoint.request_body.schema)
            # Add complexity for nested schemas
            for field in endpoint.request_body.schema.values():
                if field.properties:
                    complexity += len(field.properties)

        # Count response fields
        for response in endpoint.responses:
            complexity += len(response.schema)
            for field in response.schema.values():
                if field.properties:
                    complexity += len(field.properties)

        return complexity

    def get_critical_schemas(self) -> List[str]:
        """
        Get schemas that are used by many endpoints (high fan-in).
        """
        usage_count = {}

        for endpoint in self.spec.endpoints:
            schemas_used = set()

            # Check request body
            if endpoint.request_body:
                for field in endpoint.request_body.schema.values():
                    if field.name in self.nodes:
                        schemas_used.add(field.name)

            # Check responses
            for response in endpoint.responses:
                for field in response.schema.values():
                    if field.name in self.nodes:
                        schemas_used.add(field.name)

            for schema_name in schemas_used:
                usage_count[schema_name] = usage_count.get(schema_name, 0) + 1

        # Return schemas used by more than 2 endpoints
        return [name for name, count in usage_count.items() if count > 2]


def build_schema_graph(spec: UnifiedAPISpec) -> SchemaGraph:
    """
    Build a schema dependency graph from a unified specification.

    Args:
        spec: UnifiedAPISpec instance

    Returns:
        SchemaGraph instance
    """
    logger.info("Building schema dependency graph")
    graph = SchemaGraph(spec)
    logger.info(f"Built graph with {len(graph.nodes)} schema nodes")
    return graph
