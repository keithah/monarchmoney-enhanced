#!/usr/bin/env python3
"""
Demonstration of marking merchants as not recurring.

This example shows how to:
1. Find recurring transaction streams
2. Identify which merchants you want to mark as not recurring
3. Mark specific streams as not recurring to stop predictive forecasting
"""

import asyncio
import os
from dotenv import load_dotenv
from monarchmoney import MonarchMoney

load_dotenv()

async def demo_mark_not_recurring():
    """Demonstrate marking merchants as not recurring."""
    
    mm = MonarchMoney()
    
    try:
        # Login to Monarch Money
        await mm.interactive_login()
        
        print("\n📊 Finding recurring transaction streams...")
        
        # Get all recurring transactions to see what's available
        recurring_data = await mm.get_recurring_transactions()
        items = recurring_data.get('recurringTransactionItems', [])
        
        if not items:
            print("No recurring transactions found.")
            return
        
        print(f"\nFound {len(items)} recurring transaction items:")
        print("-" * 80)
        
        # Group by merchant to show unique recurring streams
        streams_by_merchant = {}
        for item in items:
            stream = item.get('stream', {})
            stream_id = stream.get('id')
            merchant_name = stream.get('merchant', {}).get('name', 'Unknown')
            
            if merchant_name not in streams_by_merchant:
                streams_by_merchant[merchant_name] = {
                    'stream_id': stream_id,
                    'amount': stream.get('amount', 0),
                    'frequency': stream.get('frequency', 'Unknown'),
                    'is_approximate': stream.get('isApproximate', False),
                    'count': 1
                }
            else:
                streams_by_merchant[merchant_name]['count'] += 1
        
        # Display recurring streams
        for i, (merchant, data) in enumerate(streams_by_merchant.items(), 1):
            status = "~" if data['is_approximate'] else "$"
            print(f"{i:2d}. {merchant}")
            print(f"     ID: {data['stream_id']}")
            print(f"     Amount: {status}{abs(data['amount']):,.2f}")
            print(f"     Frequency: {data['frequency']}")
            print(f"     Occurrences: {data['count']}")
            print()
        
        print("\n💡 Common reasons to mark a merchant as NOT RECURRING:")
        print("   • Cancelled subscription but old transactions still exist")
        print("   • One-time purchases incorrectly grouped as recurring")
        print("   • Variable purchases from the same merchant (like Amazon)")
        print("   • Want to remove predictive forecasting for specific merchants")
        
        print("\n🎯 Example usage:")
        print("   # Method 1: Mark stream directly if you have the ID")
        print("   stream_id = '135553558010567728'  # Example stream ID")
        print("   success = await mm.mark_stream_as_not_recurring(stream_id)")
        print("   if success:")
        print("       print('✅ Merchant marked as not recurring')")
        print("   else:")
        print("       print('❌ Failed to mark merchant')")
        print()
        print("   # Method 2: Find stream via merchant edit info")
        print("   merchant_id = '104754400339336479'  # Example merchant ID")
        print("   edit_info = await mm.get_edit_merchant(merchant_id)")
        print("   merchant = edit_info['merchant']")
        print("   if merchant['hasActiveRecurringStreams']:")
        print("       stream = merchant['recurringTransactionStream']")
        print("       stream_id = stream['id']")
        print("       success = await mm.mark_stream_as_not_recurring(stream_id)")
        
        # Demonstrate the actual API call (commented out for safety)
        print("\n⚠️  To actually mark a merchant as not recurring,")
        print("    uncomment and modify the code below:")
        print()
        print("    # Example: Mark the first merchant as not recurring")
        print("    # first_merchant = list(streams_by_merchant.keys())[0]")
        print("    # stream_id = streams_by_merchant[first_merchant]['stream_id']")
        print("    # success = await mm.mark_stream_as_not_recurring(stream_id)")
        print("    # print(f'Marked {first_merchant}: {success}')")
        print()
        print("    # OR use the edit merchant approach:")
        print("    # merchant_id = 'your_merchant_id_here'")
        print("    # edit_info = await mm.get_edit_merchant(merchant_id)")
        print("    # if edit_info['merchant']['hasActiveRecurringStreams']:")
        print("    #     stream_id = edit_info['merchant']['recurringTransactionStream']['id']")
        print("    #     success = await mm.mark_stream_as_not_recurring(stream_id)")
        print("    #     print(f'Marked as not recurring: {success}')")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if hasattr(mm, 'close'):
            await mm.close()

if __name__ == "__main__":
    asyncio.run(demo_mark_not_recurring())