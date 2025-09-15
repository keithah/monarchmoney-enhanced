"""
Robust Investment GraphQL Operations for MonarchMoney Enhanced.

This module contains concrete implementations of robust GraphQL operations
for investment-related functionality.
"""

from typing import Dict, Any, Optional
from .robust_operation import RobustGraphQLOperation, OperationResult, FieldSpec


class UpdateHoldingQuantityOperation(RobustGraphQLOperation):
    """Robust implementation of the UpdateHoldingQuantity mutation."""

    def __init__(self):
        super().__init__("UpdateHoldingQuantity", "mutation")
        self.response_type = "Holding"

        # Define field specifications with fallbacks
        self.add_required_field("id")
        self.add_optional_field("quantity", deprecated_alternatives=["shares", "amount"])
        self.add_optional_field("costBasisPerShare", deprecated_alternatives=["basisPerShare", "costBasis"])
        self.add_optional_field("currentValue", deprecated_alternatives=["marketValue", "value"])
        self.add_optional_field("totalReturn", deprecated_alternatives=["return", "gain"])
        self.add_optional_field("totalReturnPercent", deprecated_alternatives=["returnPercent", "gainPercent"])

    def get_base_query_template(self) -> str:
        """Get the base mutation template."""
        return """
            mutation UpdateHoldingQuantity($input: UpdateHoldingInput!) {
                updateHolding(input: $input) {
                    holding {
{fields}
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

    def process_response(self, raw_response: Dict[str, Any]) -> OperationResult:
        """Process the UpdateHoldingQuantity response."""
        update_result = raw_response.get("updateHolding", {})
        errors = update_result.get("errors", [])
        holding = update_result.get("holding")

        if errors:
            # Extract error messages
            error_messages = []
            for error in errors:
                if isinstance(error, dict):
                    if "message" in error:
                        error_messages.append(error["message"])
                    if "fieldErrors" in error:
                        for field_error in error["fieldErrors"]:
                            field = field_error.get("field", "unknown")
                            messages = field_error.get("messages", [])
                            for msg in messages:
                                error_messages.append(f"{field}: {msg}")

            return OperationResult(
                success=False,
                data={"errors": error_messages},
                warnings=[f"Operation failed: {error_messages}"]
            )

        if not holding:
            return OperationResult(
                success=False,
                data=None,
                warnings=["No holding returned in response"]
            )

        # Success - return holding data
        result_data = {"id": holding.get("id"), "updated": True}

        # Add optional fields that were successfully retrieved
        optional_mappings = {
            "quantity": "quantity",
            "costBasisPerShare": "cost_basis_per_share",
            "currentValue": "current_value",
            "totalReturn": "total_return",
            "totalReturnPercent": "total_return_percent"
        }

        for gql_field, result_field in optional_mappings.items():
            if gql_field in holding:
                result_data[result_field] = holding[gql_field]

        return OperationResult(
            success=True,
            data=result_data
        )


class GetAccountHoldingsOperation(RobustGraphQLOperation):
    """Robust implementation of the GetAccountHoldings query."""

    def __init__(self):
        super().__init__("Web_GetPortfolio", "query")
        self.response_type = "AggregateHolding"

        # Define field specifications for holdings
        self.add_required_field("id")
        self.add_optional_field("quantity", deprecated_alternatives=["shares"])
        self.add_optional_field("basis", deprecated_alternatives=["costBasis"])
        self.add_optional_field("totalValue", deprecated_alternatives=["marketValue", "value"])
        self.add_optional_field("ticker", deprecated_alternatives=["symbol"])

    def get_base_query_template(self) -> str:
        """Get the base query template."""
        return """
            query Web_GetPortfolio($portfolioInput: PortfolioInput) {
                portfolio(input: $portfolioInput) {
                    aggregateHoldings {
                        edges {
                            node {
{fields}
                                holdings {
                                    id
                                    type
                                    typeDisplay
                                    name
                                    ticker
                                    quantity
                                    value
                                    account {
                                        id
                                        displayName
                                        __typename
                                    }
                                    __typename
                                }
                                security {
                                    id
                                    name
                                    ticker
                                    currentPrice
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
            }
        """

    def process_response(self, raw_response: Dict[str, Any]) -> OperationResult:
        """Process the GetAccountHoldings response."""
        portfolio = raw_response.get("portfolio", {})
        aggregate_holdings = portfolio.get("aggregateHoldings", {})
        edges = aggregate_holdings.get("edges", [])

        holdings_data = []
        for edge in edges:
            node = edge.get("node", {})
            holdings = node.get("holdings", [])

            for holding in holdings:
                holding_data = {
                    "id": holding.get("id"),
                    "name": holding.get("name"),
                    "ticker": holding.get("ticker"),
                    "quantity": holding.get("quantity"),
                    "value": holding.get("value"),
                    "account": holding.get("account", {})
                }

                # Add security information
                security = node.get("security", {})
                holding_data["security"] = {
                    "id": security.get("id"),
                    "name": security.get("name"),
                    "ticker": security.get("ticker"),
                    "current_price": security.get("currentPrice")
                }

                holdings_data.append(holding_data)

        return OperationResult(
            success=True,
            data={"holdings": holdings_data}
        )


class GetSecurityDetailsOperation(RobustGraphQLOperation):
    """Robust implementation of the SecuritySearch query."""

    def __init__(self):
        super().__init__("SecuritySearch", "query")
        self.response_type = "Security"

        # Define field specifications
        self.add_required_field("id")
        self.add_required_field("name")
        self.add_required_field("ticker")
        self.add_optional_field("currentPrice", deprecated_alternatives=["price", "lastPrice"])
        self.add_optional_field("currentPriceUpdatedAt", deprecated_alternatives=["priceUpdatedAt", "lastUpdated"])

    def get_base_query_template(self) -> str:
        """Get the base query template."""
        return """
            query SecuritySearch($search: String!, $limit: Int, $orderByPopularity: Boolean) {
                securities(
                    search: $search
                    limit: $limit
                    orderByPopularity: $orderByPopularity
                ) {
{fields}
                }
            }
        """

    def process_response(self, raw_response: Dict[str, Any]) -> OperationResult:
        """Process the SecuritySearch response."""
        securities = raw_response.get("securities", [])

        securities_data = []
        for security in securities:
            security_data = {
                "id": security.get("id"),
                "name": security.get("name"),
                "ticker": security.get("ticker"),
                "current_price": security.get("currentPrice"),
                "current_price_updated_at": security.get("currentPriceUpdatedAt")
            }
            securities_data.append(security_data)

        # Transform to match expected format
        result_data = {"securitySearch": securities_data}

        return OperationResult(
            success=True,
            data=result_data
        )