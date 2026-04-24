"""Differential testing against mock servers."""

import httpx
from typing import Dict, Any

class DifferentialTester:
    """Compare API responses across implementations."""

    def __init__(self, primary_url: str, secondary_url: str = None):
        self.primary_url = primary_url
        self.secondary_url = secondary_url

    async def compare_responses(self, method: str, path: str, body: Dict = None) -> Dict[str, Any]:
        """Compare responses from two APIs."""
        async with httpx.AsyncClient() as client:
            primary_resp = await client.request(method, f"{self.primary_url}{path}", json=body)

            if self.secondary_url:
                secondary_resp = await client.request(method, f"{self.secondary_url}{path}", json=body)

                return {
                    "status_match": primary_resp.status_code == secondary_resp.status_code,
                    "body_match": primary_resp.json() == secondary_resp.json(),
                    "latency_diff_ms": abs(primary_resp.elapsed.total_seconds() - secondary_resp.elapsed.total_seconds()) * 1000
                }

        return {"primary_only": True}
