"""Tests for the Life Time Fitness integration setup."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.lifetime_fitness.const import DOMAIN


async def test_async_setup(hass: HomeAssistant) -> None:
    """Test the component gets setup."""
    assert await async_setup_component(hass, DOMAIN, {}) is True
