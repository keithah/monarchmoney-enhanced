"""
Pytest configuration and fixtures for MonarchMoney tests.
"""

from unittest.mock import AsyncMock

import pytest

from monarchmoney import MonarchMoney


@pytest.fixture
def mock_monarch():
    """Create a MonarchMoney instance with mocked dependencies."""
    return MonarchMoney(token="mock_token_12345")


@pytest.fixture
def mock_successful_login_response():
    """Mock successful login response from Monarch Money API."""
    return {
        "token": "mock_auth_token_abcdef123456",
        "tokenExpiration": None,
        "id": "12345",
        "email": "test@example.com",
        "name": "Test User",
        "household": {"id": "household_123", "name": "Test Household"},
    }


@pytest.fixture
def mock_mfa_required_response():
    """Mock response that requires MFA."""

    class MockResponse:
        status = 403
        reason = "Forbidden"

        async def json(self):
            return {"detail": "Multi-Factor Auth Required"}

    return MockResponse()


@pytest.fixture
def mock_rate_limit_response():
    """Mock 429 rate limit response."""

    class MockResponse:
        status = 429
        reason = "Too Many Requests"

        async def json(self):
            return {"detail": "Rate limit exceeded"}

    return MockResponse()


@pytest.fixture
def mock_accounts_response():
    """Mock successful accounts response."""
    return {
        "accounts": [
            {
                "id": "account_1",
                "displayName": "Test Checking",
                "currentBalance": 1500.00,
                "type": {"name": "checking", "display": "Checking"},
                "subtype": {"name": "checking", "display": "Checking"},
                "isHidden": False,
                "includeInNetWorth": True,
            },
            {
                "id": "account_2",
                "displayName": "Test Savings",
                "currentBalance": 5000.00,
                "type": {"name": "savings", "display": "Savings"},
                "subtype": {"name": "savings", "display": "Savings"},
                "isHidden": False,
                "includeInNetWorth": True,
            },
        ],
        "householdPreferences": {"id": "prefs_123", "accountGroupOrder": []},
    }


@pytest.fixture
def mock_transactions_response():
    """Mock successful transactions response."""
    return {
        "allTransactions": {
            "totalCount": 100,
            "results": [
                {
                    "id": "txn_1",
                    "amount": -25.50,
                    "date": "2024-01-15",
                    "description": "Coffee Shop",
                    "account": {"id": "account_1", "displayName": "Test Checking"},
                },
                {
                    "id": "txn_2",
                    "amount": -12.99,
                    "date": "2024-01-14",
                    "description": "Lunch",
                    "account": {"id": "account_1", "displayName": "Test Checking"},
                },
            ],
        }
    }


@pytest.fixture
def mock_session():
    """Mock aiohttp ClientSession."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def sample_credentials():
    """Sample test credentials."""
    return {
        "email": "test@example.com",
        "password": "test_password",
        "mfa_code": "123456",
    }
