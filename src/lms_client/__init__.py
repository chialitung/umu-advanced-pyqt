"""UMU LMS Python SDK."""

from .auth import AuthBase, AuthFactory, SessionAuth, TokenAuth
from .client import LMSClient
from .exceptions import (
    LMSAPIError,
    LMSAuthError,
    LMSNotFoundError,
    LMSRateLimitError,
    LMSValidationError,
)

__all__ = [
    "LMSClient",
    "AuthBase",
    "TokenAuth",
    "SessionAuth",
    "AuthFactory",
    "LMSAPIError",
    "LMSAuthError",
    "LMSNotFoundError",
    "LMSValidationError",
    "LMSRateLimitError",
]

__version__ = "0.1.0"
