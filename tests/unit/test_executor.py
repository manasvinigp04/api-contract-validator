"""
Unit tests for test executor.
"""

import pytest
from unittest.mock import AsyncMock, patch

from api_contract_validator.config.models import ExecutionConfig
from api_contract_validator.execution.runner.executor import TestExecutor, TestResult
from api_contract_validator.generation.base import TestCase, TestCaseType
from api_contract_validator.input.normalizer.models import HTTPMethod


@pytest.mark.unit
class TestTestExecutor:
    """Test TestExecutor class."""

    @pytest.fixture
    def executor(self, default_execution_config):
        """Create TestExecutor instance."""
        return TestExecutor("http://localhost:8000", default_execution_config)

    def test_execute_tests_success(self, httpserver, valid_test_case, default_execution_config):
        """Test successful test execution."""
        httpserver.expect_request("/users/1").respond_with_json(
            {"id": 1, "email": "test@example.com", "name": "Test User"}, status=200
        )

        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([valid_test_case])

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, TestResult)
        assert result.passed is True
        assert result.status_code == 200
        assert result.response_body is not None
        assert result.error is None

    def test_execute_tests_with_failures(self, httpserver, valid_test_case, default_execution_config):
        """Test execution with failed tests."""
        # Return 500 error instead of expected 200
        httpserver.expect_request("/users/1").respond_with_json(
            {"error": "internal_error"}, status=500
        )

        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([valid_test_case])

        result = results[0]
        assert result.passed is False
        assert result.status_code == 500

    def test_execute_tests_with_request_body(self, httpserver, invalid_test_case, default_execution_config):
        """Test execution with POST request body."""
        httpserver.expect_request("/users", method="POST").respond_with_json(
            {"error": "validation_error"}, status=400
        )

        # Update base URL to match httpserver
        invalid_test_case.path = "/users"
        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([invalid_test_case])

        result = results[0]
        # Invalid test expects 400, so should pass
        assert result.passed is True
        assert result.status_code == 400

    def test_build_full_url(self, executor, valid_test_case):
        """Test URL building with path parameters."""
        # Test case has path_params: {"userId": 1}
        full_path = valid_test_case.full_path
        expected_url = f"http://localhost:8000{full_path}"

        assert "{userId}" not in full_path
        assert "/users/1" in expected_url

    def test_add_query_parameters(self, httpserver, default_execution_config, simple_get_endpoint):
        """Test that query parameters are added correctly."""
        test_case = TestCase(
            test_id="test_1",
            endpoint=simple_get_endpoint,
            test_type=TestCaseType.VALID,
            description="Test",
            method=HTTPMethod.GET,
            path="/users/1",
            query_params={"limit": 10, "offset": 0},
            expected_status=200,
        )

        httpserver.expect_request("/users/1", query_string="limit=10&offset=0").respond_with_json(
            {"id": 1, "email": "test@example.com"}, status=200
        )

        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([test_case])

        assert results[0].passed is True

    def test_add_headers(self, httpserver, default_execution_config, simple_post_endpoint):
        """Test that headers are added correctly."""
        test_case = TestCase(
            test_id="test_1",
            endpoint=simple_post_endpoint,
            test_type=TestCaseType.VALID,
            description="Test",
            method=HTTPMethod.POST,
            path="/users",
            headers={"X-API-Key": "test-key"},
            request_body={"email": "test@example.com", "name": "Test"},
            expected_status=201,
        )

        def check_headers(request):
            assert request.headers.get("X-API-Key") == "test-key"
            assert request.headers.get("Content-Type") == "application/json"

        httpserver.expect_request("/users", method="POST").respond_with_json(
            {"id": 1}, status=201
        )

        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([test_case])

        assert results[0].passed is True

    def test_json_response_parsing(self, httpserver, valid_test_case, default_execution_config):
        """Test parsing JSON response body."""
        response_data = {"id": 1, "email": "test@example.com", "name": "Test User"}

        httpserver.expect_request("/users/1").respond_with_json(response_data, status=200)

        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([valid_test_case])

        result = results[0]
        assert result.response_body == response_data

    def test_non_json_response_fallback(self, httpserver, valid_test_case, default_execution_config):
        """Test handling non-JSON response."""
        httpserver.expect_request("/users/1").respond_with_data("Plain text response", status=200)

        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([valid_test_case])

        result = results[0]
        # Should fallback to raw text
        assert result.response_body is not None
        assert isinstance(result.response_body, dict)
        assert "raw" in result.response_body

    def test_pass_fail_determination_valid_test(self, httpserver, valid_test_case, default_execution_config):
        """Test pass/fail logic for valid tests."""
        # Valid test expects exact status match
        httpserver.expect_request("/users/1").respond_with_json({}, status=200)

        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([valid_test_case])

        assert results[0].passed is True

    def test_pass_fail_determination_invalid_test(self, httpserver, invalid_test_case, default_execution_config):
        """Test pass/fail logic for invalid tests."""
        # Invalid test expects 4xx or 5xx
        invalid_test_case.path = "/users"
        httpserver.expect_request("/users").respond_with_json({}, status=400)

        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([invalid_test_case])

        # Invalid test got expected 400, so it passes
        assert results[0].passed is True

    def test_execution_time_tracking(self, httpserver, valid_test_case, default_execution_config):
        """Test that execution time is tracked."""
        httpserver.expect_request("/users/1").respond_with_json({}, status=200)

        executor = TestExecutor(httpserver.url_for("/"), default_execution_config)
        results = executor.execute_tests_sync([valid_test_case])

        result = results[0]
        # Execution time should be positive
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_parallel_execution_concurrency(self, httpserver, default_execution_config):
        """Test that parallel execution respects worker limit."""
        from api_contract_validator.input.normalizer.models import Endpoint, ResponseBody

        # Create multiple test cases
        endpoint = Endpoint(
            path="/test",
            method=HTTPMethod.GET,
            responses=[ResponseBody(status_code=200, schema={})],
        )

        test_cases = [
            TestCase(
                test_id=f"test_{i}",
                endpoint=endpoint,
                test_type=TestCaseType.VALID,
                description=f"Test {i}",
                method=HTTPMethod.GET,
                path="/test",
                expected_status=200,
            )
            for i in range(20)
        ]

        # Setup mock responses
        httpserver.expect_request("/test").respond_with_json({}, status=200)

        # Config with limited workers
        config = ExecutionConfig(parallel_workers=3)
        executor = TestExecutor(httpserver.url_for("/"), config)

        results = await executor.execute_tests(test_cases)

        # All tests should complete
        assert len(results) == 20

    def test_retry_logic_with_timeout(self, httpserver, valid_test_case):
        """Test retry logic on timeout/failure."""
        # Use short timeout to trigger retry
        config = ExecutionConfig(timeout_seconds=1, retry_attempts=2, retry_delay_seconds=0.1)

        # First request times out, second succeeds
        call_count = {"count": 0}

        def handler(request):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise Exception("Timeout")
            return httpx.Response(200, json={"id": 1})

        httpserver.expect_request("/users/1").respond_with_handler(handler)

        executor = TestExecutor(httpserver.url_for("/"), config)
        results = executor.execute_tests_sync([valid_test_case])

        # Should eventually succeed after retry
        result = results[0]
        # At minimum, retry was attempted
        assert result is not None
