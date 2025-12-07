"""Tests for the Life Time Fitness coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.lifetime_fitness.api import (
    Api,
    ApiAuthExpired,
    ApiAuthRequired,
    ApiCannotConnect,
    ApiInvalidAuth,
)
from custom_components.lifetime_fitness.coordinator import (
    LifetimeFitnessCoordinator,
    LifetimeFitnessData,
)

from .conftest import (
    MOCK_VISITS_RESPONSE_EMPTY,
    MOCK_VISITS_RESPONSE_WITH_DATA,
    TEST_USERNAME,
)


class TestLifetimeFitnessCoordinator:
    """Tests for LifetimeFitnessCoordinator."""

    async def test_init(self, hass: HomeAssistant, mock_api_authenticated: Api) -> None:
        """Test coordinator initialization."""
        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        assert coordinator.api_client == mock_api_authenticated
        assert coordinator.start_of_week_day == 0
        assert coordinator.username == TEST_USERNAME

    async def test_async_update_data_success(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test successful data update."""
        mock_api_authenticated.update = AsyncMock()
        mock_api_authenticated.result_json = MOCK_VISITS_RESPONSE_WITH_DATA

        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        data = await coordinator._async_update_data()

        assert isinstance(data, LifetimeFitnessData)
        assert data.total_visits == 3
        mock_api_authenticated.update.assert_called_once()

    async def test_async_update_data_empty(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test data update with empty response."""
        mock_api_authenticated.update = AsyncMock()
        mock_api_authenticated.result_json = MOCK_VISITS_RESPONSE_EMPTY

        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        data = await coordinator._async_update_data()

        assert data.total_visits == 0
        assert data.visits_this_year == 0
        assert data.visits_this_month == 0
        assert data.visits_this_week == 0
        assert data.last_visit_timestamp is None

    async def test_async_update_data_invalid_auth(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test data update with invalid auth error."""
        mock_api_authenticated.update = AsyncMock(side_effect=ApiInvalidAuth())

        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    async def test_async_update_data_auth_required(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test data update with auth required error."""
        mock_api_authenticated.update = AsyncMock(side_effect=ApiAuthRequired())

        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    async def test_async_update_data_cannot_connect(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test data update with connection error."""
        mock_api_authenticated.update = AsyncMock(side_effect=ApiCannotConnect())

        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    async def test_async_update_data_auth_expired(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test data update with expired auth error."""
        mock_api_authenticated.update = AsyncMock(side_effect=ApiAuthExpired())

        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    async def test_update_start_of_week_day(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test updating start of week day."""
        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        assert coordinator.start_of_week_day == 0
        coordinator.update_start_of_week_day(6)
        assert coordinator.start_of_week_day == 6

    async def test_process_visits_with_invalid_timestamps(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test processing visits with invalid timestamps."""
        mock_api_authenticated.update = AsyncMock()
        mock_api_authenticated.result_json = {
            "data": [
                {"usageDateTime": 1701388800000},  # Valid
                {"usageDateTime": "invalid"},  # Invalid string
                {"otherField": "value"},  # Missing timestamp
                {"usageDateTime": 1701475200000},  # Valid
            ]
        }

        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        data = await coordinator._async_update_data()

        # Should process only valid timestamps
        assert data.total_visits == 4  # Total count includes all items
        # But calculations should work with valid ones

    async def test_process_visits_null_result(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test processing when result_json is None."""
        mock_api_authenticated.update = AsyncMock()
        mock_api_authenticated.result_json = None

        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        data = await coordinator._async_update_data()

        assert data.total_visits == 0
        assert data.raw_visits == []

    async def test_member_id_property(
        self, hass: HomeAssistant, mock_api_authenticated: Api
    ) -> None:
        """Test member_id property."""
        coordinator = LifetimeFitnessCoordinator(
            hass,
            mock_api_authenticated,
            start_of_week_day=0,
        )

        assert coordinator.member_id == "12345678"
