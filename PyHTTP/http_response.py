from .constants import *
from .utils import parse_cookie, parse_headers


class ResponseCookie:
    def __init__(self, cookie_str: str):
        self.cookie_dict = parse_cookie(cookie_str)
        self.name = self.cookie_dict["name"]
        self.value = self.cookie_dict["value"]
        self.set_time = self.cookie_dict.get("set_time")
        self.expires = self.cookie_dict.get(CookieSettings.EXPIRES)
        self.max_age = self.cookie_dict.get(CookieSettings.MAX_AGE)
        self.path = self.cookie_dict.get(CookieSettings.PATH)
        self.secure = self.cookie_dict.get(CookieSettings.SECURE)
        self.domain = self.cookie_dict.get(CookieSettings.DOMAIN)
        self.same_site = self.cookie_dict.get(CookieSettings.SAME_SITE)

    def __str__(self):
        return str(self.cookie_dict)


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
                cookie_obj = ResponseCookie(cookie)
                self.cookies[cookie_obj.name] = cookie_obj

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
