"""
Behavioral Drift Detector

Detects logical inconsistencies and unexpected behavior patterns in API responses.
"""

from collections import defaultdict
from typing import Any, Dict, List, Set

from api_contract_validator.analysis.drift.models import (
    BehavioralDriftIssue,
    DriftSeverity,
)
from api_contract_validator.config.logging import get_logger
from api_contract_validator.execution.collector.result_collector import ExecutionSummary

logger = get_logger("api_contract_validator.analyzer")


class BehavioralDriftDetector:
    """
    Detects behavioral drift by analyzing response patterns and
    identifying inconsistencies.
    """

    def detect(self, execution_summary: ExecutionSummary) -> List[BehavioralDriftIssue]:
        """
        Detect behavioral drift from test execution results.

        Behavioral drift includes:
        - Inconsistent responses for equivalent tests
        - Unexpected null values
        - Extra/missing fields across responses
        - Response structure anomalies

        Args:
            execution_summary: Test execution results

        Returns:
            List of behavioral drift issues
        """
        logger.info("Starting behavioral drift detection")
        drift_issues: List[BehavioralDriftIssue] = []

        # Group responses by endpoint for comparison
        endpoint_responses: Dict[str, List] = defaultdict(list)
        for result in execution_summary.results:
            if result.passed and result.response_body:
                endpoint_id = result.test_case.endpoint.endpoint_id
                endpoint_responses[endpoint_id].append(result)

        # Analyze each endpoint's response patterns
        for endpoint_id, results in endpoint_responses.items():
            if len(results) < 2:
                continue  # Need multiple responses to detect inconsistencies

            # Detect null value anomalies
            null_issues = self._detect_unexpected_nulls(endpoint_id, results)
            drift_issues.extend(null_issues)

            # Detect field presence inconsistencies
            field_issues = self._detect_field_inconsistencies(endpoint_id, results)
            drift_issues.extend(field_issues)

            # Detect response structure variations
            structure_issues = self._detect_structure_variations(endpoint_id, results)
            drift_issues.extend(structure_issues)

        logger.info(f"Behavioral drift detection complete: {len(drift_issues)} issues found")
        return drift_issues

    def _detect_unexpected_nulls(self, endpoint_id: str, results: List) -> List[BehavioralDriftIssue]:
        """Detect fields that are sometimes null when they shouldn't be."""
        issues = []
        field_null_status: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"null": 0, "non_null": 0}
        )

        # Track null/non-null occurrences for each field
        for result in results:
            self._track_null_status(result.response_body, "", field_null_status)

        # Find fields that are inconsistently null
        for field_path, status in field_null_status.items():
            null_count = status["null"]
            non_null_count = status["non_null"]
            total = null_count + non_null_count

            # If field is null in some responses but not others, flag it
            if null_count > 0 and non_null_count > 0:
                null_percentage = (null_count / total) * 100

                issue = BehavioralDriftIssue(
                    endpoint_id=endpoint_id,
                    test_ids=[r.test_case.test_id for r in results],
                    anomaly_type="inconsistent_null_values",
                    description=(
                        f"Field '{field_path}' is null in {null_percentage:.1f}% of responses "
                        f"({null_count}/{total}), indicating inconsistent behavior"
                    ),
                    evidence={
                        "field_path": field_path,
                        "null_count": null_count,
                        "non_null_count": non_null_count,
                        "null_percentage": null_percentage,
                    },
                    severity=DriftSeverity.MEDIUM if null_percentage > 30 else DriftSeverity.LOW,
                )
                issues.append(issue)

        return issues

    def _detect_field_inconsistencies(
        self, endpoint_id: str, results: List
    ) -> List[BehavioralDriftIssue]:
        """Detect fields that appear in some responses but not others."""
        issues = []

        # Collect all fields seen across responses
        all_fields: Dict[str, int] = defaultdict(int)
        for result in results:
            fields = self._get_all_field_paths(result.response_body, "")
            for field in fields:
                all_fields[field] += 1

        total_responses = len(results)

        # Find fields that don't appear in all responses
        for field_path, count in all_fields.items():
            if 0 < count < total_responses:
                presence_percentage = (count / total_responses) * 100

                issue = BehavioralDriftIssue(
                    endpoint_id=endpoint_id,
                    test_ids=[r.test_case.test_id for r in results],
                    anomaly_type="inconsistent_field_presence",
                    description=(
                        f"Field '{field_path}' appears in only {presence_percentage:.1f}% "
                        f"of responses ({count}/{total_responses})"
                    ),
                    evidence={
                        "field_path": field_path,
                        "present_count": count,
                        "total_responses": total_responses,
                        "presence_percentage": presence_percentage,
                    },
                    severity=DriftSeverity.LOW,
                )
                issues.append(issue)

        return issues

    def _detect_structure_variations(
        self, endpoint_id: str, results: List
    ) -> List[BehavioralDriftIssue]:
        """Detect variations in response structure."""
        issues = []

        if len(results) < 2:
            return issues

        # Compare structure types across responses
        structure_signatures = []
        for result in results:
            signature = self._get_structure_signature(result.response_body)
            structure_signatures.append(signature)

        # If all signatures are not identical, there's structural drift
        unique_signatures = set(structure_signatures)
        if len(unique_signatures) > 1:
            issue = BehavioralDriftIssue(
                endpoint_id=endpoint_id,
                test_ids=[r.test_case.test_id for r in results],
                anomaly_type="response_structure_variation",
                description=(
                    f"Response structure varies across tests. "
                    f"Found {len(unique_signatures)} different structures in {len(results)} responses"
                ),
                evidence={
                    "unique_structures": len(unique_signatures),
                    "total_responses": len(results),
                    "structures": list(unique_signatures)[:3],  # Show first 3 examples
                },
                severity=DriftSeverity.MEDIUM,
            )
            issues.append(issue)

        return issues

    def _track_null_status(
        self, data: Any, path_prefix: str, field_status: Dict[str, Dict[str, int]]
    ) -> None:
        """Recursively track null status of all fields."""
        if isinstance(data, dict):
            for key, value in data.items():
                field_path = f"{path_prefix}.{key}" if path_prefix else key
                if value is None:
                    field_status[field_path]["null"] += 1
                else:
                    field_status[field_path]["non_null"] += 1
                    # Recurse into nested structures
                    if isinstance(value, (dict, list)):
                        self._track_null_status(value, field_path, field_status)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._track_null_status(item, f"{path_prefix}[]", field_status)

    def _get_all_field_paths(self, data: Any, path_prefix: str) -> Set[str]:
        """Get all field paths in a data structure."""
        fields = set()

        if isinstance(data, dict):
            for key, value in data.items():
                field_path = f"{path_prefix}.{key}" if path_prefix else key
                fields.add(field_path)

                # Recurse into nested structures
                if isinstance(value, (dict, list)):
                    nested_fields = self._get_all_field_paths(value, field_path)
                    fields.update(nested_fields)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    nested_fields = self._get_all_field_paths(item, f"{path_prefix}[]")
                    fields.update(nested_fields)

        return fields

    def _get_structure_signature(self, data: Any) -> str:
        """Generate a signature representing the structure of the data."""
        if data is None:
            return "null"
        elif isinstance(data, dict):
            if not data:
                return "dict[empty]"
            fields = []
            for key in sorted(data.keys()):
                value_sig = self._get_structure_signature(data[key])
                fields.append(f"{key}:{value_sig}")
            return f"dict[{','.join(fields[:5])}]"  # Limit to 5 fields for readability
        elif isinstance(data, list):
            if not data:
                return "list[empty]"
            item_sig = self._get_structure_signature(data[0])
            return f"list[{item_sig}]"
        elif isinstance(data, bool):
            return "bool"
        elif isinstance(data, int):
            return "int"
        elif isinstance(data, float):
            return "float"
        elif isinstance(data, str):
            return "str"
        else:
            return type(data).__name__
