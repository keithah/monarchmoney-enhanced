"""
Authentication service for MonarchMoney Enhanced.

Handles all authentication, MFA, and session lifecycle operations.
"""

import os
from typing import TYPE_CHECKING, Any, Dict, Optional

import oathtool
from aiohttp import ClientSession
from gql import gql

from ..exceptions import (
    AuthenticationError,
    InvalidMFAError,
    MFARequiredError,
    ValidationError,
)
from ..session_storage import SecureSessionStorage, get_secure_storage
from ..validators import validate_login_credentials, validate_mfa_credentials
from .base_service import BaseService

if TYPE_CHECKING:
    from ..monarchmoney import MonarchMoney


class AuthenticationService(BaseService):
    """
    Service for managing authentication and session operations.

    This service handles:
    - Login and logout operations
    - Multi-factor authentication (MFA)
    - Session persistence and validation
    - Session lifecycle management
    """

    def __init__(self, monarch_client: "MonarchMoney"):
        """Initialize the authentication service."""
        super().__init__(monarch_client)
        self._session_storage: Optional[SecureSessionStorage] = None

    @property
    def session_storage(self) -> SecureSessionStorage:
        """Get or create the session storage instance."""
        if self._session_storage is None:
            # Get password and encryption settings from client
            password = getattr(self.client, "_session_password", None)
            use_encryption = getattr(self.client, "_use_encryption", True)
            self._session_storage = get_secure_storage(password, use_encryption)
        return self._session_storage

    async def login(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        use_saved_session: bool = True,
        save_session: bool = True,
        mfa_secret_key: Optional[str] = None,
        session_file: Optional[str] = None,
    ) -> None:
        """
        Log into a Monarch Money account.

        Args:
            email: User's email address
            password: User's password
            use_saved_session: Whether to use existing saved session
            save_session: Whether to save session after successful login
            mfa_secret_key: Optional MFA secret for automatic TOTP generation
            session_file: Optional custom session file path

        Raises:
            ValidationError: If credentials are invalid
            AuthenticationError: If login fails
            MFARequiredError: If MFA is required but not provided
        """
        session_file = session_file or self.client._session_file

        # Try to load saved session if requested
        if use_saved_session and os.path.exists(session_file):
            self.logger.info("Loading saved session", session_file=session_file)
            await self.load_session(session_file)
            return

        # Validate required credentials
        if not email or not password:
            raise ValidationError(
                "Email and password are required to login when not using a saved session.",
                details={
                    "email_provided": bool(email),
                    "password_provided": bool(password),
                },
            )

        # Validate and normalize credentials
        email, password = validate_login_credentials(email, password)

        # Perform login
        await self._login_user(email, password, mfa_secret_key)

        # Save session if requested
        if save_session:
            await self.save_session(session_file)

    async def multi_factor_authenticate(
        self, email: str, password: str, code: str
    ) -> None:
        """
        Perform multi-factor authentication.

        Args:
            email: User's email address
            password: User's password
            code: MFA code (6-8 digits)

        Raises:
            ValidationError: If credentials format is invalid
            InvalidMFAError: If MFA code is invalid
            AuthenticationError: If authentication fails
        """
        # Validate and normalize MFA credentials
        email, password, code = validate_mfa_credentials(email, password, code)

        self.logger.info("Performing multi-factor authentication", email=email)
        await self._multi_factor_authenticate(email, password, code)

    async def validate_session(self) -> bool:
        """
        Validate the current session.

        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Try a simple query to check if session is valid
            query = gql(
                """
                query ValidateSession {
                    me {
                        id
                        __typename
                    }
                }
            """
            )

            result = await self._execute_query("ValidateSession", query)
            is_valid = result.get("me", {}).get("id") is not None

            self.logger.debug(
                "Session validation completed",
                valid=is_valid,
                has_token=bool(self.client._token),
            )
            return is_valid

        except Exception as e:
            self.logger.debug("Session validation failed", error=str(e))
            return False

    def is_session_stale(self) -> bool:
        """
        Check if the session is stale and needs refresh.

        Returns:
            True if session needs refresh, False otherwise
        """
        if not self.client._last_used:
            return True

        # Check if session is older than validation interval
        import time

        session_age = time.time() - self.client._last_used
        is_stale = session_age > getattr(
            self.client, "_session_validation_interval", 3600
        )

        self.logger.debug("Session staleness check", age=session_age, stale=is_stale)
        return is_stale

    async def ensure_valid_session(self) -> None:
        """
        Ensure the session is valid, refreshing if necessary.

        Raises:
            AuthenticationError: If session cannot be validated or refreshed
        """
        if not self.client._token:
            raise AuthenticationError("No active session - please login first")

        # Check if session is stale
        if self.is_session_stale():
            self.logger.info("Session is stale, validating...")
            if not await self.validate_session():
                raise AuthenticationError("Session expired - please login again")
            else:
                # Update last used time
                import time

                self.client._last_used = time.time()
                self.logger.debug("Session validated and refreshed")

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.

        Returns:
            Dictionary with session information
        """
        import time

        return {
            "has_token": bool(self.client._token),
            "has_csrf": bool(self.client._csrf_token),
            "last_used": self.client._last_used,
            "session_age": time.time() - (self.client._last_used or 0),
            "is_stale": self.is_session_stale(),
            "session_file": self.client._session_file,
        }

    async def save_session(self, session_file: Optional[str] = None) -> None:
        """
        Save the current session to storage.

        Args:
            session_file: Optional custom session file path
        """
        session_file = session_file or self.client._session_file

        if not self.client._token:
            self.logger.warning("No active session to save")
            return

        import time

        session_data = {
            "token": self.client._token,
            "csrf_token": self.client._csrf_token,
            "last_used": time.time(),
            "headers": dict(self.client._headers),
        }

        try:
            self.session_storage.save_session(session_data, session_file)
            self.logger.info("Session saved successfully", session_file=session_file)
        except Exception as e:
            self.logger.error(
                "Failed to save session", session_file=session_file, error=str(e)
            )
            raise

    async def load_session(self, session_file: Optional[str] = None) -> None:
        """
        Load session from storage.

        Args:
            session_file: Optional custom session file path

        Raises:
            FileNotFoundError: If session file doesn't exist
            ValueError: If session file is corrupted
        """
        session_file = session_file or self.client._session_file

        try:
            session_data = self.session_storage.load_session(session_file)
            await self._load_session_data(session_data)
            self.logger.info("Session loaded successfully", session_file=session_file)
        except Exception as e:
            self.logger.error(
                "Failed to load session", session_file=session_file, error=str(e)
            )
            raise

    async def delete_session(self, session_file: Optional[str] = None) -> None:
        """
        Delete saved session.

        Args:
            session_file: Optional custom session file path
        """
        session_file = session_file or self.client._session_file

        try:
            if os.path.exists(session_file):
                os.remove(session_file)
                self.logger.info("Session deleted", session_file=session_file)
            else:
                self.logger.info("No session file to delete", session_file=session_file)

            # Clear in-memory session data
            self.client._token = None
            self.client._csrf_token = None
            self.client._last_used = None

        except Exception as e:
            self.logger.error(
                "Failed to delete session", session_file=session_file, error=str(e)
            )
            raise

    async def _load_session_data(self, session_data: Dict[str, Any]) -> None:
        """Load session data into the client."""
        self.client._token = session_data.get("token")
        self.client._csrf_token = session_data.get("csrf_token")
        self.client._last_used = session_data.get("last_used")

        # Update headers with session data
        headers = session_data.get("headers", {})
        if "Authorization" in headers:
            self.client._headers["Authorization"] = headers["Authorization"]
        if "csrftoken" in headers:
            self.client._headers["csrftoken"] = headers["csrftoken"]

        self.logger.debug("Session data loaded into client")

    async def _login_user(
        self, email: str, password: str, mfa_secret_key: Optional[str] = None
    ) -> None:
        """
        Internal method to perform user login.

        Args:
            email: User's email address
            password: User's password
            mfa_secret_key: Optional MFA secret key for automatic TOTP

        Raises:
            AuthenticationError: If login fails
            MFARequiredError: If MFA is required
        """
        from ..monarchmoney import MonarchMoneyEndpoints, retry_with_backoff

        self.logger.info("Attempting user login", email=email)

        async def _attempt_login():
            login_response = None

            async with ClientSession() as session:
                # Create JSON payload
                login_data = {
                    "username": email,
                    "password": password,
                    "trusted_device": True,
                    "supports_mfa": True,
                    "supports_email_otp": True,
                    "supports_recaptcha": True,
                }

                if mfa_secret_key:
                    # Generate TOTP code
                    totp_code = oathtool.generate_otp(mfa_secret_key)
                    login_data["totp"] = totp_code
                    self.logger.debug("Added TOTP code to login request")

                # Update headers for JSON
                headers = self.client._headers.copy()
                headers["Content-Type"] = "application/json"

                try:
                    async with session.post(
                        MonarchMoneyEndpoints.getLoginEndpoint(),
                        json=login_data,
                        headers=headers,
                    ) as response:
                        login_response = await response.json()
                        self.logger.debug(
                            "Login response received",
                            status=response.status,
                            response=login_response,
                        )

                        if response.status == 404:
                            # Fallback to GraphQL login
                            self.logger.info("REST login returned 404, trying GraphQL")
                            return await self._login_user_graphql(
                                email, password, mfa_secret_key
                            )

                        if not response.ok:
                            if response.status == 403:
                                # Use already parsed response
                                error_code = login_response.get("error_code", "")
                                detail = login_response.get("detail", "")

                                self.logger.debug(
                                    "403 response details",
                                    error_code=error_code,
                                    detail=detail,
                                    full_response=login_response,
                                )

                                # Check for various MFA indicators
                                if (
                                    error_code == "MFA_REQUIRED"
                                    or "Multi-Factor Auth Required"
                                    in str(login_response)
                                    or "MFA is required" in detail
                                ):

                                    self.logger.info(
                                        "MFA required detected, attempting MFA submission"
                                    )

                                    if mfa_secret_key:
                                        # We have MFA secret, try to submit MFA
                                        login_response = await self._submit_mfa_login(
                                            email, password, mfa_secret_key, session
                                        )
                                        return login_response
                                    else:
                                        raise MFARequiredError(
                                            "Multi-factor authentication required"
                                        )

                            raise AuthenticationError(
                                f"Login failed with status {response.status}"
                            )

                except Exception as e:
                    if "404" in str(e):
                        self.logger.info(
                            "REST login failed with 404, trying GraphQL fallback"
                        )
                        return await self._login_user_graphql(
                            email, password, mfa_secret_key
                        )
                    raise

            # Process login response
            if not login_response:
                raise AuthenticationError("No response received from login endpoint")

            # Check for MFA requirement
            if login_response.get("mfa_required"):
                raise MFARequiredError("Multi-factor authentication required")

            # Extract tokens
            token = login_response.get("token")
            csrf_token = login_response.get("csrf_token")

            if not token:
                raise AuthenticationError("No authentication token received")

            # Update client with authentication data
            self.client._token = token
            self.client._csrf_token = csrf_token
            self.client._headers["Authorization"] = f"Token {token}"
            if csrf_token:
                self.client._headers["csrftoken"] = csrf_token

            import time

            self.client._last_used = time.time()

            self.logger.info("Login successful", email=email)

        await retry_with_backoff(_attempt_login)

    async def _submit_mfa_login(
        self,
        email: str,
        password: str,
        mfa_secret_key: str,
        session: ClientSession,
    ) -> Dict[str, Any]:
        """
        Submit MFA login after receiving MFA_REQUIRED response.

        Args:
            email: User's email address
            password: User's password
            mfa_secret_key: MFA secret key for TOTP generation
            session: Active HTTP session

        Returns:
            Login response with authentication tokens

        Raises:
            AuthenticationError: If MFA submission fails
            InvalidMFAError: If MFA code is invalid
        """
        from ..monarchmoney import MonarchMoneyEndpoints

        # Generate TOTP code
        totp_code = oathtool.generate_otp(mfa_secret_key)
        self.logger.debug("Generated TOTP code for MFA submission")

        # Create JSON payload for MFA submission
        mfa_data = {
            "username": email,
            "password": password,
            "trusted_device": True,
            "supports_mfa": True,
            "supports_email_otp": True,
            "supports_recaptcha": True,
        }

        # Add the MFA code - try email_otp first, then totp
        if len(totp_code) == 6 and totp_code.isdigit():
            # Likely email OTP (6 digits)
            mfa_data["email_otp"] = totp_code
        else:
            # Likely TOTP from authenticator app
            mfa_data["totp"] = totp_code

        # Update headers for JSON
        headers = self.client._headers.copy()
        headers["Content-Type"] = "application/json"

        try:
            # Try the same login endpoint with MFA code
            async with session.post(
                MonarchMoneyEndpoints.getLoginEndpoint(),
                json=mfa_data,
                headers=headers,
            ) as response:

                response_json = await response.json()

                if not response.ok:
                    if response.status == 400:
                        # Invalid MFA code
                        error_detail = response_json.get("detail", "")
                        if (
                            "invalid" in error_detail.lower()
                            or "incorrect" in error_detail.lower()
                        ):
                            raise InvalidMFAError("Invalid MFA code provided")

                    raise AuthenticationError(
                        f"MFA submission failed with status {response.status}: {response_json}"
                    )

                self.logger.info("MFA login successful")
                return response_json

        except Exception as e:
            if isinstance(e, (AuthenticationError, InvalidMFAError)):
                raise

            self.logger.error("MFA submission error", error=str(e))
            raise AuthenticationError(f"MFA submission failed: {e}")

    async def _login_user_graphql(
        self, email: str, password: str, mfa_secret_key: Optional[str] = None
    ) -> None:
        """
        GraphQL fallback login method.

        Args:
            email: User's email address
            password: User's password
            mfa_secret_key: Optional MFA secret key

        Raises:
            AuthenticationError: If GraphQL login fails
        """
        self.logger.info("Attempting GraphQL login", email=email)

        variables = {
            "email": email,
            "password": password,
            "rememberMe": True,
        }

        if mfa_secret_key:
            totp_code = oathtool.generate_otp(mfa_secret_key)
            variables["totpToken"] = totp_code

        query = gql(
            """
            mutation LoginMutation(
                $email: String!,
                $password: String!,
                $totpToken: String,
                $rememberMe: Boolean
            ) {
                login(
                    email: $email,
                    password: $password,
                    totpToken: $totpToken,
                    rememberMe: $rememberMe
                ) {
                    token
                    user {
                        id
                        email
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

        try:
            # Use client's gql_call but without auth headers for login
            result = await self.client.gql_call(
                operation="LoginMutation", graphql_query=query, variables=variables
            )

            login_data = result.get("login", {})
            errors = login_data.get("errors", [])

            if errors:
                error_messages = []
                for error in errors:
                    messages = error.get("messages", [])
                    error_messages.extend(messages)
                raise AuthenticationError(f"Login failed: {'; '.join(error_messages)}")

            token = login_data.get("token")
            if not token:
                raise AuthenticationError("No token received from GraphQL login")

            # Update client authentication
            self.client._token = token
            self.client._headers["Authorization"] = f"Token {token}"

            import time

            self.client._last_used = time.time()

            self.logger.info("GraphQL login successful", email=email)

        except Exception as e:
            self.logger.error("GraphQL login failed", email=email, error=str(e))
            raise AuthenticationError(f"GraphQL login failed: {str(e)}")

    async def _multi_factor_authenticate(
        self, email: str, password: str, code: str
    ) -> None:
        """
        Internal method to perform MFA authentication.

        Args:
            email: User's email address
            password: User's password
            code: MFA code

        Raises:
            InvalidMFAError: If MFA code is invalid
            AuthenticationError: If authentication fails
        """
        from ..monarchmoney import MonarchMoneyEndpoints

        self.logger.info("Performing MFA authentication", email=email)

        async with ClientSession() as session:
            # Create JSON payload
            mfa_data = {
                "username": email,
                "password": password,
                "trusted_device": True,
                "supports_mfa": True,
                "supports_email_otp": True,
                "supports_recaptcha": True,
            }

            # Add the MFA code - try email_otp first, then totp
            if len(code) == 6 and code.isdigit():
                # Likely email OTP (6 digits)
                mfa_data["email_otp"] = code
            else:
                # Likely TOTP from authenticator app
                mfa_data["totp"] = code

            # Update headers for JSON
            headers = self.client._headers.copy()
            headers["Content-Type"] = "application/json"

            try:
                async with session.post(
                    MonarchMoneyEndpoints.getLoginEndpoint(),
                    json=mfa_data,
                    headers=headers,
                ) as response:
                    if response.status == 404:
                        # Fallback to GraphQL MFA
                        return await self._mfa_graphql(email, password, code)

                    mfa_response = await response.json()

                    if not response.ok:
                        if response.status == 401:
                            raise InvalidMFAError("Invalid MFA code")
                        else:
                            raise AuthenticationError(
                                f"MFA failed with status {response.status}"
                            )

            except Exception as e:
                if "404" in str(e):
                    return await self._mfa_graphql(email, password, code)
                raise

        # Process MFA response
        token = mfa_response.get("token")
        csrf_token = mfa_response.get("csrf_token")

        if not token:
            raise InvalidMFAError("Invalid MFA code or authentication failed")

        # Update client with authentication data
        self.client._token = token
        self.client._csrf_token = csrf_token
        self.client._headers["Authorization"] = f"Token {token}"
        if csrf_token:
            self.client._headers["csrftoken"] = csrf_token

        import time

        self.client._last_used = time.time()

        self.logger.info("MFA authentication successful", email=email)

    async def _mfa_graphql(self, email: str, password: str, code: str) -> None:
        """
        GraphQL fallback for MFA authentication.

        Args:
            email: User's email address
            password: User's password
            code: MFA code

        Raises:
            InvalidMFAError: If MFA code is invalid
            AuthenticationError: If authentication fails
        """
        self.logger.info("Attempting GraphQL MFA", email=email)

        variables = {
            "email": email,
            "password": password,
            "totpToken": code,
            "rememberMe": True,
        }

        query = gql(
            """
            mutation MFAMutation(
                $email: String!,
                $password: String!,
                $totpToken: String!,
                $rememberMe: Boolean
            ) {
                login(
                    email: $email,
                    password: $password,
                    totpToken: $totpToken,
                    rememberMe: $rememberMe
                ) {
                    token
                    user {
                        id
                        email
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

        try:
            result = await self.client.gql_call(
                operation="MFAMutation", graphql_query=query, variables=variables
            )

            login_data = result.get("login", {})
            errors = login_data.get("errors", [])

            if errors:
                error_messages = []
                for error in errors:
                    messages = error.get("messages", [])
                    error_messages.extend(messages)
                raise InvalidMFAError(f"MFA failed: {'; '.join(error_messages)}")

            token = login_data.get("token")
            if not token:
                raise InvalidMFAError("Invalid MFA code")

            # Update client authentication
            self.client._token = token
            self.client._headers["Authorization"] = f"Token {token}"

            import time

            self.client._last_used = time.time()

            self.logger.info("GraphQL MFA successful", email=email)

        except InvalidMFAError:
            raise
        except Exception as e:
            self.logger.error("GraphQL MFA failed", email=email, error=str(e))
            raise AuthenticationError(f"GraphQL MFA failed: {str(e)}")
