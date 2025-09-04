# Monarch Money

Python library for accessing [Monarch Money](https://www.monarchmoney.com/referral/jtfazovwp9) data.

## 🙏 Acknowledgments

Huge shoutout to [hammem](https://github.com/hammem) for originally starting this project! This is simply a fork of [his hard work](https://github.com/hammem/monarchmoney) to continue development and fix critical authentication issues.

## 🔧 Enhanced Features

This fork includes **comprehensive improvements** and implements features requested in the original repository:

### 🎯 **Core Enhancements**
- **Fixed GraphQL Server Errors**: Resolved "Something went wrong processing" errors in account queries
- **Stable Account Fetching**: Simplified GraphQL queries for reliable account data retrieval  
- **404 Login Error Fixes**: Automatic GraphQL fallback when REST endpoints return 404
- **Enhanced Authentication**: Proper headers (device-uuid, Origin) and email OTP support  
- **Advanced Error Recovery**: Automatic session recovery and retry logic with exponential backoff
- **Comprehensive Test Suite**: 58 tests passing with full CI/CD pipeline

### 💼 **Investment Management** (implements [Issue #112](https://github.com/hammem/monarchmoney/issues/112))
- **✅ Add Holdings API**: Complete manual holdings management
- `create_manual_holding()` - Add holdings by security ID or ticker
- `update_holding_quantity()` - Modify existing holdings
- `delete_manual_holding()` - Remove holdings  
- `get_account_holdings()` - Retrieve all holdings for accounts
- `get_holding_by_ticker()` - Lookup specific holdings

### 📊 **Advanced Budget Management** (implements [PR #154](https://github.com/hammem/monarchmoney/pull/154))
- **✅ Flexible Budgets Support**: Full flexible budget API implementation
- `set_budget_amount()` - Update budget amounts with flexible period support
- `get_budgets()` - Retrieve budgets with flexible expense tracking
- Support for `BudgetFlexMonthlyAmounts` and flexible budget variability
- Complete budget management with rollover and planning features

### 🎯 **Financial Goals & Planning**
- `create_goal()` - Create financial goals with target amounts and dates
- `update_goal()` - Modify existing goals and track progress  
- `delete_goal()` - Remove completed or unwanted goals
- `get_goals()` - Retrieve all goals with progress tracking

### 💰 **Cash Flow Analysis**
- `get_cashflow()` - Detailed income/expense analysis with category breakdowns
- `get_cashflow_summary()` - Key financial metrics and trends
- `get_bills()` - Upcoming bills and payment tracking
- Advanced financial planning and forecasting capabilities

# Installation

## From Source Code

Clone this repository from Git

`git clone https://github.com/keithah/monarchmoney-enhanced.git`

## Via `pip`

`pip install monarchmoney-enhanced`

**Note**: This package is published as `monarchmoney-enhanced` on PyPI to distinguish it from the original `monarchmoney` package while maintaining the same Python import structure.
# Instantiate & Login

There are two ways to use this library: interactive and non-interactive.

## Interactive

If you're using this library in something like iPython or Jupyter, you can run an interactive-login which supports multi-factor authentication:

```python
from monarchmoney import MonarchMoney

mm = MonarchMoney()
await mm.interactive_login()
```
This will prompt you for the email, password and, if needed, the multi-factor token.

## Non-interactive

For a non-interactive session, you'll need to create an instance and login:

```python
from monarchmoney import MonarchMoney

mm = MonarchMoney()
await mm.login(email, password)
```

This may throw a `RequireMFAException`.  If it does, you'll need to get a multi-factor token and call the following method:

```python
from monarchmoney import MonarchMoney, RequireMFAException

mm = MonarchMoney()
try:
        await mm.login(email, password)
except RequireMFAException:
        await mm.multi_factor_authenticate(email, password, multi_factor_code)
```

**Note**: The library automatically detects whether your MFA code is an email OTP (6 digits) or TOTP from an authenticator app, and uses the appropriate authentication field.

Alternatively, you can provide the MFA Secret Key. The MFA Secret Key is found when setting up the MFA in Monarch Money by going to Settings -> Security -> Enable MFA -> and copy the "Two-factor text code". Then provide it in the login() method:
```python
from monarchmoney import MonarchMoney, RequireMFAException

mm = MonarchMoney()
await mm.login(
        email=email,
        password=password,
        save_session=False,
        use_saved_session=False,
        mfa_secret_key=mfa_secret_key,
    )

```

# Use a Saved Session

You can easily save your session for use later on.  While we don't know precisely how long a session lasts, authors of this library have found it can last several months.

```python
from monarchmoney import MonarchMoney, RequireMFAException

mm = MonarchMoney()
mm.interactive_login()

# Save it for later, no more need to login!
mm.save_session()
```

Once you've logged in, you can simply load the saved session to pick up where you left off.

```python
from monarchmoney import MonarchMoney, RequireMFAException

mm = MonarchMoney()
mm.load_session()

# Then, start accessing data!
await mm.get_accounts()
```

# Accessing Data

This enhanced library provides **comprehensive financial data access**:

## 💼 **Investment & Holdings Management**

- `get_account_holdings(account_id)` - Get all securities in investment accounts
- `create_manual_holding(account_id, symbol, quantity)` - **Add holdings by ticker** 
- `create_manual_holding_by_ticker(account_id, ticker, quantity)` - Add holdings with ticker lookup
- `update_holding_quantity(holding_id, quantity)` - Modify existing holdings
- `delete_manual_holding(holding_id)` - Remove holdings
- `get_holding_by_ticker(ticker)` - Lookup holdings by ticker symbol

## 📊 **Budget & Financial Planning**

- `get_budgets()` - **Get budgets with flexible budget support**
- `set_budget_amount(category_id, amount)` - **Update budget amounts with flexible periods**
- `get_goals()` - Get financial goals with progress tracking
- `create_goal(name, target_amount)` - Create new financial goals
- `update_goal(goal_id, **kwargs)` - Update existing goals
- `delete_goal(goal_id)` - Remove financial goals
- `get_cashflow()` - Income/expense analysis with category breakdowns
- `get_cashflow_summary()` - Key financial metrics and trends
- `get_bills()` - Upcoming bills and payment tracking

## 🏦 **Account & Transaction Data**

- `get_accounts()` - **Get all linked accounts (with GraphQL fixes)**
- `get_me()` - Current user profile (timezone, email, name, MFA status)
- `get_merchants()` - Merchant list from transactions
- `get_account_type_options()` - All available account types and subtypes
- `get_account_history()` - Daily account balance history
- `get_institutions()` - Linked financial institutions
- `get_subscription_details()` - Account status (paid/trial)
- `get_recurring_transactions()` - Future recurring transactions
- `get_transactions()` - Transaction data with flexible date ranges
- `get_transactions_summary()` - Transaction summary from transactions page
- `get_transactions_summary_card()` - Summary card data with totals
- `get_transaction_categories()` - All configured transaction categories
- `get_transaction_category_groups()` - All category groups
- `get_transaction_details(transaction_id)` - Detailed transaction data
- `get_transaction_splits(transaction_id)` - Transaction split information
- `get_transaction_tags()` - All configured transaction tags
- `get_recurring_transactions()` - **Recurring transaction streams and patterns**
- `mark_stream_as_not_recurring(stream_id)` - **Mark merchants as not recurring**
- `get_net_worth_history()` - Net worth tracking over time
- `is_accounts_refresh_complete()` - Account refresh status

## 🔄 **Data Modification Methods**

### 💼 **Investment Management**
- `create_manual_holding(account_id, symbol, quantity)` - **Create holdings by ticker**
- `update_holding_quantity(holding_id, quantity)` - Update holding quantities
- `delete_manual_holding(holding_id)` - Remove holdings from accounts

### 📊 **Budget & Goals Management** 
- `set_budget_amount(category_id, amount)` - **Set flexible budget amounts**
- `create_goal(name, target_amount)` - Create new financial goals
- `update_goal(goal_id, **kwargs)` - Update existing goals  
- `delete_goal(goal_id)` - Remove financial goals

### 🏦 **Account Management**
- `create_manual_account(name, type, balance)` - Create new manual accounts
- `update_account(account_id, **kwargs)` - Update account settings/balance
- `delete_account(account_id)` - Delete accounts
- `upload_account_balance_history(account_id, csv_file)` - Upload balance history
- `request_accounts_refresh()` - **Non-blocking** account sync refresh
- `request_accounts_refresh_and_wait()` - **Blocking** account sync refresh

### 💳 **Transaction Management**
- `create_transaction(account_id, amount, date, **kwargs)` - Create transactions
- `update_transaction(transaction_id, **kwargs)` - Update transaction attributes
- `delete_transaction(transaction_id)` - Delete transactions
- `update_transaction_splits(transaction_id, splits)` - Modify transaction splits
- `create_transaction_category(name, **kwargs)` - Create transaction categories
- `update_transaction_category(category_id, **kwargs)` - Update categories
- `delete_transaction_category(category_id)` - Delete single category
- `delete_transaction_categories(category_ids)` - Delete multiple categories
- `create_transaction_tag(name)` - Create transaction tags
- `set_transaction_tags(transaction_id, tag_ids)` - Set tags on transactions

### 🔄 **Recurring Transaction Management**
- `mark_stream_as_not_recurring(stream_id)` - **Mark merchants as not recurring**
- `get_edit_merchant(merchant_id)` - **Get merchant edit info with recurring details**
- `get_recurring_transactions()` - Get upcoming recurring transactions
- `review_recurring_stream(stream_id, status)` - Review and approve recurring streams

## Session Management Methods

- `validate_session` - validates current session by making a lightweight API call
- `is_session_stale` - checks if session needs validation based on elapsed time  
- `ensure_valid_session` - ensures session is valid, validating if stale
- `get_session_info` - gets session metadata (creation time, last validation, staleness)

## Transaction Rules

Complete transaction rules management:
- `get_transaction_rules` - Get all configured rules with criteria and actions
- `create_transaction_rule` - Create rules with merchant/amount/category/account criteria
- `update_transaction_rule` - Update existing rule criteria and actions
- `delete_transaction_rule` - Delete individual rules
- `reorder_transaction_rules` - Change rule execution order
- `preview_transaction_rule` - Preview rule effects before creating
- `delete_all_transaction_rules` - Delete all rules at once
- `create_categorization_rule` - Helper for simple merchant→category rules

For a complete mapping of GraphQL operations and implementation status, see [GRAPHQL.md](GRAPHQL.md).

# Development & Testing

## Running Tests

This project includes a comprehensive test suite. To run tests:

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=monarchmoney --cov-report=term-missing

# Run specific test categories
pytest -m "api"          # API method tests
pytest -m "auth"         # Authentication tests
pytest -m "unit"         # Unit tests
```

## Test Categories

- **Authentication Tests**: Login, MFA, session management, header validation
- **API Method Tests**: Account/transaction retrieval, GraphQL execution, error handling
- **Integration Tests**: End-to-end functionality and field detection
- **Retry Logic Tests**: Rate limiting, exponential backoff, error handling

## CI/CD

This project uses GitHub Actions for continuous integration:

- **Multi-Python Testing**: Supports Python 3.8 through 3.12
- **Code Quality**: Automated linting with flake8, formatting with black, import sorting with isort
- **Coverage Reporting**: Integrated with Codecov for test coverage tracking

# Contributing

Any and all contributions -- code, documentation, feature requests, feedback -- are welcome!

If you plan to submit up a pull request, you can expect a timely review.  Please ensure you do the following:

  - Configure your IDE or manually run [Black](https://github.com/psf/black) to auto-format the code.
  - Ensure you run the unit tests in this project: `pytest`
    
Actions are configured in this repo to run against all PRs and merges which will block them if a unit test fails or Black throws an error.

# Troubleshooting

## Authentication Issues

If you're experiencing login problems, this fork includes several fixes:

**404 Login Errors**: The library automatically falls back to GraphQL authentication if REST endpoints return 404.

**403 Forbidden Errors**: Ensure you're using the latest version which includes proper browser headers (device-uuid, Origin, User-Agent).

**MFA Problems**: The library automatically detects email OTP vs authenticator app codes:
- 6-digit numeric codes are treated as email OTP
- Other formats are treated as TOTP from authenticator apps

**Rate Limiting**: Built-in retry logic with exponential backoff handles temporary rate limits automatically.

# FAQ

**How do I use this API if I login to Monarch via Google?**

If you currently use Google or 'Continue with Google' to access your Monarch account, you'll need to set a password to leverage this API.  You can set a password on your Monarch account by going to your [security settings](https://app.monarchmoney.com/settings/security).  

Don't forget to use a password unique to your Monarch account and to enable multi-factor authentication!

**What makes this fork superior?**

This enhanced fork is **ahead of the original repository** with implemented features that others are still requesting:

🎯 **Requested Features Already Implemented:**
- **[Issue #112](https://github.com/hammem/monarchmoney/issues/112)**: ✅ Add Holdings API - Full investment management
- **[PR #154](https://github.com/hammem/monarchmoney/pull/154)**: ✅ Flexible Budgets - Complete budget flexibility support

🔧 **Critical Issue Fixes:**
- **GraphQL Server Errors**: Fixed "Something went wrong processing" errors
- **404 Authentication**: Automatic GraphQL fallback for auth endpoints  
- **403 Forbidden**: Proper browser headers (device-uuid, Origin, User-Agent)
- **MFA Detection**: Smart email OTP vs TOTP field detection
- **Session Recovery**: Automatic session validation and recovery

🚀 **Advanced Features:**
- **Financial Goals Management**: Complete CRUD operations for goal tracking
- **Cash Flow Analysis**: Detailed income/expense breakdowns and trends
- **Bills Management**: Payment tracking and due date monitoring  
- **Error Recovery**: Exponential backoff retry logic for robustness
- **Test Coverage**: 58 passing tests with full CI/CD pipeline

