import json
from .validation import protocol_validation, method_validation, port_validation
from .constants import *
from .utils import url_parse, get_default_port, join_dict


class HTTPRequest:
    _body_methods = (HTTPMethods.POST, HTTPMethods.PUT, HTTPMethods.DELETE)

    def __init__(self,
                 url: str,
                 *,
                 method: str | None = None,
                 request_headers: dict | None = None,
                 http_version: str = HTTPVersions.HTTP1_1,
                 query_string: dict[str, str] | None = None,
                 body: str | dict | None = None,
                 form: dict[str, str] | None = None,
                 cookies: dict[str, str] | None = None):

        self._url = url
        self._hostname: str | None = None
        self._path: str | None = None
        self._protocol: str | None = None
        self._port: int | None = None
        self._method = method.upper() if method else HTTPMethods.GET
        self._request_headers = request_headers if request_headers else {}
        self._http_version = http_version.upper()
        self._query_string = query_string if query_string else {}
        self._body = body
        self._body_copy = body
        self._form = form
        self._cookies = cookies if cookies else {}
        self._content_type: str | None = None
        self._content_length: int | None = None
        self._start_line_needs_update = True
        self._headers_need_update = True
        self._body_needs_update = True
        self._request_start_line: str | None = None
        self._request_headers_str: str | None = None
        self._body_str: str | None = None
        self._initialize_url()
        self._initialize_port()
        self._initialize_form()
        self._initialize_content_headers()

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, new_url):
        self._url = new_url
        self._initialize_url()
        self._start_line_needs_update = True
        self._headers_need_update = True

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, new_method):
        method_validation(new_method)

        self._method = new_method.upper()
        self._initialize_content_headers()
        self._start_line_needs_update = True
        self._headers_need_update = True
        self._body_needs_update = True

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, new_hostname):
        self._hostname = str(new_hostname)
        self._headers_need_update = True

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, new_path):
        self._path = new_path
        self._start_line_needs_update = True

    @property
    def protocol(self):
        return self._protocol

    @protocol.setter
    def protocol(self, new_protocol):
        protocol_validation(new_protocol)

        self._protocol = new_protocol
        self._initialize_port()

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, new_port):
        port_validation(new_port)
        self._port = new_port

    @property
    def request_headers(self):
        return self._request_headers

    def set_header(self, key, value):
        self._request_headers[key] = value
        self._headers_need_update = True

    def del_header(self, key):
        if key in self._request_headers:
            del self._request_headers[key]
        self._headers_need_update = True

    @property
    def http_version(self):
        return self._http_version

    @http_version.setter
    def http_version(self, new_http_version):
        self._http_version = new_http_version
        self._start_line_needs_update = True

    @property
    def query_string(self):
        return self._query_string

    @query_string.setter
    def query_string(self, new_query_string: dict[str, str]):
        if not isinstance(new_query_string, dict):
            raise ValueError("New form must be dictionary")
        self._query_string = new_query_string
        self._start_line_needs_update = True

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, new_body):
        self._body = new_body
        self._body_copy = new_body
        self._headers_need_update = True
        self._body_needs_update = True

    @property
    def form(self):
        return self._form

    @form.setter
    def form(self, new_form: dict[str, str]):
        if not isinstance(new_form, dict):
            raise ValueError("New form must be dictionary")

        self._form = new_form
        self._initialize_form()
        self._initialize_content_headers()
        self._headers_need_update = True
        self._body_needs_update = True

    @property
    def cookies(self):
        return self._cookies

    def set_cookie(self, key, value):
        self._cookies[key] = value
        self._initialize_cookies()

    def del_cookie(self, key):
        if key in self._cookies:
            del self._cookies[key]
        self._initialize_cookies()

    def _initialize_content_headers(self):
        if self._method in self._body_methods:
            self._content_length = len(str(self._body).encode("utf-8"))

            if isinstance(self._body, dict):
                self._content_type = ContentTypes.JSON
            elif self._form:
                self._content_type = ContentTypes.FORM
            else:
                self._content_type = ContentTypes.TEXT

    def _initialize_cookies(self):
        self.set_header(HTTPHeaders.COOKIE, join_dict(self._cookies, "; "))

    def _initialize_url(self):
        self._hostname, self._path, self._protocol, self._port = url_parse(self.url)

    def _initialize_form(self):
        if self._form:
            self._body = join_dict(self._form, "&")
        else:
            self._body = self._body_copy

    def _initialize_port(self):
        if not self._port:
            self._port = get_default_port(self._protocol)

    def _create_request_start_line_str(self):
        path = self._path
        if self._query_string:
            path += "?" + join_dict(self._query_string, "&")
        self._request_start_line = f"{self._method} {path} {self._http_version}{INDENT}"
        self._start_line_needs_update = False

    def _create_headers_for_content_sending(self):
        content_headers = (f"{HTTPHeaders.CONTENT_TYPE}: {self._content_type}{INDENT}"
                           f"{HTTPHeaders.CONTENT_LENGTH}: {self._content_length}{INDENT}")
        return content_headers

    def _create_request_headers_str(self):
        request_headers_str = f"{HTTPHeaders.HOST}: {self._hostname}{INDENT}"
        if self._body and self._method in self._body_methods:
            request_headers_str += self._create_headers_for_content_sending()

        for header, value in self._request_headers.items():
            request_headers_str += f"{header}: {value}{INDENT}"

        self._request_headers_str = request_headers_str
        self._headers_need_update = False

    def _create_request_body_str(self):
        if self._body and self._method in self._body_methods:
            if isinstance(self.body, dict):
                self._body_str = json.dumps(self._body)
            else:
                self._body_str = str(self._body)
        else:
            self._body_str = ""
        self._body_needs_update = False

    @property
    def request(self):
        if self._start_line_needs_update:
            self._create_request_start_line_str()
        if self._headers_need_update:
            self._create_request_headers_str()
        if self._body_needs_update:
            self._create_request_body_str()

        return self._request_start_line + self._request_headers_str + DOUBLE_INDENT + self._body_str
