"""
Example demonstrating GraphQL optimizations in the MonarchMoney library.

This example shows how to use the new optimization features including:
- Query variants to reduce overfetching
- Caching to reduce API calls
- Batch operations for bulk actions
- Performance metrics tracking
"""

import asyncio
import time
from monarchmoney import MonarchMoney


async def basic_usage_example():
    """Basic usage with optimizations enabled."""
    print("=== Basic Usage with Optimizations ===")
    
    # Initialize with optimizations enabled
    mm = MonarchMoney(
        cache_enabled=True,
        cache_max_size_mb=50,
        batch_requests=True,
        deduplicate_requests=True,
        metrics_enabled=True,
        cache_ttl_overrides={
            "GetAccounts": 600,  # Cache accounts for 10 minutes
            "GetTransactions": 120,  # Cache transactions for 2 minutes
        }
    )
    
    # Load existing session
    try:
        mm.load_session()
    except FileNotFoundError:
        print("No session file found. Please login first.")
        return
    
    print("✓ MonarchMoney client initialized with optimizations")
    
    # Fetch accounts with basic detail level (reduces data transfer by ~70%)
    print("\n--- Fetching accounts (basic detail level) ---")
    start_time = time.time()
    accounts = await mm.get_accounts(detail_level="basic")
    duration = time.time() - start_time
    
    print(f"✓ Fetched {len(accounts.get('accounts', []))} accounts in {duration:.2f}s")
    
    # Second call should hit cache
    print("\n--- Fetching accounts again (should hit cache) ---")
    start_time = time.time()
    accounts_cached = await mm.get_accounts(detail_level="basic")
    duration = time.time() - start_time
    
    print(f"✓ Fetched accounts in {duration:.3f}s (cached)")
    
    # Get cache metrics
    metrics = mm.get_cache_metrics()
    print(f"\n📊 Cache Metrics:")
    print(f"   Cache Hit Rate: {metrics.get('cache_hit_rate', 'N/A')}")
    print(f"   API Calls Saved: {metrics.get('api_calls_saved', 0)}")
    print(f"   Cache Size: {metrics.get('cache_size_mb', 'N/A')} MB")


async def query_variants_example():
    """Demonstrate different query detail levels."""
    print("\n=== Query Variants Example ===")
    
    mm = MonarchMoney(cache_enabled=True, metrics_enabled=True)
    
    try:
        mm.load_session()
    except FileNotFoundError:
        print("No session file found. Please login first.")
        return
    
    # Test different detail levels
    detail_levels = ["basic", "balance", "full"]
    
    for level in detail_levels:
        print(f"\n--- Fetching accounts with '{level}' detail level ---")
        start_time = time.time()
        
        accounts = await mm.get_accounts(detail_level=level, force_refresh=True)
        duration = time.time() - start_time
        
        account_count = len(accounts.get('accounts', []))
        print(f"✓ {level.capitalize()}: {account_count} accounts in {duration:.3f}s")
    
    # Test transaction detail levels
    print(f"\n--- Transaction Query Variants ---")
    tx_levels = ["basic", "standard", "detailed"]
    
    for level in tx_levels:
        print(f"\n--- Fetching transactions with '{level}' detail level ---")
        start_time = time.time()
        
        transactions = await mm.get_transactions(
            limit=10, 
            detail_level=level,
            force_refresh=True
        )
        duration = time.time() - start_time
        
        tx_count = transactions.get('allTransactions', {}).get('totalCount', 0)
        print(f"✓ {level.capitalize()}: {tx_count} total transactions in {duration:.3f}s")


async def batch_operations_example():
    """Demonstrate batch operations for bulk actions."""
    print("\n=== Batch Operations Example ===")
    
    mm = MonarchMoney(cache_enabled=True)
    
    try:
        mm.load_session()
    except FileNotFoundError:
        print("No session file found. Please login first.")
        return
    
    # Get categories to demonstrate batch deletion
    categories = await mm.get_transaction_categories()
    user_categories = [
        cat for cat in categories.get('categories', [])
        if not cat.get('isSystemCategory', False)
    ]
    
    if not user_categories:
        print("No user-created categories found for batch deletion demo")
        return
    
    print(f"Found {len(user_categories)} user categories")
    
    # Demonstrate batch vs individual operations
    # Note: This is just a demonstration - uncomment to actually delete
    
    # Example category IDs for demonstration
    demo_category_ids = [cat['id'] for cat in user_categories[:2]]  # First 2 categories
    
    print(f"\n--- Batch Delete Demo (would delete {len(demo_category_ids)} categories) ---")
    print("Individual operations:")
    start_time = time.time()
    
    # This would make N API calls
    print(f"  Would make {len(demo_category_ids)} individual API calls")
    individual_duration = time.time() - start_time
    
    print(f"Batch operation:")
    start_time = time.time()
    
    # This would make 1 API call
    print(f"  Would make 1 batch API call")
    batch_duration = time.time() - start_time
    
    print(f"\n📈 Performance Comparison:")
    print(f"   Individual: {len(demo_category_ids)} API calls")
    print(f"   Batch: 1 API call ({len(demo_category_ids)}x reduction)")
    
    # Uncomment to actually perform batch deletion:
    # result = await mm.delete_transaction_categories(demo_category_ids, use_batch=True)
    # print(f"✓ Batch deletion result: {result}")


async def caching_performance_example():
    """Demonstrate caching performance improvements."""
    print("\n=== Caching Performance Example ===")
    
    # Client without caching
    mm_no_cache = MonarchMoney(cache_enabled=False)
    
    # Client with caching
    mm_cached = MonarchMoney(cache_enabled=True, metrics_enabled=True)
    
    try:
        mm_no_cache.load_session()
        mm_cached.load_session()
    except FileNotFoundError:
        print("No session file found. Please login first.")
        return
    
    # Test repeated requests without caching
    print("--- Without Caching ---")
    start_time = time.time()
    
    for i in range(3):
        await mm_no_cache.get_accounts(detail_level="basic")
    
    no_cache_duration = time.time() - start_time
    print(f"✓ 3 requests without caching: {no_cache_duration:.2f}s")
    
    # Test repeated requests with caching
    print("\n--- With Caching ---")
    start_time = time.time()
    
    for i in range(3):
        await mm_cached.get_accounts(detail_level="basic")
    
    cached_duration = time.time() - start_time
    print(f"✓ 3 requests with caching: {cached_duration:.2f}s")
    
    # Show performance improvement
    improvement = ((no_cache_duration - cached_duration) / no_cache_duration) * 100
    print(f"\n🚀 Performance Improvement: {improvement:.1f}% faster with caching")
    
    # Show cache metrics
    metrics = mm_cached.get_cache_metrics()
    print(f"\n📊 Final Cache Metrics:")
    for key, value in metrics.items():
        print(f"   {key}: {value}")


async def memory_optimization_example():
    """Demonstrate memory-optimized configuration."""
    print("\n=== Memory Optimization Example ===")
    
    # Memory-optimized configuration
    mm = MonarchMoney(
        cache_enabled=True,
        cache_max_size_mb=10,  # Smaller cache
        batch_requests=False,  # Disable batching to save memory
        deduplicate_requests=True,  # Keep deduplication for efficiency
        cache_ttl_overrides={
            "GetAccountTypeOptions": None,  # Static data - cache forever
            "GetTransactions": 60,  # Short TTL for dynamic data
        }
    )
    
    try:
        mm.load_session()
    except FileNotFoundError:
        print("No session file found. Please login first.")
        return
    
    print("✓ Initialized with memory-optimized settings")
    print("   - Cache size: 10 MB")
    print("   - Batching: Disabled")
    print("   - Deduplication: Enabled")
    print("   - Custom TTLs: Static data cached forever, dynamic data 60s")
    
    # Fetch some data to populate cache
    await mm.get_accounts(detail_level="basic")
    await mm.get_account_type_options()  # This will be cached forever
    
    metrics = mm.get_cache_metrics()
    print(f"\n📊 Memory Usage:")
    print(f"   Cache Size: {metrics.get('cache_size_mb', 'N/A')} MB")
    print(f"   Cache Entries: {metrics.get('cache_entries', 0)}")


async def main():
    """Run all examples."""
    print("🚀 MonarchMoney GraphQL Optimizations Examples\n")
    
    examples = [
        ("Basic Usage", basic_usage_example),
        ("Query Variants", query_variants_example),
        ("Batch Operations", batch_operations_example),
        ("Caching Performance", caching_performance_example),
        ("Memory Optimization", memory_optimization_example),
    ]
    
    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
        
        print("\n" + "="*60 + "\n")
    
    print("✅ All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())