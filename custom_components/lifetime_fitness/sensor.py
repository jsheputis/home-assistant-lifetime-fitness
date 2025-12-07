"""Sensor platform for Life Time Fitness integration."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Api
from .const import (
    DOMAIN,
    VISITS_SENSOR_UNIT_OF_MEASUREMENT,
    VISITS_SENSOR_ID_SUFFIX,
    VISITS_SENSOR_NAME_SUFFIX,
    CONF_START_OF_WEEK_DAY,
    CONF_DEFAULT_START_OF_WEEK_DAY,
    API_CLUB_VISITS_TIMESTAMP_JSON_KEY,
    VISITS_SENSOR_ATTR_VISITS_THIS_YEAR,
    VISITS_SENSOR_ATTR_VISITS_THIS_MONTH,
    VISITS_SENSOR_ATTR_VISITS_THIS_WEEK,
    VISITS_SENSOR_ATTR_LAST_VISIT_TIMESTAMP,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Life Time Fitness sensor platform."""
    api_client: Api = hass.data[DOMAIN][config_entry.entry_id]
    await api_client.authenticate()

    start_of_week_day = config_entry.options.get(
        CONF_START_OF_WEEK_DAY, CONF_DEFAULT_START_OF_WEEK_DAY
    )
    async_add_entities([VisitsSensor(api_client, start_of_week_day)], True)


class VisitsSensor(Entity):
    """Sensor entity for Life Time Fitness visit tracking."""

    should_poll = True

    def __init__(self, api_client: Api, start_of_week_day: int) -> None:
        """Initialize the visits sensor."""
        self._api_client = api_client
        self._name = f"{api_client.get_username()}{VISITS_SENSOR_NAME_SUFFIX}"
        self._unique_id = f"{api_client.get_username()}{VISITS_SENSOR_ID_SUFFIX}"
        self._start_of_week_day = start_of_week_day
        self._attr_extra_state_attributes: dict[str, Any] = {}

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if the sensor is available."""
        return self._api_client.update_successful

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return VISITS_SENSOR_UNIT_OF_MEASUREMENT

    def _get_visits_data(self) -> list[dict[str, Any]]:
        """Safely get visits data from the API response."""
        if self._api_client.result_json is None:
            return []
        data = self._api_client.result_json.get("data")
        if data is None:
            return []
        return data

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        await self._api_client.update()

        visits = self._get_visits_data()
        if not visits:
            self._attr_extra_state_attributes = {
                VISITS_SENSOR_ATTR_VISITS_THIS_YEAR: 0,
                VISITS_SENSOR_ATTR_VISITS_THIS_MONTH: 0,
                VISITS_SENSOR_ATTR_VISITS_THIS_WEEK: 0,
                VISITS_SENSOR_ATTR_LAST_VISIT_TIMESTAMP: None,
            }
            return

        today = date.today()
        beginning_of_week_offset = (today.weekday() - self._start_of_week_day) % 7
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

        self._attr_extra_state_attributes = {
            VISITS_SENSOR_ATTR_VISITS_THIS_YEAR: visits_this_year,
            VISITS_SENSOR_ATTR_VISITS_THIS_MONTH: visits_this_month,
            VISITS_SENSOR_ATTR_VISITS_THIS_WEEK: visits_this_week,
            VISITS_SENSOR_ATTR_LAST_VISIT_TIMESTAMP: last_visit_timestamp,
        }

    @property
    def state(self) -> int:
        """Return the state of the sensor (total visits)."""
        return len(self._get_visits_data())
