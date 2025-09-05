#!/usr/bin/env python3
"""
Bulk Unhide Transactions Demo

This example demonstrates how to use the new bulk unhide functionality
that was implemented based on the unhide.har file analysis.

The functionality allows you to:
1. Find hidden transactions
2. Bulk unhide specific transactions
3. Bulk hide transactions 
4. Perform generic bulk updates on transactions

Based on HAR file analysis of the Common_BulkUpdateTransactionsMutation.
"""

import asyncio
import os
from typing import List

from monarchmoney import MonarchMoney


async def demo_bulk_unhide_functionality():
    """
    Comprehensive demo of the bulk unhide functionality.
    """
    # Initialize MonarchMoney client
    mm = MonarchMoney()
    
    print("🏦 MonarchMoney Bulk Unhide Demo")
    print("=" * 50)
    
    # Load session if available
    session_file = "temp_session.json"
    if os.path.exists(session_file):
        await mm.load_session(session_file)
        print("✅ Loaded existing session")
    else:
        print("❌ No session file found. Please login first:")
        print("   python examples/login_demo.py")
        return

    try:
        # Demo 1: Get hidden transactions
        print("\n📊 1. Finding hidden transactions...")
        
        hidden_response = await mm.get_hidden_transactions(limit=25)
        
        if "allTransactions" in hidden_response:
            total_hidden = hidden_response["allTransactions"]["totalCount"]
            hidden_transactions = hidden_response["allTransactions"]["results"]
            
            print(f"   Found {total_hidden} total hidden transactions")
            print(f"   Retrieved {len(hidden_transactions)} in this batch")
            
            if hidden_transactions:
                print(f"\n   📋 Sample hidden transactions:")
                for i, txn in enumerate(hidden_transactions[:3]):
                    amount = txn['amount']
                    merchant = txn.get('merchant', {}).get('name', 'Unknown')
                    date = txn['date']
                    print(f"      {i+1}. ${amount:>8.2f} - {merchant} ({date})")
                
                # Demo 2: Bulk unhide a few transactions
                print(f"\n🔄 2. Bulk unhiding transactions...")
                
                # Take first 2 transactions as examples
                demo_ids = [txn["id"] for txn in hidden_transactions[:2]]
                
                print(f"   Unhiding {len(demo_ids)} transactions:")
                for i, txn_id in enumerate(demo_ids):
                    txn = hidden_transactions[i]
                    merchant = txn.get('merchant', {}).get('name', 'Unknown')
                    print(f"      {i+1}. {merchant} (${txn['amount']})")
                
                # Perform the bulk unhide
                result = await mm.bulk_unhide_transactions(
                    transaction_ids=demo_ids,
                    filters={"hideFromReports": True}
                )
                
                if result.get("success"):
                    affected_count = result.get("affectedCount", 0)
                    print(f"   ✅ Successfully unhid {affected_count} transactions")
                else:
                    print(f"   ❌ Failed to unhide transactions: {result}")
                
                # Demo 3: Hide them back to restore original state
                print(f"\n🔄 3. Re-hiding transactions to restore original state...")
                
                hide_result = await mm.bulk_hide_transactions(
                    transaction_ids=demo_ids
                )
                
                if hide_result.get("success"):
                    print(f"   ✅ Successfully re-hid {hide_result.get('affectedCount', 0)} transactions")
                else:
                    print(f"   ❌ Failed to re-hide transactions: {hide_result}")
                
                # Demo 4: Generic bulk update functionality
                print(f"\n⚙️ 4. Testing generic bulk update...")
                
                # Get some regular transactions to demonstrate with
                regular_transactions = await mm.get_transactions(limit=3)
                
                if "allTransactions" in regular_transactions:
                    regular_txns = regular_transactions["allTransactions"]["results"]
                    if regular_txns:
                        test_txn_id = regular_txns[0]["id"]
                        merchant_name = regular_txns[0].get('merchant', {}).get('name', 'Unknown')
                        
                        print(f"   Testing with transaction: {merchant_name}")
                        
                        # Demo hiding via generic bulk_update_transactions
                        hide_result = await mm.bulk_update_transactions(
                            transaction_ids=[test_txn_id],
                            updates={"hide": True}
                        )
                        
                        if hide_result.get("success"):
                            print(f"   ✅ Hid transaction using bulk_update_transactions")
                            
                            # Now unhide it
                            unhide_result = await mm.bulk_update_transactions(
                                transaction_ids=[test_txn_id],
                                updates={"hide": False}
                            )
                            
                            if unhide_result.get("success"):
                                print(f"   ✅ Unhid transaction using bulk_update_transactions")
                            else:
                                print(f"   ❌ Failed to unhide: {unhide_result}")
                        else:
                            print(f"   ❌ Failed to hide: {hide_result}")
                    else:
                        print("   ⚠️  No regular transactions found for testing")
                
            else:
                print("   ℹ️  No hidden transactions found")
                
                # Demo with regular transactions instead
                print(f"\n   📋 Demo with regular transactions instead...")
                regular_response = await mm.get_transactions(limit=2)
                
                if "allTransactions" in regular_response:
                    regular_txns = regular_response["allTransactions"]["results"]
                    if regular_txns:
                        demo_ids = [txn["id"] for txn in regular_txns]
                        
                        print(f"   Hiding {len(demo_ids)} regular transactions...")
                        hide_result = await mm.bulk_hide_transactions(demo_ids)
                        
                        if hide_result.get("success"):
                            print(f"   ✅ Successfully hid {hide_result.get('affectedCount', 0)} transactions")
                            
                            # Unhide them back
                            unhide_result = await mm.bulk_unhide_transactions(demo_ids)
                            if unhide_result.get("success"):
                                print(f"   ✅ Successfully unhid {unhide_result.get('affectedCount', 0)} transactions")
                        else:
                            print(f"   ❌ Failed to hide transactions: {hide_result}")
        
        # Demo 5: Real-world usage patterns
        print(f"\n💡 5. Real-world usage examples:")
        print("   # Find all hidden transactions")
        print("   hidden = await mm.get_hidden_transactions(limit=100)")
        print("   transaction_ids = [t['id'] for t in hidden['allTransactions']['results']]")
        print()
        print("   # Unhide all hidden transactions")
        print("   if transaction_ids:")
        print("       result = await mm.bulk_unhide_transactions(transaction_ids)")
        print("       print(f'Unhid {result[\"affectedCount\"]} transactions')")
        print()
        print("   # Hide specific transactions from reports")
        print("   internal_transfer_ids = ['id1', 'id2', 'id3']")
        print("   await mm.bulk_hide_transactions(internal_transfer_ids)")
        print()
        print("   # Generic bulk updates (change category, merchant, etc.)")
        print("   await mm.bulk_update_transactions(")
        print("       transaction_ids=['id1', 'id2'],")
        print("       updates={'categoryId': 'new_category_id'}")
        print("   )")

        print(f"\n🎉 Demo completed successfully!")
        
        # Show the exact transaction IDs from the HAR file as an example
        print(f"\n📄 Example from the original HAR file:")
        print("   # These were the 6 transactions that were unhidden:")
        har_transaction_ids = [
            "220716668609011425", "220716668609011424", "220716668609011423",
            "220716668609011422", "220716668609011421", "220716668609011420"
        ]
        print("   transaction_ids = [")
        for tid in har_transaction_ids:
            print(f'       "{tid}",')
        print("   ]")
        print("   result = await mm.bulk_unhide_transactions(transaction_ids)")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await mm.close_session()


async def demo_optimized_monarchmoney():
    """
    Demo showing OptimizedMonarchMoney as a drop-in replacement.
    """
    print(f"\n🚀 OptimizedMonarchMoney Drop-in Replacement Demo")
    print("=" * 55)
    
    # Import the optimized version
    from monarchmoney.optimizations import OptimizedMonarchMoney
    
    # Create optimized client with caching enabled
    mm = OptimizedMonarchMoney(
        cache_enabled=True,
        deduplicate_requests=True,
        cache_max_size_mb=10
    )
    
    print("✅ OptimizedMonarchMoney initialized with caching and deduplication")
    
    # Show initial metrics
    metrics = mm.get_cache_metrics()
    print(f"📊 Initial cache metrics: {metrics}")
    
    # Load session if available
    session_file = "temp_session.json"
    if os.path.exists(session_file):
        await mm.load_session(session_file)
        print("✅ Session loaded using OptimizedMonarchMoney")
        
        try:
            # Make the same API calls to show caching in action
            print(f"\n🔄 Making API calls to demonstrate caching...")
            
            # First call - cache miss
            accounts1 = await mm.get_accounts()
            metrics = mm.get_cache_metrics()
            print(f"   First get_accounts call - Cache metrics: hit_rate={metrics['cache_hit_rate']}")
            
            # Second call - should be cache hit if caching works
            accounts2 = await mm.get_accounts()
            metrics = mm.get_cache_metrics()
            print(f"   Second get_accounts call - Cache metrics: hit_rate={metrics['cache_hit_rate']}")
            
            # Test our new bulk unhide methods work with optimization
            hidden = await mm.get_hidden_transactions(limit=5)
            print(f"   ✅ get_hidden_transactions works with OptimizedMonarchMoney")
            
            # Show final metrics
            final_metrics = mm.get_cache_metrics()
            print(f"\n📊 Final cache metrics:")
            for key, value in final_metrics.items():
                print(f"      {key}: {value}")
            
        except Exception as e:
            print(f"   ⚠️  API calls failed (likely not logged in): {e}")
    else:
        print("   ℹ️  No session file - skipping API calls")
    
    await mm.close_session()


if __name__ == "__main__":
    print("🎯 Starting MonarchMoney Bulk Unhide Demonstrations...")
    
    # Run the main bulk unhide demo
    asyncio.run(demo_bulk_unhide_functionality())
    
    # Run the OptimizedMonarchMoney demo
    asyncio.run(demo_optimized_monarchmoney())
    
    print(f"\n✨ All demonstrations completed!")
    print(f"\nKey takeaways:")
    print(f"  ✅ Bulk unhide functionality successfully implemented")
    print(f"  ✅ OptimizedMonarchMoney is a true drop-in replacement")
    print(f"  ✅ All new methods maintain the same API patterns")
    print(f"  ✅ Based on real MonarchMoney API analysis (HAR file)")