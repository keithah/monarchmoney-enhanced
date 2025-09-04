"""
Investment service for MonarchMoney Enhanced.

Handles investment holdings, securities, and performance tracking.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from gql import gql

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
        holding_id = InputValidator.validate_string_length(holding_id, "holding_id", 1, 100)

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
            self.logger.error("Holding deletion failed", holding_id=holding_id, errors=errors)
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