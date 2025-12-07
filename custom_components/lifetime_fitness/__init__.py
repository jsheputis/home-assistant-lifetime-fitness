"""Life Time Fitness integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import Api
from .const import (
    CONF_DEFAULT_START_OF_WEEK_DAY,
    CONF_PASSWORD,
    CONF_START_OF_WEEK_DAY,
    CONF_USERNAME,
    DOMAIN,
    ISSUE_URL,
    VERSION,
)
from .coordinator import LifetimeFitnessCoordinator

if TYPE_CHECKING:
    from typing import TypeAlias

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]

_LOGGER = logging.getLogger(__name__)

LifetimeFitnessConfigEntry: TypeAlias = ConfigEntry[LifetimeFitnessCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: LifetimeFitnessConfigEntry) -> bool:
    """Set up Life Time Fitness from a config entry."""
    _LOGGER.info(
        "Version %s is starting, if you have any issues please report them here: %s",
        VERSION,
        ISSUE_URL,
    )

    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    start_of_week_day: int = entry.options.get(
        CONF_START_OF_WEEK_DAY, CONF_DEFAULT_START_OF_WEEK_DAY
    )

    # Create API client
    api_client = Api(async_create_clientsession(hass), username, password)

    # Authenticate before creating coordinator
    await api_client.authenticate()

    # Create coordinator
    coordinator = LifetimeFitnessCoordinator(
        hass,
        api_client,
        start_of_week_day,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in runtime_data
    entry.runtime_data = coordinator

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def options_update_listener(
    hass: HomeAssistant, config_entry: LifetimeFitnessConfigEntry
) -> None:
    """Handle options update."""
    # Update the coordinator's start of week day
    coordinator = config_entry.runtime_data
    new_start_of_week_day = config_entry.options.get(
        CONF_START_OF_WEEK_DAY, CONF_DEFAULT_START_OF_WEEK_DAY
    )
    coordinator.update_start_of_week_day(new_start_of_week_day)

    # Request a refresh to recalculate with new settings
    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: LifetimeFitnessConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
