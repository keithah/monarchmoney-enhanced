"""
monarchmoney

A Python API for interacting with MonarchMoney.
"""

from .monarchmoney import (
    MonarchMoney,
    MonarchMoneyEndpoints,
    # Legacy exceptions for backward compatibility  
    LoginFailedException,
    RequestFailedException,
    RequireMFAException,
)

# Import new exception hierarchy
from .exceptions import (
    MonarchMoneyError,
    AuthenticationError,
    MFARequiredError,
    InvalidMFAError,
    SessionExpiredError,
    RateLimitError,
    ServerError,
    ClientError,
    ValidationError,
    NetworkError,
    GraphQLError,
    DataError,
    ConfigurationError,
)

__version__ = "0.3.6"
__author__ = "keithah"
