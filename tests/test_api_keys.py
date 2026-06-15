"""Tests for the API key fetcher module."""

from __future__ import annotations

from contextlib import asynccontextmanager
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


def _patch_client_session(response: MagicMock | None = None, *, get_side_effect=None):
    """Patch aiohttp.ClientSession used inside fetch_api_keys.

    Returns the patcher and the MagicMock standing in for the session, so tests
    can assert on call counts.
    """
    session_mock = MagicMock()

    if get_side_effect is not None:
        session_mock.get = MagicMock(side_effect=get_side_effect)
    else:
        session_mock.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=response))
        )

    @asynccontextmanager
    async def fake_session_ctx(*_args, **_kwargs):
        yield session_mock

    patcher = patch(
        "custom_components.lifetime_fitness.api_keys.aiohttp.ClientSession",
        side_effect=fake_session_ctx,
    )
    return patcher, session_mock


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

        patcher, _ = _patch_client_session(mock_response)
        with patcher:
            keys = await fetch_api_keys()

        assert keys.apim_subscription_key == "924c03ce573d473793e184219a6a19bd"
        assert keys.my_account_api_key == "CkXadK3LkNF6sSj4jLGbtBB0amCwdWlv"

    async def test_fetch_api_keys_uses_cache(self, mock_html_with_keys: str) -> None:
        """Test that subsequent calls use cached keys."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_with_keys)

        patcher, session_mock = _patch_client_session(mock_response)
        with patcher:
            keys1 = await fetch_api_keys()
            keys2 = await fetch_api_keys()

        assert keys1.apim_subscription_key == keys2.apim_subscription_key
        assert session_mock.get.call_count == 1

    async def test_fetch_api_keys_force_refresh(self, mock_html_with_keys: str) -> None:
        """Test that force_refresh bypasses cache."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_with_keys)

        patcher, session_mock = _patch_client_session(mock_response)
        with patcher:
            await fetch_api_keys()
            await fetch_api_keys(force_refresh=True)

        assert session_mock.get.call_count == 2

    async def test_fetch_api_keys_http_error(self) -> None:
        """Test handling of HTTP error response."""
        mock_response = AsyncMock()
        mock_response.ok = False
        mock_response.status = 500

        patcher, _ = _patch_client_session(mock_response)
        with patcher, pytest.raises(ApiKeyFetchError, match="HTTP 500"):
            await fetch_api_keys()

    async def test_fetch_api_keys_connection_error(self) -> None:
        """Test handling of connection error."""
        patcher, _ = _patch_client_session(get_side_effect=ClientError("Connection failed"))
        with patcher, pytest.raises(ApiKeyFetchError, match="Connection error"):
            await fetch_api_keys()

    async def test_fetch_api_keys_missing_apim_key(self, mock_html_missing_apim_key: str) -> None:
        """Test handling of missing apimKey in response."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_missing_apim_key)

        patcher, _ = _patch_client_session(mock_response)
        with patcher, pytest.raises(ApiKeyFetchError, match="Could not find apimKey"):
            await fetch_api_keys()

    async def test_fetch_api_keys_missing_my_account_key(
        self, mock_html_missing_my_account_key: str
    ) -> None:
        """Test handling of missing ltMyAccountApiKey in response."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(return_value=mock_html_missing_my_account_key)

        patcher, _ = _patch_client_session(mock_response)
        with patcher, pytest.raises(ApiKeyFetchError, match="Could not find ltMyAccountApiKey"):
            await fetch_api_keys()


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

        patcher, _ = _patch_client_session(mock_response)
        with patcher:
            await fetch_api_keys()

        cached = get_cached_keys()
        assert cached is not None
        assert cached.apim_subscription_key == "924c03ce573d473793e184219a6a19bd"

    def test_clear_cache(self) -> None:
        """Test clear_cache function."""
        # This is tested by the autouse fixture, but let's be explicit
        clear_cache()
        assert get_cached_keys() is None
