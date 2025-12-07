"""Life Time Fitness integration."""
from __future__ import annotations

import logging
from typing import TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    Api,
    ApiActivationRequired,
    ApiCannotConnect,
    ApiDuplicateEmail,
    ApiInvalidAuth,
    ApiPasswordNeedsToBeChanged,
    ApiProfileError,
    ApiTooManyAuthenticationAttempts,
    ApiUnknownAuthError,
)
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
    try:
        await api_client.authenticate()
    except ApiCannotConnect as err:
        _LOGGER.error("Failed to connect to Life Time Fitness API: %s", err)
        raise ConfigEntryNotReady("Unable to connect to Life Time Fitness API") from err
    except ApiInvalidAuth as err:
        _LOGGER.error("Invalid authentication for Life Time Fitness: %s", err)
        raise ConfigEntryAuthFailed("Invalid username or password") from err
    except ApiPasswordNeedsToBeChanged as err:
        _LOGGER.error("Life Time Fitness password needs to be changed: %s", err)
        raise ConfigEntryAuthFailed(
            "Password needs to be changed on the Life Time website"
        ) from err
    except ApiTooManyAuthenticationAttempts as err:
        _LOGGER.error("Too many authentication attempts for Life Time Fitness: %s", err)
        raise ConfigEntryAuthFailed(
            "Too many authentication attempts, account may be locked"
        ) from err
    except ApiActivationRequired as err:
        _LOGGER.error("Life Time Fitness account activation required: %s", err)
        raise ConfigEntryAuthFailed("Account activation required") from err
    except ApiDuplicateEmail as err:
        _LOGGER.error("Duplicate email for Life Time Fitness account: %s", err)
        raise ConfigEntryAuthFailed(
            "Multiple accounts associated with this email"
        ) from err
    except ApiUnknownAuthError as err:
        _LOGGER.error("Unknown authentication error for Life Time Fitness: %s", err)
        raise ConfigEntryNotReady("Unknown authentication error occurred") from err
    except ApiProfileError as err:
        _LOGGER.error("Failed to fetch Life Time Fitness profile: %s", err)
        raise ConfigEntryNotReady("Failed to fetch profile data") from err

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
