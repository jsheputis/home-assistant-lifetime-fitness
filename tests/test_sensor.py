"""Tests for the Life Time Fitness sensor platform."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory

from custom_components.lifetime_fitness.coordinator import (
    LifetimeFitnessCoordinator,
    LifetimeFitnessData,
)
from custom_components.lifetime_fitness.sensor import (
    SENSOR_DESCRIPTIONS,
    LifetimeFitnessSensor,
)

from .conftest import TEST_ENTRY_ID, TEST_USERNAME


class TestSensorDescriptions:
    """Tests for sensor entity descriptions."""

    def test_total_visits_description(self) -> None:
        """Test total visits sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "total_visits")
        assert desc.translation_key == "total_visits"
        assert desc.native_unit_of_measurement == "visits"
        assert desc.state_class == SensorStateClass.TOTAL

    def test_visits_this_year_description(self) -> None:
        """Test visits this year sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "visits_this_year")
        assert desc.translation_key == "visits_this_year"
        assert desc.state_class == SensorStateClass.MEASUREMENT

    def test_visits_this_month_description(self) -> None:
        """Test visits this month sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "visits_this_month")
        assert desc.translation_key == "visits_this_month"
        assert desc.state_class == SensorStateClass.MEASUREMENT

    def test_visits_this_week_description(self) -> None:
        """Test visits this week sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "visits_this_week")
        assert desc.translation_key == "visits_this_week"
        assert desc.state_class == SensorStateClass.MEASUREMENT

    def test_last_visit_description(self) -> None:
        """Test last visit sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "last_visit")
        assert desc.translation_key == "last_visit"
        assert desc.device_class == SensorDeviceClass.TIMESTAMP
        assert desc.entity_category == EntityCategory.DIAGNOSTIC


class TestLifetimeFitnessSensor:
    """Tests for LifetimeFitnessSensor."""

    def test_sensor_init(self, mock_coordinator: LifetimeFitnessCoordinator) -> None:
        """Test sensor initialization."""
        description = SENSOR_DESCRIPTIONS[0]  # total_visits
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.unique_id == f"{TEST_ENTRY_ID}_{description.key}"
        assert sensor._attr_has_entity_name is True
        assert sensor.entity_description == description

    def test_sensor_device_info(self, mock_coordinator: LifetimeFitnessCoordinator) -> None:
        """Test sensor device info."""
        description = SENSOR_DESCRIPTIONS[0]
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        device_info = sensor._attr_device_info
        assert device_info is not None
        assert ("lifetime_fitness", TEST_ENTRY_ID) in device_info["identifiers"]
        assert f"Life Time Fitness ({TEST_USERNAME})" in device_info["name"]
        assert device_info["manufacturer"] == "Life Time Fitness"

    def test_native_value_total_visits(self, mock_coordinator: LifetimeFitnessCoordinator) -> None:
        """Test native_value for total visits sensor."""
        description = next(d for d in SENSOR_DESCRIPTIONS if d.key == "total_visits")
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.native_value == 10  # From mock_coordinator_data

    def test_native_value_visits_this_year(
        self, mock_coordinator: LifetimeFitnessCoordinator
    ) -> None:
        """Test native_value for visits this year sensor."""
        description = next(d for d in SENSOR_DESCRIPTIONS if d.key == "visits_this_year")
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.native_value == 8  # From mock_coordinator_data

    def test_native_value_visits_this_month(
        self, mock_coordinator: LifetimeFitnessCoordinator
    ) -> None:
        """Test native_value for visits this month sensor."""
        description = next(d for d in SENSOR_DESCRIPTIONS if d.key == "visits_this_month")
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.native_value == 3  # From mock_coordinator_data

    def test_native_value_visits_this_week(
        self, mock_coordinator: LifetimeFitnessCoordinator
    ) -> None:
        """Test native_value for visits this week sensor."""
        description = next(d for d in SENSOR_DESCRIPTIONS if d.key == "visits_this_week")
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.native_value == 2  # From mock_coordinator_data

    def test_native_value_last_visit_timestamp(
        self, mock_coordinator: LifetimeFitnessCoordinator
    ) -> None:
        """Test native_value for last visit sensor returns datetime."""
        description = next(d for d in SENSOR_DESCRIPTIONS if d.key == "last_visit")
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        value = sensor.native_value
        assert isinstance(value, datetime)
        assert value.tzinfo == UTC
        # 1701561600.0 = Dec 3, 2023 00:00:00 UTC
        assert value == datetime(2023, 12, 3, 0, 0, 0, tzinfo=UTC)

    def test_native_value_when_no_data(self, mock_coordinator: LifetimeFitnessCoordinator) -> None:
        """Test native_value when coordinator has no data."""
        mock_coordinator.data = None
        description = SENSOR_DESCRIPTIONS[0]
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.native_value is None

    def test_available_when_update_success(
        self, mock_coordinator: LifetimeFitnessCoordinator
    ) -> None:
        """Test availability when update is successful."""
        description = SENSOR_DESCRIPTIONS[0]
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.available is True

    def test_unavailable_when_update_failed(
        self, mock_coordinator: LifetimeFitnessCoordinator
    ) -> None:
        """Test availability when update failed."""
        mock_coordinator.last_update_success = False
        description = SENSOR_DESCRIPTIONS[0]
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.available is False

    def test_unavailable_when_no_data(self, mock_coordinator: LifetimeFitnessCoordinator) -> None:
        """Test availability when no data."""
        mock_coordinator.data = None
        description = SENSOR_DESCRIPTIONS[0]
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.available is False

    def test_last_visit_null_timestamp(self, mock_coordinator: LifetimeFitnessCoordinator) -> None:
        """Test last visit sensor when timestamp is None."""
        mock_coordinator.data = LifetimeFitnessData(
            total_visits=0,
            visits_this_year=0,
            visits_this_month=0,
            visits_this_week=0,
            last_visit_timestamp=None,
            raw_visits=[],
            reservations=[],
        )
        description = next(d for d in SENSOR_DESCRIPTIONS if d.key == "last_visit")
        sensor = LifetimeFitnessSensor(
            mock_coordinator,
            description,
            TEST_ENTRY_ID,
        )

        assert sensor.native_value is None
