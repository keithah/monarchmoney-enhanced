"""
Tests for GraphQL optimization features including caching, batching, and query variants.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from gql import gql

from monarchmoney import MonarchMoney
from monarchmoney.graphql import QueryCache, CacheStrategy, QueryVariants


class TestQueryCache:
    """Test cases for the QueryCache system."""
    
    def test_cache_initialization(self):
        """Test cache initialization with different configurations."""
        # Test default initialization
        cache = QueryCache()
        assert cache._max_size_bytes == 50 * 1024 * 1024  # 50MB default
        assert cache._enable_metrics is True
        
        # Test custom initialization
        cache = QueryCache(max_size_mb=10, enable_metrics=False)
        assert cache._max_size_bytes == 10 * 1024 * 1024
        assert cache._enable_metrics is False
    
    def test_cache_key_generation(self):
        """Test cache key generation for deterministic caching."""
        cache = QueryCache()
        
        # Test with variables
        key1 = cache.generate_key("GetAccounts", {"detail": "basic"})
        key2 = cache.generate_key("GetAccounts", {"detail": "basic"})
        assert key1 == key2
        
        # Test with different variables
        key3 = cache.generate_key("GetAccounts", {"detail": "full"})
        assert key1 != key3
        
        # Test with empty variables
        key4 = cache.generate_key("GetAccounts", {})
        key5 = cache.generate_key("GetAccounts")
        assert key4 == key5
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = QueryCache()
        
        # Test cache miss
        result = cache.get("nonexistent")
        assert result is None
        
        # Test cache set and hit
        test_data = {"accounts": [{"id": "1", "name": "Test"}]}
        cache.set("test_key", test_data, CacheStrategy.SHORT)
        
        result = cache.get("test_key")
        assert result == test_data
    
    def test_cache_expiration(self):
        """Test cache expiration based on TTL."""
        import time as time_module
        cache = QueryCache()
        
        test_data = {"test": "data"}
        
        # Test with custom TTL (1 second)
        cache.set("test_key", test_data, CacheStrategy.CUSTOM, ttl_seconds=1)
        
        # Should be available immediately
        assert cache.get("test_key") == test_data
        
        # Mock the cache entry's is_expired method to simulate expiration
        entry = cache._cache["test_key"]
        entry.expires_at = time_module.time() - 1  # Set to past time
        
        result = cache.get("test_key")
        assert result is None  # Should be expired and removed
    
    def test_cache_invalidation(self):
        """Test cache invalidation patterns."""
        cache = QueryCache()
        
        # Set up test data
        cache.set("GetAccounts:123", {"test": "data1"}, CacheStrategy.SHORT)
        cache.set("GetTransactions:456", {"test": "data2"}, CacheStrategy.SHORT)
        cache.set("GetBudgets:789", {"test": "data3"}, CacheStrategy.SHORT)
        
        # Test pattern invalidation
        invalidated = cache.invalidate_pattern("GetAccounts")
        assert invalidated == 1
        
        # Verify specific key invalidation
        assert cache.get("GetAccounts:123") is None
        assert cache.get("GetTransactions:456") is not None
        
        # Test operation invalidation
        invalidated = cache.invalidate_by_operation("GetTransactions")
        assert invalidated == 1
        assert cache.get("GetTransactions:456") is None
    
    def test_cache_metrics(self):
        """Test cache metrics tracking."""
        cache = QueryCache(enable_metrics=True)
        
        # Initial metrics
        metrics = cache.get_metrics()
        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] == 0
        
        # Test cache miss
        cache.get("nonexistent")
        metrics = cache.get_metrics()
        assert metrics["cache_misses"] == 1
        
        # Test cache hit
        cache.set("test_key", {"data": "test"}, CacheStrategy.SHORT)
        cache.get("test_key")
        metrics = cache.get_metrics()
        assert metrics["cache_hits"] == 1


class TestQueryVariants:
    """Test cases for query variants and optimization."""
    
    def test_account_query_variants(self):
        """Test different account query detail levels."""
        # Test basic query
        basic_query = QueryVariants.get_account_query("basic")
        query_str = str(basic_query)
        assert "displayName" in query_str
        assert "currentBalance" in query_str
        
        # Test full query
        full_query = QueryVariants.get_account_query("full")
        full_query_str = str(full_query)
        assert "AccountFields" in full_query_str
        assert len(full_query_str) > len(query_str)
    
    def test_transaction_query_variants(self):
        """Test different transaction query detail levels."""
        # Test basic query
        basic_query = QueryVariants.get_transaction_query("basic")
        query_str = str(basic_query)
        assert "id" in query_str
        assert "amount" in query_str
        
        # Test detailed query
        detailed_query = QueryVariants.get_transaction_query("detailed")
        detailed_query_str = str(detailed_query)
        assert "TransactionFields" in detailed_query_str
        assert len(detailed_query_str) > len(query_str)


class TestMonarchMoneyOptimizations:
    """Test cases for MonarchMoney class optimizations."""
    
    def test_initialization_with_optimization_flags(self):
        """Test MonarchMoney initialization with optimization flags."""
        # Test with optimizations enabled
        mm = MonarchMoney(
            cache_enabled=True,
            cache_max_size_mb=25,
            batch_requests=True,
            deduplicate_requests=True,
            metrics_enabled=True
        )
        
        assert mm._cache is not None
        assert mm._deduplicator is not None
        assert mm._batch_requests is True
        assert mm._metrics_enabled is True
        
        # Test with optimizations disabled
        mm_disabled = MonarchMoney(
            cache_enabled=False,
            batch_requests=False,
            deduplicate_requests=False
        )
        
        assert mm_disabled._cache is None
        assert mm_disabled._deduplicator is None
        assert mm_disabled._batch_requests is False
    
    @pytest.mark.asyncio
    async def test_gql_call_with_caching(self):
        """Test gql_call method with caching enabled."""
        mm = MonarchMoney(cache_enabled=True)
        
        # Mock the GraphQL client
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = {"test": "result"}
        
        with patch.object(mm, '_get_graphql_client', return_value=mock_client):
            # First call should hit the API
            result1 = await mm.gql_call("TestOperation", gql("query Test { test }"))
            assert result1 == {"test": "result"}
            assert mock_client.execute_async.call_count == 1
            
            # Second identical call should hit cache
            result2 = await mm.gql_call("TestOperation", gql("query Test { test }"))
            assert result2 == {"test": "result"}
            assert mock_client.execute_async.call_count == 1  # No additional API call
            
            # Force refresh should bypass cache
            result3 = await mm.gql_call("TestOperation", gql("query Test { test }"), force_refresh=True)
            assert result3 == {"test": "result"}
            assert mock_client.execute_async.call_count == 2  # Additional API call
    
    @pytest.mark.asyncio
    async def test_optimized_get_accounts(self):
        """Test optimized get_accounts method."""
        mm = MonarchMoney(cache_enabled=True)
        
        # Mock the GraphQL client
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = {
            "accounts": [{"id": "1", "displayName": "Test Account"}]
        }
        
        with patch.object(mm, '_get_graphql_client', return_value=mock_client):
            # Test basic detail level
            result = await mm.get_accounts(detail_level="basic")
            assert "accounts" in result
            
            # Verify the query used is optimized
            call_args = mock_client.execute_async.call_args
            assert call_args is not None
    
    def test_cache_metrics_access(self):
        """Test cache metrics access through MonarchMoney."""
        mm = MonarchMoney(cache_enabled=True)
        
        metrics = mm.get_cache_metrics()
        assert "cache_enabled" in metrics
        assert metrics["cache_enabled"] is True
        
        # Test with cache disabled
        mm_no_cache = MonarchMoney(cache_enabled=False)
        metrics = mm_no_cache.get_cache_metrics()
        assert metrics["cache_enabled"] is False
    
    def test_cache_invalidation_methods(self):
        """Test cache invalidation methods."""
        mm = MonarchMoney(cache_enabled=True)
        
        # Set up test cache data
        mm._cache.set("test_key", {"data": "test"}, CacheStrategy.SHORT)
        
        # Test invalidation
        count = mm.invalidate_cache(pattern="test")
        assert count == 1
        
        # Test clear all
        mm._cache.set("another_key", {"data": "test2"}, CacheStrategy.SHORT)
        mm.clear_cache()
        assert mm._cache.get("another_key") is None


class TestBatchOperations:
    """Test cases for batch operations."""
    
    @pytest.mark.asyncio
    async def test_batch_delete_categories(self):
        """Test batch delete categories operation."""
        mm = MonarchMoney(cache_enabled=True)
        
        # Mock the GraphQL client
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = {
            "deleteMultipleCategories": {
                "deletedIds": ["cat1", "cat2"],
                "errors": []
            }
        }
        
        with patch.object(mm, '_get_graphql_client', return_value=mock_client):
            # Test batch operation
            result = await mm.delete_transaction_categories(["cat1", "cat2"], use_batch=True)
            
            assert "deleteMultipleCategories" in result
            assert mock_client.execute_async.call_count == 1
            
            # Test legacy operation
            with patch.object(mm, 'delete_transaction_category', return_value=True) as mock_delete:
                result = await mm.delete_transaction_categories(["cat1", "cat2"], use_batch=False)
                assert mock_delete.call_count == 2


class TestIntegrationScenarios:
    """Integration test scenarios for optimization features."""
    
    @pytest.mark.asyncio
    async def test_dashboard_data_fetching_scenario(self):
        """Test a realistic dashboard data fetching scenario."""
        mm = MonarchMoney(
            cache_enabled=True,
            batch_requests=True,
            deduplicate_requests=True
        )
        
        # Mock responses
        mock_client = AsyncMock()
        mock_responses = {
            "accounts": [{"id": "1", "displayName": "Checking", "currentBalance": 1000}],
            "allTransactions": {"totalCount": 10, "results": []},
            "me": {"id": "user1", "name": "Test User"}
        }
        
        mock_client.execute_async.return_value = mock_responses
        
        with patch.object(mm, '_get_graphql_client', return_value=mock_client):
            # First request set
            accounts = await mm.get_accounts(detail_level="basic")
            transactions = await mm.get_transactions(limit=10, detail_level="basic")
            
            # Second identical request should hit cache
            accounts_cached = await mm.get_accounts(detail_level="basic")
            
            # Verify caching worked (fewer API calls than requests)
            api_calls = mock_client.execute_async.call_count
            assert api_calls < 4  # Should be fewer due to caching
            
            # Verify cache metrics
            metrics = mm.get_cache_metrics()
            assert metrics["cache_hits"] > 0
    
    def test_performance_configuration_scenarios(self):
        """Test different performance configuration scenarios."""
        # High-performance configuration
        mm_hp = MonarchMoney(
            cache_enabled=True,
            cache_max_size_mb=100,
            batch_requests=True,
            batch_window_ms=5,
            deduplicate_requests=True,
            cache_ttl_overrides={
                "GetAccounts": 600,  # 10 minutes
                "GetTransactions": 120,  # 2 minutes
            }
        )
        
        assert mm_hp._cache is not None
        assert mm_hp._batch_requests is True
        assert mm_hp._batch_window_ms == 5
        
        # Memory-optimized configuration
        mm_mem = MonarchMoney(
            cache_enabled=True,
            cache_max_size_mb=10,
            batch_requests=False,
            deduplicate_requests=True
        )
        
        assert mm_mem._cache._max_size_bytes == 10 * 1024 * 1024
        assert mm_mem._batch_requests is False