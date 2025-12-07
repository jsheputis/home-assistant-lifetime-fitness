"""Config flow for Life Time Fitness integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    Api,
    ApiActivationRequired,
    ApiCannotConnect,
    ApiDuplicateEmail,
    ApiInvalidAuth,
    ApiPasswordNeedsToBeChanged,
    ApiTooManyAuthenticationAttempts,
    ApiUnknownAuthError,
)
from .const import (
    CONF_DEFAULT_START_OF_WEEK_DAY,
    CONF_PASSWORD,
    CONF_START_OF_WEEK_DAY,
    CONF_START_OF_WEEK_DAY_VALUES,
    CONF_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    username, password = data[CONF_USERNAME], data[CONF_PASSWORD]
    api_client = Api(async_create_clientsession(hass), username, password)

    try:
        await api_client.authenticate()
    except ApiCannotConnect as err:
        raise CannotConnect from err
    except ApiInvalidAuth as err:
        raise InvalidAuth from err
    except ApiPasswordNeedsToBeChanged as err:
        raise PasswordNeedsToBeChanged from err
    except ApiTooManyAuthenticationAttempts as err:
        raise TooManyAuthenticationAttempts from err
    except ApiActivationRequired as err:
        raise ActivationRequired from err
    except ApiDuplicateEmail as err:
        raise DuplicateEmail from err
    except ApiUnknownAuthError as err:
        raise UnknownAuthError from err

    return {"title": f"Life Time: {username}"}


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Life Time Fitness."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_START_OF_WEEK_DAY,
                        default=self.config_entry.options.get(
                            CONF_START_OF_WEEK_DAY, CONF_DEFAULT_START_OF_WEEK_DAY
                        ),
                    ): vol.In(CONF_START_OF_WEEK_DAY_VALUES),
                }
            ),
        )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for lifetime-fitness."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except PasswordNeedsToBeChanged:
            errors["base"] = "password_needs_to_be_changed"
        except TooManyAuthenticationAttempts:
            errors["base"] = "too_many_authentication_attempts"
        except ActivationRequired:
            errors["base"] = "activation_required"
        except DuplicateEmail:
            errors["base"] = "duplicate_email"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except UnknownAuthError:
            errors["base"] = "unknown_auth_error"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class PasswordNeedsToBeChanged(HomeAssistantError):
    """Error to indicate there the password needs to be changed."""


class TooManyAuthenticationAttempts(HomeAssistantError):
    """Error to indicate there were too many authentication attempts."""


class ActivationRequired(HomeAssistantError):
    """Error to indicate that account activation is required."""


class DuplicateEmail(HomeAssistantError):
    """Error to indicate there are multiple accounts associated with this email."""


class UnknownAuthError(HomeAssistantError):
    """Error to indicate server returned unexpected authentication error."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
