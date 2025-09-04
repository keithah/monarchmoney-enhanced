import asyncio
import json
import logging

from monarchmoney import MonarchMoney

# Setup logging for demo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

_SESSION_FILE_ = ".mm/mm_session.pickle"


def main() -> None:
    """Example usage of MonarchMoney API with proper logging."""
    # Use session file
    mm = MonarchMoney(session_file=_SESSION_FILE_)
    asyncio.run(mm.interactive_login())

    # Subscription details
    subs = asyncio.run(mm.get_subscription_details())
    logger.info("Retrieved subscription details: %s", subs)

    # Accounts
    accounts = asyncio.run(mm.get_accounts())
    with open("data.json", "w") as outfile:
        json.dump(accounts, outfile)

    # Institutions
    institutions = asyncio.run(mm.get_institutions())
    with open("institutions.json", "w") as outfile:
        json.dump(institutions, outfile)

    # Budgets
    budgets = asyncio.run(mm.get_budgets())
    with open("budgets.json", "w") as outfile:
        json.dump(budgets, outfile, indent=4)

    # Transactions summary
    transactions_summary = asyncio.run(mm.get_transactions_summary())
    with open("transactions_summary.json", "w") as outfile:
        json.dump(transactions_summary, outfile)

    # # Transaction categories
    categories = asyncio.run(mm.get_transaction_categories())
    with open("categories.json", "w") as outfile:
        json.dump(categories, outfile)

    income_categories = dict()
    for c in categories.get("categories"):
        if c.get("group").get("type") == "income":
            category_info = f'{c.get("group").get("type")} - {c.get("group").get("name")} - {c.get("name")}'
            logger.info("Income category: %s", category_info)
            income_categories[c.get("name")] = 0

    expense_category_groups = dict()
    for c in categories.get("categories"):
        if c.get("group").get("type") == "expense":
            category_info = f'{c.get("group").get("type")} - {c.get("group").get("name")} - {c.get("name")}'
            logger.info("Expense category: %s", category_info)
            expense_category_groups[c.get("group").get("name")] = 0

    # Transactions
    transactions = asyncio.run(mm.get_transactions(limit=10))
    with open("transactions.json", "w") as outfile:
        json.dump(transactions, outfile)

    # Cashflow
    cashflow = asyncio.run(
        mm.get_cashflow(start_date="2023-10-01", end_date="2023-10-31")
    )
    with open("cashflow.json", "w") as outfile:
        json.dump(cashflow, outfile)

    for c in cashflow.get("summary"):
        summary_text = (
            f'Income: {c.get("summary").get("sumIncome")} '
            f'Expense: {c.get("summary").get("sumExpense")} '
            f'Savings: {c.get("summary").get("savings")} '
            f'({c.get("summary").get("savingsRate"):.0%})'
        )
        logger.info("Cashflow summary: %s", summary_text)

    for c in cashflow.get("byCategory"):
        if c.get("groupBy").get("category").get("group").get("type") == "income":
            income_categories[c.get("groupBy").get("category").get("name")] += c.get(
                "summary"
            ).get("sum")

    for c in cashflow.get("byCategoryGroup"):
        if c.get("groupBy").get("categoryGroup").get("type") == "expense":
            expense_category_groups[
                c.get("groupBy").get("categoryGroup").get("name")
            ] += c.get("summary").get("sum")

    logger.info("Income categories summary: %s", income_categories)
    logger.info("Expense category groups summary: %s", expense_category_groups)


main()
