"""Dependency graph builder for API endpoints."""

import re
from typing import Dict, List, Set, Optional
from collections import defaultdict

from api_contract_validator.input.normalizer.models import UnifiedAPISpec, Endpoint, HTTPMethod


class DependencyGraphBuilder:
    """Builds dependency relationships between API endpoints."""

    def __init__(self, spec: UnifiedAPISpec):
        self.spec = spec
        self.graph = defaultdict(list)  # endpoint_id -> [dependent_endpoint_ids]
        self.resource_map = defaultdict(list)  # resource_type -> [endpoint_ids]

    def build_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph from API spec."""
        self._categorize_endpoints()
        self._detect_crud_chains()
        self._detect_path_dependencies()
        return dict(self.graph)

    def _categorize_endpoints(self):
        """Categorize endpoints by resource type."""
        for endpoint in self.spec.endpoints:
            resource = self._extract_resource(endpoint.path)
            self.resource_map[resource].append(endpoint.endpoint_id)

    def _extract_resource(self, path: str) -> str:
        """Extract resource name from path. /users/{id} -> users"""
        parts = [p for p in path.split('/') if p and not p.startswith('{')]
        return parts[0] if parts else "root"

    def _detect_crud_chains(self):
        """Detect CRUD operation chains (POST -> GET -> PATCH -> DELETE)."""
        for resource, endpoint_ids in self.resource_map.items():
            endpoints = {eid: next(e for e in self.spec.endpoints if e.endpoint_id == eid)
                        for eid in endpoint_ids}

            post_eps = [eid for eid, e in endpoints.items() if e.method == HTTPMethod.POST]
            get_eps = [eid for eid, e in endpoints.items() if e.method == HTTPMethod.GET and '{' in e.path]
            patch_eps = [eid for eid, e in endpoints.items() if e.method in [HTTPMethod.PATCH, HTTPMethod.PUT]]
            delete_eps = [eid for eid, e in endpoints.items() if e.method == HTTPMethod.DELETE]

            # POST -> GET -> PATCH -> DELETE chain
            for post_id in post_eps:
                for get_id in get_eps:
                    self.graph[post_id].append(get_id)
                for patch_id in patch_eps:
                    self.graph[post_id].append(patch_id)
                for delete_id in delete_eps:
                    self.graph[post_id].append(delete_id)

    def _detect_path_dependencies(self):
        """Detect dependencies based on path parameters."""
        for endpoint in self.spec.endpoints:
            if '{' in endpoint.path:
                parent_path = re.sub(r'/\{[^}]+\}.*', '', endpoint.path)
                for potential_parent in self.spec.endpoints:
                    if potential_parent.path == parent_path and potential_parent.method == HTTPMethod.POST:
                        self.graph[potential_parent.endpoint_id].append(endpoint.endpoint_id)

    def get_workflow_chains(self) -> List[List[str]]:
        """Get ordered workflow chains."""
        chains = []
        visited = set()

        for start_id in self.graph.keys():
            if start_id not in visited:
                chain = self._build_chain(start_id, visited)
                if len(chain) > 1:
                    chains.append(chain)

        return chains

    def _build_chain(self, start_id: str, visited: Set[str]) -> List[str]:
        """Build chain starting from endpoint."""
        chain = [start_id]
        visited.add(start_id)

        for next_id in self.graph.get(start_id, []):
            if next_id not in visited:
                chain.append(next_id)
                visited.add(next_id)

        return chain
