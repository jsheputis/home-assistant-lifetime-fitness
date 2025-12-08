"""Dynamic API key fetcher for Life Time Fitness.

Fetches API keys from the Life Time website configuration.
Keys are cached to avoid repeated requests.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aiohttp import ClientError

if TYPE_CHECKING:
    from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

# URL where the API configuration is embedded
LIFETIME_CONFIG_URL = "https://my.lifetime.life/"

# Cache duration in seconds (24 hours)
CACHE_DURATION_SECONDS = 86400

# Regex patterns to extract keys from window.lt object
APIM_KEY_PATTERN = re.compile(r'"apimKey"\s*:\s*"([a-f0-9]{32})"')
MY_ACCOUNT_KEY_PATTERN = re.compile(r'"ltMyAccountApiKey"\s*:\s*"([A-Za-z0-9]{32})"')


@dataclass
class ApiKeys:
    """Container for Life Time API keys."""

    apim_subscription_key: str
    my_account_api_key: str


class ApiKeyCache:
    """Cache for API keys with expiration."""

    def __init__(self) -> None:
        """Initialize the cache."""
        self._keys: ApiKeys | None = None
        self._fetched_at: float = 0

    @property
    def is_valid(self) -> bool:
        """Check if the cache is valid."""
        if self._keys is None:
            return False
        return (time.time() - self._fetched_at) < CACHE_DURATION_SECONDS

    def get(self) -> ApiKeys | None:
        """Get cached keys if valid."""
        if self.is_valid:
            return self._keys
        return None

    def set(self, keys: ApiKeys) -> None:
        """Set keys in cache."""
        self._keys = keys
        self._fetched_at = time.time()

    def clear(self) -> None:
        """Clear the cache."""
        self._keys = None
        self._fetched_at = 0


# Global cache instance
_cache = ApiKeyCache()


async def fetch_api_keys(client_session: ClientSession, force_refresh: bool = False) -> ApiKeys:
    """Fetch API keys from the Life Time website.

    Args:
        client_session: aiohttp client session to use for the request.
        force_refresh: If True, bypass the cache and fetch fresh keys.

    Returns:
        ApiKeys containing the subscription key and MyAccount API key.

    Raises:
        ApiKeyFetchError: If keys cannot be fetched or parsed.
    """
    # Check cache first unless force refresh requested
    if not force_refresh:
        cached = _cache.get()
        if cached is not None:
            _LOGGER.debug("Using cached API keys")
            return cached

    _LOGGER.debug("Fetching API keys from %s", LIFETIME_CONFIG_URL)

    try:
        async with client_session.get(
            LIFETIME_CONFIG_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        ) as response:
            if not response.ok:
                raise ApiKeyFetchError(f"Failed to fetch config page: HTTP {response.status}")

            html_content = await response.text()

    except ClientError as err:
        raise ApiKeyFetchError(f"Connection error fetching API keys: {err}") from err

    # Extract apimKey
    apim_match = APIM_KEY_PATTERN.search(html_content)
    if not apim_match:
        raise ApiKeyFetchError("Could not find apimKey in page content")
    apim_key = apim_match.group(1)

    # Extract ltMyAccountApiKey
    my_account_match = MY_ACCOUNT_KEY_PATTERN.search(html_content)
    if not my_account_match:
        raise ApiKeyFetchError("Could not find ltMyAccountApiKey in page content")
    my_account_key = my_account_match.group(1)

    keys = ApiKeys(
        apim_subscription_key=apim_key,
        my_account_api_key=my_account_key,
    )

    # Cache the keys
    _cache.set(keys)
    _LOGGER.info("Successfully fetched and cached API keys")

    return keys


def get_cached_keys() -> ApiKeys | None:
    """Get cached API keys without fetching.

    Returns:
        Cached ApiKeys if available and valid, None otherwise.
    """
    return _cache.get()


def clear_cache() -> None:
    """Clear the API key cache.

    Useful for testing or forcing a refresh on next fetch.
    """
    _cache.clear()


class ApiKeyFetchError(Exception):
    """Error fetching API keys from Life Time website."""
