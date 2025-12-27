"""API client for Life Time Fitness."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from http import HTTPStatus
from typing import Any

from aiohttp import ClientConnectionError, ClientError, ClientResponseError, ClientSession
from fake_useragent import UserAgent

from .api_keys import ApiKeyFetchError, ApiKeys, fetch_api_keys
from .const import (
    API_AUTH_API_KEY_HEADER,
    API_AUTH_ENDPOINT,
    API_AUTH_REQUEST_PASSWORD_JSON_KEY,
    API_AUTH_REQUEST_USERNAME_JSON_KEY,
    API_AUTH_SUBSCRIPTION_KEY_HEADER,
    API_CLUB_VISITS_AUTH_HEADER,
    API_CLUB_VISITS_ENDPOINT_DATE_FORMAT,
    API_CLUB_VISITS_ENDPOINT_FORMATSTRING,
    API_PROFILE_ENDPOINT,
    API_RESERVATIONS_DATE_FORMAT,
    API_RESERVATIONS_ENDPOINT,
    API_RESERVATIONS_SSO_HEADER,
    AUTHENTICATION_RESPONSE_MESSAGES,
    AUTHENTICATION_RESPONSE_STATUSES,
    AuthenticationResults,
)
from .model import LifetimeAuthentication

_LOGGER = logging.getLogger(__name__)

USER_AGENT = UserAgent().chrome


def handle_authentication_response_json(
    response_json: dict[str, Any],
) -> LifetimeAuthentication:
    """Handle authentication response JSON and return authentication data.

    Raises appropriate exceptions for various authentication failure scenarios.
    """
    lifetime_authentication = LifetimeAuthentication()
    lifetime_authentication.update_non_empty(response_json)

    message = lifetime_authentication.message
    status = lifetime_authentication.status

    if message == AUTHENTICATION_RESPONSE_MESSAGES[AuthenticationResults.SUCCESS]:
        return lifetime_authentication

    if (
        message
        == AUTHENTICATION_RESPONSE_MESSAGES[AuthenticationResults.PASSWORD_NEEDS_TO_BE_CHANGED]
    ):
        if lifetime_authentication.sso_id is not None:
            _LOGGER.warning("Life Time password needs to be changed, but API can still be used")
            return lifetime_authentication
        raise ApiPasswordNeedsToBeChanged

    if (
        status == AUTHENTICATION_RESPONSE_STATUSES[AuthenticationResults.INVALID]
        or message == AUTHENTICATION_RESPONSE_MESSAGES[AuthenticationResults.INVALID]
    ):
        raise ApiInvalidAuth

    if status == AUTHENTICATION_RESPONSE_STATUSES[AuthenticationResults.TOO_MANY_ATTEMPTS]:
        raise ApiTooManyAuthenticationAttempts

    if status == AUTHENTICATION_RESPONSE_STATUSES[AuthenticationResults.ACTIVATION_REQUIRED]:
        raise ApiActivationRequired

    if status == AUTHENTICATION_RESPONSE_STATUSES[AuthenticationResults.DUPLICATE_EMAIL]:
        raise ApiDuplicateEmail

    _LOGGER.error("Received unknown authentication error in response: %s", response_json)
    raise ApiUnknownAuthError


class Api:
    """API client for Life Time Fitness."""

    def __init__(self, client_session: ClientSession, username: str, password: str) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._client_session = client_session

        self._lifetime_authentication: LifetimeAuthentication | None = None
        self._member_id: str | None = None
        self._api_keys: ApiKeys | None = None

        self.update_successful: bool = True
        self.result_json: dict[str, Any] | None = None
        self.reservations_json: dict[str, Any] | None = None

    def get_username(self) -> str:
        """Return the username."""
        return self._username

    async def _ensure_api_keys(self) -> ApiKeys:
        """Ensure API keys are fetched and cached."""
        if self._api_keys is None:
            try:
                self._api_keys = await fetch_api_keys(self._client_session)
            except ApiKeyFetchError as err:
                _LOGGER.error("Failed to fetch API keys: %s", err)
                raise ApiCannotConnect(f"Failed to fetch API keys: {err}") from err
        return self._api_keys

    async def authenticate(self) -> None:
        """Authenticate with the Life Time Fitness API."""
        try:
            api_keys = await self._ensure_api_keys()

            async with self._client_session.post(
                API_AUTH_ENDPOINT,
                json={
                    API_AUTH_REQUEST_USERNAME_JSON_KEY: self._username,
                    API_AUTH_REQUEST_PASSWORD_JSON_KEY: self._password,
                },
                headers={
                    API_AUTH_SUBSCRIPTION_KEY_HEADER: api_keys.apim_subscription_key,
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                    "Accept": "*/*",
                },
            ) as response:
                response_json = await response.json()
                self._lifetime_authentication = handle_authentication_response_json(response_json)

                await self._fetch_member_id()

        except ClientResponseError as err:
            if err.status == HTTPStatus.UNAUTHORIZED:
                raise ApiInvalidAuth from err
            _LOGGER.error("Received unknown status code in authentication response: %d", err.status)
            raise ApiUnknownAuthError from err
        except ClientConnectionError as err:
            _LOGGER.exception("Connection error while authenticating to Life Time API")
            raise ApiCannotConnect from err

    async def _fetch_member_id(self) -> None:
        """Fetch the member ID from the profile endpoint."""
        if self._lifetime_authentication is None:
            raise ApiAuthRequired("Authentication data is missing")

        access_token = self._lifetime_authentication.access_token
        if access_token is None:
            raise ApiAuthRequired("Access token is missing")

        api_keys = await self._ensure_api_keys()

        try:
            async with self._client_session.get(
                API_PROFILE_ENDPOINT,
                headers={
                    API_AUTH_SUBSCRIPTION_KEY_HEADER: api_keys.apim_subscription_key,
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                    "Accept": "*/*",
                },
            ) as profile_response:
                if profile_response.status == HTTPStatus.UNAUTHORIZED:
                    _LOGGER.error("Unauthorized when fetching profile (status 401)")
                    raise ApiInvalidAuth("Profile request returned unauthorized")

                if not profile_response.ok:
                    _LOGGER.error("Failed to fetch profile, status: %d", profile_response.status)
                    raise ApiProfileError(
                        f"Profile request failed with status {profile_response.status}"
                    )

                try:
                    profile_response_json = await profile_response.json()
                except (ValueError, TypeError) as err:
                    _LOGGER.error("Failed to parse profile response as JSON: %s", err)
                    raise ApiProfileError("Invalid JSON in profile response") from err

                member_details = profile_response_json.get("memberDetails")
                if member_details is None:
                    _LOGGER.error(
                        "Profile response missing memberDetails: %s", profile_response_json
                    )
                    raise ApiProfileError("Profile response missing memberDetails")

                member_id = member_details.get("memberId")
                if member_id is None:
                    _LOGGER.error("Profile response missing memberId: %s", profile_response_json)
                    raise ApiProfileError("Profile response missing memberId")

                self._member_id = member_id

        except ClientConnectionError as err:
            _LOGGER.exception("Connection error while fetching profile")
            raise ApiCannotConnect from err

    async def _get_visits_between_dates(self, start_date: date, end_date: date) -> dict[str, Any]:
        """Get visit data between two dates."""
        if self._lifetime_authentication is None or self._lifetime_authentication.sso_id is None:
            raise ApiAuthRequired

        api_keys = await self._ensure_api_keys()

        try:
            async with self._client_session.get(
                API_CLUB_VISITS_ENDPOINT_FORMATSTRING.format(
                    member_id=self._member_id,
                    start_date=start_date.strftime(API_CLUB_VISITS_ENDPOINT_DATE_FORMAT),
                    end_date=end_date.strftime(API_CLUB_VISITS_ENDPOINT_DATE_FORMAT),
                ),
                headers={
                    API_CLUB_VISITS_AUTH_HEADER: self._lifetime_authentication.sso_id,
                    API_AUTH_SUBSCRIPTION_KEY_HEADER: api_keys.apim_subscription_key,
                    API_AUTH_API_KEY_HEADER: api_keys.my_account_api_key,
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                    "Accept": "*/*",
                },
            ) as response:
                return await response.json()
        except ClientResponseError as err:
            if err.status == HTTPStatus.UNAUTHORIZED:
                raise ApiAuthExpired from err
            raise
        except ClientConnectionError as err:
            _LOGGER.exception("Connection error while updating from Life Time API")
            raise ApiCannotConnect from err

    async def update(self) -> None:
        """Update all data from the API."""
        await self.update_visits()
        await self.update_reservations()

    async def update_visits(self) -> None:
        """Fetch the latest visit data."""
        today = date.today()
        first_day_of_the_year = date(today.year, 1, 1)
        try:
            try:
                self.result_json = await self._get_visits_between_dates(
                    first_day_of_the_year, today
                )
            except ApiAuthExpired:
                await self.authenticate()
                self.result_json = await self._get_visits_between_dates(
                    first_day_of_the_year, today
                )
            # Update succeeded - clear any previous failure state
            self.update_successful = True
        except (ApiCannotConnect, ApiAuthRequired) as err:
            self.update_successful = False
            _LOGGER.error("API error during Life Time update: %s", err)
            raise
        except ClientError:
            self.update_successful = False
            _LOGGER.exception("Unexpected client error during Life Time API update")
            raise
        except Exception:
            self.update_successful = False
            _LOGGER.exception("Unexpected exception during Life Time API update")
            raise

    async def _get_reservations(self, start_date: date, end_date: date) -> dict[str, Any]:
        """Get reservation data between two dates."""
        if self._lifetime_authentication is None or self._lifetime_authentication.sso_id is None:
            raise ApiAuthRequired

        api_keys = await self._ensure_api_keys()

        try:
            async with self._client_session.get(
                API_RESERVATIONS_ENDPOINT,
                params={
                    "memberIds": self._member_id,
                    "start": start_date.strftime(API_RESERVATIONS_DATE_FORMAT),
                    "end": end_date.strftime(API_RESERVATIONS_DATE_FORMAT),
                    "groupCamps": "true",
                    "pageSize": "0",
                },
                headers={
                    API_AUTH_SUBSCRIPTION_KEY_HEADER: api_keys.apim_subscription_key,
                    API_RESERVATIONS_SSO_HEADER: self._lifetime_authentication.sso_id,
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
            ) as response:
                if response.status == HTTPStatus.UNAUTHORIZED:
                    raise ApiAuthExpired
                return await response.json()
        except ClientResponseError as err:
            if err.status == HTTPStatus.UNAUTHORIZED:
                raise ApiAuthExpired from err
            raise
        except ClientConnectionError as err:
            _LOGGER.exception("Connection error while fetching reservations")
            raise ApiCannotConnect from err

    async def update_reservations(self) -> None:
        """Fetch upcoming reservations."""
        today = date.today()
        # Fetch reservations for the next 30 days
        end_date = today + timedelta(days=30)
        try:
            try:
                self.reservations_json = await self._get_reservations(today, end_date)
            except ApiAuthExpired:
                await self.authenticate()
                self.reservations_json = await self._get_reservations(today, end_date)
        except (ApiCannotConnect, ApiAuthRequired) as err:
            _LOGGER.error("API error during reservations update: %s", err)
            raise
        except ClientError:
            _LOGGER.exception("Unexpected client error during reservations update")
            raise


class ApiCannotConnect(Exception):
    """Client can't connect to API server"""


class ApiPasswordNeedsToBeChanged(Exception):
    """Password needs to be changed"""


class ApiTooManyAuthenticationAttempts(Exception):
    """There were too many authentication attempts"""


class ApiActivationRequired(Exception):
    """Account activation required"""


class ApiDuplicateEmail(Exception):
    """There are multiple accounts associated with this email"""


class ApiInvalidAuth(Exception):
    """API server returned invalid auth"""


class ApiUnknownAuthError(Exception):
    """API server returned unknown error"""


class ApiAuthRequired(Exception):
    """This API call requires authenticating beforehand"""


class ApiAuthExpired(Exception):
    """Authentication has expired."""


class ApiProfileError(Exception):
    """Error fetching or parsing profile data."""
