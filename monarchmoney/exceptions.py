"""
Exception hierarchy for MonarchMoney Enhanced.

Provides specific exception types for better error handling and debugging.
"""

from typing import Any, Dict, Optional


class MonarchMoneyError(Exception):
    """Base exception for all MonarchMoney errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class AuthenticationError(MonarchMoneyError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)


class MFARequiredError(AuthenticationError):
    """Raised when multi-factor authentication is required."""

    def __init__(
        self,
        message: str = "Multi-factor authentication required",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)


class InvalidMFAError(AuthenticationError):
    """Raised when MFA code is invalid."""

    def __init__(
        self,
        message: str = "Invalid multi-factor authentication code",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)


class SessionExpiredError(AuthenticationError):
    """Raised when session has expired."""

    def __init__(
        self,
        message: str = "Session has expired",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)


class RateLimitError(MonarchMoneyError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "API rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.retry_after = retry_after

    def __str__(self):
        base_msg = super().__str__()
        if self.retry_after:
            return f"{base_msg} (retry after {self.retry_after} seconds)"
        return base_msg


class ServerError(MonarchMoneyError):
    """Raised when server returns an error (5xx)."""

    def __init__(
        self, message: str, status_code: int, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.status_code = status_code

    def __str__(self):
        return f"Server error {self.status_code}: {self.message}"


class ClientError(MonarchMoneyError):
    """Raised when client sends invalid request (4xx)."""

    def __init__(
        self, message: str, status_code: int, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.status_code = status_code

    def __str__(self):
        return f"Client error {self.status_code}: {self.message}"


class ValidationError(MonarchMoneyError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.field = field

    def __str__(self):
        if self.field:
            return f"Validation error for field '{self.field}': {self.message}"
        return f"Validation error: {self.message}"


class NetworkError(MonarchMoneyError):
    """Raised when network connectivity issues occur."""

    def __init__(
        self,
        message: str = "Network error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)


class GraphQLError(MonarchMoneyError):
    """Raised when GraphQL query fails."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        graphql_errors: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.query = query
        self.graphql_errors = graphql_errors or []

    def __str__(self):
        base_msg = super().__str__()
        if self.graphql_errors:
            error_msgs = [str(err) for err in self.graphql_errors]
            return f"{base_msg} (GraphQL errors: {'; '.join(error_msgs)})"
        return base_msg


class DataError(MonarchMoneyError):
    """Raised when data processing fails."""

    def __init__(
        self,
        message: str,
        data_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.data_type = data_type

    def __str__(self):
        if self.data_type:
            return f"Data error for {self.data_type}: {self.message}"
        return f"Data error: {self.message}"


class ConfigurationError(MonarchMoneyError):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.config_key = config_key

    def __str__(self):
        if self.config_key:
            return f"Configuration error for '{self.config_key}': {self.message}"
        return f"Configuration error: {self.message}"


class SchemaValidationError(MonarchMoneyError):
    """Raised when GraphQL schema validation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        missing_fields: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.operation = operation
        self.missing_fields = missing_fields or []

    def __str__(self):
        base_msg = super().__str__()
        if self.operation:
            base_msg = f"Schema validation error for operation '{self.operation}': {self.message}"
        if self.missing_fields:
            return f"{base_msg} (missing fields: {', '.join(self.missing_fields)})"
        return base_msg


# Backward compatibility aliases for existing exception names
class RequireMFAException(MFARequiredError):
    """Legacy alias for MFARequiredError."""

    pass


class LoginFailedException(AuthenticationError):
    """Legacy alias for AuthenticationError."""

    pass


class RequestFailedException(MonarchMoneyError):
    """Legacy alias for MonarchMoneyError."""

    pass


def handle_http_response(response, request_info: Optional[str] = None) -> None:
    """
    Convert HTTP response to appropriate exception.

    Args:
        response: HTTP response object
        request_info: Optional description of the request for context

    Raises:
        Appropriate MonarchMoneyError subclass based on status code
    """
    status = response.status
    reason = getattr(response, "reason", "Unknown")

    details = {
        "status_code": status,
        "reason": reason,
        "url": str(response.url) if hasattr(response, "url") else None,
    }

    if request_info:
        details["request"] = request_info

    if status == 401:
        raise AuthenticationError("Invalid credentials or session expired", details)
    elif status == 403:
        raise AuthenticationError("Access forbidden", details)
    elif status == 429:
        retry_after = response.headers.get("Retry-After")
        retry_seconds = (
            int(retry_after) if retry_after and retry_after.isdigit() else None
        )
        raise RateLimitError(
            "API rate limit exceeded", retry_after=retry_seconds, details=details
        )
    elif 400 <= status < 500:
        raise ClientError(
            f"Client error: {reason}", status_code=status, details=details
        )
    elif 500 <= status < 600:
        raise ServerError(
            f"Server error: {reason}", status_code=status, details=details
        )
    elif status >= 400:
        raise MonarchMoneyError(f"HTTP error {status}: {reason}", details=details)


def handle_graphql_errors(errors: list, query: Optional[str] = None) -> None:
    """
    Convert GraphQL errors to appropriate exceptions.

    Args:
        errors: List of GraphQL error objects
        query: Optional GraphQL query string for context

    Raises:
        Appropriate MonarchMoneyError subclass based on error type
    """
    if not errors:
        return

    # Check for authentication-related errors
    for error in errors:
        error_msg = str(error).lower()
        if any(
            term in error_msg
            for term in ["unauthorized", "unauthenticated", "invalid token"]
        ):
            raise AuthenticationError(
                "Authentication failed",
                details={"graphql_errors": errors, "query": query},
            )
        elif "forbidden" in error_msg or "access denied" in error_msg:
            raise AuthenticationError(
                "Access forbidden", details={"graphql_errors": errors, "query": query}
            )

    # Generic GraphQL error
    error_messages = [str(error) for error in errors]
    raise GraphQLError(
        f"GraphQL query failed: {'; '.join(error_messages)}",
        query=query,
        graphql_errors=errors,
    )
