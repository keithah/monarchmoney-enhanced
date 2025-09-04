#!/usr/bin/env python3
"""
Recurring Transactions Demo

This demo showcases the comprehensive recurring transactions functionality
implemented from HAR file analysis. It demonstrates all 6 new methods for
managing recurring transaction streams and calendar items.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from monarchmoney import MonarchMoney


class RecurringTransactionsDemo:
    """Demo class for recurring transactions functionality."""

    def __init__(self, session_file: Optional[str] = None):
        """Initialize the demo with a MonarchMoney instance."""
        self.mm = MonarchMoney(session_file=session_file)

    async def authenticate(self):
        """Authenticate with Monarch Money."""
        try:
            await self.mm.interactive_login()
            print("✓ Successfully authenticated with Monarch Money")
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            raise

    async def demo_get_recurring_streams(self):
        """Demo: Get all recurring transaction streams."""
        print("\n" + "=" * 60)
        print("1. Getting Recurring Transaction Streams")
        print("=" * 60)

        try:
            # Get all streams
            streams = await self.mm.get_recurring_streams()
            print(f"Found {len(streams.get('recurringStreams', []))} recurring streams")

            # Show first few streams
            for i, stream in enumerate(streams.get("recurringStreams", [])[:3]):
                print(f"\nStream {i+1}:")
                print(f"  ID: {stream.get('id')}")
                print(
                    f"  Merchant: {stream.get('merchant', {}).get('name', 'Unknown')}"
                )
                print(f"  Amount: ${stream.get('amount', 0):.2f}")
                print(f"  Status: {stream.get('reviewStatus', 'Unknown')}")
                print(f"  Frequency: {stream.get('frequency', 'Unknown')}")

            # Get streams with filters
            print("\nGetting streams with liabilities excluded...")
            filtered_streams = await self.mm.get_recurring_streams(
                include_liabilities=False, filters={"reviewStatus": "approved"}
            )
            print(
                f"Found {len(filtered_streams.get('recurringStreams', []))} approved non-liability streams"
            )

        except Exception as e:
            print(f"Error getting recurring streams: {e}")

    async def demo_get_aggregated_recurring_items(self):
        """Demo: Get aggregated recurring items by date range."""
        print("\n" + "=" * 60)
        print("2. Getting Aggregated Recurring Items")
        print("=" * 60)

        try:
            # Calculate date range (next 3 months)
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

            # Get aggregated items by status
            items_by_status = await self.mm.get_aggregated_recurring_items(
                start_date=start_date, end_date=end_date, group_by="status"
            )

            print(f"Aggregated items from {start_date} to {end_date} (by status):")
            for group in items_by_status.get("aggregatedRecurringItems", {}).get(
                "groups", []
            ):
                print(
                    f"  {group.get('groupKey', 'Unknown')}: {group.get('totalCount', 0)} items"
                )

            # Get aggregated items by date
            items_by_date = await self.mm.get_aggregated_recurring_items(
                start_date=start_date, end_date=end_date, group_by="date"
            )

            print(f"\nAggregated items by date (first 5 dates):")
            for group in items_by_date.get("aggregatedRecurringItems", {}).get(
                "groups", []
            )[:5]:
                date = group.get("groupKey", "Unknown")
                count = group.get("totalCount", 0)
                total_amount = sum(
                    item.get("amount", 0) for item in group.get("items", [])
                )
                print(f"  {date}: {count} items, ${total_amount:.2f} total")

        except Exception as e:
            print(f"Error getting aggregated recurring items: {e}")

    async def demo_review_recurring_stream(self):
        """Demo: Review and update recurring stream status."""
        print("\n" + "=" * 60)
        print("3. Reviewing Recurring Stream Status")
        print("=" * 60)

        try:
            # Get streams to find one to review
            streams = await self.mm.get_recurring_streams(include_pending=True)
            pending_streams = [
                s
                for s in streams.get("recurringStreams", [])
                if s.get("reviewStatus") == "pending"
            ]

            if not pending_streams:
                print("No pending streams found to review")

                # Show example of what the review would look like
                print("\nExample review operation:")
                print("  Stream ID: example-stream-123")
                print("  Current Status: pending")
                print("  Action: approve")
                print("  → Would update stream status to 'approved'")
                return

            # Review the first pending stream
            stream = pending_streams[0]
            stream_id = stream.get("id")
            merchant_name = stream.get("merchant", {}).get("name", "Unknown")

            print(f"Reviewing stream: {merchant_name} (ID: {stream_id})")
            print(f"Current status: {stream.get('reviewStatus')}")

            # Note: In a real demo, you might want to ask for user input
            # For demo purposes, we'll just show what would happen
            print("Demo action: Would approve this stream")

            # Uncomment to actually review:
            # result = await self.mm.review_recurring_stream(stream_id, "approved")
            # print(f"Review result: {result.get('reviewStream', {}).get('success', False)}")

        except Exception as e:
            print(f"Error reviewing recurring stream: {e}")

    async def demo_mark_stream_as_not_recurring(self):
        """Demo: Mark a stream as not recurring."""
        print("\n" + "=" * 60)
        print("4. Marking Stream as Not Recurring")
        print("=" * 60)

        try:
            # Get approved streams to find one to mark as not recurring
            streams = await self.mm.get_recurring_streams()
            approved_streams = [
                s
                for s in streams.get("recurringStreams", [])
                if s.get("reviewStatus") == "approved"
            ]

            if not approved_streams:
                print("No approved streams found to mark as non-recurring")

                # Show example operation
                print("\nExample mark-as-not-recurring operation:")
                print("  Stream ID: example-stream-456")
                print("  Current Status: approved")
                print("  Action: mark as not recurring")
                print("  → Would disable recurring predictions for this stream")
                return

            # Show what would happen with the first approved stream
            stream = approved_streams[0]
            stream_id = stream.get("id")
            merchant_name = stream.get("merchant", {}).get("name", "Unknown")

            print(
                f"Would mark stream as not recurring: {merchant_name} (ID: {stream_id})"
            )
            print(f"Current status: {stream.get('reviewStatus')}")

            # Uncomment to actually mark as not recurring:
            # success = await self.mm.mark_stream_as_not_recurring(stream_id)
            # print(f"Operation successful: {success}")

        except Exception as e:
            print(f"Error marking stream as not recurring: {e}")

    async def demo_get_recurring_merchant_search_status(self):
        """Demo: Get recurring merchant search status."""
        print("\n" + "=" * 60)
        print("5. Getting Recurring Merchant Search Status")
        print("=" * 60)

        try:
            status = await self.mm.get_recurring_merchant_search_status()

            print("Recurring merchant search status:")
            print(
                f"  Status: {status.get('recurringMerchantSearch', {}).get('status', 'Unknown')}"
            )
            print(
                f"  Last updated: {status.get('recurringMerchantSearch', {}).get('lastUpdated', 'Unknown')}"
            )

            # Show any additional status information
            search_info = status.get("recurringMerchantSearch", {})
            if "progress" in search_info:
                print(f"  Progress: {search_info['progress']}")
            if "totalMerchants" in search_info:
                print(f"  Total merchants: {search_info['totalMerchants']}")

        except Exception as e:
            print(f"Error getting merchant search status: {e}")

    async def demo_get_all_recurring_transaction_items(self):
        """Demo: Get all recurring transaction items with forecasts."""
        print("\n" + "=" * 60)
        print("6. Getting All Recurring Transaction Items")
        print("=" * 60)

        try:
            # Get all recurring items
            all_items = await self.mm.get_all_recurring_transaction_items()

            items_list = all_items.get("allRecurringTransactionItems", [])
            print(f"Found {len(items_list)} recurring transaction items")

            # Categorize items
            forecasts = [item for item in items_list if item.get("isForecast", False)]
            actuals = [item for item in items_list if not item.get("isForecast", False)]

            print(f"  Forecasted items: {len(forecasts)}")
            print(f"  Actual items: {len(actuals)}")

            # Show some example items
            print("\nSample items:")
            for i, item in enumerate(items_list[:5]):
                item_type = "Forecast" if item.get("isForecast") else "Actual"
                date = item.get("date", "Unknown")
                amount = item.get("amount", 0)
                merchant = item.get("merchant", {}).get("name", "Unknown")

                print(f"  {i+1}. [{item_type}] {date}: {merchant} - ${amount:.2f}")

            # Get items with filters
            print("\nGetting items excluding liabilities...")
            filtered_items = await self.mm.get_all_recurring_transaction_items(
                include_liabilities=False, filters={"isForecast": True}
            )

            filtered_count = len(filtered_items.get("allRecurringTransactionItems", []))
            print(f"Found {filtered_count} forecasted non-liability items")

        except Exception as e:
            print(f"Error getting all recurring transaction items: {e}")

    async def run_demo(self):
        """Run the complete recurring transactions demo."""
        print("Recurring Transactions Functionality Demo")
        print("=========================================")
        print("This demo showcases the comprehensive recurring transactions")
        print("functionality implemented from HAR file analysis.")

        try:
            await self.authenticate()

            # Run all demo functions
            await self.demo_get_recurring_streams()
            await self.demo_get_aggregated_recurring_items()
            await self.demo_review_recurring_stream()
            await self.demo_mark_stream_as_not_recurring()
            await self.demo_get_recurring_merchant_search_status()
            await self.demo_get_all_recurring_transaction_items()

            print("\n" + "=" * 60)
            print("Demo Summary")
            print("=" * 60)
            print("✓ Demonstrated 6 comprehensive recurring transactions methods:")
            print(
                "  1. get_recurring_streams() - Get all recurring streams with filtering"
            )
            print(
                "  2. get_aggregated_recurring_items() - Get items aggregated by date/status"
            )
            print("  3. review_recurring_stream() - Review and approve/reject streams")
            print("  4. mark_stream_as_not_recurring() - Disable recurring predictions")
            print(
                "  5. get_recurring_merchant_search_status() - Check search operation status"
            )
            print(
                "  6. get_all_recurring_transaction_items() - Get all items with forecasts"
            )
            print("\nThese methods provide full CRUD operations for managing")
            print("recurring transactions and forecasting future cash flows.")

        except Exception as e:
            print(f"\n✗ Demo failed: {e}")
            raise


async def main():
    """Main demo function."""
    # You can specify a session file path here if you have one
    demo = RecurringTransactionsDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
