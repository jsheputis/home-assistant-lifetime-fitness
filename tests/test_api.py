"""Tests for the Life Time Fitness API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientConnectionError

from custom_components.lifetime_fitness.api import (
    Api,
    ApiActivationRequired,
    ApiAuthRequired,
    ApiCannotConnect,
    ApiDuplicateEmail,
    ApiInvalidAuth,
    ApiPasswordNeedsToBeChanged,
    ApiTooManyAuthenticationAttempts,
    ApiUnknownAuthError,
    handle_authentication_response_json,
)
from custom_components.lifetime_fitness.model import LifetimeAuthentication

from .conftest import (
    MOCK_AUTH_RESPONSE_ACTIVATION_REQUIRED,
    MOCK_AUTH_RESPONSE_DUPLICATE_EMAIL,
    MOCK_AUTH_RESPONSE_INVALID,
    MOCK_AUTH_RESPONSE_PASSWORD_CHANGE,
    MOCK_AUTH_RESPONSE_SUCCESS,
    MOCK_AUTH_RESPONSE_TOO_MANY_ATTEMPTS,
    MOCK_PROFILE_RESPONSE,
    MOCK_VISITS_RESPONSE_EMPTY,
    MOCK_VISITS_RESPONSE_WITH_DATA,
    TEST_PASSWORD,
    TEST_USERNAME,
)


class TestHandleAuthenticationResponseJson:
    """Tests for handle_authentication_response_json function."""

    def test_success(self) -> None:
        """Test successful authentication response."""
        result = handle_authentication_response_json(MOCK_AUTH_RESPONSE_SUCCESS)
        assert isinstance(result, LifetimeAuthentication)
        assert result.access_token == "mock_access_token_12345"
        assert result.sso_id == "mock_sso_id_67890"

    def test_invalid_credentials(self) -> None:
        """Test invalid credentials response."""
        with pytest.raises(ApiInvalidAuth):
            handle_authentication_response_json(MOCK_AUTH_RESPONSE_INVALID)

    def test_too_many_attempts(self) -> None:
        """Test too many authentication attempts response."""
        with pytest.raises(ApiTooManyAuthenticationAttempts):
            handle_authentication_response_json(MOCK_AUTH_RESPONSE_TOO_MANY_ATTEMPTS)

    def test_activation_required(self) -> None:
        """Test activation required response."""
        with pytest.raises(ApiActivationRequired):
            handle_authentication_response_json(MOCK_AUTH_RESPONSE_ACTIVATION_REQUIRED)

    def test_duplicate_email(self) -> None:
        """Test duplicate email response."""
        with pytest.raises(ApiDuplicateEmail):
            handle_authentication_response_json(MOCK_AUTH_RESPONSE_DUPLICATE_EMAIL)

    def test_password_change_required_no_sso(self) -> None:
        """Test password change required without SSO ID."""
        with pytest.raises(ApiPasswordNeedsToBeChanged):
            handle_authentication_response_json(MOCK_AUTH_RESPONSE_PASSWORD_CHANGE)

    def test_password_change_required_with_sso(self) -> None:
        """Test password change required but SSO ID present (can still use API)."""
        response = {
            "message": "Password needs to be changed.",
            "status": "0",
            "ssoId": "valid_sso_id",
            "token": "valid_token",
        }
        result = handle_authentication_response_json(response)
        assert result.sso_id == "valid_sso_id"

    def test_unknown_error(self) -> None:
        """Test unknown error response."""
        with pytest.raises(ApiUnknownAuthError):
            handle_authentication_response_json({"message": "Unknown error", "status": "-999"})


class TestApiClient:
    """Tests for the Api class."""

    def test_init(self, mock_client_session: MagicMock) -> None:
        """Test API client initialization."""
        api = Api(mock_client_session, TEST_USERNAME, TEST_PASSWORD)
        assert api.get_username() == TEST_USERNAME
        assert api.update_successful is True
        assert api.result_json is None

    async def test_authenticate_success(self, mock_client_session: MagicMock) -> None:
        """Test successful authentication."""
        api = Api(mock_client_session, TEST_USERNAME, TEST_PASSWORD)

        mock_auth_response = AsyncMock()
        mock_auth_response.json = AsyncMock(return_value=MOCK_AUTH_RESPONSE_SUCCESS)

        mock_profile_response = AsyncMock()
        mock_profile_response.json = AsyncMock(return_value=MOCK_PROFILE_RESPONSE)

        mock_client_session.post = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_auth_response))
        )
        mock_client_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_profile_response))
        )

        await api.authenticate()

        assert api._lifetime_authentication is not None
        assert api._member_id == "12345678"

    async def test_authenticate_invalid_auth(self, mock_client_session: MagicMock) -> None:
        """Test authentication with invalid credentials."""
        api = Api(mock_client_session, TEST_USERNAME, TEST_PASSWORD)

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=MOCK_AUTH_RESPONSE_INVALID)

        mock_client_session.post = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with pytest.raises(ApiInvalidAuth):
            await api.authenticate()

    async def test_authenticate_connection_error(self, mock_client_session: MagicMock) -> None:
        """Test authentication with connection error."""
        api = Api(mock_client_session, TEST_USERNAME, TEST_PASSWORD)

        mock_client_session.post = MagicMock(side_effect=ClientConnectionError())

        with pytest.raises(ApiCannotConnect):
            await api.authenticate()

    async def test_get_visits_without_auth(self, mock_api: Api) -> None:
        """Test getting visits without authentication."""
        mock_api._lifetime_authentication = MagicMock()
        mock_api._lifetime_authentication.sso_id = None

        with pytest.raises(ApiAuthRequired):
            await mock_api._get_visits_between_dates(start_date=MagicMock(), end_date=MagicMock())

    async def test_update_visits_success(self, mock_api_authenticated: Api) -> None:
        """Test successful visits update."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=MOCK_VISITS_RESPONSE_WITH_DATA)

        mock_api_authenticated._client_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        await mock_api_authenticated.update_visits()

        assert mock_api_authenticated.result_json == MOCK_VISITS_RESPONSE_WITH_DATA

    async def test_update_visits_empty(self, mock_api_authenticated: Api) -> None:
        """Test visits update with empty response."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=MOCK_VISITS_RESPONSE_EMPTY)

        mock_api_authenticated._client_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        await mock_api_authenticated.update_visits()

        assert mock_api_authenticated.result_json == MOCK_VISITS_RESPONSE_EMPTY
        assert mock_api_authenticated.result_json["data"] == []
