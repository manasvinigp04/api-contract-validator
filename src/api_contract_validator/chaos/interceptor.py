"""Chaos testing fault injection."""

import asyncio
import random
from typing import Optional
import httpx

class ChaosInterceptor:
    """Inject faults into HTTP requests."""

    def __init__(self, latency_ms: int = 0, failure_rate: float = 0.0, timeout_rate: float = 0.0):
        self.latency_ms = latency_ms
        self.failure_rate = failure_rate
        self.timeout_rate = timeout_rate

    async def intercept(self, request: httpx.Request) -> Optional[httpx.Response]:
        """Apply chaos before request."""
        # Inject latency
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)

        # Inject failure
        if random.random() < self.failure_rate:
            return httpx.Response(503, text="Chaos: Service Unavailable")

        # Inject timeout
        if random.random() < self.timeout_rate:
            await asyncio.sleep(100)  # Trigger timeout

        return None  # Proceed normally
