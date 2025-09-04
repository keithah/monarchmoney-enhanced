"""
Budget service for MonarchMoney Enhanced.

Handles budget management, goal tracking, and financial planning operations.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from gql import gql

from ..validators import InputValidator
from .base_service import BaseService

if TYPE_CHECKING:
    from ..monarchmoney import MonarchMoney


class BudgetService(BaseService):
    """
    Service for managing budgets and financial goals.

    This service handles:
    - Budget data retrieval and management
    - Budget amount updates and planning
    - Financial goal CRUD operations
    - Cash flow analysis and summaries
    - Bill tracking and payments
    """

    async def get_budgets(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get budget data and planning information.

        Args:
            start_date: Start date for budget period (YYYY-MM-DD)
            end_date: End date for budget period (YYYY-MM-DD)
            category_ids: Optional list of category IDs to filter

        Returns:
            Budget data with categories, amounts, and spending analysis
        """
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching budgets",
            start_date=start_date,
            end_date=end_date,
            category_count=len(category_ids) if category_ids else 0,
        )

        variables = {}
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date
        if category_ids:
            variables["categoryIds"] = category_ids

        query = gql(
            """
            query Common_GetJointPlanningData(
                $startDate: String,
                $endDate: String,
                $categoryIds: [String]
            ) {
                budgets(
                    startDate: $startDate,
                    endDate: $endDate,
                    categoryIds: $categoryIds
                ) {
                    id
                    name
                    period
                    startDate
                    endDate
                    totalBudgeted
                    totalSpent
                    totalRemaining
                    categories {
                        id
                        name
                        icon
                        color
                        budgetAmount
                        spentAmount
                        remainingAmount
                        percentSpent
                        transactions {
                            id
                            amount
                            date
                            merchant {
                                name
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
                categoryGroups {
                    id
                    name
                    type
                    budgetAmount
                    spentAmount
                    categories {
                        id
                        name
                        budgetAmount
                        spentAmount
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="Common_GetJointPlanningData",
            graphql_query=query,
            variables=variables,
        )

    async def set_budget_amount(
        self,
        category_id: str,
        amount: Union[str, int, float],
        period: str = "monthly",
        start_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update budget amount for a category.

        Args:
            category_id: ID of the category to update
            amount: Budget amount to set
            period: Budget period ("monthly", "yearly", "custom")
            start_date: Start date for custom period (YYYY-MM-DD)

        Returns:
            Updated budget information

        Raises:
            ValidationError: If parameters are invalid
        """
        category_id = InputValidator.validate_string_length(
            category_id, "category_id", 1, 100
        )
        amount = InputValidator.validate_amount(amount)

        if start_date:
            start_date = InputValidator.validate_date_string(start_date)

        self.logger.info(
            "Setting budget amount",
            category_id=category_id,
            amount=amount,
            period=period,
        )

        variables = {
            "categoryId": category_id,
            "amount": amount,
            "period": period,
        }

        if start_date:
            variables["startDate"] = start_date

        query = gql(
            """
            mutation Common_UpdateBudgetItem(
                $categoryId: String!,
                $amount: Float!,
                $period: String!,
                $startDate: String
            ) {
                updateBudgetItem(
                    categoryId: $categoryId,
                    amount: $amount,
                    period: $period,
                    startDate: $startDate
                ) {
                    budget {
                        id
                        category {
                            id
                            name
                            __typename
                        }
                        amount
                        period
                        startDate
                        endDate
                        spentAmount
                        remainingAmount
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
            operation="Common_UpdateBudgetItem",
            graphql_query=query,
            variables=variables,
        )

    async def get_goals(self) -> Dict[str, Any]:
        """
        Get financial goals and targets with progress tracking.

        Returns:
            List of financial goals with progress and target information
        """
        self.logger.info("Fetching financial goals")

        query = gql(
            """
            query GetGoals {
                goals {
                    id
                    name
                    description
                    targetAmount
                    currentAmount
                    targetDate
                    createdAt
                    updatedAt
                    isCompleted
                    progressPercent
                    category {
                        id
                        name
                        icon
                        color
                        __typename
                    }
                    accounts {
                        id
                        displayName
                        currentBalance
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(operation="GetGoals", query=query)

    async def create_goal(
        self,
        name: str,
        target_amount: Union[str, int, float],
        target_date: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[str] = None,
        account_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new financial goal.

        Args:
            name: Goal name
            target_amount: Target amount to achieve
            target_date: Target completion date (YYYY-MM-DD)
            description: Optional goal description
            category_id: Optional category to associate with the goal
            account_ids: Optional list of account IDs to track for this goal

        Returns:
            Created goal data

        Raises:
            ValidationError: If parameters are invalid
        """
        name = InputValidator.validate_string_length(name, "goal name", 1, 100)
        target_amount = InputValidator.validate_amount(target_amount)

        if target_date:
            target_date = InputValidator.validate_date_string(target_date)
        if description:
            description = InputValidator.validate_string_length(
                description, "description", 0, 500
            )
        if category_id:
            category_id = InputValidator.validate_string_length(
                category_id, "category_id", 1, 100
            )

        self.logger.info(
            "Creating financial goal",
            name=name,
            target_amount=target_amount,
            target_date=target_date,
        )

        variables = {
            "name": name,
            "targetAmount": target_amount,
        }

        if target_date:
            variables["targetDate"] = target_date
        if description:
            variables["description"] = description
        if category_id:
            variables["categoryId"] = category_id
        if account_ids:
            variables["accountIds"] = account_ids

        query = gql(
            """
            mutation CreateGoal(
                $name: String!,
                $targetAmount: Float!,
                $targetDate: String,
                $description: String,
                $categoryId: String,
                $accountIds: [String]
            ) {
                createGoal(
                    name: $name,
                    targetAmount: $targetAmount,
                    targetDate: $targetDate,
                    description: $description,
                    categoryId: $categoryId,
                    accountIds: $accountIds
                ) {
                    goal {
                        id
                        name
                        description
                        targetAmount
                        currentAmount
                        targetDate
                        createdAt
                        isCompleted
                        progressPercent
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
            operation="CreateGoal", graphql_query=query, variables=variables
        )

    async def update_goal(
        self,
        goal_id: str,
        name: Optional[str] = None,
        target_amount: Optional[Union[str, int, float]] = None,
        target_date: Optional[str] = None,
        description: Optional[str] = None,
        is_completed: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing financial goal.

        Args:
            goal_id: ID of the goal to update
            name: New goal name
            target_amount: New target amount
            target_date: New target date (YYYY-MM-DD)
            description: New description
            is_completed: Whether the goal is completed

        Returns:
            Updated goal data

        Raises:
            ValidationError: If parameters are invalid
        """
        goal_id = InputValidator.validate_string_length(goal_id, "goal_id", 1, 100)

        if name is not None:
            name = InputValidator.validate_string_length(name, "goal name", 1, 100)
        if target_amount is not None:
            target_amount = InputValidator.validate_amount(target_amount)
        if target_date is not None:
            target_date = InputValidator.validate_date_string(target_date)
        if description is not None:
            description = InputValidator.validate_string_length(
                description, "description", 0, 500
            )

        self.logger.info("Updating financial goal", goal_id=goal_id, name=name)

        variables = {"id": goal_id}

        if name is not None:
            variables["name"] = name
        if target_amount is not None:
            variables["targetAmount"] = target_amount
        if target_date is not None:
            variables["targetDate"] = target_date
        if description is not None:
            variables["description"] = description
        if is_completed is not None:
            variables["isCompleted"] = is_completed

        query = gql(
            """
            mutation UpdateGoal(
                $id: String!,
                $name: String,
                $targetAmount: Float,
                $targetDate: String,
                $description: String,
                $isCompleted: Boolean
            ) {
                updateGoal(
                    id: $id,
                    name: $name,
                    targetAmount: $targetAmount,
                    targetDate: $targetDate,
                    description: $description,
                    isCompleted: $isCompleted
                ) {
                    goal {
                        id
                        name
                        description
                        targetAmount
                        currentAmount
                        targetDate
                        updatedAt
                        isCompleted
                        progressPercent
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
            operation="UpdateGoal", graphql_query=query, variables=variables
        )

    async def delete_goal(self, goal_id: str) -> bool:
        """
        Delete a financial goal.

        Args:
            goal_id: ID of the goal to delete

        Returns:
            True if deletion was successful

        Raises:
            ValidationError: If goal_id is invalid
        """
        goal_id = InputValidator.validate_string_length(goal_id, "goal_id", 1, 100)

        self.logger.info("Deleting financial goal", goal_id=goal_id)

        variables = {"id": goal_id}

        query = gql(
            """
            mutation DeleteGoal($id: String!) {
                deleteGoal(id: $id) {
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
            operation="DeleteGoal", graphql_query=query, variables=variables
        )

        delete_result = result.get("deleteGoal", {})
        errors = delete_result.get("errors", [])

        if errors:
            self.logger.error("Goal deletion failed", goal_id=goal_id, errors=errors)
            return False

        success = delete_result.get("deleted", False)
        if success:
            self.logger.info("Financial goal deleted successfully", goal_id=goal_id)

        return success

    async def get_cashflow(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "month",
    ) -> Dict[str, Any]:
        """
        Get cash flow analysis with income and expense breakdown.

        Args:
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            group_by: Grouping period ("day", "week", "month", "year")

        Returns:
            Cash flow data with income, expenses, and net flow over time
        """
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching cash flow analysis",
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
        )

        variables = {"groupBy": group_by}
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date

        query = gql(
            """
            query Web_GetCashFlowPage(
                $startDate: String,
                $endDate: String,
                $groupBy: String!
            ) {
                cashFlow(
                    startDate: $startDate,
                    endDate: $endDate,
                    groupBy: $groupBy
                ) {
                    period
                    income
                    expenses
                    netFlow
                    incomeCategories {
                        category {
                            id
                            name
                            icon
                            color
                            __typename
                        }
                        amount
                        __typename
                    }
                    expenseCategories {
                        category {
                            id
                            name
                            icon
                            color
                            __typename
                        }
                        amount
                        __typename
                    }
                    __typename
                }
                summary {
                    totalIncome
                    totalExpenses
                    netIncome
                    averageMonthlyIncome
                    averageMonthlyExpenses
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="Web_GetCashFlowPage", graphql_query=query, variables=variables
        )

    async def get_cashflow_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get cash flow summary with key metrics.

        Args:
            start_date: Start date for summary (YYYY-MM-DD)
            end_date: End date for summary (YYYY-MM-DD)

        Returns:
            Cash flow summary with totals and averages
        """
        # This can reuse the get_cashflow method and extract just the summary
        cash_flow_data = await self.get_cashflow(start_date, end_date)
        return cash_flow_data.get("summary", {})

    async def get_bills(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_completed: bool = False,
    ) -> Dict[str, Any]:
        """
        Get upcoming bills and payments with due dates.

        Args:
            start_date: Start date for bill lookup (YYYY-MM-DD)
            end_date: End date for bill lookup (YYYY-MM-DD)
            include_completed: Whether to include already paid bills

        Returns:
            Upcoming bills data with due dates, amounts, and payment status
        """
        if start_date:
            start_date = InputValidator.validate_date_string(start_date)
        if end_date:
            end_date = InputValidator.validate_date_string(end_date)

        self.logger.info(
            "Fetching bills",
            start_date=start_date,
            end_date=end_date,
            include_completed=include_completed,
        )

        variables = {"includeCompleted": include_completed}
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date

        query = gql(
            """
            query GetBills(
                $startDate: String,
                $endDate: String,
                $includeCompleted: Boolean!
            ) {
                bills(
                    startDate: $startDate,
                    endDate: $endDate,
                    includeCompleted: $includeCompleted
                ) {
                    id
                    name
                    amount
                    dueDate
                    isPaid
                    isOverdue
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
                    merchant {
                        id
                        name
                        logoUrl
                        __typename
                    }
                    recurringRule {
                        frequency
                        interval
                        nextDueDate
                        __typename
                    }
                    __typename
                }
                summary {
                    totalUpcoming
                    totalOverdue
                    totalPaid
                    nextBillDue
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="GetBills", graphql_query=query, variables=variables
        )
