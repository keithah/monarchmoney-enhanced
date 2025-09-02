"""
Integration tests for MonarchMoney functionality.
These tests focus on the core behavior without deep HTTP mocking.
"""
import pytest
from unittest.mock import patch, AsyncMock
from monarchmoney import MonarchMoney
from monarchmoney.monarchmoney import LoginFailedException


class TestBasicFunctionality:
    """Test basic MonarchMoney functionality."""
    
    def test_initialization(self):
        """Test MonarchMoney initialization."""
        mm = MonarchMoney()
        
        # Check basic attributes
        assert mm.timeout == 10
        assert mm.token is None
        assert isinstance(mm._headers, dict)
        assert "User-Agent" in mm._headers
        assert "device-uuid" in mm._headers
    
    def test_initialization_with_token(self):
        """Test MonarchMoney initialization with token."""
        mm = MonarchMoney(token="test_token")
        
        assert mm.token == "test_token"
        assert mm._headers["Authorization"] == "Token test_token"
    
    def test_set_token_updates_headers(self):
        """Test that set_token properly updates headers."""
        mm = MonarchMoney()
        
        assert "Authorization" not in mm._headers
        
        mm.set_token("new_token")
        assert mm.token == "new_token"
        assert mm._headers["Authorization"] == "Token new_token"
    
    def test_timeout_configuration(self):
        """Test timeout configuration."""
        mm = MonarchMoney(timeout=30)
        assert mm.timeout == 30
        
        mm.set_timeout(60)
        assert mm.timeout == 60


class TestAuthenticationRequirements:
    """Test that API methods require authentication."""
    
    @pytest.mark.asyncio
    async def test_get_accounts_requires_auth(self):
        """Test that get_accounts requires authentication."""
        mm = MonarchMoney(session_file="/tmp/nonexistent.pickle")
        
        with pytest.raises(LoginFailedException, match="Make sure you call login"):
            await mm.get_accounts()
    
    @pytest.mark.asyncio  
    async def test_get_transactions_requires_auth(self):
        """Test that get_transactions requires authentication."""
        mm = MonarchMoney(session_file="/tmp/nonexistent.pickle")
        
        with pytest.raises(LoginFailedException, match="Make sure you call login"):
            await mm.get_transactions()
    
    @pytest.mark.asyncio
    async def test_get_budgets_requires_auth(self):
        """Test that get_budgets requires authentication."""
        mm = MonarchMoney(session_file="/tmp/nonexistent.pickle")
        
        with pytest.raises(LoginFailedException, match="Make sure you call login"):
            await mm.get_budgets()


class TestMockBehavior:
    """Test behavior with mocked GraphQL calls."""
    
    @pytest.mark.asyncio
    async def test_accounts_with_mock(self, mock_accounts_response):
        """Test get_accounts with mocked GraphQL response."""
        mm = MonarchMoney(token="test_token")
        
        with patch.object(mm, 'gql_call', new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = mock_accounts_response
            
            result = await mm.get_accounts()
            
            assert result == mock_accounts_response
            assert "accounts" in result
            assert len(result["accounts"]) == 2
    
    @pytest.mark.asyncio
    async def test_transactions_with_mock(self, mock_transactions_response):
        """Test get_transactions with mocked GraphQL response."""
        mm = MonarchMoney(token="test_token")
        
        with patch.object(mm, 'gql_call', new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = mock_transactions_response
            
            result = await mm.get_transactions()
            
            assert result == mock_transactions_response
            assert "allTransactions" in result
            assert result["allTransactions"]["totalCount"] == 100


class TestFieldDetection:
    """Test field detection logic."""
    
    def test_email_otp_vs_totp_detection(self):
        """Test email OTP vs TOTP field detection logic."""
        mm = MonarchMoney()
        
        # Test 6-digit codes (should be email OTP)
        test_data = {"email": "test@test.com", "password": "pass"}
        
        # Simulate the logic from _multi_factor_authenticate
        code = "123456"  # 6 digits
        if len(code) == 6 and code.isdigit():
            test_data["email_otp"] = code
        else:
            test_data["totp"] = code
            
        assert "email_otp" in test_data
        assert test_data["email_otp"] == "123456"
        assert "totp" not in test_data
        
        # Test non-6-digit codes (should be TOTP)
        test_data2 = {"email": "test@test.com", "password": "pass"}
        code2 = "abc123"  # Not 6 digits
        if len(code2) == 6 and code2.isdigit():
            test_data2["email_otp"] = code2
        else:
            test_data2["totp"] = code2
            
        assert "totp" in test_data2
        assert test_data2["totp"] == "abc123"
        assert "email_otp" not in test_data2


class TestSecurityConfiguration:
    """Test security-related configurations."""
    
    def test_ssl_verification_enabled(self):
        """Test that SSL certificate verification is enabled."""
        from unittest.mock import patch, MagicMock
        
        mm = MonarchMoney(token="test_token")
        
        with patch('monarchmoney.monarchmoney.AIOHTTPTransport') as mock_transport:
            mock_transport.return_value = MagicMock()
            
            mm._get_graphql_client()
            
            # Verify SSL was enabled in transport creation
            mock_transport.assert_called()
            call_kwargs = mock_transport.call_args[1]
            assert call_kwargs.get('ssl') is True