from .constants import *
from .utils import parse_cookie, parse_headers


class HTTPResponse:
    def __init__(self, response: str | None = None, hand_init: bool = False):
        if not hand_init and not response:
            raise ValueError("Response is required when hand initialization is disabled")

        self.response = response
        self.http_version: str | None = None
        self.status_code: int | None = None
        self.headers = {}
        self.body: str | None = None
        self.cookies = {}
        if response:
            self._parse_response()
            self.initialize_cookies()

    def initialize_cookies(self):
        cookies_lst = self.headers.get(HTTPHeaders.SET_COOKIE)
        if cookies_lst:
            for cookie in cookies_lst:
                parsed_cookie = parse_cookie(cookie)
                self.cookies[parsed_cookie["name"]] = parsed_cookie

    def initialize_headers(self, http_headers: str):
        parsed_headers = parse_headers(http_headers)

        self.http_version = parsed_headers["http_version"]
        self.status_code = parsed_headers["status_code"]
        self.headers = parsed_headers["headers"]

    def _parse_response(self):
        split_response = self.response.split(DOUBLE_INDENT)
        response_headers = split_response[0]

        response_body = None
        if len(split_response) > 1:
            response_body = split_response[1]

        self.body = response_body
        self.initialize_headers(response_headers)

    def __bool__(self):
        return self.status_code == HTTPStatusCodes.OK
