"""Calendar platform for Life Time Fitness integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import LifetimeFitnessConfigEntry
from .const import DOMAIN
from .coordinator import LifetimeFitnessCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LifetimeFitnessConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Life Time Fitness calendar from a config entry."""
    coordinator = entry.runtime_data

    async_add_entities([LifetimeFitnessCalendar(coordinator, entry.entry_id)])


class LifetimeFitnessCalendar(CoordinatorEntity[LifetimeFitnessCoordinator], CalendarEntity):
    """Representation of a Life Time Fitness calendar."""

    _attr_has_entity_name = True
    _attr_name = "Reservations"

    def __init__(
        self,
        coordinator: LifetimeFitnessCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{entry_id}_reservations"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"Life Time Fitness ({coordinator.username})",
            manufacturer="Life Time Fitness",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://my.lifetime.life",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if self.coordinator.data is None:
            return None

        reservations = self.coordinator.data.reservations
        if not reservations:
            return None

        now = dt_util.now()

        # Find the next upcoming event (or current if one is happening now)
        for reservation in sorted(reservations, key=lambda r: r.get("start", "")):
            event = self._reservation_to_event(reservation)
            if event and event.end >= now:
                return event

        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if self.coordinator.data is None:
            return []

        events: list[CalendarEvent] = []
        reservations = self.coordinator.data.reservations

        for reservation in reservations:
            event = self._reservation_to_event(reservation)
            if event is None:
                continue

            # Check if event falls within the requested range
            if event.end >= start_date and event.start <= end_date:
                events.append(event)

        return sorted(events, key=lambda e: e.start)

    def _reservation_to_event(self, reservation: dict[str, Any]) -> CalendarEvent | None:
        """Convert a reservation dict to a CalendarEvent."""
        start_str = reservation.get("start")
        end_str = reservation.get("end")

        if not start_str or not end_str:
            return None

        try:
            start = datetime.fromisoformat(start_str)
            end = datetime.fromisoformat(end_str)
        except (ValueError, TypeError):
            return None

        # Build event summary
        event_name = reservation.get("eventName", "Reservation")

        # Build description with details
        description_parts: list[str] = []

        reservation_type = reservation.get("reservationType")
        if reservation_type:
            description_parts.append(f"Type: {reservation_type}")

        instructors = reservation.get("instructors", [])
        if instructors:
            instructor_names = ", ".join(i.get("name", "") for i in instructors if i.get("name"))
            if instructor_names:
                description_parts.append(f"Instructor: {instructor_names}")

        location_name = reservation.get("locationName")
        if location_name:
            description_parts.append(f"Club: {location_name}")

        description = "\n".join(description_parts) if description_parts else None

        # Location from the reservation
        location = reservation.get("location")

        return CalendarEvent(
            summary=event_name,
            start=start,
            end=end,
            description=description,
            location=location,
            uid=reservation.get("id"),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None
