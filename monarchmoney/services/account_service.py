"""
Account service for MonarchMoney Enhanced.

Handles all account operations including CRUD, balances, and refresh coordination.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from gql import gql

from ..exceptions import ValidationError
from ..validators import InputValidator
from .base_service import BaseService

if TYPE_CHECKING:
    from ..monarchmoney import MonarchMoney


class AccountService(BaseService):
    """
    Service for managing accounts and account operations.

    This service handles:
    - Account CRUD operations
    - Account balance history and snapshots
    - Account refresh and synchronization
    - Net worth tracking
    - Account type management
    """

    async def get_accounts(self) -> Dict[str, Any]:
        """
        Get the list of accounts configured in the Monarch Money account.

        Returns:
            List of accounts with balances, types, and institution info
        """
        self.logger.info("Fetching accounts")

        query = gql(
            """
            query GetAccounts {
                accounts {
                    id
                    displayName
                    currentBalance
                    __typename
                }
            }
        """
        )

        return await self._execute_query(operation="GetAccounts", query=query)

    async def get_institutions(self) -> Dict[str, Any]:
        """
        Get all financial institutions.

        Note: This endpoint may be unstable and could return server errors.
        If you encounter issues, use the institution data from individual accounts instead.

        Returns:
            List of financial institutions with metadata
        """
        self.logger.info("Fetching institutions")

        query = gql(
            """
            query GetInstitutions {
                institutions {
                    id
                    name
                    logo {
                        url
                        __typename
                    }
                    primaryColor
                    __typename
                }
            }
        """
        )

        return await self._execute_query(operation="GetInstitutions", query=query)

    async def get_account_type_options(self) -> Dict[str, Any]:
        """
        Get available account types and subtypes for account creation.

        Returns:
            Account type options with display names and groupings
        """
        self.logger.info("Fetching account type options")

        query = gql(
            """
            query GetAccountTypeOptions {
                accountTypeOptions {
                    type {
                        name
                        display
                        group
                        __typename
                    }
                    subtypes {
                        name
                        display
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(operation="GetAccountTypeOptions", query=query)

    async def create_manual_account(
        self,
        name: str,
        type_name: str,
        subtype_name: Optional[str] = None,
        balance: Optional[Union[str, int, float]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new manual account.

        Args:
            name: Display name for the account
            type_name: Account type (e.g., "checking", "savings", "investment")
            subtype_name: Account subtype (optional)
            balance: Initial account balance (optional)

        Returns:
            Created account data

        Raises:
            ValidationError: If account data is invalid
        """
        name = InputValidator.validate_string_length(name, "account name", 1, 100)
        type_name = InputValidator.validate_string_length(type_name, "type_name", 1, 50)

        if subtype_name:
            subtype_name = InputValidator.validate_string_length(
                subtype_name, "subtype_name", 1, 50
            )

        if balance is not None:
            balance = InputValidator.validate_amount(balance)

        self.logger.info(
            "Creating manual account",
            name=name,
            type_name=type_name,
            subtype_name=subtype_name,
            balance=balance,
        )

        variables = {
            "displayName": name,
            "typeName": type_name,
        }

        if subtype_name:
            variables["subtypeName"] = subtype_name
        if balance is not None:
            variables["balance"] = balance

        query = gql(
            """
            mutation Web_CreateManualAccount(
                $displayName: String!,
                $typeName: String!,
                $subtypeName: String,
                $balance: Float
            ) {
                createManualAccount(
                    displayName: $displayName,
                    typeName: $typeName,
                    subtypeName: $subtypeName,
                    balance: $balance
                ) {
                    account {
                        id
                        displayName
                        currentBalance
                        availableBalance
                        type {
                            name
                            display
                            __typename
                        }
                        subtype {
                            name
                            display
                            __typename
                        }
                        __typename
                    }
                    errors {
                        field
                        messages
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="Web_CreateManualAccount",
            graphql_query=query,
            variables=variables,
        )

    async def update_account(
        self,
        account_id: str,
        display_name: Optional[str] = None,
        is_hidden: Optional[bool] = None,
        sync_disabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update account details.

        Args:
            account_id: ID of the account to update
            display_name: New display name
            is_hidden: Whether to hide the account
            sync_disabled: Whether to disable sync for the account

        Returns:
            Updated account data

        Raises:
            ValidationError: If account data is invalid
        """
        account_id = InputValidator.validate_account_id(account_id)

        if display_name is not None:
            display_name = InputValidator.validate_string_length(
                display_name, "display_name", 1, 100
            )

        self.logger.info(
            "Updating account",
            account_id=account_id,
            display_name=display_name,
            is_hidden=is_hidden,
        )

        variables = {"id": account_id}

        if display_name is not None:
            variables["displayName"] = display_name
        if is_hidden is not None:
            variables["isHidden"] = is_hidden
        if sync_disabled is not None:
            variables["syncDisabled"] = sync_disabled

        query = gql(
            """
            mutation Common_UpdateAccount(
                $id: String!,
                $displayName: String,
                $isHidden: Boolean,
                $syncDisabled: Boolean
            ) {
                updateAccount(
                    id: $id,
                    displayName: $displayName,
                    isHidden: $isHidden,
                    syncDisabled: $syncDisabled
                ) {
                    account {
                        id
                        displayName
                        isHidden
                        syncDisabled
                        currentBalance
                        availableBalance
                        type {
                            name
                            display
                            __typename
                        }
                        subtype {
                            name
                            display
                            __typename
                        }
                        __typename
                    }
                    errors {
                        field
                        messages
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="Common_UpdateAccount", graphql_query=query, variables=variables
        )

    async def delete_account(self, account_id: str) -> bool:
        """
        Delete an account.

        Args:
            account_id: ID of the account to delete

        Returns:
            True if deletion was successful

        Raises:
            ValidationError: If account_id is invalid
        """
        account_id = InputValidator.validate_account_id(account_id)

        self.logger.info("Deleting account", account_id=account_id)

        variables = {"id": account_id}

        query = gql(
            """
            mutation Common_DeleteAccount($id: String!) {
                deleteAccount(id: $id) {
                    deleted
                    errors {
                        field
                        messages
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        result = await self.client.gql_call(
            operation="Common_DeleteAccount", graphql_query=query, variables=variables
        )

        delete_result = result.get("deleteAccount", {})
        errors = delete_result.get("errors", [])

        if errors:
            self.logger.error(
                "Account deletion failed", account_id=account_id, errors=errors
            )
            return False

        success = delete_result.get("deleted", False)
        if success:
            self.logger.info("Account deleted successfully", account_id=account_id)

        return success

    async def get_recent_account_balances(
        self,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get recent balance history for accounts.

        Args:
            account_id: Specific account ID (optional, gets all if not provided)
            start_date: Start date for balance history (YYYY-MM-DD)
            end_date: End date for balance history (YYYY-MM-DD)

        Returns:
            Recent balance data for accounts
        """
        if account_id:
            account_id = InputValidator.validate_account_id(account_id)
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching recent account balances",
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
        )

        variables = {}
        if account_id:
            variables["accountId"] = account_id
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date

        query = gql(
            """
            query GetAccountRecentBalances(
                $accountId: String,
                $startDate: String,
                $endDate: String
            ) {
                accountBalanceHistory(
                    accountId: $accountId,
                    startDate: $startDate,
                    endDate: $endDate
                ) {
                    account {
                        id
                        displayName
                        __typename
                    }
                    balances {
                        date
                        balance
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetAccountRecentBalances",
            graphql_query=query,
            variables=variables,
        )

    async def get_account_history(
        self,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed account information with transaction history.

        Args:
            account_id: ID of the account
            start_date: Start date for history (YYYY-MM-DD)
            end_date: End date for history (YYYY-MM-DD)

        Returns:
            Detailed account info with transaction history

        Raises:
            ValidationError: If account_id is invalid
        """
        account_id = InputValidator.validate_account_id(account_id)

        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching account history",
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
        )

        variables = {"accountId": account_id}

        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date

        query = gql(
            """
            query AccountDetails_getAccount(
                $accountId: String!,
                $startDate: String,
                $endDate: String
            ) {
                account(id: $accountId) {
                    id
                    displayName
                    currentBalance
                    availableBalance
                    type {
                        name
                        display
                        __typename
                    }
                    subtype {
                        name
                        display
                        __typename
                    }
                    institution {
                        id
                        name
                        logo {
                            url
                            __typename
                        }
                        __typename
                    }
                    transactions(
                        startDate: $startDate,
                        endDate: $endDate
                    ) {
                        id
                        amount
                        date
                        merchant {
                            name
                            __typename
                        }
                        category {
                            id
                            name
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="AccountDetails_getAccount",
            graphql_query=query,
            variables=variables,
        )

    async def request_accounts_refresh(self) -> Dict[str, Any]:
        """
        Request account data refresh from financial institutions.

        Returns:
            Refresh request status and details
        """
        self.logger.info("Requesting accounts refresh")

        query = gql(
            """
            mutation Common_ForceRefreshAccountsMutation {
                forceRefreshAccounts {
                    refreshId
                    status
                    message
                    errors {
                        field
                        messages
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="Common_ForceRefreshAccountsMutation", query=query
        )

    async def is_accounts_refresh_complete(
        self, refresh_id: Optional[str] = None, account_ids: Optional[List[str]] = None
    ) -> bool:
        """
        Check if account refresh is complete.

        Args:
            refresh_id: Optional specific refresh ID to check
            account_ids: Optional list of account IDs to check (if provided, only these accounts need to be complete)

        Returns:
            True if refresh is complete, False otherwise
        """
        self.logger.info(
            "Checking accounts refresh status",
            refresh_id=refresh_id,
            account_ids_count=len(account_ids) if account_ids else None,
        )

        # Validate account IDs if provided
        if account_ids:
            account_ids = [
                InputValidator.validate_account_id(account_id)
                for account_id in account_ids
            ]

        variables = {}
        if refresh_id:
            variables["refreshId"] = refresh_id
        if account_ids:
            variables["accountIds"] = account_ids

        query = gql(
            """
            query ForceRefreshAccountsQuery($refreshId: String, $accountIds: [String!]) {
                accountsRefreshStatus(refreshId: $refreshId, accountIds: $accountIds) {
                    status
                    isComplete
                    message
                    accountsStatus {
                        accountId
                        isComplete
                        status
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        result = await self.client.gql_call(
            operation="ForceRefreshAccountsQuery",
            graphql_query=query,
            variables=variables,
        )

        refresh_status = result.get("accountsRefreshStatus", {})
        is_complete = refresh_status.get("isComplete", False)

        self.logger.debug(
            "Refresh status check",
            is_complete=is_complete,
            status=refresh_status.get("status"),
        )
        return is_complete

    async def request_accounts_refresh_and_wait(
        self, timeout: int = 60, poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Request account refresh and wait for completion.

        Args:
            timeout: Maximum time to wait in seconds
            poll_interval: How often to check status in seconds

        Returns:
            Final refresh status

        Raises:
            TimeoutError: If refresh doesn't complete within timeout
        """
        import asyncio

        self.logger.info("Requesting accounts refresh and waiting", timeout=timeout)

        # Start the refresh
        refresh_result = await self.request_accounts_refresh()
        refresh_id = refresh_result.get("forceRefreshAccounts", {}).get("refreshId")

        if not refresh_id:
            return refresh_result

        # Poll for completion
        elapsed = 0
        while elapsed < timeout:
            if await self.is_accounts_refresh_complete(refresh_id):
                self.logger.info("Accounts refresh completed", elapsed=elapsed)
                return {"status": "completed", "refreshId": refresh_id}

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        self.logger.warning("Accounts refresh timed out", timeout=timeout)
        raise TimeoutError(f"Account refresh did not complete within {timeout} seconds")

    async def get_net_worth_history(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: Optional[str] = "monthly",
    ) -> Dict[str, Any]:
        """
        Get net worth history over time with breakdown by account type.

        Args:
            start_date: Start date for history (YYYY-MM-DD)
            end_date: End date for history (YYYY-MM-DD)
            interval: Data interval ("daily", "weekly", "monthly")

        Returns:
            Net worth tracking data with account type breakdown
        """
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching net worth history",
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )

        variables = {}
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date
        if interval:
            variables["interval"] = interval

        query = gql(
            """
            query GetNetWorthHistory(
                $startDate: String,
                $endDate: String,
                $interval: String
            ) {
                netWorthHistory(
                    startDate: $startDate,
                    endDate: $endDate,
                    interval: $interval
                ) {
                    date
                    assets
                    liabilities
                    netWorth
                    breakdown {
                        accountType
                        amount
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetNetWorthHistory", graphql_query=query, variables=variables
        )

    async def get_account_snapshots_by_type(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get balance snapshots grouped by account type.

        Args:
            start_date: Start date for snapshots (YYYY-MM-DD)
            end_date: End date for snapshots (YYYY-MM-DD)

        Returns:
            Balance snapshots organized by account type
        """
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching account snapshots by type",
            start_date=start_date,
            end_date=end_date,
        )

        variables = {}
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date

        query = gql(
            """
            query GetSnapshotsByAccountType(
                $startDate: String,
                $endDate: String
            ) {
                snapshotsByAccountType(
                    startDate: $startDate,
                    endDate: $endDate
                ) {
                    accountType {
                        name
                        display
                        group
                        __typename
                    }
                    snapshots {
                        date
                        balance
                        __typename
                    }
                    totalBalance
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetSnapshotsByAccountType",
            graphql_query=query,
            variables=variables,
        )

    async def get_aggregate_snapshots(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: Optional[str] = "month",
    ) -> Dict[str, Any]:
        """
        Get aggregated balance snapshots across timeframes.

        Args:
            start_date: Start date for aggregation (YYYY-MM-DD)
            end_date: End date for aggregation (YYYY-MM-DD)
            group_by: Aggregation period ("day", "week", "month", "year")

        Returns:
            Aggregated balance data across specified timeframe
        """
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching aggregate snapshots",
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
        )

        variables = {}
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date
        if group_by:
            variables["groupBy"] = group_by

        query = gql(
            """
            query GetAggregateSnapshots(
                $startDate: String,
                $endDate: String,
                $groupBy: String
            ) {
                aggregateSnapshots(
                    startDate: $startDate,
                    endDate: $endDate,
                    groupBy: $groupBy
                ) {
                    period
                    totalAssets
                    totalLiabilities
                    netWorth
                    breakdown {
                        accountType
                        amount
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetAggregateSnapshots",
            graphql_query=query,
            variables=variables,
        )

    async def upload_account_balance_history(
        self, account_id: str, balance_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Upload historical balance data for an account.

        Args:
            account_id: ID of the account
            balance_data: List of balance entries with date and balance

        Returns:
            Upload result with success/error information

        Raises:
            ValidationError: If account_id or balance_data is invalid
        """
        account_id = InputValidator.validate_account_id(account_id)

        # Validate balance data
        validated_data = []
        for entry in balance_data:
            if not isinstance(entry, dict):
                raise ValidationError("Each balance entry must be a dictionary")

            validated_entry = {
                "date": InputValidator.validate_date_string(entry.get("date")),
                "balance": InputValidator.validate_amount(entry.get("balance")),
            }
            validated_data.append(validated_entry)

        self.logger.info(
            "Uploading account balance history",
            account_id=account_id,
            entries_count=len(validated_data),
        )

        # This would typically use the REST endpoint for file upload
        # For now, return a placeholder response
        import json

        from aiohttp import ClientSession, FormData

        from ..monarchmoney import MonarchMoneyEndpoints

        async with ClientSession() as session:
            form_data = FormData()
            form_data.add_field("account_id", account_id)
            form_data.add_field("balance_data", json.dumps(validated_data))

            async with session.post(
                MonarchMoneyEndpoints.getAccountBalanceHistoryUploadEndpoint(),
                data=form_data,
                headers=self.client._headers,
            ) as response:
                if response.ok:
                    result = await response.json()
                    self.logger.info(
                        "Balance history uploaded successfully",
                        account_id=account_id,
                        entries_processed=result.get("entries_processed", 0),
                    )
                    return result
                else:
                    error_text = await response.text()
                    self.logger.error(
                        "Balance history upload failed",
                        account_id=account_id,
                        status=response.status,
                        error=error_text,
                    )
                    return {
                        "success": False,
                        "error": f"Upload failed with status {response.status}",
                    }
