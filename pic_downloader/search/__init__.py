"""
Search domain - handles search operations and strategies.

This package contains all search-related functionality including
providers for different search engines and strategies for search optimization.
"""

from .providers.google_provider import GoogleSearchProvider
from .strategies.smart_strategy import SmartSearchStrategy

__all__ = [
    "GoogleSearchProvider",
    "SmartSearchStrategy"
]
