"""
Master Test Generator

Coordinates all test generators and creates complete test suites.
"""

from typing import List

from api_contract_validator.config.logging import get_logger
from api_contract_validator.config.models import TestGenerationConfig
from api_contract_validator.generation.base import TestCase, TestSuite
from api_contract_validator.generation.boundary.generator import BoundaryTestGenerator
from api_contract_validator.generation.fuzzing.fuzzer import FuzzingTestGenerator
from api_contract_validator.generation.invalid.generator import InvalidTestGenerator
from api_contract_validator.generation.prioritizer.risk_ranker import RiskBasedPrioritizer
from api_contract_validator.generation.valid.generator import ValidTestGenerator
from api_contract_validator.input.normalizer.models import UnifiedAPISpec

logger = get_logger(__name__)


class MasterTestGenerator:
    """
    Coordinates all test generators to create comprehensive test suites.
    """

    def __init__(self, config: TestGenerationConfig):
        self.config = config
        self.valid_generator = ValidTestGenerator()
        self.invalid_generator = InvalidTestGenerator()
        self.boundary_generator = BoundaryTestGenerator()
        self.fuzzing_generator = FuzzingTestGenerator(corpus_size=getattr(config, 'fuzzing_corpus_size', 20))
        self.prioritizer = RiskBasedPrioritizer(config)

    def generate_test_suite(self, spec: UnifiedAPISpec) -> TestSuite:
        """
        Generate complete test suite for an API specification.

        Args:
            spec: UnifiedAPISpec instance

        Returns:
            TestSuite with all generated tests
        """
        logger.info(f"Generating test suite for API: {spec.metadata.title}")

        test_suite = TestSuite(
            name=f"Test Suite - {spec.metadata.title}",
            description=f"Comprehensive test suite for {spec.metadata.title} v{spec.metadata.version}",
        )

        for endpoint in spec.endpoints:
            endpoint_tests = self._generate_endpoint_tests(endpoint)
            for test in endpoint_tests:
                test_suite.add_test(test)

        # Apply prioritization if enabled
        if self.config.enable_prioritization:
            test_suite = self.prioritizer.prioritize(test_suite)

        # Limit total tests if specified
        if len(test_suite.test_cases) > self.config.max_tests_per_endpoint * len(spec.endpoints):
            max_total = self.config.max_tests_per_endpoint * len(spec.endpoints)
            test_suite.test_cases = self.prioritizer.select_top_tests(test_suite, max_total)

        logger.info(
            f"Generated {len(test_suite.test_cases)} tests for {len(spec.endpoints)} endpoints"
        )

        # Log test distribution
        distribution = self._get_test_distribution(test_suite)
        logger.info(f"Test distribution: {distribution}")

        return test_suite

    def _generate_endpoint_tests(self, endpoint) -> List[TestCase]:
        """Generate all tests for a single endpoint."""
        tests = []

        # Generate valid tests
        if self.config.generate_valid:
            valid_tests = self.valid_generator.generate_tests(endpoint)
            tests.extend(valid_tests)

        # Generate invalid tests
        if self.config.generate_invalid:
            invalid_tests = self.invalid_generator.generate_tests(endpoint)
            tests.extend(invalid_tests)

        # Generate boundary tests
        if self.config.generate_boundary:
            boundary_tests = self.boundary_generator.generate_tests(endpoint)
            tests.extend(boundary_tests)

        # Generate fuzzing tests
        if getattr(self.config, 'generate_fuzzing', False):
            fuzzing_tests = self.fuzzing_generator.generate_tests(endpoint)
            tests.extend(fuzzing_tests)

        # Limit tests per endpoint
        if len(tests) > self.config.max_tests_per_endpoint:
            # Sort by priority and keep top N
            tests = sorted(tests, key=lambda t: t.priority, reverse=True)
            tests = tests[: self.config.max_tests_per_endpoint]

        return tests

    def _get_test_distribution(self, test_suite: TestSuite) -> dict:
        """Get distribution of test types."""
        return {
            "valid": len(test_suite.get_valid_tests()),
            "invalid": len(test_suite.get_invalid_tests()),
            "boundary": len(test_suite.get_boundary_tests()),
            "total": len(test_suite.test_cases),
        }


def generate_tests(spec: UnifiedAPISpec, config: TestGenerationConfig) -> TestSuite:
    """
    Convenience function to generate tests from a specification.

    Args:
        spec: UnifiedAPISpec instance
        config: TestGenerationConfig instance

    Returns:
        TestSuite with all generated tests
    """
    generator = MasterTestGenerator(config)
    return generator.generate_test_suite(spec)
