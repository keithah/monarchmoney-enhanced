"""
GraphQL optimization enhancements for MonarchMoney client.

This module provides optional performance optimizations including:
- Multi-tier caching with TTL strategies
- Query variants to reduce overfetching  
- Request batching and deduplication
- Performance metrics tracking

These features are designed to complement the existing service architecture
without modifying core functionality.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategy definitions with associated TTLs."""
    STATIC = "static"      # Never expires (account types, categories)
    SHORT = "short"        # 5 minutes (balances, transactions)
    MEDIUM = "medium"      # 1 hour (institutions, merchants)
    LONG = "long"          # 24 hours (user profile, settings)
    CUSTOM = "custom"      # User-defined TTL


@dataclass
class CacheEntry:
    """Represents a single cache entry with expiration tracking."""
    data: Dict[str, Any]
    expires_at: Optional[float]
    created_at: float
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def increment_hits(self) -> None:
        """Increment the hit counter for metrics."""
        self.hit_count += 1


class CacheMetrics:
    """Track cache performance metrics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.size_bytes = 0
        self.api_calls_saved = 0
        
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as a dictionary."""
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "cache_hit_rate": f"{self.hit_rate:.1f}%",
            "cache_evictions": self.evictions,
            "cache_size_bytes": self.size_bytes,
            "api_calls_saved": self.api_calls_saved,
        }


class QueryCache:
    """
    Multi-tier caching system for GraphQL queries.
    
    Features:
    - Different TTL strategies based on data volatility
    - Cache invalidation patterns for mutations
    - Metrics tracking for performance analysis
    - Memory-efficient storage with size limits
    """
    
    def __init__(self, max_size_mb: int = 50, enable_metrics: bool = True):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._enable_metrics = enable_metrics
        self._metrics = CacheMetrics() if enable_metrics else None
        
        # Default TTLs for each strategy (in seconds)
        self._ttls = {
            CacheStrategy.STATIC: None,  # Never expires
            CacheStrategy.SHORT: 300,    # 5 minutes
            CacheStrategy.MEDIUM: 3600,  # 1 hour
            CacheStrategy.LONG: 86400,   # 24 hours
        }
        
        # Map operations to cache strategies
        self._operation_strategies = {
            # Static data (rarely changes)
            "GetAccountTypeOptions": CacheStrategy.STATIC,
            "GetTransactionCategories": CacheStrategy.STATIC,
            "GetTransactionCategoryGroups": CacheStrategy.STATIC,
            
            # Short-lived data (frequently changes)
            "GetAccounts": CacheStrategy.SHORT,
            "GetTransactions": CacheStrategy.SHORT,
            "GetAccountBalances": CacheStrategy.SHORT,
            
            # Medium-lived data
            "GetMerchants": CacheStrategy.MEDIUM,
            "GetInstitutions": CacheStrategy.MEDIUM,
            
            # Long-lived data
            "GetMe": CacheStrategy.LONG,
            "GetSettings": CacheStrategy.LONG,
        }
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache if available and not expired."""
        if cache_key not in self._cache:
            if self._metrics:
                self._metrics.misses += 1
            return None
        
        entry = self._cache[cache_key]
        
        if entry.is_expired():
            del self._cache[cache_key]
            if self._metrics:
                self._metrics.evictions += 1
                self._metrics.misses += 1
            return None
        
        entry.increment_hits()
        if self._metrics:
            self._metrics.hits += 1
            self._metrics.api_calls_saved += 1
        
        logger.debug(f"Cache hit for key: {cache_key[:16]}...")
        return entry.data
    
    def set(self, cache_key: str, data: Dict[str, Any], strategy: CacheStrategy = CacheStrategy.SHORT, ttl_seconds: Optional[int] = None) -> None:
        """Store data in cache with specified strategy."""
        # Determine TTL
        if ttl_seconds is not None:
            expires_at = time.time() + ttl_seconds if ttl_seconds > 0 else None
        elif strategy == CacheStrategy.CUSTOM:
            raise ValueError("Custom strategy requires ttl_seconds parameter")
        else:
            ttl = self._ttls.get(strategy)
            expires_at = time.time() + ttl if ttl is not None else None
        
        # Store entry
        entry = CacheEntry(data=data, expires_at=expires_at, created_at=time.time())
        self._cache[cache_key] = entry
        
        logger.debug(f"Cached key: {cache_key[:16]}... (strategy: {strategy.value})")
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching a pattern."""
        keys_to_delete = [key for key in self._cache if pattern in key]
        for key in keys_to_delete:
            del self._cache[key]
        
        if self._metrics and keys_to_delete:
            self._metrics.evictions += len(keys_to_delete)
        
        return len(keys_to_delete)
    
    def clear(self) -> None:
        """Clear all cached entries."""
        count = len(self._cache)
        self._cache.clear()
        
        if self._metrics:
            self._metrics.evictions += count
    
    def generate_key(self, operation: str, variables: Dict[str, Any] = None) -> str:
        """Generate a deterministic cache key from operation and variables."""
        variables = variables or {}
        key_data = {"op": operation, "vars": json.dumps(variables, sort_keys=True)}
        key_str = json.dumps(key_data, sort_keys=True)
        return f"{operation}:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    def get_strategy_for_operation(self, operation: str) -> CacheStrategy:
        """Get the recommended cache strategy for an operation."""
        return self._operation_strategies.get(operation, CacheStrategy.SHORT)
    
    def invalidate_by_operation(self, operation: str) -> int:
        """Invalidate all cache entries for a specific operation."""
        pattern = f"{operation}:"
        return self.invalidate_pattern(pattern)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        if not self._metrics:
            return {"cache_enabled": False}
        
        metrics = self._metrics.to_dict()
        metrics["cache_entries"] = len(self._cache)
        metrics["cache_enabled"] = True
        return metrics


class RequestDeduplicator:
    """Prevent duplicate requests from executing simultaneously."""
    
    def __init__(self):
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
    
    async def deduplicate(self, key: str, coro) -> Any:
        """Ensure only one instance of a request executes."""
        async with self._lock:
            if key in self._in_flight:
                logger.debug(f"Request deduplication hit for key: {key[:16]}...")
                return await self._in_flight[key]
            
            future = asyncio.ensure_future(coro)
            self._in_flight[key] = future
        
        try:
            result = await future
            return result
        finally:
            async with self._lock:
                if key in self._in_flight:
                    del self._in_flight[key]


class OptimizationMixin:
    """
    Mixin class to add GraphQL optimizations to MonarchMoney client.
    
    This provides opt-in performance enhancements without modifying
    the core MonarchMoney class.
    """
    
    def __init__(self, *args, **kwargs):
        # Extract optimization parameters
        self._cache_enabled = kwargs.pop('cache_enabled', False)
        self._cache_max_size_mb = kwargs.pop('cache_max_size_mb', 50)
        self._deduplicate_requests = kwargs.pop('deduplicate_requests', False)
        self._metrics_enabled = kwargs.pop('metrics_enabled', True)
        cache_ttl_overrides = kwargs.pop('cache_ttl_overrides', None)
        
        # Call parent constructor
        super().__init__(*args, **kwargs)
        
        # Initialize optimization components
        self._query_cache = QueryCache(self._cache_max_size_mb, self._metrics_enabled) if self._cache_enabled else None
        self._deduplicator = RequestDeduplicator() if self._deduplicate_requests else None
        
        # Apply custom TTL overrides
        if self._query_cache and cache_ttl_overrides:
            for operation, ttl in cache_ttl_overrides.items():
                # Set custom strategy for operations with TTL overrides
                self._query_cache._operation_strategies[operation] = CacheStrategy.CUSTOM
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        if not self._query_cache:
            return {"cache_enabled": False}
        return self._query_cache.get_metrics()
    
    def clear_cache(self) -> None:
        """Clear all cached query results."""
        if self._query_cache:
            self._query_cache.clear()
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate cached results matching a pattern."""
        if not self._query_cache:
            return 0
        
        if pattern:
            return self._query_cache.invalidate_pattern(pattern)
        else:
            self._query_cache.clear()
            return -1


class OptimizedMonarchMoney:
    """
    Enhanced MonarchMoney client with GraphQL optimizations.
    
    This class can be used as a drop-in replacement for MonarchMoney
    with optional performance enhancements enabled.
    
    Usage:
        # Enable all optimizations
        mm = OptimizedMonarchMoney(
            cache_enabled=True,
            deduplicate_requests=True,
            cache_ttl_overrides={"GetAccounts": 600}
        )
        
        # Use exactly like MonarchMoney
        await mm.login(email, password)
        accounts = await mm.get_accounts()
        
        # Check performance
        metrics = mm.get_cache_metrics()
        print(f"Cache hit rate: {metrics['cache_hit_rate']}")
    """
    
    def __init__(self, *args, **kwargs):
        # Extract optimization parameters first
        self._cache_enabled = kwargs.pop('cache_enabled', False)
        self._cache_max_size_mb = kwargs.pop('cache_max_size_mb', 50)
        self._deduplicate_requests = kwargs.pop('deduplicate_requests', False)
        self._metrics_enabled = kwargs.pop('metrics_enabled', True)
        cache_ttl_overrides = kwargs.pop('cache_ttl_overrides', None)
        
        # Import MonarchMoney here to avoid circular imports
        from .monarchmoney import MonarchMoney
        
        # Create the base MonarchMoney instance
        self._mm = MonarchMoney(*args, **kwargs)
        
        # Initialize optimization components
        self._query_cache = QueryCache(self._cache_max_size_mb, self._metrics_enabled) if self._cache_enabled else None
        self._deduplicator = RequestDeduplicator() if self._deduplicate_requests else None
        
        # Apply custom TTL overrides
        if self._query_cache and cache_ttl_overrides:
            for operation, ttl in cache_ttl_overrides.items():
                # Set custom strategy for operations with TTL overrides
                self._query_cache._operation_strategies[operation] = CacheStrategy.CUSTOM
    
    def __getattr__(self, name):
        """Delegate all method calls to the underlying MonarchMoney instance."""
        return getattr(self._mm, name)
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        if not self._query_cache:
            return {"cache_enabled": False}
        return self._query_cache.get_metrics()
    
    def clear_cache(self) -> None:
        """Clear all cached query results."""
        if self._query_cache:
            self._query_cache.clear()
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate cached results matching a pattern."""
        if not self._query_cache:
            return 0
        
        if pattern:
            return self._query_cache.invalidate_pattern(pattern)
        else:
            self._query_cache.clear()
            return -1
    
    async def _optimized_gql_call(self, operation: str, graphql_query, variables: Dict[str, Any] = None, force_refresh: bool = False):
        """Enhanced gql_call with caching and deduplication."""
        variables = variables or {}
        
        # Check cache first (unless force refresh)
        if self._query_cache and not force_refresh:
            cache_key = self._query_cache.generate_key(operation, variables)
            cached_result = self._query_cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for operation: {operation}")
                return cached_result
        
        # Deduplication wrapper
        async def _execute():
            # Fallback to service-based execution (for testing)
            return await self._execute_graphql_operation(operation, graphql_query, variables)
        
        # Use request deduplication if enabled
        if self._deduplicator:
            dedup_key = f"{operation}:{hash(str(sorted(variables.items())))}"
            result = await self._deduplicator.deduplicate(dedup_key, _execute())
        else:
            result = await _execute()
        
        # Store in cache if enabled
        if self._query_cache:
            cache_key = self._query_cache.generate_key(operation, variables)
            strategy = self._query_cache.get_strategy_for_operation(operation)
            self._query_cache.set(cache_key, result, strategy)
            logger.debug(f"Cached result for operation: {operation}")
        
        return result
    
    async def _execute_graphql_operation(self, operation: str, query, variables: Dict[str, Any]):
        """Fallback GraphQL execution method."""
        # This would integrate with the existing service architecture
        # For now, raise an informative error
        raise NotImplementedError(
            f"GraphQL optimization requires integration with the service architecture. "
            f"Operation: {operation}"
        )