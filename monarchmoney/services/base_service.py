"""
Base service class for MonarchMoney Enhanced services.

Provides common functionality and patterns for all service classes.
"""

from typing import TYPE_CHECKING, Any, Dict

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

    async def _execute_query(self, operation: str, query: Any) -> Dict[str, Any]:
        """
        Execute a GraphQL query with error handling and logging.

        Args:
            operation: The GraphQL operation name
            query: The GraphQL query object

        Returns:
            The query response data
        """
        self.logger.debug("Executing GraphQL operation", operation=operation)
        try:
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
