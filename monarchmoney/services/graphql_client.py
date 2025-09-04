"""
GraphQL client service for MonarchMoney Enhanced.

Provides optimized GraphQL operations with caching, retry logic, and performance monitoring.
"""

import asyncio
import hashlib
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from graphql import DocumentNode

from ..exceptions import GraphQLError, NetworkError, RateLimitError, ServerError
from ..logging_config import MonarchLogger
from .base_service import BaseService

if TYPE_CHECKING:
    from ..monarchmoney import MonarchMoney


class GraphQLCache:
    """Simple in-memory cache for GraphQL responses."""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl

    def _is_expired(self, timestamp: float) -> bool:
        return time.time() - timestamp > self.ttl

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]

    def _make_key(
        self, operation: str, query: DocumentNode, variables: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key from operation details."""
        query_str = str(query)
        variables_str = str(sorted(variables.items())) if variables else ""
        key_data = f"{operation}:{query_str}:{variables_str}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    def get(
        self, operation: str, query: DocumentNode, variables: Optional[Dict[str, Any]]
    ) -> Optional[Any]:
        """Get cached result if available and not expired."""
        key = self._make_key(operation, query, variables)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if not self._is_expired(timestamp):
                return result
            else:
                del self.cache[key]
        return None

    def set(
        self,
        operation: str,
        query: DocumentNode,
        variables: Optional[Dict[str, Any]],
        result: Any,
    ) -> None:
        """Cache a result."""
        # Cleanup if cache is getting too large
        if len(self.cache) >= self.max_size:
            self._cleanup_expired()
            # If still too large, remove oldest entries
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest_key]

        key = self._make_key(operation, query, variables)
        self.cache[key] = (result, time.time())

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()


class PerformanceMonitor:
    """Monitor GraphQL operation performance."""

    def __init__(self):
        self.operations: Dict[str, List[float]] = {}
        self.slow_operations: List[Tuple[str, float, Dict[str, Any]]] = []
        self.slow_threshold = 2.0  # seconds

    def record_operation(
        self,
        operation: str,
        duration: float,
        variables: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record operation timing."""
        if operation not in self.operations:
            self.operations[operation] = []

        self.operations[operation].append(duration)

        # Keep only last 100 measurements per operation
        if len(self.operations[operation]) > 100:
            self.operations[operation] = self.operations[operation][-100:]

        # Track slow operations
        if duration > self.slow_threshold:
            self.slow_operations.append((operation, duration, variables or {}))
            # Keep only last 50 slow operations
            if len(self.slow_operations) > 50:
                self.slow_operations = self.slow_operations[-50:]

    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get performance statistics for an operation."""
        if operation not in self.operations:
            return {}

        durations = self.operations[operation]
        return {
            "count": len(durations),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "p95_duration": (
                sorted(durations)[int(0.95 * len(durations))] if durations else 0
            ),
        }

    def get_slow_operations(
        self, limit: int = 10
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Get recent slow operations."""
        return sorted(self.slow_operations, key=lambda x: x[1], reverse=True)[:limit]


class GraphQLClient(BaseService):
    """
    Advanced GraphQL client with caching, performance monitoring, and retry logic.
    """

    def __init__(self, monarch_client: "MonarchMoney"):
        super().__init__(monarch_client)
        self.logger = MonarchLogger("GraphQLClient")

        # Performance and caching
        self.cache = GraphQLCache()
        self.performance_monitor = PerformanceMonitor()

        # Rate limiting
        self.last_request_time = 0.0
        self.min_request_interval = 0.1  # seconds between requests

        # Connection pooling
        self._gql_client: Optional[Client] = None
        self._transport: Optional[AIOHTTPTransport] = None

    async def _get_client(self) -> Client:
        """Get or create GraphQL client with connection pooling."""
        if self._gql_client is None:
            from ..monarchmoney import MonarchMoneyEndpoints

            self._transport = AIOHTTPTransport(
                url=MonarchMoneyEndpoints.getGraphQL(),
                headers=self.client._headers,
                timeout=self.client._timeout,
            )

            self._gql_client = Client(
                transport=self._transport,
                fetch_schema_from_transport=False,
            )

            self.logger.debug("Created new GraphQL client")

        return self._gql_client

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()

    def _should_cache(self, operation: str) -> bool:
        """Determine if an operation should be cached."""
        # Cache read-only operations, not mutations
        read_only_operations = {
            "GetAccounts",
            "GetTransactions",
            "GetCategories",
            "GetMe",
            "GetMerchants",
            "GetInstitutions",
            "GetBudgets",
            "GetGoals",
            "GetTransactionRules",
            "GetHoldings",
            "GetInsights",
        }
        return operation in read_only_operations

    async def execute_query(
        self,
        operation: str,
        query: DocumentNode,
        variables: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute GraphQL query with caching, monitoring, and error handling.

        Args:
            operation: Operation name for logging/monitoring
            query: GraphQL query document
            variables: Query variables
            use_cache: Whether to use caching for this query
            timeout: Optional timeout override

        Returns:
            GraphQL response data

        Raises:
            GraphQLError: If GraphQL execution fails
            NetworkError: If network request fails
            RateLimitError: If rate limited
        """
        start_time = time.time()

        try:
            # Check cache first for read-only operations
            if use_cache and self._should_cache(operation):
                cached_result = self.cache.get(operation, query, variables)
                if cached_result is not None:
                    self.logger.debug("Cache hit", operation=operation)
                    return cached_result

            # Rate limiting
            await self._rate_limit()

            # Execute query
            client = await self._get_client()

            # Update timeout if specified
            if timeout and self._transport:
                original_timeout = self._transport.timeout
                self._transport.timeout = timeout

            try:
                self.logger.debug("Executing GraphQL operation", operation=operation)

                if variables:
                    result = await client.execute_async(
                        query, variable_values=variables
                    )
                else:
                    result = await client.execute_async(query)

                # Cache successful read-only results
                if use_cache and self._should_cache(operation):
                    self.cache.set(operation, query, variables, result)

                self.logger.debug("GraphQL operation completed", operation=operation)
                return result

            finally:
                # Restore original timeout
                if timeout and self._transport:
                    self._transport.timeout = original_timeout

        except Exception as e:
            error_msg = str(e).lower()

            # Convert to appropriate exception types
            if "rate limit" in error_msg or "429" in error_msg:
                raise RateLimitError(f"Rate limited: {str(e)}")
            elif "timeout" in error_msg:
                raise NetworkError(f"Request timeout: {str(e)}")
            elif "network" in error_msg or "connection" in error_msg:
                raise NetworkError(f"Network error: {str(e)}")
            elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
                raise ServerError(f"Server error: {str(e)}")
            else:
                raise GraphQLError(f"GraphQL error: {str(e)}")

        finally:
            # Record performance metrics
            duration = time.time() - start_time
            self.performance_monitor.record_operation(operation, duration, variables)

            if duration > self.performance_monitor.slow_threshold:
                self.logger.warning(
                    "Slow GraphQL operation detected",
                    operation=operation,
                    duration=duration,
                    variables=variables,
                )

    async def execute_batch(
        self,
        operations: List[Tuple[str, DocumentNode, Optional[Dict[str, Any]]]],
        max_concurrent: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple GraphQL operations concurrently.

        Args:
            operations: List of (operation_name, query, variables) tuples
            max_concurrent: Maximum concurrent operations

        Returns:
            List of results in the same order as operations
        """
        self.logger.info("Executing batch GraphQL operations", count=len(operations))

        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_single(
            op_data: Tuple[str, DocumentNode, Optional[Dict[str, Any]]],
        ) -> Dict[str, Any]:
            operation, query, variables = op_data
            async with semaphore:
                return await self.execute_query(operation, query, variables)

        tasks = [execute_single(op) for op in operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions back to regular exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                operation_name = operations[i][0]
                self.logger.error(
                    "Batch operation failed",
                    operation=operation_name,
                    error=str(result),
                )
                raise result
            final_results.append(result)

        return final_results

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all operations."""
        stats = {}
        for operation in self.performance_monitor.operations:
            stats[operation] = self.performance_monitor.get_stats(operation)

        return {
            "operations": stats,
            "slow_operations": self.performance_monitor.get_slow_operations(),
            "cache_size": len(self.cache.cache),
        }

    def clear_cache(self) -> None:
        """Clear the operation cache."""
        self.cache.clear()
        self.logger.info("GraphQL cache cleared")

    async def close(self) -> None:
        """Close the GraphQL client and cleanup resources."""
        if self._transport:
            await self._transport.close()
            self._transport = None
            self._gql_client = None
            self.logger.debug("GraphQL client closed")
