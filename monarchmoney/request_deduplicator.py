"""
Request deduplication for MonarchMoney Enhanced.

Prevents duplicate concurrent API calls by caching in-flight requests.
"""

import asyncio
import hashlib
import time
from typing import Any, Dict, Optional

from .logging_config import logger


class RequestDeduplicator:
    """
    Deduplicates concurrent identical API requests.

    When multiple parts of the application request the same data simultaneously,
    only one actual API call is made and the result is shared.
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize the request deduplicator.

        Args:
            timeout: Maximum time to wait for a pending request (seconds)
        """
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._timeout = timeout
        self.stats = {
            "requests_deduplicated": 0,
            "api_calls_saved": 0,
            "total_requests": 0
        }

    def _make_key(self, operation: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for the request."""
        key_data = f"{operation}:{variables or {}}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    async def deduplicate_request(self, operation: str, request_func, variables: Optional[Dict[str, Any]] = None):
        """
        Deduplicate a request by operation and variables.

        Args:
            operation: The GraphQL operation name
            request_func: Async function that makes the actual API call
            variables: GraphQL variables

        Returns:
            The result of the API call (from cache or fresh request)
        """
        cache_key = self._make_key(operation, variables)
        self.stats["total_requests"] += 1

        # Check if there's already a pending request for this exact operation
        if cache_key in self._pending_requests:
            logger.debug("Deduplicating request", operation=operation, cache_key=cache_key)
            self.stats["requests_deduplicated"] += 1
            self.stats["api_calls_saved"] += 1

            # Wait for the existing request to complete
            try:
                result = await asyncio.wait_for(
                    self._pending_requests[cache_key],
                    timeout=self._timeout
                )
                return result
            except asyncio.TimeoutError:
                logger.warning("Deduplicated request timed out", operation=operation)
                # Remove the timed-out request and fall through to make a new one
                self._pending_requests.pop(cache_key, None)

        # Create a new request
        future = asyncio.create_task(self._execute_request(request_func))
        self._pending_requests[cache_key] = future

        try:
            result = await future
            return result
        finally:
            # Clean up the completed request
            self._pending_requests.pop(cache_key, None)

    async def _execute_request(self, request_func):
        """Execute the actual request function."""
        return await request_func()

    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        stats = self.stats.copy()
        if stats["total_requests"] > 0:
            stats["deduplication_rate"] = round(
                (stats["requests_deduplicated"] / stats["total_requests"]) * 100, 2
            )
        else:
            stats["deduplication_rate"] = 0.0
        return stats

    def clear_stats(self):
        """Reset statistics."""
        self.stats = {
            "requests_deduplicated": 0,
            "api_calls_saved": 0,
            "total_requests": 0
        }