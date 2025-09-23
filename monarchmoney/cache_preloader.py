"""
Cache preloader for MonarchMoney Enhanced.

Provides intelligent preloading of commonly accessed data to reduce API calls.
"""

import asyncio
from typing import TYPE_CHECKING, Dict, List, Optional

from .logging_config import logger

if TYPE_CHECKING:
    from .monarchmoney import MonarchMoney


class CachePreloader:
    """
    Intelligent cache preloader that prefetches commonly accessed data.

    Reduces API calls by proactively loading static and frequently accessed data
    into the query cache.
    """

    def __init__(self, client: "MonarchMoney"):
        self.client = client
        self.logger = logger

    async def preload_essential_data(self) -> Dict[str, bool]:
        """
        Preload essential data that's commonly accessed.

        Returns:
            Dict indicating which preloads succeeded
        """
        self.logger.info("Starting essential data preload")

        results = {}

        # Preload tasks that can run concurrently
        preload_tasks = [
            ("categories", self._preload_categories()),
            ("account_types", self._preload_account_types()),
            ("user_profile", self._preload_user_profile()),
            ("institutions", self._preload_institutions()),
        ]

        # Run preloads concurrently for maximum efficiency
        for name, task in preload_tasks:
            try:
                await task
                results[name] = True
                self.logger.debug(f"Preloaded {name} successfully")
            except Exception as e:
                results[name] = False
                self.logger.warning(f"Failed to preload {name}", error=str(e))

        success_count = sum(results.values())
        self.logger.info(
            "Essential data preload completed",
            successful=success_count,
            total=len(results)
        )

        return results

    async def preload_dashboard_data(self) -> Dict[str, bool]:
        """
        Preload data commonly needed for dashboard views.

        Returns:
            Dict indicating which preloads succeeded
        """
        self.logger.info("Starting dashboard data preload")

        results = {}

        # Dashboard-specific preloads
        dashboard_tasks = [
            ("accounts_basic", self._preload_accounts_basic()),
            ("recent_transactions", self._preload_recent_transactions()),
            ("merchants", self._preload_merchants()),
            ("transaction_rules", self._preload_transaction_rules()),
        ]

        for name, task in dashboard_tasks:
            try:
                await task
                results[name] = True
                self.logger.debug(f"Preloaded {name} for dashboard")
            except Exception as e:
                results[name] = False
                self.logger.warning(f"Failed to preload {name} for dashboard", error=str(e))

        return results

    async def preload_investment_data(self) -> Dict[str, bool]:
        """
        Preload investment-related data.

        Returns:
            Dict indicating which preloads succeeded
        """
        self.logger.info("Starting investment data preload")

        results = {}

        try:
            # Check if user has investment accounts first
            accounts = await self.client.get_accounts(detail_level="basic")
            has_investments = any(
                acc.get("type", {}).get("name") in ["investment", "retirement"]
                for acc in accounts.get("accounts", [])
            )

            if has_investments:
                # Preload investment holdings in batch
                await self.client._investment_service.get_all_holdings_batch()
                results["holdings"] = True
                self.logger.debug("Preloaded investment holdings")
            else:
                results["holdings"] = True  # No investments to preload
                self.logger.debug("No investment accounts found, skipping holdings preload")

        except Exception as e:
            results["holdings"] = False
            self.logger.warning("Failed to preload investment holdings", error=str(e))

        return results

    async def _preload_categories(self):
        """Preload transaction categories."""
        try:
            await self.client.get_transaction_categories()
        except Exception as e:
            self.logger.debug("Failed to preload categories", error=str(e))
            raise

    async def _preload_account_types(self):
        """Preload account type options."""
        try:
            await self.client.get_account_type_options()
        except Exception as e:
            self.logger.debug("Failed to preload account types", error=str(e))
            raise

    async def _preload_user_profile(self):
        """Preload user profile data."""
        try:
            await self.client.get_me()
        except Exception as e:
            self.logger.debug("Failed to preload user profile", error=str(e))
            raise

    async def _preload_institutions(self):
        """Preload financial institutions."""
        try:
            await self.client.get_institutions()
        except Exception as e:
            self.logger.debug("Failed to preload institutions", error=str(e))
            raise

    async def _preload_accounts_basic(self):
        """Preload basic account data."""
        try:
            await self.client.get_accounts(detail_level="basic")
        except Exception as e:
            self.logger.debug("Failed to preload basic accounts", error=str(e))
            raise

    async def _preload_recent_transactions(self):
        """Preload recent transactions for quick dashboard display."""
        try:
            from datetime import date, timedelta

            start_date = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
            await self.client.get_transactions(
                start_date=start_date,
                limit=50  # Just recent transactions for quick loading
            )
        except Exception as e:
            self.logger.debug("Failed to preload recent transactions", error=str(e))
            raise

    async def _preload_merchants(self):
        """Preload merchant data."""
        try:
            await self.client.get_merchants()
        except Exception as e:
            self.logger.debug("Failed to preload merchants", error=str(e))
            raise

    async def _preload_transaction_rules(self):
        """Preload transaction rules if user has any."""
        try:
            await self.client.get_transaction_rules()
        except Exception as e:
            # Rules might not be available for all users, or client not authenticated
            self.logger.debug("Failed to preload transaction rules", error=str(e))
            pass

    async def smart_preload(self, context: str = "general") -> Dict[str, bool]:
        """
        Intelligently preload data based on usage context.

        Args:
            context: Usage context ("general", "dashboard", "investments", "transactions")

        Returns:
            Dict indicating which preloads succeeded
        """
        self.logger.info("Starting smart preload", context=context)

        results = {}

        # Always preload essential data
        essential_results = await self.preload_essential_data()
        results.update(essential_results)

        # Context-specific preloading
        if context == "dashboard":
            dashboard_results = await self.preload_dashboard_data()
            results.update(dashboard_results)
        elif context == "investments":
            investment_results = await self.preload_investment_data()
            results.update(investment_results)
        elif context == "transactions":
            # Preload transaction-related data
            transaction_results = await self.preload_dashboard_data()  # Same as dashboard for now
            results.update(transaction_results)

        return results

    def get_preload_metrics(self) -> Dict[str, int]:
        """
        Get metrics about cache preloading effectiveness.

        Returns:
            Dict with preload metrics
        """
        # Get cache metrics if available
        if hasattr(self.client, '_graphql_client') and self.client._graphql_client:
            cache = getattr(self.client._graphql_client, '_cache', None)
            if cache and hasattr(cache, '_metrics'):
                return cache._metrics.to_dict()

        return {"message": "Cache metrics not available"}