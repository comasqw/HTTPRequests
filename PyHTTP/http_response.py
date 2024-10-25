from .constants import *
from .utils import parse_cookie


class HTTPResponse:
    def __init__(self, response: str):
        self.response = response
        self.http_version: str | None = None
        self.status_code: int | None = None
        self.headers = {}
        self.body: str | None = None
        self.cookies = {}
        self._cookies_str = []
        self._parse_response()
        self._initialize_cookies()

    def _initialize_cookies(self):
        if self._cookies_str:
            for cookie in self._cookies_str:
                parsed_cookie = parse_cookie(cookie)
                self.cookies[parsed_cookie["name"]] = parsed_cookie

    def _parse_response(self):
        splited_response = self.response.split(DOUBLE_INDENT)
        response_header = splited_response[0]

        response_body = None
        if len(splited_response) >= 2:
            response_body = splited_response[1]

        self.body = response_body

        response_header_lines = response_header.split(INDENT)
        http_version, status_code, *_ = response_header_lines[0].split()

        self.http_version = http_version
        self.status_code = int(status_code)

        for line in response_header_lines[1:]:
            header, value = line.split(": ", 1)
            if header == HTTPHeaders.SET_COOKIE:
                self._cookies_str.append("".join(value))
                continue

            self.headers[header] = value

    def __bool__(self):
        return self.status_code == HTTPStatusCodes.OK
