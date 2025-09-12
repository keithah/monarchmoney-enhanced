"""
Investment service for MonarchMoney Enhanced.

Handles investment holdings, securities, and performance tracking.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from gql import gql

from ..exceptions import ValidationError
from ..validators import InputValidator
from .base_service import BaseService

if TYPE_CHECKING:
    from ..monarchmoney import MonarchMoney


class InvestmentService(BaseService):
    """
    Service for managing investment holdings and performance.

    This service handles:
    - Investment holdings management
    - Manual holdings CRUD operations
    - Security details and ticker lookup
    - Investment performance analytics
    """

    async def get_account_holdings(
        self, account_id: str, start_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get investment holdings for a specific account.

        Args:
            account_id: ID of the investment account
            start_date: Optional start date for historical holdings

        Returns:
            Investment holdings data with positions and values

        Raises:
            ValidationError: If account_id is invalid
        """
        account_id = InputValidator.validate_account_id(account_id)

        if start_date:
            start_date = InputValidator.validate_date_string(start_date)

        self.logger.info(
            "Fetching account holdings", account_id=account_id, start_date=start_date
        )

        variables = {"accountId": account_id}
        if start_date:
            variables["startDate"] = start_date

        query = gql(
            """
            query Web_GetHoldings($accountId: String!, $startDate: String) {
                account(id: $accountId) {
                    id
                    displayName
                    holdings(startDate: $startDate) {
                        id
                        quantity
                        basis
                        marketValue
                        totalReturn
                        totalReturnPercent
                        security {
                            id
                            symbol
                            name
                            cusip
                            currentPrice
                            securityType
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
            operation="Web_GetHoldings", graphql_query=query, variables=variables
        )

    async def create_manual_holding(
        self,
        account_id: str,
        symbol: str,
        quantity: Union[str, int, float],
        basis_per_share: Optional[Union[str, int, float]] = None,
        acquisition_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a manual investment holding.

        Args:
            account_id: ID of the investment account
            symbol: Stock/security symbol (ticker)
            quantity: Number of shares/units
            basis_per_share: Cost basis per share (optional)
            acquisition_date: Date the holding was acquired (YYYY-MM-DD)

        Returns:
            Created holding data

        Raises:
            ValidationError: If input parameters are invalid
        """
        account_id = InputValidator.validate_account_id(account_id)
        symbol = InputValidator.validate_string_length(symbol, "symbol", 1, 20)
        quantity = InputValidator.validate_amount(quantity)

        if basis_per_share is not None:
            basis_per_share = InputValidator.validate_amount(basis_per_share)

        if acquisition_date:
            acquisition_date = InputValidator.validate_date_string(acquisition_date)

        self.logger.info(
            "Creating manual holding",
            account_id=account_id,
            symbol=symbol,
            quantity=quantity,
        )

        variables = {
            "accountId": account_id,
            "symbol": symbol,
            "quantity": quantity,
        }

        if basis_per_share is not None:
            variables["basisPerShare"] = basis_per_share
        if acquisition_date:
            variables["acquisitionDate"] = acquisition_date

        query = gql(
            """
            mutation Common_CreateManualHolding(
                $accountId: String!,
                $symbol: String!,
                $quantity: Float!,
                $basisPerShare: Float,
                $acquisitionDate: String
            ) {
                createManualHolding(
                    accountId: $accountId,
                    symbol: $symbol,
                    quantity: $quantity,
                    basisPerShare: $basisPerShare,
                    acquisitionDate: $acquisitionDate
                ) {
                    holding {
                        id
                        quantity
                        basis
                        marketValue
                        security {
                            id
                            symbol
                            name
                            currentPrice
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
            operation="Common_CreateManualHolding",
            graphql_query=query,
            variables=variables,
        )

    async def create_manual_holding_by_ticker(
        self,
        account_id: str,
        ticker: str,
        quantity: Union[str, int, float],
        basis_per_share: Optional[Union[str, int, float]] = None,
    ) -> Dict[str, Any]:
        """
        Create a manual holding by ticker symbol.

        Args:
            account_id: ID of the investment account
            ticker: Stock ticker symbol
            quantity: Number of shares
            basis_per_share: Cost basis per share (optional)

        Returns:
            Created holding data

        Raises:
            ValidationError: If input parameters are invalid
        """
        # This is an alias for create_manual_holding for backward compatibility
        return await self.create_manual_holding(
            account_id=account_id,
            symbol=ticker,
            quantity=quantity,
            basis_per_share=basis_per_share,
        )

    async def delete_manual_holding(self, holding_id: str) -> bool:
        """
        Delete a manual investment holding.

        Args:
            holding_id: ID of the holding to delete

        Returns:
            True if deletion was successful

        Raises:
            ValidationError: If holding_id is invalid
        """
        holding_id = InputValidator.validate_string_length(
            holding_id, "holding_id", 1, 100
        )

        self.logger.info("Deleting manual holding", holding_id=holding_id)

        variables = {"id": holding_id}

        query = gql(
            """
            mutation Common_DeleteHolding($id: String!) {
                deleteHolding(id: $id) {
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
            operation="Common_DeleteHolding", graphql_query=query, variables=variables
        )

        delete_result = result.get("deleteHolding", {})
        errors = delete_result.get("errors", [])

        if errors:
            self.logger.error(
                "Holding deletion failed", holding_id=holding_id, errors=errors
            )
            return False

        success = delete_result.get("deleted", False)
        if success:
            self.logger.info("Holding deleted successfully", holding_id=holding_id)

        return success

    async def get_security_details(
        self, ticker: Optional[str] = None, cusip: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get security details by ticker symbol or CUSIP.

        Args:
            ticker: Stock ticker symbol
            cusip: CUSIP identifier

        Returns:
            Security information including name, price, and metadata

        Raises:
            ValidationError: If neither ticker nor cusip is provided
        """
        if not ticker and not cusip:
            raise ValidationError("Either ticker or cusip must be provided")

        if ticker:
            ticker = InputValidator.validate_string_length(ticker, "ticker", 1, 20)
        if cusip:
            cusip = InputValidator.validate_string_length(cusip, "cusip", 1, 50)

        self.logger.info("Fetching security details", ticker=ticker, cusip=cusip)

        variables = {}
        if ticker:
            variables["ticker"] = ticker
        if cusip:
            variables["cusip"] = cusip

        query = gql(
            """
            query SecuritySearch($ticker: String, $cusip: String) {
                securitySearch(ticker: $ticker, cusip: $cusip) {
                    id
                    symbol
                    name
                    cusip
                    currentPrice
                    previousClose
                    change
                    changePercent
                    securityType
                    exchange
                    currency
                    marketCap
                    peRatio
                    dividendYield
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="SecuritySearch", graphql_query=query, variables=variables
        )

    async def get_investment_performance(
        self,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        time_period: str = "1Y",
    ) -> Dict[str, Any]:
        """
        Get investment performance metrics and analytics.

        Args:
            account_id: Specific account ID (optional, gets all if not provided)
            start_date: Start date for performance analysis (YYYY-MM-DD)
            end_date: End date for performance analysis (YYYY-MM-DD)
            time_period: Time period for analysis ("1M", "3M", "6M", "1Y", "2Y", "5Y", "ALL")

        Returns:
            Investment performance data with returns, volatility, and benchmarks
        """
        if account_id:
            account_id = InputValidator.validate_account_id(account_id)
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching investment performance",
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            time_period=time_period,
        )

        variables = {"timePeriod": time_period}

        if account_id:
            variables["accountId"] = account_id
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date

        query = gql(
            """
            query GetInvestmentPerformance(
                $accountId: String,
                $startDate: String,
                $endDate: String,
                $timePeriod: String!
            ) {
                investmentPerformance(
                    accountId: $accountId,
                    startDate: $startDate,
                    endDate: $endDate,
                    timePeriod: $timePeriod
                ) {
                    totalReturn
                    totalReturnPercent
                    annualizedReturn
                    volatility
                    sharpeRatio
                    maxDrawdown
                    winRate
                    benchmark {
                        name
                        totalReturn
                        totalReturnPercent
                        annualizedReturn
                        __typename
                    }
                    holdings {
                        security {
                            symbol
                            name
                            __typename
                        }
                        totalReturn
                        totalReturnPercent
                        weightPercent
                        __typename
                    }
                    performanceHistory {
                        date
                        portfolioValue
                        totalReturn
                        benchmarkReturn
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetInvestmentPerformance",
            graphql_query=query,
            variables=variables,
        )

    async def get_security_price_history(
        self, symbol: str, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """
        Get historical price data for a security.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date for price history (YYYY-MM-DD)
            end_date: End date for price history (YYYY-MM-DD)

        Returns:
            Historical price data with OHLCV information

        Raises:
            ValidationError: If parameters are invalid
        """
        symbol = InputValidator.validate_string_length(symbol, "symbol", 1, 20)
        start_date = InputValidator.validate_date_string(start_date)
        end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching security price history",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        variables = {
            "symbol": symbol,
            "startDate": start_date,
            "endDate": end_date,
        }

        query = gql(
            """
            query GetSecurityPriceHistory(
                $symbol: String!,
                $startDate: String!,
                $endDate: String!
            ) {
                securityPriceHistory(
                    symbol: $symbol,
                    startDate: $startDate,
                    endDate: $endDate
                ) {
                    symbol
                    prices {
                        date
                        open
                        high
                        low
                        close
                        volume
                        adjustedClose
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetSecurityPriceHistory",
            graphql_query=query,
            variables=variables,
        )

    async def get_holding_by_ticker(
        self, ticker: str, account_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get holding information by ticker symbol.

        This method searches through the user's holdings to find a specific
        security by its ticker symbol. Useful for programmatic holding management.

        Args:
            ticker: Stock ticker symbol to search for
            account_id: Optional account ID to limit search to specific account

        Returns:
            Holding information if found, None otherwise

        Raises:
            ValidationError: If ticker is invalid
        """
        ticker = InputValidator.validate_string_length(ticker, "ticker", 1, 20)
        if account_id:
            account_id = InputValidator.validate_account_id(account_id)

        self.logger.info(
            "Searching for holding by ticker", ticker=ticker, account_id=account_id
        )

        # Get all holdings
        if account_id:
            holdings_data = await self.get_account_holdings(account_id)
            holdings = holdings_data.get("holdings", [])
        else:
            # Get holdings from all investment accounts
            accounts = await self.client.get_accounts()
            all_holdings = []

            for account in accounts.get("accounts", []):
                if account.get("type", {}).get("name") in ["investment", "retirement"]:
                    try:
                        account_holdings = await self.get_account_holdings(
                            account["id"]
                        )
                        all_holdings.extend(account_holdings.get("holdings", []))
                    except Exception as e:
                        self.logger.debug(
                            "Failed to get holdings for account",
                            account_id=account["id"],
                            error=str(e),
                        )
                        continue
            holdings = all_holdings

        # Search for ticker in holdings
        for holding in holdings:
            security = holding.get("security", {})
            if security.get("symbol", "").upper() == ticker.upper():
                self.logger.info(
                    "Found holding by ticker",
                    ticker=ticker,
                    holding_id=holding.get("id"),
                )
                return holding

        self.logger.info("No holding found for ticker", ticker=ticker)
        return None

    async def add_holding_by_ticker(
        self,
        account_id: str,
        ticker: str,
        quantity: Union[str, int, float],
        basis_per_share: Optional[Union[str, int, float]] = None,
    ) -> Dict[str, Any]:
        """
        Add a manual holding by ticker symbol.

        This method first looks up the security by ticker, then creates
        a manual holding in the specified account. This enables programmatic
        investment portfolio management.

        Args:
            account_id: ID of the investment account
            ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
            quantity: Number of shares to add
            basis_per_share: Cost basis per share (optional)

        Returns:
            Created holding information

        Raises:
            ValidationError: If parameters are invalid
            ValueError: If ticker is not found or holding creation fails
        """
        ticker = InputValidator.validate_string_length(ticker, "ticker", 1, 20)
        account_id = InputValidator.validate_account_id(account_id)

        if basis_per_share is not None:
            basis_per_share = InputValidator.validate_amount(basis_per_share)
        quantity = InputValidator.validate_amount(quantity)

        self.logger.info(
            "Adding holding by ticker",
            account_id=account_id,
            ticker=ticker,
            quantity=quantity,
            basis_per_share=basis_per_share,
        )

        # First, get security details by ticker
        security_data = await self.get_security_details(ticker=ticker)
        securities = security_data.get("securitySearch", [])

        if not securities:
            raise ValueError(f"Security with ticker '{ticker}' not found")

        security = securities[0]  # Use first match
        security_id = security.get("id")

        if not security_id:
            raise ValueError(f"Could not get security ID for ticker '{ticker}'")

        # Create the manual holding using the security ID
        variables = {
            "input": {
                "accountId": account_id,
                "securityId": security_id,
                "quantity": str(quantity),
                "costBasisPerShare": str(basis_per_share) if basis_per_share else None,
            }
        }

        query = gql(
            """
            mutation CreateManualHoldingByTicker($input: CreateManualHoldingInput!) {
                createManualHolding(input: $input) {
                    holding {
                        id
                        quantity
                        costBasisPerShare
                        currentValue
                        totalReturn
                        totalReturnPercent
                        security {
                            id
                            symbol
                            name
                            currentPrice
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

        result = await self.client.gql_call(
            operation="CreateManualHoldingByTicker",
            graphql_query=query,
            variables=variables,
        )

        create_result = result.get("createManualHolding", {})
        errors = create_result.get("errors", [])

        if errors:
            error_msg = f"Failed to create holding for {ticker}: {errors}"
            self.logger.error("Holdings creation failed", ticker=ticker, errors=errors)
            raise ValueError(error_msg)

        holding = create_result.get("holding")
        if not holding:
            raise ValueError(
                f"Failed to create holding for {ticker}: No holding returned"
            )

        self.logger.info(
            "Successfully added holding by ticker",
            ticker=ticker,
            holding_id=holding.get("id"),
        )
        return holding

    async def remove_holding_by_ticker(
        self, ticker: str, account_id: Optional[str] = None
    ) -> bool:
        """
        Remove a holding by ticker symbol.

        This method finds the holding by ticker symbol and deletes it.
        Useful for programmatic portfolio management.

        Args:
            ticker: Stock ticker symbol to remove
            account_id: Optional account ID to limit search to specific account

        Returns:
            True if holding was found and deleted successfully

        Raises:
            ValidationError: If ticker is invalid
            ValueError: If holding is not found
        """
        ticker = InputValidator.validate_string_length(ticker, "ticker", 1, 20)

        self.logger.info(
            "Removing holding by ticker", ticker=ticker, account_id=account_id
        )

        # Find the holding by ticker
        holding = await self.get_holding_by_ticker(ticker, account_id)

        if not holding:
            raise ValueError(f"No holding found for ticker '{ticker}'")

        holding_id = holding.get("id")
        if not holding_id:
            raise ValueError(f"Could not get holding ID for ticker '{ticker}'")

        # Delete the holding
        success = await self.delete_manual_holding(holding_id)

        if success:
            self.logger.info("Successfully removed holding by ticker", ticker=ticker)
        else:
            self.logger.error("Failed to remove holding by ticker", ticker=ticker)

        return success

    async def update_holding_quantity(
        self,
        holding_id: str,
        new_quantity: Union[str, int, float],
        new_basis_per_share: Optional[Union[str, int, float]] = None,
    ) -> Dict[str, Any]:
        """
        Update the quantity and optionally cost basis of a manual holding.

        Args:
            holding_id: ID of the holding to update
            new_quantity: New number of shares
            new_basis_per_share: New cost basis per share (optional)

        Returns:
            Updated holding information

        Raises:
            ValidationError: If parameters are invalid
        """
        holding_id = InputValidator.validate_string_length(
            holding_id, "holding_id", 1, 100
        )
        new_quantity = InputValidator.validate_amount(new_quantity)

        if new_basis_per_share is not None:
            new_basis_per_share = InputValidator.validate_amount(new_basis_per_share)

        self.logger.info(
            "Updating holding quantity",
            holding_id=holding_id,
            new_quantity=new_quantity,
            new_basis_per_share=new_basis_per_share,
        )

        variables = {
            "input": {
                "id": holding_id,
                "quantity": str(new_quantity),
            }
        }

        if new_basis_per_share is not None:
            variables["input"]["costBasisPerShare"] = str(new_basis_per_share)

        query = gql(
            """
            mutation UpdateHoldingQuantity($input: UpdateHoldingInput!) {
                updateHolding(input: $input) {
                    holding {
                        id
                        quantity
                        costBasisPerShare
                        currentValue
                        totalReturn
                        totalReturnPercent
                        security {
                            id
                            symbol
                            name
                            currentPrice
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

        result = await self.client.gql_call(
            operation="UpdateHoldingQuantity",
            graphql_query=query,
            variables=variables,
        )

        update_result = result.get("updateHolding", {})
        errors = update_result.get("errors", [])

        if errors:
            self.logger.error(
                "Holding update failed", holding_id=holding_id, errors=errors
            )
            raise ValueError(f"Failed to update holding: {errors}")

        holding = update_result.get("holding")
        if not holding:
            raise ValueError("Failed to update holding: No holding returned")

        self.logger.info("Successfully updated holding quantity", holding_id=holding_id)
        return holding
