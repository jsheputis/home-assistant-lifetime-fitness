"""Pytest configuration and fixtures for Life Time Fitness tests."""
from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

from homeassistant.core import HomeAssistant

from custom_components.lifetime_fitness.api import Api
from custom_components.lifetime_fitness.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)
from custom_components.lifetime_fitness.coordinator import (
    LifetimeFitnessCoordinator,
    LifetimeFitnessData,
)

pytest_plugins = "pytest_homeassistant_custom_component"


# Test credentials
TEST_USERNAME = "testuser@example.com"
TEST_PASSWORD = "testpassword123"
TEST_ENTRY_ID = "test_entry_id_12345"


# Sample API responses
MOCK_AUTH_RESPONSE_SUCCESS = {
    "message": "Success",
    "status": "0",
    "token": "mock_access_token_12345",
    "ssoId": "mock_sso_id_67890",
    "partyId": "mock_party_id_11111",
}

MOCK_AUTH_RESPONSE_INVALID = {
    "message": "Invalid username or password",
    "status": "-201",
}

MOCK_AUTH_RESPONSE_TOO_MANY_ATTEMPTS = {
    "message": "Too many attempts",
    "status": "-207",
}

MOCK_AUTH_RESPONSE_ACTIVATION_REQUIRED = {
    "message": "Activation required",
    "status": "-208",
}

MOCK_AUTH_RESPONSE_DUPLICATE_EMAIL = {
    "message": "Duplicate email",
    "status": "-209",
}

MOCK_AUTH_RESPONSE_PASSWORD_CHANGE = {
    "message": "Password needs to be changed.",
    "status": "0",
    "ssoId": None,
}

MOCK_PROFILE_RESPONSE = {
    "memberDetails": {
        "memberId": "12345678",
        "firstName": "Test",
        "lastName": "User",
    }
}

MOCK_VISITS_RESPONSE_EMPTY: dict[str, Any] = {
    "data": [],
}

MOCK_VISITS_RESPONSE_WITH_DATA: dict[str, Any] = {
    "data": [
        {"usageDateTime": 1701388800000},  # Dec 1, 2023
        {"usageDateTime": 1701475200000},  # Dec 2, 2023
        {"usageDateTime": 1701561600000},  # Dec 3, 2023
    ],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> Generator[None]:
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_config_entry_data() -> dict[str, Any]:
    """Return mock config entry data."""
    return {
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }


@pytest.fixture
def mock_client_session() -> MagicMock:
    """Return a mock aiohttp ClientSession."""
    return MagicMock(spec=ClientSession)


@pytest.fixture
def mock_api(mock_client_session: MagicMock) -> Api:
    """Return a mock API client."""
    return Api(mock_client_session, TEST_USERNAME, TEST_PASSWORD)


@pytest.fixture
def mock_api_authenticated(mock_api: Api) -> Api:
    """Return a mock API client that appears authenticated."""
    mock_api._lifetime_authentication = MagicMock()
    mock_api._lifetime_authentication.sso_id = "mock_sso_id"
    mock_api._lifetime_authentication.access_token = "mock_token"
    mock_api._member_id = "12345678"
    mock_api.result_json = MOCK_VISITS_RESPONSE_WITH_DATA.copy()
    mock_api.update_successful = True
    return mock_api


@pytest.fixture
def mock_coordinator_data() -> LifetimeFitnessData:
    """Return mock coordinator data."""
    return LifetimeFitnessData(
        total_visits=10,
        visits_this_year=8,
        visits_this_month=3,
        visits_this_week=2,
        last_visit_timestamp=1701561600.0,
        raw_visits=[
            {"usageDateTime": 1701388800000},
            {"usageDateTime": 1701475200000},
            {"usageDateTime": 1701561600000},
        ],
    )


@pytest.fixture
def mock_coordinator(
    hass: HomeAssistant,
    mock_api_authenticated: Api,
    mock_coordinator_data: LifetimeFitnessData,
) -> LifetimeFitnessCoordinator:
    """Return a mock coordinator with data."""
    coordinator = LifetimeFitnessCoordinator(
        hass,
        mock_api_authenticated,
        start_of_week_day=0,
    )
    coordinator.data = mock_coordinator_data
    coordinator.last_update_success = True
    return coordinator
