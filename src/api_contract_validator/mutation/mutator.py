"""Contract mutation testing."""

from copy import deepcopy
from typing import List, Dict
from api_contract_validator.input.normalizer.models import UnifiedAPISpec, FieldConstraint

class SpecMutator:
    """Mutate OpenAPI specs to validate spec quality."""

    def mutate_spec(self, spec: UnifiedAPISpec) -> List[UnifiedAPISpec]:
        """Generate mutated specs."""
        mutations = []
        for endpoint in spec.endpoints:
            if endpoint.request_body:
                for field_name in list(endpoint.request_body.schema.keys()):
                    # Mutation: Remove required constraint
                    mutated = deepcopy(spec)
                    mutated_endpoint = next(e for e in mutated.endpoints if e.endpoint_id == endpoint.endpoint_id)
                    mutated_endpoint.request_body.schema[field_name].constraints.required = False
                    mutations.append(mutated)
                    if len(mutations) >= 10:
                        break
        return mutations

    def calculate_mutation_score(self, original_results: int, mutated_results: List[int]) -> float:
        """Calculate mutation score (% of mutations caught)."""
        caught = sum(1 for r in mutated_results if r != original_results)
        return caught / len(mutated_results) if mutated_results else 0.0
