"""
API Context Ranker

Uses PageRank-inspired algorithm to prioritize API endpoints and drift issues
for cost-efficient Claude API context sharing.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import hashlib
import json

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    # Fallback to simple ranking

from api_contract_validator.config.logging import get_logger

logger = get_logger("api_contract_validator.context_ranker")


@dataclass
class ContextChunk:
    """Represents a prioritized context chunk for Claude API."""

    endpoint_id: str
    score: float
    issues: List[any]
    dependencies: List[str]
    token_estimate: int
    rank: int

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'endpoint_id': self.endpoint_id,
            'score': self.score,
            'issue_count': len(self.issues),
            'dependencies': self.dependencies,
            'token_estimate': self.token_estimate,
            'rank': self.rank,
        }


class APIContextRanker:
    """
    Ranks API endpoints and drift issues using PageRank-inspired algorithm.

    Considers:
    - Endpoint dependencies (via schema references)
    - Issue severity weights
    - Endpoint complexity (params, body, response fields)
    - Historical drift patterns (if available)
    """

    # Severity weights for scoring
    SEVERITY_WEIGHTS = {
        'critical': 10.0,
        'high': 5.0,
        'medium': 2.0,
        'low': 1.0,
    }

    # Token estimation constants
    TOKENS_PER_ISSUE = 150  # Average tokens per issue description
    TOKENS_PER_DEPENDENCY = 50  # Tokens for dependency context

    def __init__(self, use_networkx: bool = True):
        """
        Initialize context ranker.

        Args:
            use_networkx: Use NetworkX for PageRank (if available)
        """
        self.use_networkx = use_networkx and HAS_NETWORKX
        if not self.use_networkx and use_networkx:
            logger.warning("NetworkX not available, using simple ranking fallback")

    def rank_contexts(
        self,
        endpoints: List[any],
        drift_issues: Dict[str, List[any]],
        max_tokens: int = 3000,
        max_contexts: int = 10
    ) -> List[ContextChunk]:
        """
        Rank and select most relevant context chunks for Claude API.

        Args:
            endpoints: List of API endpoints from contract model
            drift_issues: Dict mapping endpoint_id to list of issues
            max_tokens: Maximum token budget for contexts
            max_contexts: Maximum number of contexts to return

        Returns:
            Prioritized list of context chunks that fit within token budget
        """
        logger.info(f"Ranking contexts for {len(endpoints)} endpoints, {sum(len(issues) for issues in drift_issues.values())} total issues")

        # Build dependency graph
        graph = self._build_dependency_graph(endpoints, drift_issues)

        # Calculate scores
        if self.use_networkx:
            scores = self._pagerank_scores(graph, drift_issues)
        else:
            scores = self._simple_scores(graph, drift_issues)

        # Build context chunks
        contexts = self._build_context_chunks(
            endpoints=endpoints,
            drift_issues=drift_issues,
            scores=scores,
            graph=graph
        )

        # Sort by score and select top contexts within budget
        contexts.sort(key=lambda c: c.score, reverse=True)

        selected = []
        total_tokens = 0

        for i, context in enumerate(contexts):
            if i >= max_contexts:
                break
            if total_tokens + context.token_estimate > max_tokens:
                break

            context.rank = i + 1
            selected.append(context)
            total_tokens += context.token_estimate

        logger.info(f"Selected {len(selected)} contexts ({total_tokens} tokens)")
        return selected

    def _build_dependency_graph(
        self,
        endpoints: List[any],
        drift_issues: Dict[str, List[any]]
    ) -> Dict[str, Dict]:
        """
        Build dependency graph of endpoints.

        Graph structure:
        {
            'endpoint_id': {
                'method': 'POST',
                'path': '/users',
                'complexity': 10,
                'issue_count': 5,
                'issue_severity': 25.0,
                'dependencies': ['GET /users', 'POST /auth']
            }
        }
        """
        graph = {}

        for endpoint in endpoints:
            endpoint_id = endpoint.endpoint_id

            # Calculate endpoint complexity
            complexity = self._calculate_complexity(endpoint)

            # Get issue metrics
            issues = drift_issues.get(endpoint_id, [])
            issue_count = len(issues)
            issue_severity = sum(
                self.SEVERITY_WEIGHTS.get(getattr(issue, 'severity', 'medium'), 1.0)
                for issue in issues
            )

            # Extract dependencies from schema references
            dependencies = self._extract_dependencies(endpoint)

            graph[endpoint_id] = {
                'method': endpoint.method,
                'path': endpoint.path,
                'complexity': complexity,
                'issue_count': issue_count,
                'issue_severity': issue_severity,
                'dependencies': dependencies,
            }

        return graph

    def _calculate_complexity(self, endpoint: any) -> int:
        """
        Calculate endpoint complexity score.

        Factors:
        - Number of path parameters
        - Request body fields (if any)
        - Response body fields
        - Query parameters
        """
        complexity = 0

        # Path parameters
        complexity += endpoint.path.count('{')

        # Request body complexity
        if hasattr(endpoint, 'request_body') and endpoint.request_body:
            complexity += self._count_schema_fields(endpoint.request_body)

        # Response complexity
        if hasattr(endpoint, 'responses') and endpoint.responses:
            for response in endpoint.responses.values():
                if hasattr(response, 'schema'):
                    complexity += self._count_schema_fields(response.schema)

        # Query parameters
        if hasattr(endpoint, 'parameters'):
            complexity += len([p for p in endpoint.parameters if p.location == 'query'])

        return max(1, complexity)  # At least 1

    def _count_schema_fields(self, schema: any) -> int:
        """Count total fields in schema (recursive for nested objects)."""
        if not schema or not hasattr(schema, 'properties'):
            return 0

        count = len(schema.properties)

        # Add nested fields
        for prop in schema.properties.values():
            if hasattr(prop, 'properties'):
                count += self._count_schema_fields(prop)

        return count

    def _extract_dependencies(self, endpoint: any) -> List[str]:
        """
        Extract endpoint dependencies from schema references.

        For example, if POST /users references User schema,
        and GET /users also uses User schema, they're related.
        """
        dependencies = []

        # This is a simplified version - in production you'd:
        # 1. Track schema usage across endpoints
        # 2. Identify shared $ref patterns
        # 3. Build dependency links based on data flow

        # For now, use simple heuristics:
        # - Same resource path = related
        # - Write operations depend on read operations

        path_base = endpoint.path.split('{')[0].rstrip('/')

        if endpoint.method in ['POST', 'PUT', 'PATCH']:
            # Write ops might depend on GET
            dependencies.append(f"GET {path_base}")

        if endpoint.method == 'DELETE':
            # Delete might depend on GET and PUT
            dependencies.extend([f"GET {path_base}", f"PUT {path_base}"])

        return dependencies

    def _pagerank_scores(
        self,
        graph: Dict[str, Dict],
        drift_issues: Dict[str, List[any]]
    ) -> Dict[str, float]:
        """Calculate PageRank scores using NetworkX."""
        if not HAS_NETWORKX:
            return self._simple_scores(graph, drift_issues)

        # Build NetworkX directed graph
        G = nx.DiGraph()

        # Add nodes with attributes
        for endpoint_id, data in graph.items():
            G.add_node(
                endpoint_id,
                complexity=data['complexity'],
                issue_count=data['issue_count'],
                issue_severity=data['issue_severity'],
            )

        # Add edges (dependencies)
        for endpoint_id, data in graph.items():
            for dep in data['dependencies']:
                if dep in graph:  # Only add if dependency exists
                    G.add_edge(endpoint_id, dep)

        # Create personalization vector (endpoints with more issues = higher importance)
        personalization = self._create_personalization(graph, drift_issues)

        # Calculate PageRank
        try:
            scores = nx.pagerank(
                G,
                personalization=personalization,
                weight=None,
                alpha=0.85,  # Standard damping factor
                max_iter=100
            )
        except nx.PowerIterationFailedConvergence:
            logger.warning("PageRank failed to converge, using simple scores")
            return self._simple_scores(graph, drift_issues)

        # Boost scores by issue severity
        for endpoint_id in scores:
            issue_severity = graph[endpoint_id]['issue_severity']
            scores[endpoint_id] *= (1.0 + issue_severity / 10.0)

        return scores

    def _simple_scores(
        self,
        graph: Dict[str, Dict],
        drift_issues: Dict[str, List[any]]
    ) -> Dict[str, float]:
        """
        Calculate simple scores without PageRank (fallback).

        Score = (issue_severity * 0.6) + (complexity * 0.2) + (issue_count * 0.2)
        """
        scores = {}

        for endpoint_id, data in graph.items():
            score = (
                data['issue_severity'] * 0.6 +
                data['complexity'] * 0.2 +
                data['issue_count'] * 0.2
            )
            scores[endpoint_id] = max(0.1, score)  # Minimum score

        return scores

    def _create_personalization(
        self,
        graph: Dict[str, Dict],
        drift_issues: Dict[str, List[any]]
    ) -> Dict[str, float]:
        """
        Create personalization vector for PageRank.

        Endpoints with more/severe drift get higher initial importance.
        """
        personalization = {}

        for endpoint_id, data in graph.items():
            # Score based on issue severity and count
            severity_score = data['issue_severity']
            count_score = data['issue_count']

            personalization[endpoint_id] = max(0.1, severity_score + count_score)

        # Normalize to sum to 1.0
        total = sum(personalization.values())
        if total > 0:
            personalization = {
                k: v / total for k, v in personalization.items()
            }
        else:
            # Equal distribution if no issues
            equal = 1.0 / len(personalization)
            personalization = {k: equal for k in personalization}

        return personalization

    def _build_context_chunks(
        self,
        endpoints: List[any],
        drift_issues: Dict[str, List[any]],
        scores: Dict[str, float],
        graph: Dict[str, Dict]
    ) -> List[ContextChunk]:
        """Build context chunks from scored endpoints."""
        chunks = []

        for endpoint in endpoints:
            endpoint_id = endpoint.endpoint_id

            if endpoint_id not in scores:
                continue

            issues = drift_issues.get(endpoint_id, [])
            if not issues:
                continue  # Skip endpoints without issues

            dependencies = graph[endpoint_id]['dependencies']

            # Estimate tokens
            token_estimate = (
                len(issues) * self.TOKENS_PER_ISSUE +
                len(dependencies) * self.TOKENS_PER_DEPENDENCY
            )

            chunk = ContextChunk(
                endpoint_id=endpoint_id,
                score=scores[endpoint_id],
                issues=issues,
                dependencies=dependencies,
                token_estimate=token_estimate,
                rank=0,  # Set later
            )

            chunks.append(chunk)

        return chunks

    def get_cache_key(self, context: ContextChunk) -> str:
        """
        Generate cache key for context chunk.

        Key is based on endpoint and issue characteristics.
        """
        fingerprint = {
            'endpoint': context.endpoint_id,
            'issue_types': sorted([type(issue).__name__ for issue in context.issues]),
            'issue_count': len(context.issues),
            'severities': sorted([
                getattr(issue, 'severity', 'medium')
                for issue in context.issues
            ]),
        }

        key_str = json.dumps(fingerprint, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def explain_ranking(self, contexts: List[ContextChunk]) -> str:
        """
        Generate human-readable explanation of ranking.

        Useful for debugging and transparency.
        """
        lines = [
            "Context Ranking Explanation:",
            f"Total contexts: {len(contexts)}",
            "",
            "Top Contexts (by score):"
        ]

        for i, ctx in enumerate(contexts[:10], 1):
            lines.append(
                f"  {i}. {ctx.endpoint_id} "
                f"(score: {ctx.score:.2f}, issues: {len(ctx.issues)}, "
                f"tokens: ~{ctx.token_estimate})"
            )

        return "\n".join(lines)
