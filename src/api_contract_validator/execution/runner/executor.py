"""
Test Executor

Executes HTTP test cases against target APIs.
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from api_contract_validator.config.logging import get_logger
from api_contract_validator.config.models import ExecutionConfig
from api_contract_validator.generation.base import TestCase

logger = get_logger(__name__)


class TestResult:
    """Represents the result of executing a single test case."""

    def __init__(
        self,
        test_case: TestCase,
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
        response_headers: Optional[Dict[str, str]] = None,
        execution_time_ms: float = 0.0,
        error: Optional[str] = None,
        passed: bool = False,
    ):
        self.test_case = test_case
        self.status_code = status_code
        self.response_body = response_body
        self.response_headers = response_headers
        self.execution_time_ms = execution_time_ms
        self.error = error
        self.passed = passed


class TestExecutor:
    """
    Executes HTTP test cases with parallel execution, retries, and timeouts.
    """

    def __init__(self, base_url: str, config: ExecutionConfig):
        self.base_url = base_url.rstrip("/")
        self.config = config

    async def execute_tests(self, test_cases: List[TestCase]) -> List[TestResult]:
        """
        Execute all test cases with parallel execution.

        Args:
            test_cases: List of test cases to execute

        Returns:
            List of test results
        """
        logger.info(f"Executing {len(test_cases)} tests against {self.base_url}")

        # Create semaphore for parallel execution limit
        semaphore = asyncio.Semaphore(self.config.parallel_workers)

        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            verify=self.config.verify_ssl,
            follow_redirects=self.config.follow_redirects,
        ) as client:
            tasks = [
                self._execute_test_with_semaphore(client, test_case, semaphore)
                for test_case in test_cases
            ]
            results = await asyncio.gather(*tasks)

        passed = sum(1 for r in results if r.passed)
        logger.info(f"Execution complete: {passed}/{len(results)} tests passed")

        return results

    async def _execute_test_with_semaphore(
        self, client: httpx.AsyncClient, test_case: TestCase, semaphore: asyncio.Semaphore
    ) -> TestResult:
        """Execute a single test with semaphore control."""
        async with semaphore:
            return await self._execute_test(client, test_case)

    async def _execute_test(
        self, client: httpx.AsyncClient, test_case: TestCase
    ) -> TestResult:
        """Execute a single test case with retry logic."""
        import time

        start_time = time.time()

        for attempt in range(self.config.retry_attempts + 1):
            try:
                # Build URL
                url = f"{self.base_url}{test_case.full_path}"

                # Add query parameters
                params = test_case.query_params if test_case.query_params else None

                # Prepare headers
                headers = test_case.headers.copy() if test_case.headers else {}
                if test_case.request_body:
                    headers.setdefault("Content-Type", "application/json")

                # Execute request
                response = await client.request(
                    method=test_case.method.value,
                    url=url,
                    params=params,
                    headers=headers,
                    json=test_case.request_body,
                )

                # Calculate execution time
                execution_time = (time.time() - start_time) * 1000

                # Parse response
                response_body = None
                try:
                    response_body = response.json()
                except Exception:
                    response_body = {"raw": response.text}

                # Check if test passed
                passed = self._check_test_passed(test_case, response.status_code)

                return TestResult(
                    test_case=test_case,
                    status_code=response.status_code,
                    response_body=response_body,
                    response_headers=dict(response.headers),
                    execution_time_ms=execution_time,
                    passed=passed,
                )

            except httpx.TimeoutException as e:
                if attempt < self.config.retry_attempts:
                    logger.warning(
                        f"Timeout on attempt {attempt + 1} for {test_case.test_id}, retrying..."
                    )
                    await asyncio.sleep(self.config.retry_delay_seconds)
                    continue
                else:
                    execution_time = (time.time() - start_time) * 1000
                    return TestResult(
                        test_case=test_case,
                        execution_time_ms=execution_time,
                        error=f"Timeout after {self.config.retry_attempts + 1} attempts",
                        passed=False,
                    )

            except Exception as e:
                if attempt < self.config.retry_attempts:
                    logger.warning(
                        f"Error on attempt {attempt + 1} for {test_case.test_id}: {e}, retrying..."
                    )
                    await asyncio.sleep(self.config.retry_delay_seconds)
                    continue
                else:
                    execution_time = (time.time() - start_time) * 1000
                    return TestResult(
                        test_case=test_case,
                        execution_time_ms=execution_time,
                        error=str(e),
                        passed=False,
                    )

        # Should not reach here
        execution_time = (time.time() - start_time) * 1000
        return TestResult(
            test_case=test_case,
            execution_time_ms=execution_time,
            error="Max retries exceeded",
            passed=False,
        )

    def _check_test_passed(self, test_case: TestCase, actual_status: int) -> bool:
        """Check if test passed based on expected vs actual status."""
        # For valid tests, expect success status
        if test_case.should_pass:
            return actual_status == test_case.expected_status

        # For invalid tests, expect error status (4xx or 5xx)
        else:
            return actual_status >= 400

    def execute_tests_sync(self, test_cases: List[TestCase]) -> List[TestResult]:
        """
        Synchronous wrapper for test execution (instance method).

        Args:
            test_cases: List of test cases

        Returns:
            List of test results
        """
        return asyncio.run(self.execute_tests(test_cases))


def execute_tests_sync(
    base_url: str, test_cases: List[TestCase], config: ExecutionConfig
) -> List[TestResult]:
    """
    Synchronous wrapper for test execution.

    Args:
        base_url: Base URL of the API
        test_cases: List of test cases
        config: ExecutionConfig instance

    Returns:
        List of test results
    """
    executor = TestExecutor(base_url, config)
    return asyncio.run(executor.execute_tests(test_cases))
