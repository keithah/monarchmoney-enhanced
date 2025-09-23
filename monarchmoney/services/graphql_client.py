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
from ..request_deduplicator import RequestDeduplicator
from .base_service import BaseService

if TYPE_CHECKING:
    from ..monarchmoney import MonarchMoney


class GraphQLCache:
    """Enhanced in-memory cache for GraphQL responses with operation-specific TTLs."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: Dict[str, Tuple[Any, float, str]] = {}  # value, timestamp, operation
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }
        # Operation-specific TTLs (in seconds)
        self._operation_ttls = {
            # Static data - long cache times
            "GetTransactionCategories": 3600,  # 1 hour
            "GetInstitutions": 3600,  # 1 hour
            "GetAccountTypeOptions": 3600,  # 1 hour
            "GetMe": 1800,  # 30 minutes

            # Semi-static data - medium cache times
            "GetAccountsBasic": 900,  # 15 minutes (basic info changes less)
            "GetMerchants": 900,  # 15 minutes
            "GetTransactionRules": 900,  # 15 minutes

            # Dynamic data - short cache times
            "GetAccounts": 300,  # 5 minutes (balances change)
            "GetAccountsBalance": 300,  # 5 minutes
            "GetTransactions": 180,  # 3 minutes
            "GetHoldings": 180,  # 3 minutes
        }

    def _get_ttl_for_operation(self, operation: str) -> int:
        """Get TTL for a specific operation."""
        return self._operation_ttls.get(operation, self.default_ttl)

    def _is_expired(self, timestamp: float, operation: str) -> bool:
        """Check if cache entry is expired based on operation-specific TTL."""
        ttl = self._get_ttl_for_operation(operation)
        return time.time() - timestamp > ttl

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        expired_keys = []
        for key, (_, timestamp, operation) in self.cache.items():
            if self._is_expired(timestamp, operation):
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]
            self._metrics["expirations"] += 1

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
            result, timestamp, cached_operation = self.cache[key]
            if not self._is_expired(timestamp, cached_operation):
                self._metrics["hits"] += 1
                return result
            else:
                del self.cache[key]
                self._metrics["expirations"] += 1

        self._metrics["misses"] += 1
        return None

    def set(
        self,
        operation: str,
        query: DocumentNode,
        variables: Optional[Dict[str, Any]],
        result: Any,
    ) -> None:
        """Cache a result with operation-specific TTL."""
        # Cleanup if cache is getting too large
        if len(self.cache) >= self.max_size:
            self._cleanup_expired()
            # If still too large, remove oldest entries
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest_key]
                self._metrics["evictions"] += 1

        key = self._make_key(operation, query, variables)
        self.cache[key] = (result, time.time(), operation)

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        # Reset metrics except for cumulative counters
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        total_requests = self._metrics["hits"] + self._metrics["misses"]
        hit_rate = 0.0
        if total_requests > 0:
            hit_rate = (self._metrics["hits"] / total_requests) * 100

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self._metrics["hits"],
            "misses": self._metrics["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "evictions": self._metrics["evictions"],
            "expirations": self._metrics["expirations"],
            "total_requests": total_requests,
        }


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

        # Request deduplication for concurrent identical requests
        self.request_deduplicator = RequestDeduplicator(timeout=30.0)

        # Rate limiting
        self.last_request_time = 0.0
        self.min_request_interval = 0.1  # seconds between requests

        # Enhanced connection pooling
        self._gql_client: Optional[Client] = None
        self._transport: Optional[AIOHTTPTransport] = None
        self._connection_pool_size = 10  # Maximum concurrent connections
        self._connection_timeout = 30  # Connection timeout in seconds
        self._keepalive_timeout = 30  # Keep connections alive for reuse

    async def _get_client(self) -> Client:
        """Get or create GraphQL client with connection pooling."""
        if self._gql_client is None:
            from ..monarchmoney import MonarchMoneyEndpoints
            import aiohttp

            # Create connector with optimized connection pooling
            connector = aiohttp.TCPConnector(
                limit=self._connection_pool_size,
                limit_per_host=self._connection_pool_size,
                keepalive_timeout=self._keepalive_timeout,
                enable_cleanup_closed=True,
                force_close=False,
                ttl_dns_cache=300,  # DNS cache for 5 minutes
            )

            self._transport = AIOHTTPTransport(
                url=MonarchMoneyEndpoints.getGraphQL(),
                headers=self.client._headers,
                timeout=self._connection_timeout,
                connector=connector,
            )

            self._gql_client = Client(
                transport=self._transport,
                fetch_schema_from_transport=False,
            )

            self.logger.debug(
                "Created GraphQL client with connection pooling",
                pool_size=self._connection_pool_size,
                keepalive_timeout=self._keepalive_timeout,
            )

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

            # Use request deduplication for concurrent identical requests
            async def _execute_request():
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

                    self.logger.debug("GraphQL operation completed", operation=operation)
                    return result

                finally:
                    # Restore original timeout
                    if timeout and self._transport:
                        self._transport.timeout = original_timeout

            # Deduplicate the request
            result = await self.request_deduplicator.deduplicate_request(
                operation, _execute_request, variables
            )

            # Cache successful read-only results
            if use_cache and self._should_cache(operation):
                self.cache.set(operation, query, variables, result)

            return result

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

        connection_stats = {}
        if self._transport and hasattr(self._transport, '_session'):
            connector = getattr(self._transport._session, '_connector', None)
            if connector:
                connection_stats = {
                    "total_connections": len(connector._conns),
                    "pool_size": self._connection_pool_size,
                    "keepalive_timeout": self._keepalive_timeout,
                }

        return {
            "operations": stats,
            "slow_operations": self.performance_monitor.get_slow_operations(),
            "cache": self.cache.get_metrics(),
            "deduplication": self.request_deduplicator.get_stats(),
            "connection_pool": connection_stats,
        }

    def clear_cache(self) -> None:
        """Clear the operation cache."""
        self.cache.clear()
        self.logger.info("GraphQL cache cleared")

    async def close(self) -> None:
        """Clean up resources including connection pool."""
        if self._transport:
            # Close the transport which will close the underlying session and connector
            await self._transport.close()
            self.logger.debug("Closed GraphQL client and connection pool")

        self._gql_client = None
        self._transport = None
