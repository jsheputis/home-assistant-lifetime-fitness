"""DataUpdateCoordinator for Life Time Fitness integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    Api,
    ApiAuthExpired,
    ApiAuthRequired,
    ApiCannotConnect,
    ApiInvalidAuth,
)
from .const import API_CLUB_VISITS_TIMESTAMP_JSON_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Update interval for polling
UPDATE_INTERVAL = timedelta(minutes=5)


@dataclass
class LifetimeFitnessData:
    """Data class to hold processed visit data."""

    total_visits: int
    visits_this_year: int
    visits_this_month: int
    visits_this_week: int
    last_visit_timestamp: float | None
    raw_visits: list[dict[str, Any]]
    reservations: list[dict[str, Any]]


class LifetimeFitnessCoordinator(DataUpdateCoordinator[LifetimeFitnessData]):
    """Coordinator to manage data updates for Life Time Fitness."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: Api,
        start_of_week_day: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api_client = api_client
        self.start_of_week_day = start_of_week_day

    async def _async_update_data(self) -> LifetimeFitnessData:
        """Fetch data from the API."""
        try:
            await self.api_client.update()
        except ApiInvalidAuth as err:
            raise ConfigEntryAuthFailed("Invalid authentication") from err
        except ApiAuthRequired as err:
            raise ConfigEntryAuthFailed("Authentication required") from err
        except ApiCannotConnect as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except ApiAuthExpired:
            # This should be handled internally by the API client
            # If it bubbles up, treat it as an auth failure
            raise ConfigEntryAuthFailed("Authentication expired") from None

        return self._process_visits_data()

    def _process_visits_data(self) -> LifetimeFitnessData:
        """Process raw visit data into structured format."""
        visits = self._get_visits_list()
        reservations = self._get_reservations_list()

        if not visits:
            return LifetimeFitnessData(
                total_visits=0,
                visits_this_year=0,
                visits_this_month=0,
                visits_this_week=0,
                last_visit_timestamp=None,
                raw_visits=[],
                reservations=reservations,
            )

        today = date.today()
        beginning_of_week_offset = (today.weekday() - self.start_of_week_day) % 7
        beginning_of_week_date = today - timedelta(days=beginning_of_week_offset)

        last_visit_timestamp: float | None = None
        visits_this_year = 0
        visits_this_month = 0
        visits_this_week = 0

        for visit in visits:
            timestamp_ms = visit.get(API_CLUB_VISITS_TIMESTAMP_JSON_KEY)
            if timestamp_ms is None:
                _LOGGER.warning("Visit data missing timestamp: %s", visit)
                continue

            try:
                visit_timestamp = timestamp_ms / 1000
                visit_date = date.fromtimestamp(visit_timestamp)
            except (TypeError, ValueError, OSError) as err:
                _LOGGER.warning("Invalid visit timestamp %s: %s", timestamp_ms, err)
                continue

            if visit_date.year == today.year:
                visits_this_year += 1
                if visit_date.month == today.month:
                    visits_this_month += 1

            if visit_date >= beginning_of_week_date:
                visits_this_week += 1

            if last_visit_timestamp is None or visit_timestamp > last_visit_timestamp:
                last_visit_timestamp = visit_timestamp

        return LifetimeFitnessData(
            total_visits=len(visits),
            visits_this_year=visits_this_year,
            visits_this_month=visits_this_month,
            visits_this_week=visits_this_week,
            last_visit_timestamp=last_visit_timestamp,
            raw_visits=visits,
            reservations=reservations,
        )

    def _get_visits_list(self) -> list[dict[str, Any]]:
        """Safely get visits data from the API response."""
        if self.api_client.result_json is None:
            return []
        data = self.api_client.result_json.get("data")
        if data is None:
            return []
        return data

    def _get_reservations_list(self) -> list[dict[str, Any]]:
        """Safely get reservations data from the API response."""
        if self.api_client.reservations_json is None:
            return []
        results = self.api_client.reservations_json.get("results")
        if results is None:
            return []
        return results

    def update_start_of_week_day(self, start_of_week_day: int) -> None:
        """Update the start of week day setting."""
        self.start_of_week_day = start_of_week_day

    @property
    def member_id(self) -> str | None:
        """Return the member ID."""
        return self.api_client._member_id

    @property
    def username(self) -> str:
        """Return the username."""
        return self.api_client.get_username()
