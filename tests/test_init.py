"""Tests for the Life Time Fitness integration setup."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.lifetime_fitness.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)

from .conftest import TEST_USERNAME, TEST_PASSWORD


async def test_async_setup(hass: HomeAssistant) -> None:
    """Test the component gets setup."""
    assert await async_setup_component(hass, DOMAIN, {}) is True


async def test_async_setup_entry(hass: HomeAssistant) -> None:
    """Test setting up an entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }
    entry.options = {}
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    entry.async_on_unload = MagicMock()

    with patch(
        "custom_components.lifetime_fitness.Api"
    ) as mock_api_class, patch(
        "custom_components.lifetime_fitness.async_create_clientsession"
    ) as mock_session:
        mock_api = MagicMock()
        mock_api.authenticate = AsyncMock()
        mock_api.get_username = MagicMock(return_value=TEST_USERNAME)
        mock_api.update = AsyncMock()
        mock_api.update_successful = True
        mock_api.result_json = {"data": []}
        mock_api_class.return_value = mock_api

        from custom_components.lifetime_fitness import async_setup_entry

        result = await async_setup_entry(hass, entry)

        assert result is True
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]


async def test_async_unload_entry(hass: HomeAssistant) -> None:
    """Test unloading an entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }
    entry.options = {}
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    entry.async_on_unload = MagicMock()

    # Set up first
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = MagicMock()

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=True
    ):
        from custom_components.lifetime_fitness import async_unload_entry

        result = await async_unload_entry(hass, entry)

        assert result is True
        assert entry.entry_id not in hass.data[DOMAIN]
