"""Sensor platform for Life Time Fitness integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LifetimeFitnessConfigEntry
from .const import DOMAIN
from .coordinator import LifetimeFitnessCoordinator, LifetimeFitnessData


@dataclass(frozen=True, kw_only=True)
class LifetimeFitnessSensorEntityDescription(SensorEntityDescription):
    """Describes a Life Time Fitness sensor entity."""

    value_fn: Callable[[LifetimeFitnessData], Any]


SENSOR_DESCRIPTIONS: tuple[LifetimeFitnessSensorEntityDescription, ...] = (
    LifetimeFitnessSensorEntityDescription(
        key="total_visits",
        translation_key="total_visits",
        native_unit_of_measurement="visits",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.total_visits,
    ),
    LifetimeFitnessSensorEntityDescription(
        key="visits_this_year",
        translation_key="visits_this_year",
        native_unit_of_measurement="visits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.visits_this_year,
    ),
    LifetimeFitnessSensorEntityDescription(
        key="visits_this_month",
        translation_key="visits_this_month",
        native_unit_of_measurement="visits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.visits_this_month,
    ),
    LifetimeFitnessSensorEntityDescription(
        key="visits_this_week",
        translation_key="visits_this_week",
        native_unit_of_measurement="visits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.visits_this_week,
    ),
    LifetimeFitnessSensorEntityDescription(
        key="last_visit",
        translation_key="last_visit",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_visit_timestamp,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LifetimeFitnessConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Life Time Fitness sensors from a config entry."""
    coordinator = entry.runtime_data

    async_add_entities(
        LifetimeFitnessSensor(coordinator, description, entry.entry_id)
        for description in SENSOR_DESCRIPTIONS
    )


class LifetimeFitnessSensor(
    CoordinatorEntity[LifetimeFitnessCoordinator], SensorEntity
):
    """Representation of a Life Time Fitness sensor."""

    entity_description: LifetimeFitnessSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LifetimeFitnessCoordinator,
        description: LifetimeFitnessSensorEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        # Use entry_id + key for unique_id to ensure uniqueness
        self._attr_unique_id = f"{entry_id}_{description.key}"

        # Device info for grouping entities under a device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"Life Time Fitness ({coordinator.username})",
            manufacturer="Life Time Fitness",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://my.lifetime.life",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None

        value = self.entity_description.value_fn(self.coordinator.data)

        # Convert timestamp to datetime for timestamp sensor
        if (
            self.entity_description.device_class == SensorDeviceClass.TIMESTAMP
            and value is not None
        ):
            from datetime import UTC, datetime

            return datetime.fromtimestamp(value, tz=UTC)

        return value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None
