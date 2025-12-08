"""Tests for the API key fetcher module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError

from custom_components.lifetime_fitness.api_keys import (
    ApiKeyCache,
    ApiKeyFetchError,
    ApiKeys,
    clear_cache,
    fetch_api_keys,
    get_cached_keys,
)


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    """Reset the global cache before each test."""
    clear_cache()


@pytest.fixture
def mock_html_with_keys() -> str:
    """Return mock HTML content containing API keys."""
    return """
    <html>
    <script>
    window.lt = {
        api: {
            "apimKey": "924c03ce573d473793e184219a6a19bd",
            "ltMyAccountApiKey": "CkXadK3LkNF6sSj4jLGbtBB0amCwdWlv",
            "otherKey": "somevalue"
        }
    };
    </script>
    </html>
    """


@pytest.fixture
def mock_html_missing_apim_key() -> str:
    """Return mock HTML content missing apimKey."""
    return """
    <html>
    <script>
    window.lt = {
        api: {
            "ltMyAccountApiKey": "CkXadK3LkNF6sSj4jLGbtBB0amCwdWlv"
        }
    };
    </script>
    </html>
    """


@pytest.fixture
def mock_html_missing_my_account_key() -> str:
    """Return mock HTML content missing ltMyAccountApiKey."""
    return """
    <html>
    <script>
    window.lt = {
        api: {
            "apimKey": "924c03ce573d473793e184219a6a19bd"
        }
    };
    </script>
    </html>
    """


class TestApiKeyCache:
    """Tests for ApiKeyCache class."""

    def test_cache_initially_invalid(self) -> None:
        """Test that cache is initially invalid."""
        cache = ApiKeyCache()
        assert not cache.is_valid
        assert cache.get() is None

    def test_cache_set_and_get(self) -> None:
        """Test setting and getting cache values."""
        cache = ApiKeyCache()
        keys = ApiKeys(
            apim_subscription_key="test_apim_key",
            my_account_api_key="test_my_account_key",
        )
        cache.set(keys)

        assert cache.is_valid
        cached = cache.get()
        assert cached is not None
        assert cached.apim_subscription_key == "test_apim_key"
        assert cached.my_account_api_key == "test_my_account_key"

    def test_cache_clear(self) -> None:
        """Test clearing the cache."""
        cache = ApiKeyCache()
        keys = ApiKeys(
            apim_subscription_key="test_apim_key",
            my_account_api_key="test_my_account_key",
        )
        cache.set(keys)
        assert cache.is_valid

        cache.clear()
        assert not cache.is_valid
        assert cache.get() is None

    def test_cache_expiration(self) -> None:
        """Test that cache expires after duration."""
        cache = ApiKeyCache()
        keys = ApiKeys(
            apim_subscription_key="test_apim_key",
            my_account_api_key="test_my_account_key",
        )
        cache.set(keys)

        # Mock time to be past expiration
        with patch("custom_components.lifetime_fitness.api_keys.time") as mock_time:
            mock_time.time.return_value = cache._fetched_at + 86401  # 24 hours + 1 second
            assert not cache.is_valid
            assert cache.get() is None


class TestFetchApiKeys:
    """Tests for fetch_api_keys function."""

    async def test_fetch_api_keys_success(self, mock_html_with_keys: str) -> None:
        """Test successful API key fetching."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_with_keys)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        keys = await fetch_api_keys(mock_session)

        assert keys.apim_subscription_key == "924c03ce573d473793e184219a6a19bd"
        assert keys.my_account_api_key == "CkXadK3LkNF6sSj4jLGbtBB0amCwdWlv"

    async def test_fetch_api_keys_uses_cache(self, mock_html_with_keys: str) -> None:
        """Test that subsequent calls use cached keys."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_with_keys)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        # First call fetches
        keys1 = await fetch_api_keys(mock_session)

        # Second call should use cache
        keys2 = await fetch_api_keys(mock_session)

        assert keys1.apim_subscription_key == keys2.apim_subscription_key
        # get() should have been called only once
        assert mock_session.get.call_count == 1

    async def test_fetch_api_keys_force_refresh(self, mock_html_with_keys: str) -> None:
        """Test that force_refresh bypasses cache."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_with_keys)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        # First call fetches
        await fetch_api_keys(mock_session)

        # Second call with force_refresh should fetch again
        await fetch_api_keys(mock_session, force_refresh=True)

        assert mock_session.get.call_count == 2

    async def test_fetch_api_keys_http_error(self) -> None:
        """Test handling of HTTP error response."""
        mock_response = AsyncMock()
        mock_response.ok = False
        mock_response.status = 500

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with pytest.raises(ApiKeyFetchError, match="HTTP 500"):
            await fetch_api_keys(mock_session)

    async def test_fetch_api_keys_connection_error(self) -> None:
        """Test handling of connection error."""
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=ClientError("Connection failed"))

        with pytest.raises(ApiKeyFetchError, match="Connection error"):
            await fetch_api_keys(mock_session)

    async def test_fetch_api_keys_missing_apim_key(self, mock_html_missing_apim_key: str) -> None:
        """Test handling of missing apimKey in response."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_missing_apim_key)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with pytest.raises(ApiKeyFetchError, match="Could not find apimKey"):
            await fetch_api_keys(mock_session)

    async def test_fetch_api_keys_missing_my_account_key(
        self, mock_html_missing_my_account_key: str
    ) -> None:
        """Test handling of missing ltMyAccountApiKey in response."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_missing_my_account_key)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with pytest.raises(ApiKeyFetchError, match="Could not find ltMyAccountApiKey"):
            await fetch_api_keys(mock_session)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_cached_keys_empty(self) -> None:
        """Test get_cached_keys when cache is empty."""
        assert get_cached_keys() is None

    async def test_get_cached_keys_after_fetch(self, mock_html_with_keys: str) -> None:
        """Test get_cached_keys after successful fetch."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_with_keys)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        await fetch_api_keys(mock_session)

        cached = get_cached_keys()
        assert cached is not None
        assert cached.apim_subscription_key == "924c03ce573d473793e184219a6a19bd"

    def test_clear_cache(self) -> None:
        """Test clear_cache function."""
        # This is tested by the autouse fixture, but let's be explicit
        clear_cache()
        assert get_cached_keys() is None
