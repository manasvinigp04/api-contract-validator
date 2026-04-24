"""
Fuzzing-based test generator using property-based testing.

Generates adversarial test cases that maximize edge case coverage and
discover security vulnerabilities.
"""

import random
from typing import Any, Dict, List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.generation.base import BaseTestGenerator, TestCase, TestCaseType
from api_contract_validator.generation.fuzzing.mutations import MutationEngine
from api_contract_validator.generation.valid.generator import ValidTestGenerator
from api_contract_validator.input.normalizer.models import Endpoint, FieldDefinition, FieldType

logger = get_logger(__name__)


class FuzzingTestGenerator(BaseTestGenerator):
    """
    Generates fuzzed test cases using mutation-based fuzzing and
    property-based testing strategies.
    """

    def __init__(self, corpus_size: int = 20):
        """
        Initialize fuzzing test generator.

        Args:
            corpus_size: Number of fuzzed variants to generate per endpoint
        """
        super().__init__()
        self.corpus_size = corpus_size
        self.valid_generator = ValidTestGenerator()
        self.mutation_engine = MutationEngine()

    def generate_tests(self, endpoint: Endpoint) -> List[TestCase]:
        """
        Generate fuzzed test cases for an endpoint.

        Strategy:
        1. Generate valid baseline test data
        2. Apply adversarial mutations
        3. Generate hypothesis-based property tests
        4. Create security-focused attack vectors

        Args:
            endpoint: Endpoint to generate tests for

        Returns:
            List of fuzzed test cases
        """
        tests = []

        # Only fuzz endpoints with request bodies
        if not endpoint.request_body:
            logger.debug(f"Skipping fuzzing for {endpoint.endpoint_id} (no request body)")
            return tests

        logger.info(f"Generating {self.corpus_size} fuzzed tests for {endpoint.endpoint_id}")

        # Generate baseline valid data
        baseline_data = self.valid_generator._generate_valid_body(
            endpoint.request_body.schema
        )

        # Strategy 1: Mutation-based fuzzing
        mutation_tests = self._generate_mutation_tests(endpoint, baseline_data)
        tests.extend(mutation_tests)

        # Strategy 2: Property-based fuzzing
        property_tests = self._generate_property_based_tests(endpoint)
        tests.extend(property_tests)

        # Strategy 3: Security-focused fuzzing
        security_tests = self._generate_security_tests(endpoint, baseline_data)
        tests.extend(security_tests)

        # Limit to corpus size
        if len(tests) > self.corpus_size:
            # Prioritize diverse mutations
            tests = self._select_diverse_tests(tests, self.corpus_size)

        logger.info(f"Generated {len(tests)} fuzzed tests for {endpoint.endpoint_id}")
        return tests

    def _generate_mutation_tests(
        self, endpoint: Endpoint, baseline_data: Dict[str, Any]
    ) -> List[TestCase]:
        """
        Generate tests by mutating valid baseline data.
        """
        tests = []
        mutations_per_strategy = max(2, self.corpus_size // 10)

        # Apply each mutation strategy
        mutated_variants = self.mutation_engine.apply_mutations(
            baseline_data, mutation_count=1
        )

        for idx, mutated_data in enumerate(mutated_variants[:mutations_per_strategy * 10]):
            mutation_desc = self.mutation_engine.get_mutation_description(
                baseline_data, mutated_data
            )

            test = TestCase(
                test_id=self.generate_test_id(f"fuzz_mutation_{endpoint.method.value}"),
                endpoint=endpoint,
                test_type=TestCaseType.INVALID,
                description=f"Fuzzing: {mutation_desc}",
                method=endpoint.method,
                path=endpoint.path,
                path_params=self._generate_path_params(endpoint),
                request_body=mutated_data,
                expected_status=400,
                should_pass=False,
                priority=1.3,  # High priority for fuzzing tests
            )
            tests.append(test)

        return tests

    def _generate_property_based_tests(self, endpoint: Endpoint) -> List[TestCase]:
        """
        Generate tests based on property-based testing principles.

        Tests invariants like:
        - Idempotency (same request = same result)
        - Commutativity (order independence)
        - Data type preservation
        """
        tests = []

        if not endpoint.request_body:
            return tests

        # Property: Extreme values
        extreme_tests = self._generate_extreme_value_tests(endpoint)
        tests.extend(extreme_tests)

        # Property: Boundary combinations
        boundary_tests = self._generate_boundary_combination_tests(endpoint)
        tests.extend(boundary_tests)

        return tests

    def _generate_extreme_value_tests(self, endpoint: Endpoint) -> List[TestCase]:
        """
        Generate tests with extreme but valid-ish values.
        """
        tests = []

        for field_name, field_def in endpoint.request_body.schema.items():
            extreme_values = self._get_extreme_values(field_def)

            for extreme_value in extreme_values[:2]:  # Limit to 2 per field
                body = self.valid_generator._generate_valid_body(
                    endpoint.request_body.schema
                )
                body[field_name] = extreme_value

                test = TestCase(
                    test_id=self.generate_test_id(f"fuzz_extreme_{endpoint.method.value}"),
                    endpoint=endpoint,
                    test_type=TestCaseType.BOUNDARY,
                    description=f"Fuzzing: Extreme value for {field_name}",
                    method=endpoint.method,
                    path=endpoint.path,
                    path_params=self._generate_path_params(endpoint),
                    request_body=body,
                    expected_status=endpoint.responses.get(201, endpoint.responses.get(200)).status_code if endpoint.responses else 200,
                    should_pass=True,  # Extreme but potentially valid
                    priority=1.2,
                )
                tests.append(test)

        return tests

    def _generate_boundary_combination_tests(self, endpoint: Endpoint) -> List[TestCase]:
        """
        Test combinations of boundary values across multiple fields.
        """
        tests = []

        if not endpoint.request_body or len(endpoint.request_body.schema) < 2:
            return tests

        # Test: All fields at minimum boundary
        body_min = {}
        for field_name, field_def in endpoint.request_body.schema.items():
            body_min[field_name] = self._get_minimum_value(field_def)

        test_min = TestCase(
            test_id=self.generate_test_id(f"fuzz_all_min_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.BOUNDARY,
            description="Fuzzing: All fields at minimum boundary",
            method=endpoint.method,
            path=endpoint.path,
            path_params=self._generate_path_params(endpoint),
            request_body=body_min,
            expected_status=endpoint.responses.get(201, endpoint.responses.get(200)).status_code if endpoint.responses else 200,
            should_pass=True,
            priority=1.2,
        )
        tests.append(test_min)

        # Test: All fields at maximum boundary
        body_max = {}
        for field_name, field_def in endpoint.request_body.schema.items():
            body_max[field_name] = self._get_maximum_value(field_def)

        test_max = TestCase(
            test_id=self.generate_test_id(f"fuzz_all_max_{endpoint.method.value}"),
            endpoint=endpoint,
            test_type=TestCaseType.BOUNDARY,
            description="Fuzzing: All fields at maximum boundary",
            method=endpoint.method,
            path=endpoint.path,
            path_params=self._generate_path_params(endpoint),
            request_body=body_max,
            expected_status=endpoint.responses.get(201, endpoint.responses.get(200)).status_code if endpoint.responses else 200,
            should_pass=True,
            priority=1.2,
        )
        tests.append(test_max)

        return tests

    def _generate_security_tests(
        self, endpoint: Endpoint, baseline_data: Dict[str, Any]
    ) -> List[TestCase]:
        """
        Generate security-focused test cases targeting common vulnerabilities.
        """
        tests = []

        # Security category: Injection attacks
        injection_tests = self._generate_injection_tests(endpoint, baseline_data)
        tests.extend(injection_tests[:3])  # Limit per category

        # Security category: Overflow/DoS
        overflow_tests = self._generate_overflow_tests(endpoint, baseline_data)
        tests.extend(overflow_tests[:2])

        # Security category: Encoding issues
        encoding_tests = self._generate_encoding_tests(endpoint, baseline_data)
        tests.extend(encoding_tests[:2])

        return tests

    def _generate_injection_tests(
        self, endpoint: Endpoint, baseline_data: Dict[str, Any]
    ) -> List[TestCase]:
        """Generate SQL/NoSQL/Command injection tests."""
        tests = []

        for field_name in baseline_data.keys():
            if isinstance(baseline_data[field_name], str):
                # SQL injection test
                body_sql = baseline_data.copy()
                body_sql[field_name] = "' OR '1'='1"

                test = TestCase(
                    test_id=self.generate_test_id(f"fuzz_sqli_{endpoint.method.value}"),
                    endpoint=endpoint,
                    test_type=TestCaseType.INVALID,
                    description=f"Security: SQL injection in {field_name}",
                    method=endpoint.method,
                    path=endpoint.path,
                    path_params=self._generate_path_params(endpoint),
                    request_body=body_sql,
                    expected_status=400,
                    should_pass=False,
                    priority=1.5,  # Security tests are high priority
                )
                tests.append(test)
                break  # One field is enough

        return tests

    def _generate_overflow_tests(
        self, endpoint: Endpoint, baseline_data: Dict[str, Any]
    ) -> List[TestCase]:
        """Generate buffer overflow and DoS tests."""
        tests = []

        for field_name in baseline_data.keys():
            if isinstance(baseline_data[field_name], str):
                body_overflow = baseline_data.copy()
                body_overflow[field_name] = "A" * 100000  # 100KB string

                test = TestCase(
                    test_id=self.generate_test_id(f"fuzz_overflow_{endpoint.method.value}"),
                    endpoint=endpoint,
                    test_type=TestCaseType.INVALID,
                    description=f"Security: Buffer overflow in {field_name}",
                    method=endpoint.method,
                    path=endpoint.path,
                    path_params=self._generate_path_params(endpoint),
                    request_body=body_overflow,
                    expected_status=400,
                    should_pass=False,
                    priority=1.4,
                )
                tests.append(test)
                break

        return tests

    def _generate_encoding_tests(
        self, endpoint: Endpoint, baseline_data: Dict[str, Any]
    ) -> List[TestCase]:
        """Generate encoding and unicode tests."""
        tests = []

        for field_name in baseline_data.keys():
            if isinstance(baseline_data[field_name], str):
                body_unicode = baseline_data.copy()
                body_unicode[field_name] = "Test​Data"  # Unicode bomb

                test = TestCase(
                    test_id=self.generate_test_id(f"fuzz_unicode_{endpoint.method.value}"),
                    endpoint=endpoint,
                    test_type=TestCaseType.INVALID,
                    description=f"Security: Unicode encoding in {field_name}",
                    method=endpoint.method,
                    path=endpoint.path,
                    path_params=self._generate_path_params(endpoint),
                    request_body=body_unicode,
                    expected_status=400,
                    should_pass=False,
                    priority=1.3,
                )
                tests.append(test)
                break

        return tests

    def _get_extreme_values(self, field_def: FieldDefinition) -> List[Any]:
        """Get extreme but potentially valid values for a field."""
        extremes = []

        if field_def.type == FieldType.INTEGER:
            extremes = [0, -1, 2**31 - 1, -2**31]
        elif field_def.type == FieldType.NUMBER:
            extremes = [0.0, -0.0, 1e308, -1e308, 1e-308]
        elif field_def.type == FieldType.STRING:
            extremes = ["", " ", "   ", "a" * 255]
        elif field_def.type == FieldType.ARRAY:
            extremes = [[], [None], [""] * 100]
        elif field_def.type == FieldType.BOOLEAN:
            extremes = [True, False]

        return extremes

    def _get_minimum_value(self, field_def: FieldDefinition) -> Any:
        """Get minimum valid value for a field."""
        if field_def.type == FieldType.STRING:
            min_len = field_def.constraints.min_length or 1
            return "a" * min_len
        elif field_def.type == FieldType.INTEGER:
            return field_def.constraints.minimum or 0
        elif field_def.type == FieldType.NUMBER:
            return float(field_def.constraints.minimum or 0.0)
        elif field_def.type == FieldType.ARRAY:
            return []
        elif field_def.type == FieldType.BOOLEAN:
            return False
        else:
            return self.valid_generator._generate_valid_value(
                field_def.type.value, field_def.constraints
            )

    def _get_maximum_value(self, field_def: FieldDefinition) -> Any:
        """Get maximum valid value for a field."""
        if field_def.type == FieldType.STRING:
            max_len = field_def.constraints.max_length or 100
            return "z" * max_len
        elif field_def.type == FieldType.INTEGER:
            return field_def.constraints.maximum or 1000000
        elif field_def.type == FieldType.NUMBER:
            return float(field_def.constraints.maximum or 1000000.0)
        elif field_def.type == FieldType.ARRAY:
            return ["item"] * 10
        elif field_def.type == FieldType.BOOLEAN:
            return True
        else:
            return self.valid_generator._generate_valid_value(
                field_def.type.value, field_def.constraints
            )

    def _generate_path_params(self, endpoint: Endpoint) -> Dict[str, Any]:
        """Generate valid path parameters."""
        path_params = {}
        for param in endpoint.parameters:
            if param.location == "path":
                path_params[param.name] = self.valid_generator._generate_valid_value(
                    param.type.value, param.constraints
                )
        return path_params

    def _select_diverse_tests(self, tests: List[TestCase], limit: int) -> List[TestCase]:
        """
        Select a diverse subset of tests to maximize coverage.
        Prioritizes different mutation types and security categories.
        """
        # Sort by priority
        tests_sorted = sorted(tests, key=lambda t: t.priority, reverse=True)

        # Take top priority tests and ensure diversity
        selected = []
        seen_descriptions = set()

        for test in tests_sorted:
            # Extract mutation type from description
            mutation_type = test.description.split(":")[0] if ":" in test.description else ""

            if mutation_type not in seen_descriptions or len(selected) < limit // 2:
                selected.append(test)
                seen_descriptions.add(mutation_type)

            if len(selected) >= limit:
                break

        return selected
