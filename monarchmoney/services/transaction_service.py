"""
Transaction service for MonarchMoney Enhanced.

Handles all transaction operations, rules, categories, tags, and splits.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from gql import gql

from ..exceptions import ValidationError
from ..validators import InputValidator
from .base_service import BaseService

if TYPE_CHECKING:
    from ..monarchmoney import MonarchMoney


class TransactionService(BaseService):
    """
    Service for managing transactions and related operations.

    This service handles:
    - Transaction CRUD operations
    - Transaction rules (create, update, delete, preview)
    - Transaction categories and category groups
    - Transaction tags
    - Transaction splits
    - Recurring transactions
    """

    async def get_transactions_summary(self) -> Dict[str, Any]:
        """
        Get a summary of transactions for the account.

        Returns:
            Transaction summary with aggregates and overview data
        """
        self.logger.info("Fetching transactions summary")

        query = gql(
            """
            query GetTransactionsPage {
                accounts {
                    id
                    displayName
                    __typename
                }
                categories {
                    ...CategoryFields
                    __typename
                }
                categoryGroups {
                    id
                    name
                    __typename
                }
            }

            fragment CategoryFields on Category {
                id
                name
                icon
                color
                group {
                    id
                    type
                    __typename
                }
                __typename
            }
        """
        )

        return await self._execute_query(operation="GetTransactionsPage", query=query)

    async def get_transactions_summary_card(self) -> Dict[str, Any]:
        """
        Get transaction summary card data.

        Returns:
            Transaction summary card with total counts and key metrics
        """
        self.logger.info("Fetching transaction summary card")

        query = gql(
            """
            query Web_GetTransactionsSummaryCard {
                transactionsSummaryCard {
                    totalTransactionsCount
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="Web_GetTransactionsSummaryCard", query=query
        )

    async def get_transactions(
        self,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category_ids: Optional[List[str]] = None,
        account_ids: Optional[List[str]] = None,
        tag_ids: Optional[List[str]] = None,
        merchant_ids: Optional[List[str]] = None,
        search: Optional[str] = None,
        is_credit: Optional[bool] = None,
        abs_amount_range: Optional[List[Optional[float]]] = None,
    ) -> Dict[str, Any]:
        """
        Get paginated list of transactions with filtering options.

        Args:
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            start_date: Filter start date (YYYY-MM-DD)
            end_date: Filter end date (YYYY-MM-DD)
            category_ids: List of category IDs to filter by
            account_ids: List of account IDs to filter by
            tag_ids: List of tag IDs to filter by
            merchant_ids: List of merchant IDs to filter by
            search: Search term for transaction description/merchant
            is_credit: Filter by transaction type (True=credits/income, False=debits/expenses)
            abs_amount_range: Filter by absolute amount range [min, max]. Use None for open-ended ranges.

        Returns:
            Paginated transaction list with total count and filtering metadata

        Examples:
            # Get only credit transactions (income)
            transactions = await mm.get_transactions(is_credit=True)

            # Get only debit transactions (expenses)
            transactions = await mm.get_transactions(is_credit=False)

            # Get transactions >= $100
            transactions = await mm.get_transactions(abs_amount_range=[100.0, None])

            # Get transactions <= $50
            transactions = await mm.get_transactions(abs_amount_range=[None, 50.0])

            # Get transactions between $20 and $100
            transactions = await mm.get_transactions(abs_amount_range=[20.0, 100.0])

            # Get transactions exactly $25.99
            transactions = await mm.get_transactions(abs_amount_range=[25.99, 25.99])
        """
        # Validate inputs
        validated_limit = InputValidator.validate_limit(limit) or 100
        validated_offset = offset or 0

        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        # Validate amount range
        if abs_amount_range is not None:
            if not isinstance(abs_amount_range, list) or len(abs_amount_range) != 2:
                raise ValueError(
                    "abs_amount_range must be a list of two values: [min, max]"
                )

            min_amount, max_amount = abs_amount_range
            if min_amount is not None and min_amount < 0:
                raise ValueError("min_amount must be non-negative or None")
            if max_amount is not None and max_amount < 0:
                raise ValueError("max_amount must be non-negative or None")
            if (
                min_amount is not None
                and max_amount is not None
                and min_amount > max_amount
            ):
                raise ValueError("min_amount cannot be greater than max_amount")

        self.logger.info(
            "Fetching transactions",
            limit=validated_limit,
            offset=validated_offset,
            start_date=start_date,
            end_date=end_date,
            is_credit=is_credit,
            abs_amount_range=abs_amount_range,
        )

        variables = {
            "limit": validated_limit,
            "offset": validated_offset,
        }

        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date
        if category_ids:
            variables["categoryIds"] = category_ids
        if account_ids:
            variables["accountIds"] = account_ids
        if tag_ids:
            variables["tagIds"] = tag_ids
        if merchant_ids:
            variables["merchantIds"] = merchant_ids
        if search:
            variables["search"] = search
        if is_credit is not None:
            variables["isCredit"] = is_credit
        if abs_amount_range is not None:
            variables["minAmount"] = abs_amount_range[0]
            variables["maxAmount"] = abs_amount_range[1]

        query = gql(
            """
            query GetTransactionsList(
                $limit: Int!,
                $offset: Int!,
                $startDate: String,
                $endDate: String,
                $categoryIds: [String],
                $accountIds: [String],
                $tagIds: [String],
                $merchantIds: [String],
                $search: String,
                $isCredit: Boolean,
                $minAmount: Float,
                $maxAmount: Float
            ) {
                allTransactions(
                    first: $limit,
                    offset: $offset,
                    startDate: $startDate,
                    endDate: $endDate,
                    categoryIds: $categoryIds,
                    accountIds: $accountIds,
                    tagIds: $tagIds,
                    merchantIds: $merchantIds,
                    search: $search,
                    isCredit: $isCredit,
                    minAmount: $minAmount,
                    maxAmount: $maxAmount
                ) {
                    totalCount
                    results {
                        ...TransactionFields
                        __typename
                    }
                    __typename
                }
                accounts {
                    id
                    displayName
                    __typename
                }
            }

            fragment TransactionFields on Transaction {
                id
                amount
                date
                hideFromReports
                plaidName
                notes
                isRecurring
                reviewStatus
                needsReview
                dataProviderDescription
                originalDescription
                isChild
                merchant {
                    id
                    name
                    __typename
                }
                category {
                    id
                    name
                    icon
                    color
                    __typename
                }
                account {
                    id
                    displayName
                    __typename
                }
                tags {
                    id
                    name
                    color
                    __typename
                }
                __typename
            }
        """
        )

        # Validate variables for potential injection
        variables = InputValidator.validate_graphql_variables(variables)

        return await self.client.gql_call(
            operation="GetTransactionsList", graphql_query=query, variables=variables
        )

    async def create_transaction(
        self,
        account_id: str,
        merchant: str,
        amount: Union[str, int, float],
        date: str,
        category_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new transaction.

        Args:
            account_id: ID of the account for the transaction
            merchant: Merchant/description for the transaction
            amount: Transaction amount (negative for expenses, positive for income)
            date: Transaction date (YYYY-MM-DD)
            category_id: Optional category ID
            notes: Optional transaction notes

        Returns:
            Created transaction data

        Raises:
            ValidationError: If required parameters are invalid
        """
        # Validate inputs
        account_id = InputValidator.validate_account_id(account_id)
        merchant = InputValidator.validate_string_length(merchant, "merchant", 1, 200)
        amount = InputValidator.validate_amount(amount)
        date = InputValidator.validate_date_string(date)

        if notes:
            notes = InputValidator.validate_string_length(notes, "notes", 0, 500)

        self.logger.info(
            "Creating transaction",
            account_id=account_id,
            merchant=merchant,
            amount=amount,
            date=date,
        )

        variables = {
            "accountId": account_id,
            "merchant": merchant,
            "amount": amount,
            "date": date,
        }

        if category_id:
            variables["categoryId"] = category_id
        if notes:
            variables["notes"] = notes

        query = gql(
            """
            mutation Common_CreateTransactionMutation(
                $accountId: String!,
                $merchant: String!,
                $amount: Float!,
                $date: String!,
                $categoryId: String,
                $notes: String
            ) {
                createTransaction(
                    accountId: $accountId,
                    merchant: $merchant,
                    amount: $amount,
                    date: $date,
                    categoryId: $categoryId,
                    notes: $notes
                ) {
                    transaction {
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
                        account {
                            id
                            displayName
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
            operation="Common_CreateTransactionMutation",
            graphql_query=query,
            variables=variables,
        )

    async def delete_transaction(self, transaction_id: str) -> bool:
        """
        Delete a transaction.

        Args:
            transaction_id: ID of the transaction to delete

        Returns:
            True if deletion was successful

        Raises:
            ValidationError: If transaction_id is invalid
        """
        transaction_id = InputValidator.validate_transaction_id(transaction_id)

        self.logger.info("Deleting transaction", transaction_id=transaction_id)

        variables = {"id": transaction_id}

        query = gql(
            """
            mutation Common_DeleteTransactionMutation($id: String!) {
                deleteTransaction(id: $id) {
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
            operation="Common_DeleteTransactionMutation",
            graphql_query=query,
            variables=variables,
        )

        delete_result = result.get("deleteTransaction", {})
        errors = delete_result.get("errors", [])

        if errors:
            self.logger.error(
                "Transaction deletion failed",
                transaction_id=transaction_id,
                errors=errors,
            )
            return False

        success = delete_result.get("deleted", False)
        if success:
            self.logger.info(
                "Transaction deleted successfully", transaction_id=transaction_id
            )

        return success

    async def update_transaction(
        self,
        transaction_id: str,
        merchant: Optional[str] = None,
        amount: Optional[Union[str, int, float]] = None,
        date: Optional[str] = None,
        category_id: Optional[str] = None,
        notes: Optional[str] = None,
        hide_from_reports: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing transaction.

        Args:
            transaction_id: ID of the transaction to update
            merchant: New merchant name
            amount: New transaction amount
            date: New transaction date (YYYY-MM-DD)
            category_id: New category ID
            notes: New transaction notes
            hide_from_reports: Whether to hide from reports

        Returns:
            Updated transaction data

        Raises:
            ValidationError: If parameters are invalid
        """
        # Validate inputs
        transaction_id = InputValidator.validate_transaction_id(transaction_id)

        if merchant is not None:
            merchant = InputValidator.validate_string_length(
                merchant, "merchant", 1, 200
            )
        if amount is not None:
            amount = InputValidator.validate_amount(amount)
        if date is not None:
            date = InputValidator.validate_date_string(date)
        if notes is not None:
            notes = InputValidator.validate_string_length(notes, "notes", 0, 500)

        self.logger.info(
            "Updating transaction",
            transaction_id=transaction_id,
            merchant=merchant,
            amount=amount,
            date=date,
        )

        # Build variables with only non-None values
        variables = {"id": transaction_id}

        if merchant is not None:
            variables["merchant"] = merchant
        if amount is not None:
            variables["amount"] = amount
        if date is not None:
            variables["date"] = date
        if category_id is not None:
            variables["categoryId"] = category_id
        if notes is not None:
            variables["notes"] = notes
        if hide_from_reports is not None:
            variables["hideFromReports"] = hide_from_reports

        query = gql(
            """
            mutation Web_TransactionDrawerUpdateTransaction(
                $id: String!,
                $merchant: String,
                $amount: Float,
                $date: String,
                $categoryId: String,
                $notes: String,
                $hideFromReports: Boolean
            ) {
                updateTransaction(
                    id: $id,
                    merchant: $merchant,
                    amount: $amount,
                    date: $date,
                    categoryId: $categoryId,
                    notes: $notes,
                    hideFromReports: $hideFromReports
                ) {
                    transaction {
                        id
                        amount
                        date
                        notes
                        hideFromReports
                        merchant {
                            id
                            name
                            __typename
                        }
                        category {
                            id
                            name
                            icon
                            color
                            __typename
                        }
                        account {
                            id
                            displayName
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
            operation="Web_TransactionDrawerUpdateTransaction",
            graphql_query=query,
            variables=variables,
        )

    async def get_transaction_details(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a single transaction.

        Args:
            transaction_id: ID of the transaction

        Returns:
            Detailed transaction data including splits, tags, and related info

        Raises:
            ValidationError: If transaction_id is invalid
        """
        transaction_id = InputValidator.validate_transaction_id(transaction_id)

        self.logger.info("Fetching transaction details", transaction_id=transaction_id)

        variables = {"id": transaction_id}

        query = gql(
            """
            query GetTransactionDrawer($id: String!) {
                transaction(id: $id) {
                    ...TransactionDrawerFields
                    __typename
                }
                categories {
                    ...CategoryFields
                    __typename
                }
                tags {
                    id
                    name
                    color
                    __typename
                }
            }

            fragment TransactionDrawerFields on Transaction {
                id
                amount
                date
                hideFromReports
                plaidName
                notes
                isRecurring
                reviewStatus
                needsReview
                dataProviderDescription
                originalDescription
                isChild
                merchant {
                    id
                    name
                    __typename
                }
                category {
                    id
                    name
                    icon
                    color
                    __typename
                }
                account {
                    id
                    displayName
                    institution {
                        name
                        __typename
                    }
                    __typename
                }
                tags {
                    id
                    name
                    color
                    __typename
                }
                splits {
                    id
                    amount
                    category {
                        id
                        name
                        __typename
                    }
                    __typename
                }
                __typename
            }

            fragment CategoryFields on Category {
                id
                name
                icon
                color
                group {
                    id
                    type
                    __typename
                }
                __typename
            }
        """
        )

        return await self.client.gql_call(
            operation="GetTransactionDrawer", graphql_query=query, variables=variables
        )

    async def get_transaction_splits(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get splits for a transaction.

        Args:
            transaction_id: ID of the transaction

        Returns:
            Transaction splits data

        Raises:
            ValidationError: If transaction_id is invalid
        """
        transaction_id = InputValidator.validate_transaction_id(transaction_id)

        self.logger.info("Fetching transaction splits", transaction_id=transaction_id)

        variables = {"transactionId": transaction_id}

        query = gql(
            """
            query TransactionSplitQuery($transactionId: String!) {
                transaction(id: $transactionId) {
                    id
                    splits {
                        id
                        amount
                        category {
                            id
                            name
                            icon
                            color
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
                categories {
                    id
                    name
                    icon
                    color
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="TransactionSplitQuery", graphql_query=query, variables=variables
        )

    async def update_transaction_splits(
        self,
        transaction_id: str,
        splits: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Update splits for a transaction.

        Args:
            transaction_id: ID of the transaction
            splits: List of split data with amount and category_id

        Returns:
            Updated transaction with splits

        Raises:
            ValidationError: If inputs are invalid
        """
        transaction_id = InputValidator.validate_transaction_id(transaction_id)

        # Validate splits
        validated_splits = []
        for split in splits:
            if not isinstance(split, dict):
                raise ValidationError("Each split must be a dictionary")

            split_data = {
                "amount": InputValidator.validate_amount(split.get("amount")),
                "categoryId": split.get("category_id") or split.get("categoryId"),
            }
            validated_splits.append(split_data)

        self.logger.info(
            "Updating transaction splits",
            transaction_id=transaction_id,
            splits_count=len(validated_splits),
        )

        variables = {
            "transactionId": transaction_id,
            "splits": validated_splits,
        }

        query = gql(
            """
            mutation Common_SplitTransactionMutation(
                $transactionId: String!,
                $splits: [TransactionSplitInput!]!
            ) {
                splitTransaction(
                    transactionId: $transactionId,
                    splits: $splits
                ) {
                    transaction {
                        id
                        splits {
                            id
                            amount
                            category {
                                id
                                name
                                __typename
                            }
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
            operation="Common_SplitTransactionMutation",
            graphql_query=query,
            variables=variables,
        )

    async def get_recurring_transactions(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get future recurring transactions.

        Args:
            start_date: Start date for recurring transactions (YYYY-MM-DD)
            end_date: End date for recurring transactions (YYYY-MM-DD)

        Returns:
            Recurring transactions data
        """
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching recurring transactions",
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
            query GetRecurringTransactions(
                $startDate: String,
                $endDate: String
            ) {
                recurringTransactions(
                    startDate: $startDate,
                    endDate: $endDate
                ) {
                    id
                    amount
                    frequency
                    nextDate
                    endDate
                    merchant {
                        name
                        __typename
                    }
                    category {
                        id
                        name
                        __typename
                    }
                    account {
                        id
                        displayName
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetRecurringTransactions",
            graphql_query=query,
            variables=variables,
        )

    async def get_recurring_streams(
        self,
        include_liabilities: bool = True,
        include_pending: bool = True,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get all recurring transaction streams.

        Args:
            include_liabilities: Include liability-based streams (credit cards, loans)
            include_pending: Include streams pending review
            filters: Optional filters for accounts, categories, etc.

        Returns:
            List of recurring transaction streams with details
        """
        self.logger.info(
            "Fetching recurring streams",
            include_liabilities=include_liabilities,
            include_pending=include_pending,
            filters=filters,
        )

        variables = {
            "includeLiabilities": include_liabilities,
            "includePending": include_pending,
        }

        if filters:
            variables["filters"] = filters

        query = gql(
            """
            query Common_GetRecurringStreams(
                $includeLiabilities: Boolean,
                $includePending: Boolean,
                $filters: RecurringTransactionFilter
            ) {
                recurringTransactionStreams(
                    includePending: $includePending,
                    includeLiabilities: $includeLiabilities,
                    filters: $filters
                ) {
                    stream {
                        id
                        reviewStatus
                        frequency
                        amount
                        baseDate
                        dayOfTheMonth
                        isApproximate
                        name
                        logoUrl
                        recurringType
                        isActive
                        merchant {
                            id
                            name
                            logoUrl
                            __typename
                        }
                        creditReportLiabilityAccount {
                            id
                            account {
                                id
                                displayName
                                __typename
                            }
                            lastStatement {
                                id
                                dueDate
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    nextForecastedTransaction {
                        date
                        amount
                        __typename
                    }
                    category {
                        id
                        name
                        icon
                        __typename
                    }
                    account {
                        id
                        displayName
                        icon
                        logoUrl
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="Common_GetRecurringStreams", query=query, variables=variables
        )

    async def get_aggregated_recurring_items(
        self,
        start_date: str,
        end_date: str,
        group_by: str = "status",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated recurring transaction items for a date range.

        Args:
            start_date: Start date for recurring items (YYYY-MM-DD)
            end_date: End date for recurring items (YYYY-MM-DD)
            group_by: How to group results ("status", "category", "account")
            filters: Optional filters for accounts, categories, etc.

        Returns:
            Aggregated recurring transaction items with summaries

        Raises:
            ValidationError: If dates are invalid
        """
        start_date = InputValidator.validate_date_string(start_date)
        end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching aggregated recurring items",
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            filters=filters,
        )

        variables = {
            "startDate": start_date,
            "endDate": end_date,
            "groupBy": group_by,
        }

        if filters:
            variables["filters"] = filters

        query = gql(
            """
            query Common_GetAggregatedRecurringItems(
                $startDate: Date!,
                $endDate: Date!,
                $groupBy: String!,
                $filters: RecurringTransactionFilter
            ) {
                aggregatedRecurringItems(
                    startDate: $startDate,
                    endDate: $endDate,
                    groupBy: $groupBy,
                    filters: $filters
                ) {
                    groups {
                        groupBy {
                            status
                            __typename
                        }
                        results {
                            ...RecurringItemFields
                            __typename
                        }
                        summary {
                            expense {
                                total
                                __typename
                            }
                            creditCard {
                                total
                                __typename
                            }
                            income {
                                total
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    aggregatedSummary {
                        expense {
                            completed
                            remaining
                            total
                            count
                            pendingAmountCount
                            __typename
                        }
                        creditCard {
                            completed
                            remaining
                            total
                            count
                            pendingAmountCount
                            __typename
                        }
                        income {
                            completed
                            remaining
                            total
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
            }

            fragment RecurringItemStreamFields on RecurringTransactionStream {
                id
                frequency
                isActive
                amount
                isApproximate
                name
                logoUrl
                merchant {
                    id
                    name
                    logoUrl
                    __typename
                }
                creditReportLiabilityAccount {
                    id
                    liabilityType
                    account {
                        id
                        __typename
                    }
                    __typename
                }
                __typename
            }

            fragment RecurringItemLiabilityFields on LiabilityStatement {
                id
                minimumPaymentAmount
                paymentsInformation {
                    status
                    remainingBalance
                    transactions {
                        id
                        amount
                        date
                        category {
                            id
                            name
                            icon
                            group {
                                id
                                name
                                type
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
                __typename
            }

            fragment RecurringItemFields on RecurringTransactionCalendarItem {
                stream {
                    ...RecurringItemStreamFields
                    __typename
                }
                date
                isPast
                isLate
                markedPaidAt
                isCompleted
                transactionId
                amount
                amountDiff
                isAmountDifferentThanOriginal
                creditReportLiabilityStatementId
                category {
                    id
                    name
                    icon
                    __typename
                }
                account {
                    id
                    displayName
                    icon
                    logoUrl
                    __typename
                }
                liabilityStatement {
                    ...RecurringItemLiabilityFields
                    __typename
                }
                __typename
            }
        """
        )

        return await self._execute_query(
            operation="Common_GetAggregatedRecurringItems",
            query=query,
            variables=variables,
        )

    async def review_recurring_stream(
        self, stream_id: str, review_status: str
    ) -> Dict[str, Any]:
        """
        Review and update the status of a recurring transaction stream.

        Args:
            stream_id: ID of the recurring stream to review
            review_status: New status ("approved", "ignored", "pending")

        Returns:
            Updated stream information

        Raises:
            ValidationError: If parameters are invalid
        """
        stream_id = InputValidator.validate_string_length(
            stream_id, "stream_id", 1, 100
        )

        valid_statuses = ["approved", "ignored", "pending"]
        if review_status not in valid_statuses:
            raise ValueError(f"review_status must be one of: {valid_statuses}")

        self.logger.info(
            "Reviewing recurring stream",
            stream_id=stream_id,
            review_status=review_status,
        )

        variables = {
            "input": {
                "streamId": stream_id,
                "reviewStatus": review_status,
            }
        }

        query = gql(
            """
            mutation Web_ReviewStream($input: ReviewRecurringStreamInput!) {
                reviewRecurringStream(input: $input) {
                    stream {
                        id
                        reviewStatus
                        __typename
                    }
                    errors {
                        ...PayloadErrorFields
                        __typename
                    }
                    __typename
                }
            }

            fragment PayloadErrorFields on PayloadError {
                fieldErrors {
                    field
                    messages
                    __typename
                }
                message
                code
                __typename
            }
        """
        )

        result = await self.client.gql_call(
            operation="Web_ReviewStream",
            graphql_query=query,
            variables=variables,
        )

        review_result = result.get("reviewRecurringStream", {})
        errors = review_result.get("errors", [])

        if errors:
            self.logger.error(
                "Stream review failed", stream_id=stream_id, errors=errors
            )
            raise ValueError(f"Failed to review stream: {errors}")

        stream = review_result.get("stream")
        if stream:
            self.logger.info(
                "Stream review successful",
                stream_id=stream_id,
                new_status=stream.get("reviewStatus"),
            )

        return review_result

    async def mark_stream_as_not_recurring(self, stream_id: str) -> bool:
        """
        Mark a recurring stream as not recurring (disable it).

        Args:
            stream_id: ID of the recurring stream to disable

        Returns:
            True if successful, False otherwise

        Raises:
            ValidationError: If stream_id is invalid
        """
        stream_id = InputValidator.validate_string_length(
            stream_id, "stream_id", 1, 100
        )

        self.logger.info("Marking stream as not recurring", stream_id=stream_id)

        variables = {"streamId": stream_id}

        query = gql(
            """
            mutation Common_MarkAsNotRecurring($streamId: ID!) {
                markStreamAsNotRecurring(streamId: $streamId) {
                    success
                    errors {
                        ...PayloadErrorFields
                        __typename
                    }
                    __typename
                }
            }

            fragment PayloadErrorFields on PayloadError {
                fieldErrors {
                    field
                    messages
                    __typename
                }
                message
                code
                __typename
            }
        """
        )

        result = await self.client.gql_call(
            operation="Common_MarkAsNotRecurring",
            graphql_query=query,
            variables=variables,
        )

        mark_result = result.get("markStreamAsNotRecurring", {})
        errors = mark_result.get("errors", [])

        if errors:
            self.logger.error(
                "Mark as not recurring failed", stream_id=stream_id, errors=errors
            )
            return False

        success = mark_result.get("success", False)
        if success:
            self.logger.info("Stream marked as not recurring", stream_id=stream_id)

        return success

    async def get_recurring_merchant_search_status(self) -> Dict[str, Any]:
        """
        Get the status of recurring merchant search operations.

        Returns:
            Search status with timing and count information
        """
        self.logger.info("Fetching recurring merchant search status")

        query = gql(
            """
            query RecurringMerchantSearch {
                recurringMerchantSearch {
                    startedAt
                    nextAt
                    finishedAt
                    createdCount
                    __typename
                }
                recurringTransactionStreams {
                    stream {
                        id
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="RecurringMerchantSearch", query=query
        )

    async def get_all_recurring_transaction_items(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_liabilities: bool = True,
    ) -> Dict[str, Any]:
        """
        Get all recurring transaction items with optional filtering.

        Args:
            filters: Optional filters for accounts, categories, etc.
            include_liabilities: Include liability-based transactions

        Returns:
            List of all recurring transaction items with forecasts
        """
        self.logger.info(
            "Fetching all recurring transaction items",
            filters=filters,
            include_liabilities=include_liabilities,
        )

        variables = {
            "includeLiabilities": include_liabilities,
        }

        if filters:
            variables["filters"] = filters

        query = gql(
            """
            query Web_GetAllRecurringTransactionItems(
                $filters: RecurringTransactionFilter,
                $includeLiabilities: Boolean
            ) {
                recurringTransactionStreams(
                    filters: $filters,
                    includeLiabilities: $includeLiabilities
                ) {
                    stream {
                        id
                        frequency
                        isActive
                        isApproximate
                        name
                        logoUrl
                        merchant {
                            id
                            name
                            logoUrl
                            __typename
                        }
                        creditReportLiabilityAccount {
                            id
                            account {
                                id
                                displayName
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    nextForecastedTransaction {
                        date
                        amount
                        __typename
                    }
                    category {
                        id
                        name
                        icon
                        __typename
                    }
                    account {
                        id
                        displayName
                        icon
                        logoUrl
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="Web_GetAllRecurringTransactionItems",
            query=query,
            variables=variables,
        )

    # Transaction Rules Methods
    async def get_transaction_rules(self) -> Dict[str, Any]:
        """
        Get all transaction rules with their criteria and actions.

        Returns:
            List of transaction rules with conditions and actions
        """
        self.logger.info("Fetching transaction rules")

        query = gql(
            """
            query GetTransactionRules {
                transactionRules {
                    id
                    name
                    priority
                    isEnabled
                    conditions {
                        field
                        operator
                        value
                        __typename
                    }
                    actions {
                        type
                        value
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(operation="GetTransactionRules", query=query)

    async def create_transaction_rule(
        self,
        name: str,
        conditions: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        priority: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new transaction rule.

        Args:
            name: Name for the rule
            conditions: List of rule conditions (field, operator, value)
            actions: List of rule actions (type, value)
            priority: Rule priority (optional)

        Returns:
            Created rule data

        Raises:
            ValidationError: If rule data is invalid
        """
        name = InputValidator.validate_string_length(name, "rule name", 1, 100)

        self.logger.info(
            "Creating transaction rule", name=name, conditions_count=len(conditions)
        )

        variables = {
            "name": name,
            "conditions": conditions,
            "actions": actions,
        }

        if priority is not None:
            variables["priority"] = priority

        query = gql(
            """
            mutation Common_CreateTransactionRuleMutationV2(
                $name: String!,
                $conditions: [RuleConditionInput!]!,
                $actions: [RuleActionInput!]!,
                $priority: Int
            ) {
                createTransactionRule(
                    name: $name,
                    conditions: $conditions,
                    actions: $actions,
                    priority: $priority
                ) {
                    rule {
                        id
                        name
                        priority
                        isEnabled
                        conditions {
                            field
                            operator
                            value
                            __typename
                        }
                        actions {
                            type
                            value
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
            operation="Common_CreateTransactionRuleMutationV2",
            graphql_query=query,
            variables=variables,
        )

    async def update_transaction_rule(
        self,
        rule_id: str,
        name: Optional[str] = None,
        conditions: Optional[List[Dict[str, Any]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        priority: Optional[int] = None,
        is_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing transaction rule.

        Args:
            rule_id: ID of the rule to update
            name: New rule name
            conditions: New rule conditions
            actions: New rule actions
            priority: New rule priority
            is_enabled: Whether rule is enabled

        Returns:
            Updated rule data

        Raises:
            ValidationError: If rule data is invalid
        """
        rule_id = InputValidator.validate_string_length(rule_id, "rule_id", 1, 100)

        if name is not None:
            name = InputValidator.validate_string_length(name, "rule name", 1, 100)

        self.logger.info("Updating transaction rule", rule_id=rule_id, name=name)

        variables = {"id": rule_id}

        if name is not None:
            variables["name"] = name
        if conditions is not None:
            variables["conditions"] = conditions
        if actions is not None:
            variables["actions"] = actions
        if priority is not None:
            variables["priority"] = priority
        if is_enabled is not None:
            variables["isEnabled"] = is_enabled

        query = gql(
            """
            mutation Common_UpdateTransactionRuleMutationV2(
                $id: String!,
                $name: String,
                $conditions: [RuleConditionInput!],
                $actions: [RuleActionInput!],
                $priority: Int,
                $isEnabled: Boolean
            ) {
                updateTransactionRule(
                    id: $id,
                    name: $name,
                    conditions: $conditions,
                    actions: $actions,
                    priority: $priority,
                    isEnabled: $isEnabled
                ) {
                    rule {
                        id
                        name
                        priority
                        isEnabled
                        conditions {
                            field
                            operator
                            value
                            __typename
                        }
                        actions {
                            type
                            value
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
            operation="Common_UpdateTransactionRuleMutationV2",
            graphql_query=query,
            variables=variables,
        )

    async def delete_transaction_rule(self, rule_id: str) -> bool:
        """
        Delete a transaction rule.

        Args:
            rule_id: ID of the rule to delete

        Returns:
            True if deletion was successful

        Raises:
            ValidationError: If rule_id is invalid
        """
        rule_id = InputValidator.validate_string_length(rule_id, "rule_id", 1, 100)

        self.logger.info("Deleting transaction rule", rule_id=rule_id)

        variables = {"id": rule_id}

        query = gql(
            """
            mutation Common_DeleteTransactionRule($id: String!) {
                deleteTransactionRule(id: $id) {
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
            operation="Common_DeleteTransactionRule",
            graphql_query=query,
            variables=variables,
        )

        delete_result = result.get("deleteTransactionRule", {})
        errors = delete_result.get("errors", [])

        if errors:
            self.logger.error("Rule deletion failed", rule_id=rule_id, errors=errors)
            return False

        success = delete_result.get("deleted", False)
        if success:
            self.logger.info("Transaction rule deleted successfully", rule_id=rule_id)

        return success

    async def delete_all_transaction_rules(self) -> bool:
        """
        Delete all transaction rules.

        Returns:
            True if deletion was successful
        """
        self.logger.info("Deleting all transaction rules")

        query = gql(
            """
            mutation Web_DeleteAllTransactionRulesMutation {
                deleteAllTransactionRules {
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

        result = await self._execute_query(
            operation="Web_DeleteAllTransactionRulesMutation", query=query
        )

        delete_result = result.get("deleteAllTransactionRules", {})
        errors = delete_result.get("errors", [])

        if errors:
            self.logger.error("Delete all rules failed", errors=errors)
            return False

        success = delete_result.get("deleted", False)
        if success:
            self.logger.info("All transaction rules deleted successfully")

        return success

    # Transaction Categories Methods
    async def get_transaction_categories(self) -> Dict[str, Any]:
        """
        Get all transaction categories.

        Returns:
            List of categories with names, icons, colors, and group information
        """
        self.logger.info("Fetching transaction categories")

        query = gql(
            """
            query GetCategories {
                categories {
                    ...CategoryFields
                    __typename
                }
                categoryGroups {
                    id
                    name
                    type
                    __typename
                }
            }

            fragment CategoryFields on Category {
                id
                name
                icon
                color
                group {
                    id
                    type
                    __typename
                }
                __typename
            }
        """
        )

        return await self._execute_query(operation="GetCategories", query=query)

    async def create_transaction_category(
        self,
        name: str,
        group_id: str,
        icon: Optional[str] = None,
        color: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new transaction category.

        Args:
            name: Category name
            group_id: ID of the category group
            icon: Category icon (optional)
            color: Category color hex code (optional)

        Returns:
            Created category data

        Raises:
            ValidationError: If category data is invalid
        """
        name = InputValidator.validate_string_length(name, "category name", 1, 100)
        group_id = InputValidator.validate_string_length(group_id, "group_id", 1, 100)

        self.logger.info("Creating transaction category", name=name, group_id=group_id)

        variables = {
            "name": name,
            "groupId": group_id,
        }

        if icon:
            variables["icon"] = icon
        if color:
            variables["color"] = color

        query = gql(
            """
            mutation Web_CreateCategory(
                $name: String!,
                $groupId: String!,
                $icon: String,
                $color: String
            ) {
                createCategory(
                    name: $name,
                    groupId: $groupId,
                    icon: $icon,
                    color: $color
                ) {
                    category {
                        id
                        name
                        icon
                        color
                        group {
                            id
                            name
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
            operation="Web_CreateCategory", graphql_query=query, variables=variables
        )

    async def update_transaction_category(
        self,
        category_id: str,
        name: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing transaction category.

        Args:
            category_id: ID of the category to update
            name: New category name
            icon: New category icon
            color: New category color hex code

        Returns:
            Updated category data

        Raises:
            ValidationError: If category data is invalid
        """
        category_id = InputValidator.validate_string_length(
            category_id, "category_id", 1, 100
        )

        if name is not None:
            name = InputValidator.validate_string_length(name, "category name", 1, 100)

        self.logger.info(
            "Updating transaction category", category_id=category_id, name=name
        )

        variables = {"id": category_id}

        if name is not None:
            variables["name"] = name
        if icon is not None:
            variables["icon"] = icon
        if color is not None:
            variables["color"] = color

        query = gql(
            """
            mutation Web_UpdateCategory(
                $id: String!,
                $name: String,
                $icon: String,
                $color: String
            ) {
                updateCategory(
                    id: $id,
                    name: $name,
                    icon: $icon,
                    color: $color
                ) {
                    category {
                        id
                        name
                        icon
                        color
                        group {
                            id
                            name
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
            operation="Web_UpdateCategory", graphql_query=query, variables=variables
        )

    async def delete_transaction_category(self, category_id: str) -> bool:
        """
        Delete a transaction category.

        Args:
            category_id: ID of the category to delete

        Returns:
            True if deletion was successful

        Raises:
            ValidationError: If category_id is invalid
        """
        category_id = InputValidator.validate_string_length(
            category_id, "category_id", 1, 100
        )

        self.logger.info("Deleting transaction category", category_id=category_id)

        variables = {"id": category_id}

        query = gql(
            """
            mutation Web_DeleteCategory($id: String!) {
                deleteCategory(id: $id) {
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
            operation="Web_DeleteCategory", graphql_query=query, variables=variables
        )

        delete_result = result.get("deleteCategory", {})
        errors = delete_result.get("errors", [])

        if errors:
            self.logger.error(
                "Category deletion failed", category_id=category_id, errors=errors
            )
            return False

        success = delete_result.get("deleted", False)
        if success:
            self.logger.info(
                "Transaction category deleted successfully", category_id=category_id
            )

        return success

    async def get_transaction_category_groups(self) -> Dict[str, Any]:
        """
        Get transaction category groups.

        Returns:
            List of category groups with their metadata
        """
        self.logger.info("Fetching transaction category groups")

        query = gql(
            """
            query ManageGetCategoryGroups {
                categoryGroups {
                    id
                    name
                    type
                    categories {
                        id
                        name
                        icon
                        color
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="ManageGetCategoryGroups", query=query
        )

    # Transaction Tags Methods
    async def create_transaction_tag(self, name: str, color: str) -> Dict[str, Any]:
        """
        Create a new transaction tag.

        Args:
            name: Tag name
            color: Tag color hex code

        Returns:
            Created tag data

        Raises:
            ValidationError: If tag data is invalid
        """
        name = InputValidator.validate_string_length(name, "tag name", 1, 50)
        color = InputValidator.validate_string_length(color, "color", 3, 7)

        self.logger.info("Creating transaction tag", name=name, color=color)

        variables = {
            "name": name,
            "color": color,
        }

        query = gql(
            """
            mutation Common_CreateTransactionTag(
                $name: String!,
                $color: String!
            ) {
                createTransactionTag(
                    name: $name,
                    color: $color
                ) {
                    tag {
                        id
                        name
                        color
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
            operation="Common_CreateTransactionTag",
            graphql_query=query,
            variables=variables,
        )

    async def get_transaction_tags(self) -> Dict[str, Any]:
        """
        Get all transaction tags.

        Returns:
            List of available transaction tags with names and colors
        """
        self.logger.info("Fetching transaction tags")

        query = gql(
            """
            query GetHouseholdTransactionTags {
                tags {
                    id
                    name
                    color
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="GetHouseholdTransactionTags", query=query
        )

    async def set_transaction_tags(
        self, transaction_id: str, tag_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Set tags on a transaction.

        Args:
            transaction_id: ID of the transaction
            tag_ids: List of tag IDs to set on the transaction

        Returns:
            Updated transaction with tags

        Raises:
            ValidationError: If inputs are invalid
        """
        transaction_id = InputValidator.validate_transaction_id(transaction_id)

        # Validate tag IDs
        validated_tag_ids = []
        for tag_id in tag_ids:
            validated_tag_ids.append(
                InputValidator.validate_string_length(tag_id, "tag_id", 1, 100)
            )

        self.logger.info(
            "Setting transaction tags",
            transaction_id=transaction_id,
            tag_count=len(validated_tag_ids),
        )

        variables = {
            "transactionId": transaction_id,
            "tagIds": validated_tag_ids,
        }

        query = gql(
            """
            mutation Web_SetTransactionTags(
                $transactionId: String!,
                $tagIds: [String!]!
            ) {
                setTransactionTags(
                    transactionId: $transactionId,
                    tagIds: $tagIds
                ) {
                    transaction {
                        id
                        tags {
                            id
                            name
                            color
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
            operation="Web_SetTransactionTags",
            graphql_query=query,
            variables=variables,
        )

    # Categories and Merchants API Methods
    async def get_transaction_categories(self) -> Dict[str, Any]:
        """
        Get all available transaction categories.

        This method retrieves the complete list of transaction categories
        available in Monarch Money, including custom categories.

        Returns:
            List of categories with IDs, names, icons, colors, and group information
        """
        self.logger.info("Fetching transaction categories")

        query = gql(
            """
            query GetTransactionCategories {
                categories {
                    id
                    name
                    icon
                    color
                    isSystemCategory
                    group {
                        id
                        name
                        type
                        __typename
                    }
                    __typename
                }
                categoryGroups {
                    id
                    name
                    type
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="GetTransactionCategories", query=query
        )

    async def get_merchants(
        self,
        search: Optional[str] = None,
        limit: Optional[int] = 100,
    ) -> Dict[str, Any]:
        """
        Get merchants used in transactions.

        This method retrieves merchants that have been used in transactions,
        with optional search filtering.

        Args:
            search: Optional search term to filter merchants
            limit: Maximum number of merchants to return (default: 100)

        Returns:
            List of merchants with IDs, names, and transaction counts
        """
        validated_limit = InputValidator.validate_limit(limit) or 100

        self.logger.info("Fetching merchants", search=search, limit=validated_limit)

        variables = {"limit": validated_limit}

        if search:
            variables["search"] = search

        query = gql(
            """
            query GetMerchants($search: String, $limit: Int!) {
                merchants(search: $search, limit: $limit) {
                    id
                    name
                    logoUrl
                    transactionCount
                    lastTransactionDate
                    categories {
                        id
                        name
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="GetMerchants", query=query, variables=variables
        )

    async def get_merchant_details(self, merchant_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific merchant.

        Args:
            merchant_id: ID of the merchant to get details for

        Returns:
            Detailed merchant information including recent transactions

        Raises:
            ValidationError: If merchant_id is invalid
        """
        merchant_id = InputValidator.validate_string_length(
            merchant_id, "merchant_id", 1, 100
        )

        self.logger.info("Fetching merchant details", merchant_id=merchant_id)

        variables = {"merchantId": merchant_id}

        query = gql(
            """
            query GetMerchantDetails($merchantId: String!) {
                merchant(id: $merchantId) {
                    id
                    name
                    logoUrl
                    website
                    transactionCount
                    totalSpent
                    averageAmount
                    firstTransactionDate
                    lastTransactionDate
                    categories {
                        id
                        name
                        color
                        icon
                        __typename
                    }
                    recentTransactions(limit: 10) {
                        id
                        amount
                        date
                        description
                        account {
                            id
                            displayName
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

        return await self._execute_query(
            operation="GetMerchantDetails", query=query, variables=variables
        )

    async def get_edit_merchant(self, merchant_id: str) -> Dict[str, Any]:
        """
        Get merchant information for editing, including recurring transaction settings.

        This method is specifically designed for editing merchant settings and
        includes recurring transaction stream information that's needed for
        managing merchant recurring behavior.

        Args:
            merchant_id: ID of the merchant to get edit information for

        Returns:
            Merchant edit information including:
            - Basic merchant details (id, name, logoUrl)
            - Transaction and rule counts
            - Whether merchant can be deleted
            - Recurring transaction stream details
            - Active recurring stream status

        Raises:
            ValidationError: If merchant_id is invalid

        Example:
            # Get merchant edit info for managing recurring settings
            edit_info = await mm._transaction_service.get_edit_merchant("104754400339336479")
            has_recurring = edit_info["merchant"]["hasActiveRecurringStreams"]
            if has_recurring:
                stream = edit_info["merchant"]["recurringTransactionStream"]
                print(f"Recurring: {stream['frequency']} - ${stream['amount']}")
        """
        merchant_id = InputValidator.validate_string_length(
            merchant_id, "merchant_id", 1, 100
        )

        self.logger.info("Fetching merchant edit information", merchant_id=merchant_id)

        variables = {"merchantId": merchant_id}

        query = gql(
            """
            query Common_GetEditMerchant($merchantId: ID!) {
                merchant(id: $merchantId) {
                    id
                    name
                    logoUrl
                    transactionCount
                    ruleCount
                    canBeDeleted
                    hasActiveRecurringStreams
                    recurringTransactionStream {
                        id
                        frequency
                        amount
                        baseDate
                        isActive
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="Common_GetEditMerchant", query=query, variables=variables
        )

    async def get_category_details(self, category_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific category.

        Args:
            category_id: ID of the category to get details for

        Returns:
            Detailed category information including transaction statistics

        Raises:
            ValidationError: If category_id is invalid
        """
        category_id = InputValidator.validate_string_length(
            category_id, "category_id", 1, 100
        )

        self.logger.info("Fetching category details", category_id=category_id)

        variables = {"categoryId": category_id}

        query = gql(
            """
            query GetCategoryDetails($categoryId: String!) {
                category(id: $categoryId) {
                    id
                    name
                    icon
                    color
                    isSystemCategory
                    group {
                        id
                        name
                        type
                        __typename
                    }
                    transactionStats {
                        transactionCount
                        totalSpent
                        averageAmount
                        monthlyAverage
                        lastTransactionDate
                        __typename
                    }
                    topMerchants(limit: 5) {
                        merchant {
                            id
                            name
                            logoUrl
                            __typename
                        }
                        transactionCount
                        totalAmount
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="GetCategoryDetails", query=query, variables=variables
        )

    async def bulk_update_transactions(
        self,
        transaction_ids: List[str],
        updates: Dict[str, Any],
        excluded_transaction_ids: Optional[List[str]] = None,
        all_selected: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Bulk update multiple transactions with specified changes.

        Args:
            transaction_ids: List of transaction IDs to update
            updates: Dictionary of updates to apply (e.g., {"hide": False})
            excluded_transaction_ids: Optional list of transaction IDs to exclude
            all_selected: Whether all transactions are selected (for large bulk operations)
            filters: Optional filters that were used to select transactions

        Returns:
            Result of bulk update operation with success status and affected count

        Raises:
            ValidationError: If inputs are invalid

        Examples:
            # Unhide specific transactions
            result = await mm.bulk_update_transactions(
                transaction_ids=["123", "456", "789"],
                updates={"hide": False}
            )

            # Hide transactions from reports
            result = await mm.bulk_update_transactions(
                transaction_ids=["123", "456"],
                updates={"hide": True}
            )
        """
        # Validate transaction IDs
        if not transaction_ids or not isinstance(transaction_ids, list):
            raise ValidationError("transaction_ids must be a non-empty list")

        validated_ids = []
        for tid in transaction_ids:
            validated_ids.append(InputValidator.validate_transaction_id(tid))

        # Validate updates
        if not updates or not isinstance(updates, dict):
            raise ValidationError("updates must be a non-empty dictionary")

        # Validate excluded IDs if provided
        validated_excluded_ids = excluded_transaction_ids or []
        if excluded_transaction_ids:
            for tid in excluded_transaction_ids:
                InputValidator.validate_transaction_id(tid)

        expected_count = len(validated_ids) - len(validated_excluded_ids)

        self.logger.info(
            "Bulk updating transactions",
            transaction_count=len(validated_ids),
            excluded_count=len(validated_excluded_ids),
            expected_affected_count=expected_count,
            updates=updates,
        )

        variables = {
            "selectedTransactionIds": validated_ids,
            "excludedTransactionIds": validated_excluded_ids,
            "updates": updates,
            "allSelected": all_selected,
            "expectedAffectedTransactionCount": expected_count,
        }

        if filters:
            variables["filters"] = filters

        query = gql(
            """
            mutation Common_BulkUpdateTransactionsMutation(
                $selectedTransactionIds: [ID!]!,
                $excludedTransactionIds: [ID!],
                $allSelected: Boolean!,
                $expectedAffectedTransactionCount: Int!,
                $updates: TransactionUpdateParams!,
                $filters: TransactionFilterInput
            ) {
                bulkUpdateTransactions(
                    selectedTransactionIds: $selectedTransactionIds,
                    excludedTransactionIds: $excludedTransactionIds,
                    updates: $updates,
                    allSelected: $allSelected,
                    expectedAffectedTransactionCount: $expectedAffectedTransactionCount,
                    filters: $filters
                ) {
                    success
                    affectedCount
                    errors {
                        message
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        result = await self.client.gql_call(
            operation="Common_BulkUpdateTransactionsMutation",
            graphql_query=query,
            variables=variables,
        )

        bulk_result = result.get("bulkUpdateTransactions", {})
        errors = bulk_result.get("errors", [])

        if errors:
            self.logger.error(
                "Bulk update failed",
                transaction_count=len(validated_ids),
                errors=errors,
            )
            raise ValueError(f"Bulk update failed: {errors}")

        success = bulk_result.get("success", False)
        affected_count = bulk_result.get("affectedCount", 0)

        if success:
            self.logger.info(
                "Bulk update successful",
                affected_count=affected_count,
                expected_count=expected_count,
            )

        return bulk_result

    async def bulk_unhide_transactions(
        self, transaction_ids: List[str], filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Bulk unhide transactions (set hideFromReports to false).

        This is a convenience method that calls bulk_update_transactions with
        the appropriate parameters to unhide transactions.

        Args:
            transaction_ids: List of transaction IDs to unhide
            filters: Optional filters that were used to select the transactions

        Returns:
            Result of bulk unhide operation with success status and affected count

        Raises:
            ValidationError: If transaction_ids is invalid

        Example:
            # Unhide specific hidden transactions
            result = await mm.bulk_unhide_transactions(
                transaction_ids=["220716668609011425", "220716668609011424"],
                filters={"hideFromReports": True}
            )
            
            if result["success"]:
                print(f"Successfully unhid {result['affectedCount']} transactions")
        """
        self.logger.info(
            "Bulk unhiding transactions", transaction_count=len(transaction_ids)
        )

        return await self.bulk_update_transactions(
            transaction_ids=transaction_ids,
            updates={"hide": False},
            filters=filters,
        )

    async def bulk_hide_transactions(
        self, transaction_ids: List[str], filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Bulk hide transactions (set hideFromReports to true).

        This is a convenience method that calls bulk_update_transactions with
        the appropriate parameters to hide transactions from reports.

        Args:
            transaction_ids: List of transaction IDs to hide
            filters: Optional filters that were used to select the transactions

        Returns:
            Result of bulk hide operation with success status and affected count

        Raises:
            ValidationError: If transaction_ids is invalid

        Example:
            # Hide specific transactions from reports
            result = await mm.bulk_hide_transactions(
                transaction_ids=["220716668609011425", "220716668609011424"]
            )
            
            if result["success"]:
                print(f"Successfully hid {result['affectedCount']} transactions")
        """
        self.logger.info(
            "Bulk hiding transactions", transaction_count=len(transaction_ids)
        )

        return await self.bulk_update_transactions(
            transaction_ids=transaction_ids,
            updates={"hide": True},
            filters=filters,
        )

    async def get_hidden_transactions(
        self,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
        order_by: str = "date",
    ) -> Dict[str, Any]:
        """
        Get transactions that are hidden from reports.

        This method retrieves transactions where hideFromReports is true,
        making it easy to see what transactions are currently hidden and
        potentially bulk unhide them.

        Args:
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            order_by: Field to order by (default: "date")

        Returns:
            List of hidden transactions with full transaction details

        Example:
            # Get all hidden transactions
            hidden = await mm.get_hidden_transactions(limit=50)
            transaction_ids = [t["id"] for t in hidden["allTransactions"]["results"]]
            
            # Unhide them all
            await mm.bulk_unhide_transactions(transaction_ids)
        """
        validated_limit = InputValidator.validate_limit(limit) or 100
        validated_offset = offset or 0

        self.logger.info(
            "Fetching hidden transactions",
            limit=validated_limit,
            offset=validated_offset,
        )

        variables = {
            "orderBy": order_by,
            "limit": validated_limit,
            "offset": validated_offset,
            "filters": {"hideFromReports": True},
        }

        query = gql(
            """
            query Web_GetTransactionsList(
                $offset: Int,
                $limit: Int,
                $filters: TransactionFilterInput,
                $orderBy: TransactionOrdering
            ) {
                allTransactions(filters: $filters) {
                    totalCount
                    totalSelectableCount
                    results(offset: $offset, limit: $limit, orderBy: $orderBy) {
                        id
                        ...TransactionOverviewFields
                        __typename
                    }
                    __typename
                }
                transactionRules {
                    id
                    __typename
                }
            }

            fragment TransactionOverviewFields on Transaction {
                id
                amount
                pending
                date
                hideFromReports
                hiddenByAccount
                plaidName
                notes
                isRecurring
                reviewStatus
                needsReview
                isSplitTransaction
                dataProviderDescription
                attachments {
                    id
                    __typename
                }
                goal {
                    id
                    name
                    __typename
                }
                category {
                    id
                    name
                    icon
                    group {
                        id
                        type
                        __typename
                    }
                    __typename
                }
                merchant {
                    name
                    id
                    transactionsCount
                    logoUrl
                    recurringTransactionStream {
                        frequency
                        isActive
                        __typename
                    }
                    __typename
                }
                tags {
                    id
                    name
                    color
                    order
                    __typename
                }
                account {
                    id
                    displayName
                    icon
                    logoUrl
                    __typename
                }
                __typename
            }
        """
        )

        return await self.client.gql_call(
            operation="Web_GetTransactionsList",
            graphql_query=query,
            variables=variables,
        )
