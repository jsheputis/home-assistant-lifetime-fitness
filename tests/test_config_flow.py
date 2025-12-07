"""Tests for the Life Time Fitness config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.lifetime_fitness.api import (
    ApiActivationRequired,
    ApiCannotConnect,
    ApiDuplicateEmail,
    ApiInvalidAuth,
    ApiPasswordNeedsToBeChanged,
    ApiTooManyAuthenticationAttempts,
    ApiUnknownAuthError,
)
from custom_components.lifetime_fitness.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)

from .conftest import TEST_PASSWORD, TEST_USERNAME


async def test_form_user_step(hass: HomeAssistant) -> None:
    """Test the user step shows the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_form_user_success(hass: HomeAssistant) -> None:
    """Test successful user configuration."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch("custom_components.lifetime_fitness.config_flow.Api") as mock_api_class,
        patch("custom_components.lifetime_fitness.config_flow.async_create_clientsession"),
        patch("custom_components.lifetime_fitness.async_setup_entry", return_value=True),
    ):
        mock_api = AsyncMock()
        mock_api.authenticate = AsyncMock()
        mock_api_class.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Life Time: {TEST_USERNAME}"
    assert result["data"] == {
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test handling of connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.lifetime_fitness.config_flow.Api") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.authenticate = AsyncMock(side_effect=ApiCannotConnect())
        mock_api_class.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test handling of invalid auth error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.lifetime_fitness.config_flow.Api") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.authenticate = AsyncMock(side_effect=ApiInvalidAuth())
        mock_api_class.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_password_needs_change(hass: HomeAssistant) -> None:
    """Test handling of password needs to be changed error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.lifetime_fitness.config_flow.Api") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.authenticate = AsyncMock(side_effect=ApiPasswordNeedsToBeChanged())
        mock_api_class.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "password_needs_to_be_changed"}


async def test_form_too_many_attempts(hass: HomeAssistant) -> None:
    """Test handling of too many authentication attempts error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.lifetime_fitness.config_flow.Api") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.authenticate = AsyncMock(side_effect=ApiTooManyAuthenticationAttempts())
        mock_api_class.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "too_many_authentication_attempts"}


async def test_form_activation_required(hass: HomeAssistant) -> None:
    """Test handling of activation required error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.lifetime_fitness.config_flow.Api") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.authenticate = AsyncMock(side_effect=ApiActivationRequired())
        mock_api_class.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "activation_required"}


async def test_form_duplicate_email(hass: HomeAssistant) -> None:
    """Test handling of duplicate email error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.lifetime_fitness.config_flow.Api") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.authenticate = AsyncMock(side_effect=ApiDuplicateEmail())
        mock_api_class.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "duplicate_email"}


async def test_form_unknown_auth_error(hass: HomeAssistant) -> None:
    """Test handling of unknown auth error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.lifetime_fitness.config_flow.Api") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.authenticate = AsyncMock(side_effect=ApiUnknownAuthError())
        mock_api_class.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown_auth_error"}


async def test_form_unexpected_exception(hass: HomeAssistant) -> None:
    """Test handling of unexpected exception."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.lifetime_fitness.config_flow.Api") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.authenticate = AsyncMock(side_effect=Exception("Unexpected error"))
        mock_api_class.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}
