"""
Fuzzing-based test generation module.

Provides coverage-guided fuzzing and property-based testing to discover
edge cases and security vulnerabilities that rule-based generators miss.
"""

from api_contract_validator.generation.fuzzing.fuzzer import FuzzingTestGenerator
from api_contract_validator.generation.fuzzing.mutations import MutationEngine

__all__ = ["FuzzingTestGenerator", "MutationEngine"]
