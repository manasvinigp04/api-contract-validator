"""
Reference Resolver

Resolves $ref references in OpenAPI specifications and builds schema graphs.
"""

from typing import Any, Dict, Optional, Set

from api_contract_validator.config.logging import get_logger

logger = get_logger(__name__)


class ReferenceResolver:
    """
    Resolves JSON references ($ref) in OpenAPI specifications.
    """

    def __init__(self, spec_dict: Dict[str, Any]):
        self.spec_dict = spec_dict
        self.resolved_cache: Dict[str, Any] = {}
        self.resolving_stack: Set[str] = set()

    def resolve(self, ref: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a $ref reference.

        Args:
            ref: Reference string (e.g., "#/components/schemas/User")

        Returns:
            Resolved schema dictionary or None if not found
        """
        if ref in self.resolved_cache:
            return self.resolved_cache[ref]

        if ref in self.resolving_stack:
            logger.warning(f"Circular reference detected: {ref}")
            return None

        self.resolving_stack.add(ref)

        try:
            resolved = self._resolve_pointer(ref)
            if resolved:
                # Recursively resolve nested references
                resolved = self._resolve_nested_refs(resolved)
                self.resolved_cache[ref] = resolved
            return resolved
        finally:
            self.resolving_stack.discard(ref)

    def _resolve_pointer(self, ref: str) -> Optional[Dict[str, Any]]:
        """Resolve a JSON pointer reference."""
        if not ref.startswith("#/"):
            logger.warning(f"External references not supported: {ref}")
            return None

        # Remove the leading "#/" and split by "/"
        parts = ref[2:].split("/")

        current = self.spec_dict
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    logger.warning(f"Reference not found: {ref}")
                    return None
            else:
                return None

        return current if isinstance(current, dict) else None

    def _resolve_nested_refs(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve nested $ref references."""
        if not isinstance(schema, dict):
            return schema

        resolved = {}
        for key, value in schema.items():
            if key == "$ref" and isinstance(value, str):
                # Resolve this reference
                ref_resolved = self.resolve(value)
                if ref_resolved:
                    resolved.update(ref_resolved)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_nested_refs(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_nested_refs(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved

    def resolve_all_refs(self) -> Dict[str, Any]:
        """
        Resolve all references in the specification.

        Returns:
            Specification with all $ref references resolved
        """
        return self._resolve_nested_refs(self.spec_dict)
