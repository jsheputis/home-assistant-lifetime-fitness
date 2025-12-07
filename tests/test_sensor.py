"""Tests for the Life Time Fitness sensor platform."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.lifetime_fitness.sensor import VisitsSensor
from custom_components.lifetime_fitness.const import (
    VISITS_SENSOR_ATTR_VISITS_THIS_YEAR,
    VISITS_SENSOR_ATTR_VISITS_THIS_MONTH,
    VISITS_SENSOR_ATTR_VISITS_THIS_WEEK,
    VISITS_SENSOR_ATTR_LAST_VISIT_TIMESTAMP,
    VISITS_SENSOR_UNIT_OF_MEASUREMENT,
)

from .conftest import TEST_USERNAME


class TestVisitsSensor:
    """Tests for the VisitsSensor class."""

    def test_init(self, mock_api_authenticated: MagicMock) -> None:
        """Test sensor initialization."""
        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)

        assert sensor.name == f"{TEST_USERNAME} Life Time Visits"
        assert sensor.unique_id == f"{TEST_USERNAME}_lifetime_visits"
        assert sensor.unit_of_measurement == VISITS_SENSOR_UNIT_OF_MEASUREMENT
        assert sensor.should_poll is True

    def test_available_when_update_successful(self, mock_api_authenticated: MagicMock) -> None:
        """Test sensor availability when update is successful."""
        mock_api_authenticated.update_successful = True
        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)

        assert sensor.available is True

    def test_unavailable_when_update_failed(self, mock_api_authenticated: MagicMock) -> None:
        """Test sensor availability when update failed."""
        mock_api_authenticated.update_successful = False
        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)

        assert sensor.available is False

    def test_state_with_visits(self, mock_api_authenticated: MagicMock) -> None:
        """Test sensor state with visit data."""
        mock_api_authenticated.result_json = {
            "data": [
                {"usageDateTime": 1701388800000},
                {"usageDateTime": 1701475200000},
            ]
        }
        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)

        assert sensor.state == 2

    def test_state_with_no_visits(self, mock_api_authenticated: MagicMock) -> None:
        """Test sensor state with no visits."""
        mock_api_authenticated.result_json = {"data": []}
        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)

        assert sensor.state == 0

    def test_state_with_null_result(self, mock_api_authenticated: MagicMock) -> None:
        """Test sensor state when result_json is None."""
        mock_api_authenticated.result_json = None
        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)

        assert sensor.state == 0

    def test_state_with_null_data(self, mock_api_authenticated: MagicMock) -> None:
        """Test sensor state when data is None."""
        mock_api_authenticated.result_json = {"data": None}
        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)

        assert sensor.state == 0

    async def test_async_update_with_visits(self, mock_api_authenticated: MagicMock) -> None:
        """Test async_update with visit data."""
        today = date.today()
        current_year = today.year
        current_month = today.month

        # Create timestamps for visits
        today_timestamp = today.replace(hour=12).strftime("%s")
        today_ms = int(today_timestamp) * 1000

        yesterday = today - timedelta(days=1)
        yesterday_ms = int(yesterday.strftime("%s")) * 1000

        mock_api_authenticated.result_json = {
            "data": [
                {"usageDateTime": today_ms},
                {"usageDateTime": yesterday_ms},
            ]
        }
        mock_api_authenticated.update = AsyncMock()

        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)
        await sensor.async_update()

        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_VISITS_THIS_YEAR] >= 2
        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_VISITS_THIS_MONTH] >= 0
        assert VISITS_SENSOR_ATTR_LAST_VISIT_TIMESTAMP in sensor._attr_extra_state_attributes

    async def test_async_update_with_empty_data(self, mock_api_authenticated: MagicMock) -> None:
        """Test async_update with empty visit data."""
        mock_api_authenticated.result_json = {"data": []}
        mock_api_authenticated.update = AsyncMock()

        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)
        await sensor.async_update()

        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_VISITS_THIS_YEAR] == 0
        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_VISITS_THIS_MONTH] == 0
        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_VISITS_THIS_WEEK] == 0
        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_LAST_VISIT_TIMESTAMP] is None

    async def test_async_update_with_null_result(self, mock_api_authenticated: MagicMock) -> None:
        """Test async_update when result_json is None."""
        mock_api_authenticated.result_json = None
        mock_api_authenticated.update = AsyncMock()

        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)
        await sensor.async_update()

        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_VISITS_THIS_YEAR] == 0
        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_VISITS_THIS_MONTH] == 0
        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_VISITS_THIS_WEEK] == 0
        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_LAST_VISIT_TIMESTAMP] is None

    async def test_async_update_with_missing_timestamp(
        self, mock_api_authenticated: MagicMock
    ) -> None:
        """Test async_update handles missing timestamp gracefully."""
        mock_api_authenticated.result_json = {
            "data": [
                {"usageDateTime": 1701388800000},
                {"someOtherField": "value"},  # Missing timestamp
            ]
        }
        mock_api_authenticated.update = AsyncMock()

        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)
        await sensor.async_update()

        # Should process the valid visit and skip the invalid one
        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_LAST_VISIT_TIMESTAMP] is not None

    async def test_async_update_with_invalid_timestamp(
        self, mock_api_authenticated: MagicMock
    ) -> None:
        """Test async_update handles invalid timestamp gracefully."""
        mock_api_authenticated.result_json = {
            "data": [
                {"usageDateTime": "not_a_number"},
                {"usageDateTime": 1701388800000},  # Valid timestamp
            ]
        }
        mock_api_authenticated.update = AsyncMock()

        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)
        await sensor.async_update()

        # Should process the valid visit and skip the invalid one
        assert sensor._attr_extra_state_attributes[VISITS_SENSOR_ATTR_LAST_VISIT_TIMESTAMP] is not None

    def test_week_calculation_monday_start(self, mock_api_authenticated: MagicMock) -> None:
        """Test week calculation with Monday as start of week."""
        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=0)
        assert sensor._start_of_week_day == 0

    def test_week_calculation_sunday_start(self, mock_api_authenticated: MagicMock) -> None:
        """Test week calculation with Sunday as start of week."""
        sensor = VisitsSensor(mock_api_authenticated, start_of_week_day=6)
        assert sensor._start_of_week_day == 6
