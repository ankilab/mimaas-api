"""
MIMaaS Python API Client

A Python client library for interacting with the MIMaaS REST API.

Example:
    >>> from mimaas import MIMaaSClient
    >>> client = MIMaaSClient()
    >>> client.login("username", "password")
    >>> request = client.submit_request("model.tflite", "nrf5340dk")
    >>> results = client.wait_for_completion(request.id)
    >>> print(results)
"""

__version__ = "0.1.0"

# Main client
from .client import MIMaaSClient

# Data models
from .models import User, Board, BoardUtilization, Request, Results, Plan

# Exceptions
from .exceptions import (
    MIMaaSError,
    NetworkError,
    AuthenticationError,
    QuotaExceededError,
    ValidationError,
    ProcessingError,
    ResourceNotFoundError,
    BoardNotAvailableError,
    TimeoutError,
    ConfigurationError
)

__all__ = [
    # Version
    "__version__",

    # Main client
    "MIMaaSClient",

    # Data models
    "User",
    "Board",
    "BoardUtilization",
    "Request",
    "Results",
    "Plan",

    # Exceptions
    "MIMaaSError",
    "NetworkError",
    "AuthenticationError",
    "QuotaExceededError",
    "ValidationError",
    "ProcessingError",
    "ResourceNotFoundError",
    "BoardNotAvailableError",
    "TimeoutError",
    "ConfigurationError",
]
