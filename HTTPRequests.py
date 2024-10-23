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

        self.url = url
        self.hostname, self.path, self.protocol, self.port = url_parse(url)
        self._initialize_port()
        self.method = method.upper() if method else HTTPMethods.GET
        self.request_headers = request_headers if request_headers else base_request_headers
        self.http_version = http_version.upper()
        self.query_string = query_string
        self.body = body
        self.form = form
        self.cookies = cookies
        self._content_type: str | None = None
        self._content_length: int | None = None
        self._initialize_form()
        self._initialize_content_headers()
        self.request = self.create_request_str()

    def _initialize_content_headers(self):
        if self.method in self._body_methods:
            if isinstance(self.body, dict):
                self._content_length = len(json.dumps(self.body))
                self._content_type = ContentTypes.JSON
            else:
                self._content_length = len(str(self.body))
                if self.form:
                    self._content_type = ContentTypes.FORM
                else:
                    self._content_type = ContentTypes.TEXT

    def _initialize_form(self):
        if self.form:
            self.body = join_dict(self.form, "&")

    def _initialize_port(self):
        if not self.port:
            self.port = 80 if self.protocol == HTTPProtocols.HTTP else 443

    def _initialize_cookies(self):
        if self.cookies:
            self.request_headers[HTTPHeaders.COOKIE] = join_dict(self.cookies, " ; ")

    def _create_request_start_line_str(self) -> str:
        path = self.path
        if self.query_string:
            path += "?" + join_dict(self.query_string, "&")
        request_start_line = f"{self.method} {path} {self.http_version}{INDENT}"
        return request_start_line

    def _create_headers_for_content_sending(self):
        content_headers = (f"{HTTPHeaders.CONTENT_TYPE}: {self._content_type}{INDENT}"
                           f"{HTTPHeaders.CONTENT_LENGTH}: {self._content_length}{INDENT}")
        return content_headers

    def _create_request_headers_str(self) -> str:
        request_headers_str = f"{HTTPHeaders.HOST}: {self.hostname}{INDENT}"
        if self.body and self.method in self._body_methods:
            request_headers_str += self._create_headers_for_content_sending()

        for header, value in self.request_headers.items():
            request_headers_str += f"{header}: {value}{INDENT}"

        return request_headers_str

    def create_request_str(self) -> str:
        request_start_line_str = self._create_request_start_line_str()
        request_headers_str = self._create_request_headers_str()
        request_str = request_start_line_str + request_headers_str + DOUBLE_INDENT
        if self.body and self.method in self._body_methods:
            if isinstance(self.body, dict):
                body_str = json.dumps(self.body)
            else:
                body_str = str(self.body)
            request_str += body_str
        return request_str


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
