"""
Schema Composition Module

Handles complex OpenAPI schema composition:
- discriminator (polymorphic types)
- oneOf (exactly one match)
- anyOf (at least one match)
- allOf (all must match)
"""

from api_contract_validator.schema.composition.discriminator_validator import DiscriminatorValidator
from api_contract_validator.schema.composition.oneof_validator import OneOfValidator
from api_contract_validator.schema.composition.anyof_validator import AnyOfValidator
from api_contract_validator.schema.composition.allof_validator import AllOfValidator

__all__ = [
    "DiscriminatorValidator",
    "OneOfValidator",
    "AnyOfValidator",
    "AllOfValidator",
]
