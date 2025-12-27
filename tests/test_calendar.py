"""Tests for the Life Time Fitness calendar platform."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from homeassistant.core import HomeAssistant

from custom_components.lifetime_fitness.calendar import LifetimeFitnessCalendar
from custom_components.lifetime_fitness.coordinator import (
    LifetimeFitnessCoordinator,
    LifetimeFitnessData,
)

from .conftest import TEST_ENTRY_ID, TEST_USERNAME

# Sample reservation data for testing
MOCK_RESERVATION = {
    "id": "ZXhlcnA6NTJwMTUyODMzOjUyYm9vazYyMzk4Ng==",
    "memberId": 114937419,
    "memberName": "James",
    "eventId": "ZXhlcnA6NTJib29rNjIzOTg2OjIwMjYtMDEtMDY=",
    "eventName": "PT Private",
    "location": "Fitness Floor, Warrenville",
    "locationName": "Warrenville",
    "clubId": 52,
    "instructors": [{"name": "Zoe W."}],
    "start": "2026-01-06T08:00:00-06:00",
    "end": "2026-01-06T09:00:00-06:00",
    "reservationType": "Personal Training",
    "category": "class",
}

MOCK_RESERVATION_SECOND = {
    "id": "ZXhlcnA6NTJwMTUyODMzOjUyYm9vazYyMzk4Nw==",
    "memberId": 114937419,
    "memberName": "James",
    "eventId": "ZXhlcnA6NTJib29rNjIzOTg3OjIwMjYtMDEtMDg=",
    "eventName": "Yoga Class",
    "location": "Studio A, Warrenville",
    "locationName": "Warrenville",
    "clubId": 52,
    "instructors": [{"name": "John D."}],
    "start": "2026-01-08T10:00:00-06:00",
    "end": "2026-01-08T11:00:00-06:00",
    "reservationType": "Group Fitness",
    "category": "class",
}


@pytest.fixture
def mock_coordinator_with_reservations(
    hass: HomeAssistant,
    mock_api_authenticated,
) -> LifetimeFitnessCoordinator:
    """Return a mock coordinator with reservation data."""
    coordinator = LifetimeFitnessCoordinator(
        hass,
        mock_api_authenticated,
        start_of_week_day=0,
    )
    coordinator.data = LifetimeFitnessData(
        total_visits=10,
        visits_this_year=8,
        visits_this_month=3,
        visits_this_week=2,
        last_visit_timestamp=1701561600.0,
        raw_visits=[],
        reservations=[MOCK_RESERVATION, MOCK_RESERVATION_SECOND],
    )
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_coordinator_no_reservations(
    hass: HomeAssistant,
    mock_api_authenticated,
) -> LifetimeFitnessCoordinator:
    """Return a mock coordinator with no reservations."""
    coordinator = LifetimeFitnessCoordinator(
        hass,
        mock_api_authenticated,
        start_of_week_day=0,
    )
    coordinator.data = LifetimeFitnessData(
        total_visits=10,
        visits_this_year=8,
        visits_this_month=3,
        visits_this_week=2,
        last_visit_timestamp=1701561600.0,
        raw_visits=[],
        reservations=[],
    )
    coordinator.last_update_success = True
    return coordinator


class TestLifetimeFitnessCalendar:
    """Tests for LifetimeFitnessCalendar."""

    def test_calendar_init(
        self, mock_coordinator_with_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test calendar initialization."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        assert calendar.unique_id == f"{TEST_ENTRY_ID}_reservations"
        assert calendar._attr_has_entity_name is True
        assert calendar._attr_name == "Reservations"

    def test_calendar_device_info(
        self, mock_coordinator_with_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test calendar device info."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        device_info = calendar._attr_device_info
        assert device_info is not None
        assert ("lifetime_fitness", TEST_ENTRY_ID) in device_info["identifiers"]
        assert f"Life Time Fitness ({TEST_USERNAME})" in device_info["name"]
        assert device_info["manufacturer"] == "Life Time Fitness"

    def test_event_property_returns_next_event(
        self, mock_coordinator_with_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test that event property returns the next upcoming event."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        event = calendar.event
        assert event is not None
        assert event.summary == "PT Private"
        assert event.location == "Fitness Floor, Warrenville"

    def test_event_property_no_reservations(
        self, mock_coordinator_no_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test that event property returns None when no reservations."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_no_reservations,
            TEST_ENTRY_ID,
        )

        assert calendar.event is None

    def test_event_property_no_data(
        self, mock_coordinator_no_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test that event property returns None when coordinator has no data."""
        mock_coordinator_no_reservations.data = None
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_no_reservations,
            TEST_ENTRY_ID,
        )

        assert calendar.event is None

    @pytest.mark.asyncio
    async def test_async_get_events(
        self,
        hass: HomeAssistant,
        mock_coordinator_with_reservations: LifetimeFitnessCoordinator,
    ) -> None:
        """Test getting events within a date range."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        # Get events for January 2026
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 31, tzinfo=UTC)

        events = await calendar.async_get_events(hass, start, end)

        assert len(events) == 2
        assert events[0].summary == "PT Private"
        assert events[1].summary == "Yoga Class"

    @pytest.mark.asyncio
    async def test_async_get_events_filtered_by_range(
        self,
        hass: HomeAssistant,
        mock_coordinator_with_reservations: LifetimeFitnessCoordinator,
    ) -> None:
        """Test that events are filtered by date range."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        # Get events only for Jan 6, 2026
        start = datetime(2026, 1, 6, tzinfo=UTC)
        end = datetime(2026, 1, 7, tzinfo=UTC)

        events = await calendar.async_get_events(hass, start, end)

        assert len(events) == 1
        assert events[0].summary == "PT Private"

    @pytest.mark.asyncio
    async def test_async_get_events_no_data(
        self,
        hass: HomeAssistant,
        mock_coordinator_no_reservations: LifetimeFitnessCoordinator,
    ) -> None:
        """Test getting events when coordinator has no data."""
        mock_coordinator_no_reservations.data = None
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_no_reservations,
            TEST_ENTRY_ID,
        )

        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 31, tzinfo=UTC)

        events = await calendar.async_get_events(hass, start, end)

        assert events == []

    def test_reservation_to_event(
        self, mock_coordinator_with_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test conversion of reservation dict to CalendarEvent."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        event = calendar._reservation_to_event(MOCK_RESERVATION)

        assert event is not None
        assert event.summary == "PT Private"
        assert event.location == "Fitness Floor, Warrenville"
        assert event.uid == "ZXhlcnA6NTJwMTUyODMzOjUyYm9vazYyMzk4Ng=="
        assert "Type: Personal Training" in event.description
        assert "Instructor: Zoe W." in event.description
        assert "Club: Warrenville" in event.description

    def test_reservation_to_event_missing_times(
        self, mock_coordinator_with_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test that reservation without times returns None."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        reservation = {"eventName": "Test Event"}
        event = calendar._reservation_to_event(reservation)

        assert event is None

    def test_reservation_to_event_invalid_times(
        self, mock_coordinator_with_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test that reservation with invalid times returns None."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        reservation = {"start": "invalid", "end": "invalid"}
        event = calendar._reservation_to_event(reservation)

        assert event is None

    def test_reservation_to_event_no_optional_fields(
        self, mock_coordinator_with_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test reservation with minimal fields."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        reservation = {
            "start": "2026-01-06T08:00:00-06:00",
            "end": "2026-01-06T09:00:00-06:00",
        }
        event = calendar._reservation_to_event(reservation)

        assert event is not None
        assert event.summary == "Reservation"
        assert event.description is None
        assert event.location is None

    def test_available_when_update_success(
        self, mock_coordinator_with_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test availability when update is successful."""
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        assert calendar.available is True

    def test_unavailable_when_update_failed(
        self, mock_coordinator_with_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test availability when update failed."""
        mock_coordinator_with_reservations.last_update_success = False
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_with_reservations,
            TEST_ENTRY_ID,
        )

        assert calendar.available is False

    def test_unavailable_when_no_data(
        self, mock_coordinator_no_reservations: LifetimeFitnessCoordinator
    ) -> None:
        """Test availability when no data."""
        mock_coordinator_no_reservations.data = None
        calendar = LifetimeFitnessCalendar(
            mock_coordinator_no_reservations,
            TEST_ENTRY_ID,
        )

        assert calendar.available is False
