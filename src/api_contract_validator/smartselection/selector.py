"""Smart test selection using ML."""

import subprocess
from typing import List, Set, Dict
from collections import defaultdict

class SmartTestSelector:
    """Select tests based on code changes and historical data."""

    def __init__(self, historical_data_path: str = "./test_history.json"):
        self.historical_data_path = historical_data_path
        self.file_to_endpoint_map = defaultdict(list)
        self.failure_rates = {}

    def analyze_git_diff(self) -> Set[str]:
        """Get changed files from git diff."""
        result = subprocess.run(['git', 'diff', '--name-only', 'HEAD~1'],
                              capture_output=True, text=True)
        return set(result.stdout.strip().split('\n'))

    def select_tests(self, all_tests: List, changed_files: Set[str]) -> List:
        """Select high-priority tests based on changes."""
        # Map files to endpoints
        prioritized = []
        for test in all_tests:
            endpoint_id = test.endpoint.endpoint_id
            priority_score = self._calculate_priority(endpoint_id, changed_files)
            if priority_score > 0.5:
                prioritized.append((test, priority_score))

        prioritized.sort(key=lambda x: x[1], reverse=True)
        return [t[0] for t in prioritized[:int(len(all_tests) * 0.3)]]  # Top 30%

    def _calculate_priority(self, endpoint_id: str, changed_files: Set[str]) -> float:
        """Calculate test priority score."""
        # Check if endpoint's code files were modified
        affected = any(f in changed_files for f in self.file_to_endpoint_map.get(endpoint_id, []))
        failure_rate = self.failure_rates.get(endpoint_id, 0.1)
        return (0.7 if affected else 0.1) + (0.3 * failure_rate)
