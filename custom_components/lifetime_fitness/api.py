"""API client for Life Time Fitness"""
from aiohttp import ClientSession, ClientError, ClientResponseError, ClientConnectionError
from datetime import date
from http import HTTPStatus
import logging

from .const import (
    API_AUTH_ENDPOINT,
    API_AUTH_REQUEST_USERNAME_JSON_KEY,
    API_AUTH_REQUEST_PASSWORD_JSON_KEY,
    API_AUTH_REQUEST_SUBSCRIPTION_KEY_HEADER,
    API_AUTH_REQUEST_SUBSCRIPTION_KEY_HEADER_VALUE,
    API_AUTH_TOKEN_JSON_KEY,
    API_AUTH_ACCESS_TOKEN_KEY,
    API_AUTH_API_KEY_HEADER,
    API_AUTH_REQUEST_LT_MY_ACCOUNT_KEY_HEADER_VALUE,
    API_AUTH_MESSAGE_JSON_KEY,
    API_AUTH_STATUS_JSON_KEY,
    API_CLUB_VISITS_ENDPOINT_FORMATSTRING,
    API_CLUB_VISITS_ENDPOINT_DATE_FORMAT,
    API_PROFILE_ENDPOINT,
    API_CLUB_VISITS_AUTH_HEADER,
    AuthenticationResults,
    AUTHENTICATION_RESPONSE_MESSAGES,
    AUTHENTICATION_RESPONSE_STATUSES
)

_LOGGER = logging.getLogger(__name__)


def handle_authentication_response_json(response_json: dict):
    # Based on https://my.lifetime.life/components/login/index.js
    message = response_json.get(API_AUTH_MESSAGE_JSON_KEY)
    status = response_json.get(API_AUTH_STATUS_JSON_KEY)
    if message == AUTHENTICATION_RESPONSE_MESSAGES[AuthenticationResults.SUCCESS]:
        return (response_json[API_AUTH_TOKEN_JSON_KEY], response_json[API_AUTH_ACCESS_TOKEN_KEY])
    elif message == AUTHENTICATION_RESPONSE_MESSAGES[AuthenticationResults.PASSWORD_NEEDS_TO_BE_CHANGED]:
        if API_AUTH_TOKEN_JSON_KEY in response_json:
            _LOGGER.warning("Life Time password needs to be changed, but API can still be used")
            return (response_json[API_AUTH_TOKEN_JSON_KEY], response_json[API_AUTH_ACCESS_TOKEN_KEY])
        else:
            raise ApiPasswordNeedsToBeChanged
    elif (
            status == AUTHENTICATION_RESPONSE_STATUSES[AuthenticationResults.INVALID] or
            message == AUTHENTICATION_RESPONSE_MESSAGES[AuthenticationResults.INVALID]
    ):
        raise ApiInvalidAuth
    elif status == AUTHENTICATION_RESPONSE_STATUSES[AuthenticationResults.TOO_MANY_ATTEMPTS]:
        raise ApiTooManyAuthenticationAttempts
    elif status == AUTHENTICATION_RESPONSE_STATUSES[AuthenticationResults.ACTIVATION_REQUIRED]:
        raise ApiActivationRequired
    elif status == AUTHENTICATION_RESPONSE_STATUSES[AuthenticationResults.DUPLICATE_EMAIL]:
        raise ApiDuplicateEmail
    _LOGGER.error("Received unknown authentication error in response: %s", response_json)
    raise ApiUnknownAuthError


class Api:
    def __init__(self, client_session: ClientSession, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._client_session = client_session
        self._sso_token = None
        self._access_token = None
        self._member_id = None

        self.update_successful = True
        self.result_json = None

    def get_username(self):
        return self._username

    async def authenticate(self):
        try:
            async with self._client_session.post(
                API_AUTH_ENDPOINT,
                json={
                    API_AUTH_REQUEST_USERNAME_JSON_KEY: self._username,
                    API_AUTH_REQUEST_PASSWORD_JSON_KEY: self._password,
                },
                headers={
                    API_AUTH_REQUEST_SUBSCRIPTION_KEY_HEADER: API_AUTH_REQUEST_SUBSCRIPTION_KEY_HEADER_VALUE,
                    'Content-Type': 'application/json',
                    'User-Agent': 'PostmanRuntime/7.43.3', # Temp fix 
                    'Accept': '*/*',
                },
            ) as response:
                response_json = await response.json()
                auth_data = handle_authentication_response_json(response_json)
                self._sso_token = auth_data[0]
                self._access_token = auth_data[1]
                
                # Get member ID... todo move to separate func
                async with self._client_session.get(
                    API_PROFILE_ENDPOINT,
                    headers={
                        API_AUTH_REQUEST_SUBSCRIPTION_KEY_HEADER: API_AUTH_REQUEST_SUBSCRIPTION_KEY_HEADER_VALUE,
                        'Authorization': self._access_token,
                        'Content-Type': 'application/json',
                        'User-Agent': 'PostmanRuntime/7.43.3', # Temp fix 
                        'Accept': '*/*',
                    },
                ) as profile_response:
                    profile_response_json = await profile_response.json()
                    self._member_id = profile_response_json['memberDetails']['memberId']
                    
        except ClientResponseError as err:
            if err.status == HTTPStatus.UNAUTHORIZED:
                raise ApiInvalidAuth
            _LOGGER.error("Received unknown status code in authentication response: %d", err.status)
            raise ApiUnknownAuthError
        except ClientConnectionError:
            _LOGGER.exception("Connection error while authenticating to Life Time API")
            raise ApiCannotConnect

    async def _get_visits_between_dates(self, start_date: date, end_date: date):
        if self._sso_token is None:
            raise ApiAuthRequired

        try:
            async with self._client_session.get(
                API_CLUB_VISITS_ENDPOINT_FORMATSTRING.format(
                    member_id=self._member_id,
                    start_date=start_date.strftime(API_CLUB_VISITS_ENDPOINT_DATE_FORMAT),
                    end_date=end_date.strftime(API_CLUB_VISITS_ENDPOINT_DATE_FORMAT),
                ),
                headers={
                    API_CLUB_VISITS_AUTH_HEADER: self._sso_token,
                    API_AUTH_REQUEST_SUBSCRIPTION_KEY_HEADER: API_AUTH_REQUEST_SUBSCRIPTION_KEY_HEADER_VALUE,
                    API_AUTH_API_KEY_HEADER: API_AUTH_REQUEST_LT_MY_ACCOUNT_KEY_HEADER_VALUE,
                    'Content-Type': 'application/json',
                    'User-Agent': 'PostmanRuntime/7.43.3', # Temp fix 
                    'Accept': '*/*',
                },
            ) as response:
                response_json = await response.json()
                return response_json
        except ClientResponseError as err:
            if err.status == HTTPStatus.UNAUTHORIZED:
                raise ApiAuthExpired
            raise err
        except ClientConnectionError:
            _LOGGER.exception("Connection error while updating from Life Time API")
            raise ApiCannotConnect

    async def update(self):
        await self.update_visits()
            
    async def update_visits(self):
        today = date.today()
        first_day_of_the_year = date(today.year, 1, 1)
        try:
            try:
                self.result_json = await self._get_visits_between_dates(first_day_of_the_year, today)
            except ApiAuthExpired:
                await self.authenticate()
                # Try again after authenticating
                self.result_json = await self._get_visits_between_dates(first_day_of_the_year, today)
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


# Test the API client by running this script with username and password:
async def main():
    import sys, aiohttp
    username, password = sys.argv[1:]
    async with aiohttp.ClientSession() as client_session:
        api = Api(client_session, username, password)
        await api.authenticate()
        await api.update()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
