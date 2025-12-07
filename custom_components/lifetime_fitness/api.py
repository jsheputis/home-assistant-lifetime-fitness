"""API client for Life Time Fitness."""
from __future__ import annotations

import logging
from datetime import date
from http import HTTPStatus
from typing import Any

from aiohttp import ClientConnectionError, ClientError, ClientResponseError, ClientSession
from fake_useragent import UserAgent

from .const import (
    API_AUTH_API_KEY_HEADER,
    API_AUTH_ENDPOINT,
    API_AUTH_LT_MY_ACCOUNT_KEY_HEADER_VALUE,
    API_AUTH_REQUEST_PASSWORD_JSON_KEY,
    API_AUTH_REQUEST_USERNAME_JSON_KEY,
    API_AUTH_SUBSCRIPTION_KEY_HEADER,
    API_AUTH_SUBSCRIPTION_KEY_HEADER_VALUE,
    API_CLUB_VISITS_AUTH_HEADER,
    API_CLUB_VISITS_ENDPOINT_DATE_FORMAT,
    API_CLUB_VISITS_ENDPOINT_FORMATSTRING,
    API_PROFILE_ENDPOINT,
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

    if message == AUTHENTICATION_RESPONSE_MESSAGES[AuthenticationResults.PASSWORD_NEEDS_TO_BE_CHANGED]:
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

        self.update_successful: bool = True
        self.result_json: dict[str, Any] | None = None

    def get_username(self) -> str:
        """Return the username."""
        return self._username

    async def authenticate(self) -> None:
        """Authenticate with the Life Time Fitness API."""
        try:
            async with self._client_session.post(
                API_AUTH_ENDPOINT,
                json={
                    API_AUTH_REQUEST_USERNAME_JSON_KEY: self._username,
                    API_AUTH_REQUEST_PASSWORD_JSON_KEY: self._password,
                },
                headers={
                    API_AUTH_SUBSCRIPTION_KEY_HEADER: API_AUTH_SUBSCRIPTION_KEY_HEADER_VALUE,
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
            _LOGGER.error(
                "Received unknown status code in authentication response: %d", err.status
            )
            raise ApiUnknownAuthError from err
        except ClientConnectionError as err:
            _LOGGER.exception("Connection error while authenticating to Life Time API")
            raise ApiCannotConnect from err

    async def _fetch_member_id(self) -> None:
        """Fetch the member ID from the profile endpoint."""
        if self._lifetime_authentication is None:
            raise ApiAuthRequired

        async with self._client_session.get(
            API_PROFILE_ENDPOINT,
            headers={
                API_AUTH_SUBSCRIPTION_KEY_HEADER: API_AUTH_SUBSCRIPTION_KEY_HEADER_VALUE,
                "Authorization": self._lifetime_authentication.access_token,
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
            },
        ) as profile_response:
            profile_response_json = await profile_response.json()
            self._member_id = profile_response_json["memberDetails"]["memberId"]

    async def _get_visits_between_dates(
        self, start_date: date, end_date: date
    ) -> dict[str, Any]:
        """Get visit data between two dates."""
        if self._lifetime_authentication is None or self._lifetime_authentication.sso_id is None:
            raise ApiAuthRequired

        try:
            async with self._client_session.get(
                API_CLUB_VISITS_ENDPOINT_FORMATSTRING.format(
                    member_id=self._member_id,
                    start_date=start_date.strftime(API_CLUB_VISITS_ENDPOINT_DATE_FORMAT),
                    end_date=end_date.strftime(API_CLUB_VISITS_ENDPOINT_DATE_FORMAT),
                ),
                headers={
                    API_CLUB_VISITS_AUTH_HEADER: self._lifetime_authentication.sso_id,
                    API_AUTH_SUBSCRIPTION_KEY_HEADER: API_AUTH_SUBSCRIPTION_KEY_HEADER_VALUE,
                    API_AUTH_API_KEY_HEADER: API_AUTH_LT_MY_ACCOUNT_KEY_HEADER_VALUE,
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
        except ClientError:
            self.update_successful = False
            _LOGGER.exception("Unexpected exception during Life Time API update")


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
    """Authentication has expired"""
