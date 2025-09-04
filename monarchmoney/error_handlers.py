"""
Advanced error handling patterns for MonarchMoney Enhanced.

Provides context-aware error handling, recovery strategies, and user-friendly error messages.
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union

from .exceptions import (
    AuthenticationError,
    ClientError,
    MonarchMoneyError,
    NetworkError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from .logging_config import MonarchLogger

logger = MonarchLogger("ErrorHandlers")


class ErrorContext:
    """Context information for error handling decisions."""

    def __init__(
        self,
        operation: str,
        user_id: Optional[str] = None,
        session_age: Optional[float] = None,
        retry_count: int = 0,
        last_success: Optional[float] = None,
    ):
        self.operation = operation
        self.user_id = user_id
        self.session_age = session_age
        self.retry_count = retry_count
        self.last_success = last_success
        self.error_history: List[Exception] = []

    def add_error(self, error: Exception) -> None:
        """Add an error to the context history."""
        self.error_history.append(error)
        # Keep only last 10 errors
        if len(self.error_history) > 10:
            self.error_history = self.error_history[-10:]


class ErrorRecoveryStrategy:
    """Base class for error recovery strategies."""

    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        """
        Check if this strategy can handle the given error.

        Args:
            error: The exception to check
            context: Error context information

        Returns:
            True if this strategy can handle the error, False otherwise
        """
        return False

    async def handle(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle the error and return whether recovery was successful.

        Args:
            error: The exception to handle
            context: Error context information

        Returns:
            True if the error was recovered from, False otherwise
        """
        logger.warning(
            "Base strategy handle called - should be overridden",
            strategy=self.__class__.__name__,
            error_type=error.__class__.__name__,
        )
        return False


class AuthenticationRecoveryStrategy(ErrorRecoveryStrategy):
    """Recovery strategy for authentication errors."""

    def __init__(self, monarch_client):
        self.client = monarch_client

    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        return isinstance(error, AuthenticationError)

    async def handle(self, error: Exception, context: ErrorContext) -> bool:
        """Attempt to recover from authentication errors."""
        logger.info("Attempting authentication recovery", operation=context.operation)

        try:
            # If we have a saved session, try to reload it
            if hasattr(self.client, "_session_file") and self.client._session_file:
                await self.client._auth_service.load_session()

                # Validate the reloaded session
                if await self.client._auth_service.validate_session():
                    logger.info("Authentication recovered via session reload")
                    return True

            # If session reload failed, clear invalid session
            await self.client._auth_service.delete_session()

            # For non-interactive scenarios, we can't recover
            logger.warning("Authentication recovery failed - manual login required")
            return False

        except Exception as recovery_error:
            logger.error("Authentication recovery failed", error=str(recovery_error))
            return False


class RateLimitRecoveryStrategy(ErrorRecoveryStrategy):
    """Recovery strategy for rate limit errors."""

    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        return isinstance(error, RateLimitError)

    async def handle(self, error: Exception, context: ErrorContext) -> bool:
        """Handle rate limiting with exponential backoff."""
        logger.info(
            "Handling rate limit",
            operation=context.operation,
            retry_count=context.retry_count,
        )

        # Calculate delay with exponential backoff
        base_delay = 1.0
        max_delay = 60.0
        delay = min(base_delay * (2**context.retry_count), max_delay)

        # Add jitter to avoid thundering herd
        import random

        delay += random.uniform(0, delay * 0.1)

        logger.info("Rate limit backoff", delay=delay, retry_count=context.retry_count)
        await asyncio.sleep(delay)

        return True  # Always recoverable with waiting


class NetworkRecoveryStrategy(ErrorRecoveryStrategy):
    """Recovery strategy for network errors."""

    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        return isinstance(error, NetworkError)

    async def handle(self, error: Exception, context: ErrorContext) -> bool:
        """Handle network errors with progressive delays."""
        logger.info(
            "Handling network error",
            operation=context.operation,
            retry_count=context.retry_count,
        )

        # For network errors, use shorter delays
        delays = [0.5, 1.0, 2.0, 5.0, 10.0]
        if context.retry_count < len(delays):
            delay = delays[context.retry_count]
            logger.info("Network error backoff", delay=delay)
            await asyncio.sleep(delay)
            return True

        logger.warning("Network error retry limit exceeded")
        return False


class ServerErrorRecoveryStrategy(ErrorRecoveryStrategy):
    """Recovery strategy for server errors."""

    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        return isinstance(error, ServerError)

    async def handle(self, error: Exception, context: ErrorContext) -> bool:
        """Handle server errors with conservative retry."""
        logger.info(
            "Handling server error",
            operation=context.operation,
            retry_count=context.retry_count,
        )

        # For server errors, be more conservative
        if context.retry_count < 3:
            delay = 2.0 * (1.5**context.retry_count)
            logger.info("Server error backoff", delay=delay)
            await asyncio.sleep(delay)
            return True

        logger.warning("Server error retry limit exceeded")
        return False


class ErrorRecoveryManager:
    """Manages error recovery strategies and coordinated recovery attempts."""

    def __init__(self, monarch_client):
        self.client = monarch_client
        self.strategies: List[ErrorRecoveryStrategy] = [
            AuthenticationRecoveryStrategy(monarch_client),
            RateLimitRecoveryStrategy(),
            NetworkRecoveryStrategy(),
            ServerErrorRecoveryStrategy(),
        ]

    async def attempt_recovery(self, error: Exception, context: ErrorContext) -> bool:
        """
        Attempt to recover from an error using available strategies.

        Args:
            error: The error to recover from
            context: Error context information

        Returns:
            True if recovery was successful, False otherwise
        """
        context.add_error(error)

        for strategy in self.strategies:
            if strategy.can_handle(error, context):
                logger.debug(
                    "Attempting error recovery",
                    strategy=strategy.__class__.__name__,
                    error_type=error.__class__.__name__,
                    operation=context.operation,
                )

                try:
                    if await strategy.handle(error, context):
                        logger.info(
                            "Error recovery successful",
                            strategy=strategy.__class__.__name__,
                            operation=context.operation,
                        )
                        return True
                except Exception as recovery_error:
                    logger.error(
                        "Recovery strategy failed",
                        strategy=strategy.__class__.__name__,
                        recovery_error=str(recovery_error),
                    )

        logger.warning(
            "No recovery strategy succeeded", error_type=error.__class__.__name__
        )
        return False


def with_error_recovery(
    max_retries: int = 3,
    recoverable_exceptions: Optional[List[Type[Exception]]] = None,
    operation_name: Optional[str] = None,
):
    """
    Decorator that adds advanced error recovery to async functions.

    Args:
        max_retries: Maximum number of retry attempts
        recoverable_exceptions: List of exception types that can be recovered from
        operation_name: Name of the operation for logging (defaults to function name)
    """
    if recoverable_exceptions is None:
        recoverable_exceptions = [
            RateLimitError,
            NetworkError,
            ServerError,
            AuthenticationError,
        ]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get the monarch client from args/kwargs
            monarch_client = None
            if args and hasattr(args[0], "client"):
                monarch_client = args[0].client
            elif args and hasattr(args[0], "_auth_service"):
                monarch_client = args[0]

            if not monarch_client:
                # If we can't find the client, just execute normally
                return await func(*args, **kwargs)

            recovery_manager = ErrorRecoveryManager(monarch_client)
            op_name = operation_name or func.__name__

            for attempt in range(max_retries + 1):
                context = ErrorContext(
                    operation=op_name,
                    retry_count=attempt,
                    last_success=getattr(monarch_client, "_last_success", None),
                )

                try:
                    result = await func(*args, **kwargs)

                    # Record successful operation
                    monarch_client._last_success = time.time()

                    if attempt > 0:
                        logger.info(
                            "Operation succeeded after retry",
                            operation=op_name,
                            attempt=attempt,
                        )

                    return result

                except Exception as error:
                    # Check if this is a recoverable error type
                    if not any(
                        isinstance(error, exc_type)
                        for exc_type in recoverable_exceptions
                    ):
                        # Not recoverable, re-raise immediately
                        raise

                    logger.warning(
                        "Operation failed, attempting recovery",
                        operation=op_name,
                        attempt=attempt,
                        error_type=error.__class__.__name__,
                        error_message=str(error),
                    )

                    # If this is the last attempt, don't try recovery
                    if attempt >= max_retries:
                        logger.error(
                            "Operation failed after all retries",
                            operation=op_name,
                            total_attempts=attempt + 1,
                            final_error=str(error),
                        )
                        raise

                    # Attempt recovery
                    if await recovery_manager.attempt_recovery(error, context):
                        # Recovery succeeded, continue to next attempt
                        continue
                    else:
                        # Recovery failed, re-raise the error
                        logger.error(
                            "Error recovery failed, aborting retries",
                            operation=op_name,
                            attempt=attempt,
                        )
                        raise

        return wrapper

    return decorator


class ErrorMessageFormatter:
    """Formats error messages for user-friendly display."""

    @staticmethod
    def format_error(
        error: Exception, context: Optional[ErrorContext] = None
    ) -> Dict[str, Any]:
        """
        Format an error into a user-friendly message.

        Args:
            error: The error to format
            context: Optional error context

        Returns:
            Dictionary with formatted error information
        """
        error_info = {
            "error_type": error.__class__.__name__,
            "message": str(error),
            "user_message": ErrorMessageFormatter._get_user_message(error),
            "recoverable": ErrorMessageFormatter._is_recoverable(error),
            "suggested_actions": ErrorMessageFormatter._get_suggested_actions(error),
        }

        if context:
            error_info["context"] = {
                "operation": context.operation,
                "retry_count": context.retry_count,
                "error_history_count": len(context.error_history),
            }

        return error_info

    @staticmethod
    def _get_user_message(error: Exception) -> str:
        """Get a user-friendly error message."""
        if isinstance(error, AuthenticationError):
            return "Authentication failed. Please check your credentials and try logging in again."
        elif isinstance(error, RateLimitError):
            return "Too many requests. Please wait a moment and try again."
        elif isinstance(error, NetworkError):
            return "Network connection issue. Please check your internet connection."
        elif isinstance(error, ServerError):
            return (
                "Server is temporarily unavailable. Please try again in a few minutes."
            )
        elif isinstance(error, ValidationError):
            return f"Invalid input: {str(error)}"
        else:
            return "An unexpected error occurred. Please try again."

    @staticmethod
    def _is_recoverable(error: Exception) -> bool:
        """Determine if an error is potentially recoverable."""
        recoverable_types = (
            RateLimitError,
            NetworkError,
            ServerError,
        )
        return isinstance(error, recoverable_types)

    @staticmethod
    def _get_suggested_actions(error: Exception) -> List[str]:
        """Get suggested actions for the user."""
        if isinstance(error, AuthenticationError):
            return [
                "Verify your email and password are correct",
                "Check if MFA is required",
                "Try logging out and logging back in",
            ]
        elif isinstance(error, RateLimitError):
            return [
                "Wait a few minutes before trying again",
                "Reduce the frequency of requests",
            ]
        elif isinstance(error, NetworkError):
            return [
                "Check your internet connection",
                "Try again in a few moments",
                "Contact support if the issue persists",
            ]
        elif isinstance(error, ServerError):
            return [
                "Try again in a few minutes",
                "Check the service status page",
                "Contact support if the issue persists",
            ]
        elif isinstance(error, ValidationError):
            return [
                "Check the format of your input data",
                "Refer to the API documentation",
            ]
        else:
            return [
                "Try the operation again",
                "Contact support if the issue persists",
            ]
