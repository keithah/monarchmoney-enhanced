"""
GraphQL optimization utilities for MonarchMoney client.
"""

from .fragments import FRAGMENTS, get_fragment
from .cache import QueryCache, CacheStrategy
from .query_builder import QueryBuilder, BatchedGraphQLClient, RequestDeduplicator
from .query_variants import QueryVariants

__all__ = [
    "FRAGMENTS",
    "get_fragment",
    "QueryCache",
    "CacheStrategy",
    "QueryBuilder",
    "BatchedGraphQLClient", 
    "RequestDeduplicator",
    "QueryVariants",
]