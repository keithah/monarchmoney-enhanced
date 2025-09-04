"""
Insight service for MonarchMoney Enhanced.

Handles financial insights, analytics, and reporting operations.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from gql import gql

from ..validators import InputValidator
from .base_service import BaseService

if TYPE_CHECKING:
    from ..monarchmoney import MonarchMoney


class InsightService(BaseService):
    """
    Service for managing financial insights and analytics.

    This service handles:
    - Financial insights and recommendations
    - Credit score monitoring
    - Spending analysis and trends
    - Income vs expense reporting
    - Financial health metrics
    """

    async def get_insights(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        insight_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get financial insights and recommendations.

        Args:
            start_date: Start date for insight analysis (YYYY-MM-DD)
            end_date: End date for insight analysis (YYYY-MM-DD)
            insight_types: Optional list of insight types to filter

        Returns:
            Financial insights with recommendations and analysis
        """
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching financial insights",
            start_date=start_date,
            end_date=end_date,
            insight_types=insight_types,
        )

        variables = {}
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date
        if insight_types:
            variables["insightTypes"] = insight_types

        query = gql(
            """
            query GetInsights(
                $startDate: String,
                $endDate: String,
                $insightTypes: [String]
            ) {
                insights(
                    startDate: $startDate,
                    endDate: $endDate,
                    insightTypes: $insightTypes
                ) {
                    id
                    type
                    title
                    description
                    priority
                    category
                    value
                    recommendation
                    actionable
                    createdAt
                    data {
                        ... on SpendingInsight {
                            amount
                            previousAmount
                            change
                            changePercent
                            category {
                                id
                                name
                                icon
                                color
                                __typename
                            }
                            __typename
                        }
                        ... on IncomeInsight {
                            amount
                            previousAmount
                            change
                            changePercent
                            source
                            __typename
                        }
                        ... on BudgetInsight {
                            budgetAmount
                            spentAmount
                            remainingAmount
                            percentSpent
                            category {
                                id
                                name
                                __typename
                            }
                            __typename
                        }
                        ... on GoalInsight {
                            goalId
                            currentAmount
                            targetAmount
                            progressPercent
                            monthsRemaining
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
            operation="GetInsights", graphql_query=query, variables=variables
        )

    async def get_credit_score(self, include_history: bool = True) -> Dict[str, Any]:
        """
        Get credit score monitoring data.

        Args:
            include_history: Whether to include historical credit score data

        Returns:
            Credit score information with history and factors
        """
        self.logger.info("Fetching credit score data", include_history=include_history)

        variables = {"includeHistory": include_history}

        query = gql(
            """
            query GetCreditScore($includeHistory: Boolean!) {
                creditScore {
                    current {
                        score
                        provider
                        asOfDate
                        grade
                        range {
                            min
                            max
                            __typename
                        }
                        __typename
                    }
                    history @include(if: $includeHistory) {
                        date
                        score
                        change
                        __typename
                    }
                    factors {
                        type
                        impact
                        description
                        recommendation
                        __typename
                    }
                    summary {
                        trend
                        changeFromLastMonth
                        changeFromLastYear
                        percentile
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetCreditScore", graphql_query=query, variables=variables
        )

    async def get_spending_analysis(
        self,
        start_date: str,
        end_date: str,
        group_by: str = "category",
        compare_period: bool = False,
    ) -> Dict[str, Any]:
        """
        Get detailed spending analysis and trends.

        Args:
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            group_by: Grouping method ("category", "merchant", "account", "month")
            compare_period: Whether to include comparison with previous period

        Returns:
            Spending analysis with trends and comparisons

        Raises:
            ValidationError: If dates are invalid
        """
        start_date = InputValidator.validate_date_string(start_date)
        end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching spending analysis",
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            compare_period=compare_period,
        )

        variables = {
            "startDate": start_date,
            "endDate": end_date,
            "groupBy": group_by,
            "comparePeriod": compare_period,
        }

        query = gql(
            """
            query GetSpendingAnalysis(
                $startDate: String!,
                $endDate: String!,
                $groupBy: String!,
                $comparePeriod: Boolean!
            ) {
                spendingAnalysis(
                    startDate: $startDate,
                    endDate: $endDate,
                    groupBy: $groupBy,
                    comparePeriod: $comparePeriod
                ) {
                    totalSpent
                    averageDaily
                    averageTransaction
                    transactionCount
                    topCategories {
                        category {
                            id
                            name
                            icon
                            color
                            __typename
                        }
                        amount
                        percent
                        transactionCount
                        avgTransaction
                        __typename
                    }
                    topMerchants {
                        merchant {
                            id
                            name
                            logoUrl
                            __typename
                        }
                        amount
                        percent
                        transactionCount
                        __typename
                    }
                    timeline {
                        date
                        amount
                        transactionCount
                        __typename
                    }
                    comparison @include(if: $comparePeriod) {
                        totalSpent
                        change
                        changePercent
                        categories {
                            categoryId
                            currentAmount
                            previousAmount
                            change
                            changePercent
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
            operation="GetSpendingAnalysis", graphql_query=query, variables=variables
        )

    async def get_income_analysis(
        self,
        start_date: str,
        end_date: str,
        group_by: str = "source",
        include_projections: bool = False,
    ) -> Dict[str, Any]:
        """
        Get detailed income analysis and trends.

        Args:
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            group_by: Grouping method ("source", "account", "category", "month")
            include_projections: Whether to include income projections

        Returns:
            Income analysis with sources and trends

        Raises:
            ValidationError: If dates are invalid
        """
        start_date = InputValidator.validate_date_string(start_date)
        end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching income analysis",
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            include_projections=include_projections,
        )

        variables = {
            "startDate": start_date,
            "endDate": end_date,
            "groupBy": group_by,
            "includeProjections": include_projections,
        }

        query = gql(
            """
            query GetIncomeAnalysis(
                $startDate: String!,
                $endDate: String!,
                $groupBy: String!,
                $includeProjections: Boolean!
            ) {
                incomeAnalysis(
                    startDate: $startDate,
                    endDate: $endDate,
                    groupBy: $groupBy,
                    includeProjections: $includeProjections
                ) {
                    totalIncome
                    averageMonthly
                    averageDaily
                    transactionCount
                    sources {
                        name
                        amount
                        percent
                        transactionCount
                        category {
                            id
                            name
                            icon
                            color
                            __typename
                        }
                        __typename
                    }
                    timeline {
                        date
                        amount
                        transactionCount
                        __typename
                    }
                    projections @include(if: $includeProjections) {
                        nextMonth
                        next3Months
                        next6Months
                        nextYear
                        confidence
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetIncomeAnalysis", graphql_query=query, variables=variables
        )

    async def get_financial_health_score(self) -> Dict[str, Any]:
        """
        Get overall financial health score and metrics.

        Returns:
            Financial health score with component breakdowns and recommendations
        """
        self.logger.info("Fetching financial health score")

        query = gql(
            """
            query GetFinancialHealthScore {
                financialHealth {
                    overallScore
                    grade
                    components {
                        name
                        score
                        weight
                        status
                        recommendation
                        metrics {
                            name
                            value
                            benchmark
                            status
                            __typename
                        }
                        __typename
                    }
                    trends {
                        month
                        score
                        __typename
                    }
                    recommendations {
                        priority
                        title
                        description
                        actionItems
                        potentialImpact
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="GetFinancialHealthScore", query=query
        )

    async def get_net_worth_insights(
        self,
        time_period: str = "1Y",
        include_projections: bool = False,
    ) -> Dict[str, Any]:
        """
        Get net worth insights and growth analysis.

        Args:
            time_period: Time period for analysis ("1M", "3M", "6M", "1Y", "2Y", "ALL")
            include_projections: Whether to include future net worth projections

        Returns:
            Net worth insights with growth trends and analysis
        """
        self.logger.info(
            "Fetching net worth insights",
            time_period=time_period,
            include_projections=include_projections,
        )

        variables = {
            "timePeriod": time_period,
            "includeProjections": include_projections,
        }

        query = gql(
            """
            query GetNetWorthInsights(
                $timePeriod: String!,
                $includeProjections: Boolean!
            ) {
                netWorthInsights(
                    timePeriod: $timePeriod,
                    includeProjections: $includeProjections
                ) {
                    current {
                        totalAssets
                        totalLiabilities
                        netWorth
                        asOfDate
                        __typename
                    }
                    growth {
                        period
                        change
                        changePercent
                        annualizedGrowthRate
                        __typename
                    }
                    breakdown {
                        accountType
                        currentValue
                        contribution
                        contributionPercent
                        __typename
                    }
                    milestones {
                        amount
                        achievedDate
                        daysToAchieve
                        __typename
                    }
                    projections @include(if: $includeProjections) {
                        year
                        projectedNetWorth
                        confidence
                        assumptions {
                            incomeGrowth
                            savingsRate
                            investmentReturn
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
            operation="GetNetWorthInsights", graphql_query=query, variables=variables
        )

    async def get_subscription_details(self) -> Dict[str, Any]:
        """
        Get account subscription details and plan information.

        Returns:
            Subscription details including plan type, status, and billing info
        """
        # Delegate to SettingsService for consistency
        return await self.client._settings_service.get_subscription_details()

    async def generate_financial_report(
        self,
        start_date: str,
        end_date: str,
        report_type: str = "comprehensive",
        include_charts: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive financial report.

        Args:
            start_date: Start date for report period (YYYY-MM-DD)
            end_date: End date for report period (YYYY-MM-DD)
            report_type: Type of report ("summary", "detailed", "comprehensive")
            include_charts: Whether to include chart data

        Returns:
            Comprehensive financial report with all key metrics

        Raises:
            ValidationError: If dates are invalid
        """
        start_date = InputValidator.validate_date_string(start_date)
        end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Generating financial report",
            start_date=start_date,
            end_date=end_date,
            report_type=report_type,
        )

        variables = {
            "startDate": start_date,
            "endDate": end_date,
            "reportType": report_type,
            "includeCharts": include_charts,
        }

        query = gql(
            """
            query GenerateFinancialReport(
                $startDate: String!,
                $endDate: String!,
                $reportType: String!,
                $includeCharts: Boolean!
            ) {
                financialReport(
                    startDate: $startDate,
                    endDate: $endDate,
                    reportType: $reportType,
                    includeCharts: $includeCharts
                ) {
                    summary {
                        totalIncome
                        totalExpenses
                        netIncome
                        savingsRate
                        topIncomeCategory
                        topExpenseCategory
                        __typename
                    }
                    accounts {
                        totalAssets
                        totalLiabilities
                        netWorth
                        netWorthChange
                        __typename
                    }
                    budgets {
                        totalBudgeted
                        totalSpent
                        budgetUtilization
                        categoriesOverBudget
                        __typename
                    }
                    goals {
                        totalGoals
                        completedGoals
                        averageProgress
                        nextMilestone
                        __typename
                    }
                    insights {
                        keyFindings
                        recommendations
                        riskFactors
                        opportunities
                        __typename
                    }
                    charts @include(if: $includeCharts) {
                        incomeVsExpenses
                        spendingByCategory
                        netWorthTrend
                        budgetPerformance
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GenerateFinancialReport",
            graphql_query=query,
            variables=variables,
        )
