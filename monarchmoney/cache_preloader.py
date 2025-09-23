"""
Cache preloader for MonarchMoney Enhanced.

Provides intelligent preloading of commonly accessed data to reduce API calls.
Includes predictive prefetching based on usage patterns.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

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

        # Predictive prefetching data structures
        self._access_patterns: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))  # Recent access times
        self._operation_sequences: deque = deque(maxlen=100)  # Recent operation sequences
        self._operation_dependencies: Dict[str, Set[str]] = defaultdict(set)  # Which operations follow others
        self._usage_context_history: deque = deque(maxlen=20)  # Recent contexts used
        self._last_access_time: Dict[str, float] = {}  # Last access time per operation

    def track_operation_access(self, operation: str, context: str = "general") -> None:
        """Track when an operation is accessed for predictive analysis."""
        current_time = time.time()

        # Record access time
        self._access_patterns[operation].append(current_time)
        self._last_access_time[operation] = current_time

        # Track operation sequences for dependency analysis
        if self._operation_sequences:
            last_operation = self._operation_sequences[-1][0]
            # If operations happen within 30 seconds, consider them related
            if current_time - self._operation_sequences[-1][1] < 30:
                self._operation_dependencies[last_operation].add(operation)

        self._operation_sequences.append((operation, current_time))

        # Track context usage
        if not self._usage_context_history or self._usage_context_history[-1] != context:
            self._usage_context_history.append(context)

    def predict_next_operations(self, current_operation: str, limit: int = 3) -> List[str]:
        """Predict what operations are likely to be called next."""
        predictions = []

        # Look at dependencies from current operation
        dependencies = self._operation_dependencies.get(current_operation, set())
        for dep in dependencies:
            if dep not in predictions:
                predictions.append(dep)
                if len(predictions) >= limit:
                    break

        # If we need more predictions, look at frequently accessed operations
        if len(predictions) < limit:
            frequent_ops = self._get_frequently_accessed_operations(limit - len(predictions))
            for op in frequent_ops:
                if op not in predictions and op != current_operation:
                    predictions.append(op)
                    if len(predictions) >= limit:
                        break

        return predictions

    def _get_frequently_accessed_operations(self, limit: int = 5) -> List[str]:
        """Get operations that are accessed most frequently."""
        # Count accesses in the last hour
        current_time = time.time()
        one_hour_ago = current_time - 3600

        access_counts = {}
        for operation, access_times in self._access_patterns.items():
            recent_accesses = [t for t in access_times if t > one_hour_ago]
            access_counts[operation] = len(recent_accesses)

        # Sort by access count and return top operations
        sorted_ops = sorted(access_counts.items(), key=lambda x: x[1], reverse=True)
        return [op for op, count in sorted_ops[:limit] if count > 0]

    def should_prefetch_operation(self, operation: str) -> bool:
        """Determine if an operation should be prefetched based on patterns."""
        if operation not in self._access_patterns:
            return False

        current_time = time.time()
        access_times = list(self._access_patterns[operation])

        if len(access_times) < 2:
            return False

        # Calculate average time between accesses
        intervals = []
        for i in range(1, len(access_times)):
            intervals.append(access_times[i] - access_times[i-1])

        if not intervals:
            return False

        avg_interval = sum(intervals) / len(intervals)
        last_access = self._last_access_time.get(operation, 0)
        time_since_last = current_time - last_access

        # If it's been longer than the average interval, consider prefetching
        return time_since_last >= (avg_interval * 0.8)

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
            await self.client.get_accounts()
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

    async def predictive_prefetch(self, triggered_by: str = None, max_operations: int = 3) -> Dict[str, bool]:
        """
        Perform predictive prefetching based on usage patterns.

        Args:
            triggered_by: The operation that triggered this prefetch
            max_operations: Maximum number of operations to prefetch

        Returns:
            Dict indicating which prefetches succeeded
        """
        results = {}

        if triggered_by:
            # Predict what might be needed next
            predicted_operations = self.predict_next_operations(triggered_by, max_operations)
            self.logger.debug("Predictive prefetch triggered",
                             triggered_by=triggered_by,
                             predictions=predicted_operations)

            for operation in predicted_operations:
                try:
                    # Map operation names to actual methods
                    if operation == "GetAccounts" and self.should_prefetch_operation(operation):
                        await self.client.get_accounts()
                        results[f"predicted_{operation}"] = True
                    elif operation == "GetTransactions" and self.should_prefetch_operation(operation):
                        await self._preload_recent_transactions()
                        results[f"predicted_{operation}"] = True
                    elif operation == "GetTransactionCategories" and self.should_prefetch_operation(operation):
                        await self.client.get_transaction_categories()
                        results[f"predicted_{operation}"] = True
                    elif operation == "GetMerchants" and self.should_prefetch_operation(operation):
                        await self.client.get_merchants()
                        results[f"predicted_{operation}"] = True
                    elif operation == "GetHoldings" and self.should_prefetch_operation(operation):
                        await self.client._investment_service.get_all_holdings_batch()
                        results[f"predicted_{operation}"] = True
                except Exception as e:
                    results[f"predicted_{operation}"] = False
                    self.logger.debug(f"Predictive prefetch failed for {operation}", error=str(e))

        # Also prefetch operations that are due based on their access patterns
        all_operations = ["GetAccounts", "GetTransactions", "GetTransactionCategories",
                         "GetMerchants", "GetHoldings", "GetMe"]

        for operation in all_operations:
            if operation not in [f"predicted_{op}" for op in predicted_operations if triggered_by]:
                if self.should_prefetch_operation(operation):
                    try:
                        if operation == "GetAccounts":
                            await self.client.get_accounts()
                        elif operation == "GetTransactions":
                            await self._preload_recent_transactions()
                        elif operation == "GetTransactionCategories":
                            await self.client.get_transaction_categories()
                        elif operation == "GetMerchants":
                            await self.client.get_merchants()
                        elif operation == "GetHoldings":
                            await self.client._investment_service.get_all_holdings_batch()
                        elif operation == "GetMe":
                            await self.client.get_me()

                        results[f"pattern_{operation}"] = True
                        self.logger.debug(f"Pattern-based prefetch succeeded for {operation}")
                    except Exception as e:
                        results[f"pattern_{operation}"] = False
                        self.logger.debug(f"Pattern-based prefetch failed for {operation}", error=str(e))

        prefetch_count = sum(results.values())
        if prefetch_count > 0:
            self.logger.info("Predictive prefetch completed",
                           successful_prefetches=prefetch_count,
                           total_attempts=len(results))

        return results

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

        # Add predictive prefetching based on usage patterns
        try:
            predictive_results = await self.predictive_prefetch(max_operations=2)
            results.update(predictive_results)
        except Exception as e:
            self.logger.debug("Predictive prefetch failed during smart preload", error=str(e))

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

    def get_predictive_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about predictive prefetching effectiveness.

        Returns:
            Dict with predictive analytics metrics
        """
        current_time = time.time()

        # Calculate metrics from access patterns
        total_operations_tracked = len(self._access_patterns)
        total_accesses = sum(len(times) for times in self._access_patterns.values())

        # Count recent activity (last hour)
        one_hour_ago = current_time - 3600
        recent_accesses = 0
        for access_times in self._access_patterns.values():
            recent_accesses += len([t for t in access_times if t > one_hour_ago])

        # Most common operation sequences
        operation_frequencies = {}
        for operation, dependencies in self._operation_dependencies.items():
            operation_frequencies[operation] = len(dependencies)

        most_predictable = sorted(operation_frequencies.items(),
                                key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_operations_tracked": total_operations_tracked,
            "total_accesses_recorded": total_accesses,
            "recent_accesses_hour": recent_accesses,
            "operation_sequences_recorded": len(self._operation_sequences),
            "context_switches_recorded": len(self._usage_context_history),
            "most_predictable_operations": dict(most_predictable),
            "average_sequence_length": len(self._operation_sequences) / max(1, len(set(op[0] for op in self._operation_sequences))),
        }