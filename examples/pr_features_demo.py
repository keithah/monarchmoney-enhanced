#!/usr/bin/env python3
"""
Demo script showcasing new features implemented from community PRs.

This script demonstrates:
- Holdings management by ticker (PR #151)
- Transaction filtering by amount (PR #148)  
- Transaction summary card (PR #140)
- Categories and merchants API (PR #128)
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import monarchmoney
sys.path.insert(0, str(Path(__file__).parent.parent))

from monarchmoney import MonarchMoney


async def demo_holdings_management():
    """Demonstrate holdings management by ticker (PR #151)."""
    print("🔹 Holdings Management by Ticker (PR #151)")
    print("-" * 50)
    
    async with MonarchMoney() as mm:
        # This would typically be done with real authentication
        print("📋 Holdings Management Features:")
        print("  • get_holding_by_ticker() - Find holdings by ticker symbol")
        print("  • add_holding_by_ticker() - Add holdings programmatically")  
        print("  • remove_holding_by_ticker() - Remove holdings by ticker")
        print("  • update_holding_quantity() - Update share quantities")
        print()
        
        print("🔧 Example Usage:")
        print("""
        # Find existing AAPL holding
        aapl_holding = await mm._investment_service.get_holding_by_ticker('AAPL')
        
        # Add 10 shares of MSFT to investment account
        new_holding = await mm._investment_service.add_holding_by_ticker(
            account_id='account_123',
            ticker='MSFT',
            quantity=10,
            basis_per_share=150.00
        )
        
        # Remove all TSLA holdings
        success = await mm._investment_service.remove_holding_by_ticker('TSLA')
        
        # Update quantity of existing holding
        updated = await mm._investment_service.update_holding_quantity(
            holding_id='holding_456',
            new_quantity=25
        )
        """)
        print("✅ Holdings management enables complete programmatic portfolio control!")


async def demo_transaction_filtering():
    """Demonstrate transaction filtering by amount (PR #148)."""
    print("\n🔹 Transaction Filtering by Amount (PR #148)")
    print("-" * 50)
    
    async with MonarchMoney() as mm:
        print("💰 Enhanced Transaction Filtering:")
        print("  • Filter by credit/debit transactions")
        print("  • Filter by amount ranges (min/max)")  
        print("  • Combine with existing filters")
        print()
        
        print("🔧 Example Usage:")
        print("""
        # Get only credit transactions (income)
        income = await mm.get_transactions(is_credit=True)
        
        # Get only debit transactions (expenses)
        expenses = await mm.get_transactions(is_credit=False)
        
        # Get transactions >= $100
        large_txns = await mm.get_transactions(abs_amount_range=[100.0, None])
        
        # Get transactions <= $25
        small_txns = await mm.get_transactions(abs_amount_range=[None, 25.0])
        
        # Get transactions between $50-$200
        medium_txns = await mm.get_transactions(abs_amount_range=[50.0, 200.0])
        
        # Get transactions exactly $99.99
        specific = await mm.get_transactions(abs_amount_range=[99.99, 99.99])
        
        # Combine with date filtering
        recent_large = await mm.get_transactions(
            start_date='2024-01-01',
            is_credit=False,
            abs_amount_range=[100.0, None]
        )
        """)
        print("✅ Advanced filtering enables precise transaction analysis!")


async def demo_transaction_summary_card():
    """Demonstrate transaction summary card (PR #140)."""
    print("\n🔹 Transaction Summary Card (PR #140)")
    print("-" * 50)
    
    async with MonarchMoney() as mm:
        print("📊 Enhanced Transaction Summary:")
        print("  • More accurate transaction counts")
        print("  • Matches Monarch UI exactly")
        print("  • Better data consistency")
        print()
        
        print("🔧 Example Usage:")
        print("""
        # Get enhanced transaction summary (matches UI)
        summary_card = await mm._transaction_service.get_transactions_summary_card()
        
        # Compare with standard summary
        standard_summary = await mm._transaction_service.get_transactions_summary()
        
        print(f"Standard count: {standard_summary['count']}")
        print(f"UI-accurate count: {summary_card['totalTransactionsCount']}")
        """)
        print("✅ Summary card provides UI-consistent transaction counts!")


async def demo_categories_merchants_api():
    """Demonstrate categories and merchants API (PR #128)."""
    print("\n🔹 Categories and Merchants API (PR #128)")
    print("-" * 50)
    
    async with MonarchMoney() as mm:
        print("🏪 Categories & Merchants Management:")
        print("  • get_transaction_categories() - All available categories")
        print("  • get_merchants() - Merchants with search & filtering")
        print("  • get_merchant_details() - Detailed merchant information")
        print("  • get_category_details() - Category statistics & insights")
        print()
        
        print("🔧 Example Usage:")
        print("""
        # Get all transaction categories
        categories = await mm._transaction_service.get_transaction_categories()
        
        # Search for merchants
        starbucks = await mm._transaction_service.get_merchants(search='Starbucks')
        
        # Get all merchants (paginated)
        merchants = await mm._transaction_service.get_merchants(limit=50)
        
        # Get detailed merchant info with recent transactions
        merchant_details = await mm._transaction_service.get_merchant_details('merchant_123')
        
        # Get category statistics and top merchants
        category_details = await mm._transaction_service.get_category_details('category_456')
        """)
        print("✅ Categories & merchants APIs enable advanced transaction management!")


async def demo_service_architecture():
    """Demonstrate the service-oriented architecture benefits."""
    print("\n🔹 Service-Oriented Architecture Benefits")
    print("-" * 50)
    
    async with MonarchMoney() as mm:
        print("🏗️ Clean Service Organization:")
        print(f"  • InvestmentService: {len([m for m in dir(mm._investment_service) if not m.startswith('_')])} methods")
        print(f"  • TransactionService: {len([m for m in dir(mm._transaction_service) if not m.startswith('_')])} methods")
        print(f"  • AccountService: {len([m for m in dir(mm._account_service) if not m.startswith('_')])} methods")
        print(f"  • AuthenticationService: {len([m for m in dir(mm._auth_service) if not m.startswith('_')])} methods")
        print()
        
        print("💡 Direct Service Access:")
        print("""
        # Access services directly for advanced operations
        investment_service = mm._investment_service
        transaction_service = mm._transaction_service
        account_service = mm._account_service
        
        # Or use convenience methods on main client
        accounts = await mm.get_accounts()  # → AccountService
        transactions = await mm.get_transactions()  # → TransactionService  
        """)
        print("✅ Services provide clean separation of concerns!")


async def demo_performance_features():
    """Demonstrate performance optimizations."""
    print("\n🔹 Performance Optimizations")
    print("-" * 50)
    
    async with MonarchMoney() as mm:
        print("⚡ Advanced Performance Features:")
        print("  • GraphQL query caching with TTL")
        print("  • Connection pooling and reuse")
        print("  • Rate limiting with smart backoff")
        print("  • Performance monitoring and metrics")
        print("  • Error recovery with automatic retry")
        print()
        
        # Show performance stats
        stats = mm.get_performance_stats()
        print(f"📈 Performance Stats:")
        print(f"  Cache Size: {stats.get('cache_size', 0)} entries")
        print(f"  Operations Monitored: {len(stats.get('operations', {}))}")
        print(f"  Slow Operations: {len(stats.get('slow_operations', []))}")
        print()
        
        print("✅ Enterprise-grade performance optimizations active!")


async def main():
    """Main demo function."""
    print("🚀 MonarchMoney Enhanced - Community PR Features Demo")
    print("=" * 60)
    print("Showcasing valuable features implemented from community PRs")
    print()
    
    try:
        await demo_holdings_management()
        await demo_transaction_filtering()
        await demo_transaction_summary_card() 
        await demo_categories_merchants_api()
        await demo_service_architecture()
        await demo_performance_features()
        
        print("\n" + "=" * 60)
        print("🎉 Community PR Features Demo Complete!")
        print("   All features are ready for production use.")
        print("   These PRs add significant value to the library!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))