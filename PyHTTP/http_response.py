from .constants import *
from .utils import parse_cookie


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
        self._cookies_str = []
        if response:
            self._parse_response()
            self.initialize_cookies()

    def initialize_cookies(self):
        if self._cookies_str:
            for cookie in self._cookies_str:
                parsed_cookie = parse_cookie(cookie)
                self.cookies[parsed_cookie["name"]] = parsed_cookie

    def parse_response_headers(self, http_headers: str):
        response_header_lines = http_headers.split(INDENT)
        http_version, status_code, *_ = response_header_lines[0].split()

        self.http_version = http_version
        self.status_code = int(status_code)

        for line in response_header_lines[1:]:
            header, value = line.split(": ", 1)
            if header == HTTPHeaders.SET_COOKIE:
                self._cookies_str.append("".join(value))
                continue

            self.headers[header] = value

    def _parse_response(self):
        splited_response = self.response.split(DOUBLE_INDENT)
        response_headers = splited_response[0]

        response_body = None
        if len(splited_response) > 1:
            response_body = splited_response[1]

        self.body = response_body
        self.parse_response_headers(response_headers)

    def __bool__(self):
        return self.status_code == HTTPStatusCodes.OK
