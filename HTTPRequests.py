import json
import socket
import ssl

INDENT = "\r\n"
DOUBLE_INDENT = INDENT + INDENT


class HTTPProtocols:
    HTTP = "http://"
    HTTPS = "https://"


class HTTPHeaders:
    USER_AGENT = "user-agent"
    ACCEPT = "accept"
    CONTENT_TYPE = "Content-Type"
    HOST = "Host"
    CONTENT_LENGTH = "Content-Length"
    LOCATION = "Location"
    COOKIE = "Cookie"


class HTTPStatusCodes:
    OK = 200
    MOVED_PERMANENTLY = 301


class HTTPVersions:
    HTTP1 = "HTTP/1"
    HTTP1_1 = "HTTP/1.1"
    HTTP2 = "HTTP/2"


class HTTPMethods:
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class ContentTypes:
    JSON = "application/json"
    TEXT = "text/plain"
    FORM = "application/x-www-form-urlencoded"


base_request_headers = {
    HTTPHeaders.USER_AGENT: "HTTPRequests, comasqw",
    HTTPHeaders.ACCEPT: "*/*"
}


def url_parse(url: str) -> tuple[str, str, str, int | None]:
    http_protocol = HTTPProtocols.HTTP

    for protocol in (HTTPProtocols.HTTPS, HTTPProtocols.HTTP):
        if url.startswith(protocol):
            url = url[len(protocol):]
            http_protocol = protocol
            break

    parsed_url = url.split("/")

    hostname_with_port = parsed_url[0].split(":")
    hostname = hostname_with_port[0]
    port = hostname_with_port[-1] if len(hostname_with_port) >= 2 else None
    if port:
        port = int(port)

    path = "/" + "/".join(parsed_url[1::]) if len(parsed_url) > 1 else "/"
    return hostname, path, http_protocol, port


def join_dict(dct: dict[any, any], sep: str) -> str:
    return sep.join([f"{key}={value}" for key, value in dct.items()])


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
        self._request_headers = request_headers if request_headers else base_request_headers
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
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, new_hostname):
        self._hostname = new_hostname
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
        self._protocol = new_protocol
        self._initialize_port()

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, new_port):
        self._port = new_port

    @property
    def request_headers(self):
        return self._request_headers

    def new_header(self, key, value):
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
    def form(self, new_form):
        self._form = new_form
        self._initialize_form()
        self._initialize_content_headers()
        self._headers_need_update = True
        self._body_needs_update = True

    @property
    def cookies(self):
        return self._cookies

    def new_cookie(self, key, value):
        self._cookies[key] = value
        self._headers_need_update = True

    def del_cookie(self, key):
        if key in self._cookies:
            del self._cookies[key]
        self._headers_need_update = True

    @property
    def request(self):
        if self._start_line_needs_update:
            self._create_request_start_line_str()
        if self._headers_need_update:
            self._create_request_headers_str()
        if self._body_needs_update:
            self._create_request_body_str()

        return self._request_start_line + self._request_headers_str + DOUBLE_INDENT + self._body_str

    def _initialize_content_headers(self):
        if self._method in self._body_methods:
            self._content_length = len(str(self.body))

            if isinstance(self.body, dict):
                self._content_type = ContentTypes.JSON
            elif self._form:
                self._content_type = ContentTypes.FORM
            else:
                self._content_type = ContentTypes.TEXT

    def _initialize_url(self):
        self._hostname, self._path, self._protocol, self._port = url_parse(self.url)

    def _initialize_form(self):
        if self._form:
            self._body = join_dict(self._form, "&")
        else:
            self._body = self._body_copy

    def _initialize_port(self):
        if not self._port:
            self._port = 80 if self._protocol == HTTPProtocols.HTTP else 443

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


class HTTPResponse:
    def __init__(self, response: str):
        self.response = response
        self.http_version: str | None = None
        self.status_code: int | None = None
        self.headers = {}
        self.body: str | None = None
        self._parse_response()

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
            header, *value = line.split(": ")
            self.headers[header] = "".join(value)

    def __bool__(self):
        return self.status_code == HTTPStatusCodes.OK


class BaseHTTPClient:
    @staticmethod
    def _check_if_need_to_redirect(http_response: HTTPResponse):
        location = None
        if http_response.status_code == HTTPStatusCodes.MOVED_PERMANENTLY:
            location = http_response.headers.get(HTTPHeaders.LOCATION)

        return location

    def request(self, http_request: HTTPRequest) -> HTTPResponse:
        pass


class HTTPClient(BaseHTTPClient):
    def __init__(self, recv_bytes: int = 4096, max_redirect_count: int = 5):
        self.recv_bytes = recv_bytes
        self.max_redirect_count = max_redirect_count
        self._redirect_count = 0

    def _connect_and_send_request_https(self, http_request: HTTPRequest):
        context = ssl.create_default_context()
        with socket.create_connection((http_request.hostname, http_request.port)) as sock:
            with context.wrap_socket(sock, server_hostname=http_request.hostname) as ssl_sock:
                ssl_sock.send(http_request.request.encode())

                response = ssl_sock.recv(self.recv_bytes)
                return response.decode()

    def _connect_and_send_request_http(self, http_request: HTTPRequest):
        with socket.create_connection((http_request.hostname, http_request.port)) as sock:
            sock.send(http_request.request.encode())

            response = sock.recv(self.recv_bytes)
            return response.decode()

    def _connect_and_send_request(self, http_request: HTTPRequest):
        if http_request.protocol == HTTPProtocols.HTTP:
            return self._connect_and_send_request_http(http_request)
        else:
            return self._connect_and_send_request_https(http_request)

    def _get_response(self, http_request: HTTPRequest) -> HTTPResponse:
        response = self._connect_and_send_request(http_request)
        http_response = HTTPResponse(response)
        location = self._check_if_need_to_redirect(http_response)
        if location:
            if self._redirect_count >= self.max_redirect_count:
                raise Exception("To many redirects")

            redirect_request = HTTPRequest(location,
                                           request_headers=http_request.request_headers,
                                           body=http_request.body,
                                           form=http_request.form,
                                           query_string=http_request.query_string)
            self._redirect_count += 1
            return self.request(redirect_request)

        return http_response

    def request(self, http_request: HTTPRequest) -> HTTPResponse:

        response = self._get_response(http_request)
        self._redirect_count = 0
        return response
