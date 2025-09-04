"""
Base service class for MonarchMoney Enhanced services.

Provides common functionality and patterns for all service classes.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from ..error_handlers import with_error_recovery
from ..logging_config import MonarchLogger

if TYPE_CHECKING:
    from ..monarchmoney import MonarchMoney


class BaseService:
    """
    Base class for all MonarchMoney services.

    Provides common functionality like logging and GraphQL client access.
    """

    def __init__(self, monarch_client: "MonarchMoney"):
        """
        Initialize the base service.

        Args:
            monarch_client: Reference to the main MonarchMoney client
        """
        self.client = monarch_client
        self.logger = MonarchLogger(self.__class__.__name__)

    @with_error_recovery(max_retries=3)
    async def _execute_query(
        self,
        operation: str,
        query: Any,
        variables: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query with advanced error handling and performance optimization.

        Args:
            operation: The GraphQL operation name
            query: The GraphQL query object
            variables: Optional query variables
            use_cache: Whether to use caching for this query
            timeout: Optional timeout override

        Returns:
            The query response data
        """
        self.logger.debug("Executing GraphQL operation", operation=operation)

        # Use the advanced GraphQL client if available, properly authenticated, and not in test mode
        use_advanced_client = (
            hasattr(self.client, "_graphql_client")
            and self.client._graphql_client
            and hasattr(self.client, "_token")
            and self.client._token
            and
            # Don't use advanced client if token looks like a test/mock token
            not (
                self.client._token
                and any(
                    word in self.client._token.lower()
                    for word in ["mock", "test", "fake", "demo"]
                )
            )
        )

        if use_advanced_client:
            return await self.client._graphql_client.execute_query(
                operation=operation,
                query=query,
                variables=variables,
                use_cache=use_cache,
                timeout=timeout,
            )

        # Fallback to legacy method
        try:
            if variables:
                result = await self.client.gql_call(
                    operation=operation, graphql_query=query, variables=variables
                )
            else:
                result = await self.client.gql_call(
                    operation=operation, graphql_query=query
                )
            self.logger.debug(
                "GraphQL operation completed successfully", operation=operation
            )
            return result
        except Exception as e:
            self.logger.error(
                "GraphQL operation failed", operation=operation, error=str(e)
            )
            raise
