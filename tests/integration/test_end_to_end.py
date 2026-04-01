"""
End-to-end integration tests.
"""

import pytest

from api_contract_validator.analysis.drift.detector import DriftDetector
from api_contract_validator.config.models import DriftDetectionConfig, ExecutionConfig, TestGenerationConfig
from api_contract_validator.execution.collector.result_collector import ResultCollector
from api_contract_validator.execution.runner.executor import TestExecutor
from api_contract_validator.generation.test_generator import MasterTestGenerator
from api_contract_validator.input.openapi.parser import OpenAPIParser
from api_contract_validator.schema.contract.constraint_extractor import ConstraintExtractor


@pytest.mark.integration
class TestEndToEnd:
    """Test end-to-end workflows."""

    def test_openapi_to_contract_to_tests(self, openapi_spec_path):
        """Test Parse → Extract → Generate workflow."""
        # Step 1: Parse OpenAPI spec
        parser = OpenAPIParser()
        spec = parser.parse_file(openapi_spec_path)

        assert len(spec.endpoints) == 3

        # Step 2: Extract contract
        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        assert len(contract.endpoint_contracts) == 3

        # Step 3: Generate test suite
        gen_config = TestGenerationConfig(max_tests_per_endpoint=10)
        generator = MasterTestGenerator(gen_config)
        test_suite = generator.generate_test_suite(spec)

        assert len(test_suite.test_cases) > 0
        # Should have mix of valid, invalid, boundary
        assert len(test_suite.get_valid_tests()) > 0

    def test_generate_execute_collect_flow(self, openapi_spec_path, httpserver):
        """Test Generate → Execute → Collect workflow."""
        # Parse and generate tests
        parser = OpenAPIParser()
        spec = parser.parse_file(openapi_spec_path)

        gen_config = TestGenerationConfig(
            max_tests_per_endpoint=5, generate_invalid=False, generate_boundary=False
        )
        generator = MasterTestGenerator(gen_config)
        test_suite = generator.generate_test_suite(spec)

        # Setup mock API
        httpserver.expect_request("/users").respond_with_json(
            [{"id": 1, "email": "test@example.com", "name": "Test"}], status=200
        )
        httpserver.expect_request("/users", method="POST").respond_with_json(
            {"id": 2, "email": "new@example.com", "name": "New User"}, status=201
        )
        httpserver.expect_request("/users/1").respond_with_json(
            {"id": 1, "email": "test@example.com", "name": "Test"}, status=200
        )

        # Execute tests
        exec_config = ExecutionConfig(parallel_workers=2, timeout_seconds=5)
        executor = TestExecutor(httpserver.url_for("/"), exec_config)
        results = executor.execute_tests_sync(test_suite.test_cases)

        # Collect results
        collector = ResultCollector()
        collector.add_results(results)
        summary = collector.get_summary()

        assert summary.total == len(test_suite.test_cases)
        assert summary.total > 0

    def test_full_validation_pipeline(self, openapi_spec_path, httpserver):
        """Test complete validation pipeline end-to-end."""
        # Step 1: Parse
        parser = OpenAPIParser()
        spec = parser.parse_file(openapi_spec_path)

        # Step 2: Extract contract
        extractor = ConstraintExtractor(spec)
        contract = extractor.extract_contract()

        # Step 3: Generate tests
        gen_config = TestGenerationConfig(max_tests_per_endpoint=5)
        generator = MasterTestGenerator(gen_config)
        test_suite = generator.generate_test_suite(spec)

        # Step 4: Setup mock API
        httpserver.expect_request("/users").respond_with_json([], status=200)
        httpserver.expect_request("/users", method="POST").respond_with_json(
            {"id": 1, "email": "test@example.com", "name": "Test"}, status=201
        )
        httpserver.expect_request("/users/1").respond_with_json(
            {"id": 1, "email": "test@example.com", "name": "Test"}, status=200
        )

        # Step 5: Execute
        exec_config = ExecutionConfig(parallel_workers=2)
        executor = TestExecutor(httpserver.url_for("/"), exec_config)
        results = executor.execute_tests_sync(test_suite.test_cases)

        # Step 6: Collect
        collector = ResultCollector()
        collector.add_results(results)
        summary = collector.get_summary()

        # Step 7: Detect drift
        drift_config = DriftDetectionConfig()
        detector = DriftDetector(contract, drift_config)
        drift_report = detector.detect_drift(summary)

        # Verify complete pipeline
        assert drift_report is not None
        assert drift_report.spec_source == str(openapi_spec_path)
        assert summary.total > 0

    def test_parse_and_generate_workflow(self, openapi_spec_path):
        """Test parsing spec and generating tests separately."""
        # Parse specification
        parser = OpenAPIParser()
        spec = parser.parse_file(openapi_spec_path)

        assert spec.metadata.title == "Sample User API"
        assert len(spec.endpoints) == 3

        # Generate tests from parsed spec
        gen_config = TestGenerationConfig()
        generator = MasterTestGenerator(gen_config)
        test_suite = generator.generate_test_suite(spec)

        assert test_suite.name == f"Test Suite - {spec.metadata.title}"
        assert len(test_suite.test_cases) > 0

        # Verify test suite can be serialized to JSON
        test_suite_dict = test_suite.model_dump(mode="json")
        json_str = json.dumps(test_suite_dict)
        assert len(json_str) > 100
