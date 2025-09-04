#!/usr/bin/env python3
"""
Demo script showing the performance optimizations and error recovery capabilities
of MonarchMoney Enhanced.

This script demonstrates:
- Service-oriented architecture with focused responsibilities
- Advanced GraphQL client with caching and performance monitoring
- Error recovery with automatic retry and exponential backoff
- Context manager for proper resource cleanup
- Performance statistics and monitoring
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the parent directory to the path so we can import monarchmoney
sys.path.insert(0, str(Path(__file__).parent.parent))

from monarchmoney import MonarchMoney
from monarchmoney.exceptions import AuthenticationError


async def demo_performance_features():
    """Demonstrate the performance optimization features."""
    
    # Configure logging to see the performance monitoring in action
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 MonarchMoney Enhanced - Performance Demo")
    print("=" * 50)
    
    # Use the context manager for automatic cleanup
    async with MonarchMoney() as mm:
        
        # Show version information
        version_info = mm.get_version()
        print(f"📦 Version: {version_info['library_version']}")
        print(f"🔧 Library: {version_info['library_name']}")
        print()
        
        # This would typically be done with real credentials
        print("🔐 Authentication (simulated)")
        print("In a real application, you would:")
        print("  await mm.login('your-email@example.com', 'your-password')")
        print("  await mm.multi_factor_authenticate('123456', 'email')")
        print()
        
        # Demonstrate service architecture
        print("🏗️  Service-Oriented Architecture:")
        print(f"  ✓ Authentication Service: {mm._auth_service.__class__.__name__}")
        print(f"  ✓ Account Service: {mm._account_service.__class__.__name__}")
        print(f"  ✓ Transaction Service: {mm._transaction_service.__class__.__name__}")
        print(f"  ✓ Budget Service: {mm._budget_service.__class__.__name__}")
        print(f"  ✓ Investment Service: {mm._investment_service.__class__.__name__}")
        print(f"  ✓ Insight Service: {mm._insight_service.__class__.__name__}")
        print(f"  ✓ Settings Service: {mm._settings_service.__class__.__name__}")
        print()
        
        # Demonstrate performance monitoring
        print("📊 Performance Monitoring Features:")
        print("  ✓ GraphQL Query Caching with TTL")
        print("  ✓ Connection Pooling and Reuse") 
        print("  ✓ Rate Limiting with Smart Backoff")
        print("  ✓ Performance Metrics Collection")
        print("  ✓ Slow Query Detection and Logging")
        print()
        
        # Show performance stats (will be empty without real usage)
        stats = mm.get_performance_stats()
        if 'operations' in stats:
            print(f"📈 Current Cache Size: {stats.get('cache_size', 0)} entries")
            print(f"📊 Monitored Operations: {len(stats.get('operations', {}))}")
            if stats.get('slow_operations'):
                print(f"⚠️  Slow Operations Detected: {len(stats['slow_operations'])}")
        print()
        
        # Demonstrate error recovery capabilities  
        print("🛡️  Error Recovery Features:")
        print("  ✓ Automatic Authentication Recovery")
        print("  ✓ Rate Limit Handling with Exponential Backoff")
        print("  ✓ Network Error Retry with Progressive Delays")
        print("  ✓ Server Error Recovery with Conservative Retry")
        print("  ✓ Context-Aware Error Handling")
        print("  ✓ User-Friendly Error Messages")
        print()
        
        # Show security improvements
        print("🔒 Security Enhancements:")
        print("  ✓ Secure Session Storage with Encryption")
        print("  ✓ Input Validation and Sanitization")
        print("  ✓ GraphQL Injection Protection")
        print("  ✓ Comprehensive Logging (No Secrets Logged)")
        print("  ✓ Session Migration from Unsafe Pickle")
        print()
        
        # Demonstrate async context manager cleanup
        print("🧹 Resource Cleanup:")
        print("  ✓ Automatic Connection Cleanup on Exit")
        print("  ✓ GraphQL Client Resource Management")
        print("  ✓ Memory Efficient Caching with Size Limits")
        
        print()
        print("✨ Demo completed successfully!")
        print("   Use 'await mm.close()' or context manager for proper cleanup")


def demo_error_formatting():
    """Demonstrate error message formatting capabilities."""
    print("\n" + "=" * 50)
    print("🔍 Error Message Formatting Demo")
    print("=" * 50)
    
    from monarchmoney.error_handlers import ErrorMessageFormatter, ErrorContext
    from monarchmoney.exceptions import AuthenticationError, RateLimitError, NetworkError
    
    # Demo different error types
    errors_to_demo = [
        AuthenticationError("Invalid credentials provided"),
        RateLimitError("Too many requests", retry_after=60),
        NetworkError("Connection timeout after 30 seconds"),
    ]
    
    for error in errors_to_demo:
        context = ErrorContext("GetAccounts", retry_count=1)
        formatted = ErrorMessageFormatter.format_error(error, context)
        
        print(f"\n❌ {formatted['error_type']}:")
        print(f"   Message: {formatted['user_message']}")
        print(f"   Recoverable: {formatted['recoverable']}")
        print(f"   Suggestions:")
        for action in formatted['suggested_actions']:
            print(f"     • {action}")


async def main():
    """Main demo function."""
    try:
        await demo_performance_features()
        demo_error_formatting()
        
        print("\n" + "=" * 50) 
        print("🎉 MonarchMoney Enhanced Demo Complete!")
        print("   Ready for production use with enhanced performance,")
        print("   security, and error handling capabilities.")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))