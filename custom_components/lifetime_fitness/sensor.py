from datetime import date, timedelta

from homeassistant.helpers.entity import Entity

from .api import Api
from .const import (
    DOMAIN,
    UNIT_OF_MEASUREMENT,
    VISITS_SENSOR_ID_SUFFIX,
    VISITS_SENSOR_NAME_SUFFIX,
    CONF_START_OF_WEEK_DAY,
    DEFAULT_START_OF_WEEK_DAY,
    API_CLUB_VISITS_TIMESTAMP_JSON_KEY,
    ATTR_VISITS_THIS_YEAR,
    ATTR_VISITS_THIS_MONTH,
    ATTR_VISITS_THIS_WEEK,
    ATTR_LAST_VISIT_TIMESTAMP,
)

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(hass, config_entry, async_add_devices):
    api_client = hass.data[DOMAIN][config_entry.entry_id]
    await api_client.authenticate()

    new_devices = [VisitsSensor(
        api_client,
        config_entry.options.get(CONF_START_OF_WEEK_DAY, DEFAULT_START_OF_WEEK_DAY),
    )]

    async_add_devices(new_devices, True)


class VisitsSensor(Entity):
    should_poll = True

    def __init__(self, api_client: Api, start_of_week_day: int):
        self._api_client = api_client
        self._name = f"{api_client.get_username()}{VISITS_SENSOR_NAME_SUFFIX}"
        self._unique_id = f"{api_client.get_username()}{VISITS_SENSOR_ID_SUFFIX}"
        self._start_of_week_day = start_of_week_day
        self._attr_extra_state_attributes = {}

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def available(self):
        return self._api_client.update_successful

    @property
    def unit_of_measurement(self):
        return UNIT_OF_MEASUREMENT

    async def async_update(self):
        await self._api_client.update()
        today = date.today()
        beginning_of_week_offset = (today.weekday() - self._start_of_week_day) % 7
        beginning_of_week_date = today - timedelta(days=beginning_of_week_offset)
        last_visit_timestamp = None
        visits_this_year = 0
        visits_this_month = 0
        visits_this_week = 0
        # TODO: Handle empty result more gracefully
        for visit in self._api_client.result_json['data']:
            # Convert milliseconds to seconds timestamp
            visit_timestamp = visit[API_CLUB_VISITS_TIMESTAMP_JSON_KEY] / 1000
            visit_date = date.fromtimestamp(visit_timestamp)
            if visit_date.year == today.year:
                visits_this_year += 1
                if visit_date.month == today.month:
                    visits_this_month += 1
            if visit_date >= beginning_of_week_date:
                visits_this_week += 1
            if last_visit_timestamp is None or visit_timestamp > last_visit_timestamp:
                last_visit_timestamp = visit_timestamp
        self._attr_extra_state_attributes = {
            ATTR_VISITS_THIS_YEAR: visits_this_year,
            ATTR_VISITS_THIS_MONTH: visits_this_month,
            ATTR_VISITS_THIS_WEEK: visits_this_week,
            ATTR_LAST_VISIT_TIMESTAMP: last_visit_timestamp,
        }

    @property
    def state(self):
        if self._api_client.result_json is None or self._api_client.result_json['data'] is None:
            return -1
        return len(self._api_client.result_json['data'])
