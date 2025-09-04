"""
monarchmoney

A Python API for interacting with MonarchMoney.
"""

# Import new exception hierarchy
from .exceptions import (
    AuthenticationError,
    ClientError,
    ConfigurationError,
    DataError,
    GraphQLError,
    InvalidMFAError,
    MFARequiredError,
    MonarchMoneyError,
    NetworkError,
    RateLimitError,
    ServerError,
    SessionExpiredError,
    ValidationError,
)
from .monarchmoney import (  # Legacy exceptions for backward compatibility
    LoginFailedException,
    MonarchMoney,
    MonarchMoneyEndpoints,
    RequestFailedException,
    RequireMFAException,
)

__version__ = "0.6.2"
__author__ = "keithah"
