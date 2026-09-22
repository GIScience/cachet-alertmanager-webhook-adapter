import logging
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth
from requests.sessions import HTTPAdapter
from urllib3 import Retry

log = logging.getLogger(__name__)


class HttpConnection:
    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        max_retries: int = 5,
    ):
        self.base_url = base_url
        self.session = requests.Session()

        self.configure_session(max_retries=max_retries, token=token, username=username, password=password)

    def configure_session(
        self, max_retries: int, token: Optional[str], username: Optional[str], password: Optional[str]
    ):
        self.session.headers.update(
            {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
        )

        self.set_auth(token=token, username=username, password=password)

        retries = Retry(total=max_retries, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])

        # We have to mount http:// to overwrite the default adapters
        # noinspection HttpUrlsUsage
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

        self.session.hooks['response'].append(self._log_error_response)

    @staticmethod
    def _log_error_response(response: requests.Response, **_kwargs):
        if not response.ok:
            log.error(f'{response.request.method} {response.url} returned {response.status_code}: {response.text}')

    def set_auth(self, token: Optional[str], username: Optional[str], password: Optional[str]):
        if token is not None:
            self.session.headers.update({'Authorization': f'Bearer {token}'})

        if username is not None and password is not None:
            basic = HTTPBasicAuth(username=username, password=password.encode())
            self.session.auth = basic
