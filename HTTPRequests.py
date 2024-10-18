import json
import socket


INDENT = "\r\n"


class HTTPProtocols:
    HTTP = "http://"
    HTTPS = "https://"


def url_parse(url: str) -> tuple[str, str, str]:
    http_protocol = HTTPProtocols.HTTP
        
    for protocol in (HTTPProtocols.HTTPS, HTTPProtocols.HTTP):
        if url.startswith(protocol):
            url = url[len(protocol):]
            http_protocol = protocol
            break

    parsed_url = url.split("/")

    hostname = parsed_url[0]
    path = "/" + "/".join(parsed_url[1::]) if len(parsed_url) > 1 else "/"
    return hostname, path, http_protocol


class HTTPHeaders:
    USER_AGENT = "user-agent"
    ACCEPT = "accept"
    CONTENT_TYPE = "Content-Type"
    HOST = "Host"
    CONTENT_LENGTH = "Content-Length"
    LOCATION = "Location"


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


class ContentTypes:
    JSON = "application/json"
    TEXT = "text/plain"


base_request_headers = {
    HTTPHeaders.USER_AGENT: "HTTPRequests, comasqw",
    HTTPHeaders.ACCEPT: "*/*"
}


class HTTPRequest:
    def __init__(self,
                 url: str,
                 *,
                 method: str | None = None,
                 request_headers: dict | None = None,
                 http_version: str = HTTPVersions.HTTP1_1,
                 query_string: dict[str, str] | None = None,
                 body: str | dict | None = None):

        self.url = url
        self.hostname, self.path, self.protocol = url_parse(url)
        self.method = method.upper() if method else HTTPMethods.GET
        self.request_headers = request_headers if request_headers else base_request_headers
        self.http_version = http_version.upper()
        self.query_string = query_string
        self.body = body
        self.request = self.create_request_str()

    def _create_request_start_line_str(self) -> str:
        path = self.path
        if self.query_string:
            path += "?" + "&".join([f"{key}={value}" for key, value in self.query_string.items()])
        request_start_line = f"{self.method} {path} {self.http_version}{INDENT}"
        return request_start_line

    def _create_headers_for_content_sending(self):
        content_headers = ""

        content_type = ContentTypes.TEXT
        if isinstance(self.body, dict):
            content_type = ContentTypes.JSON

        content_headers += f"{HTTPHeaders.CONTENT_TYPE}: {content_type}{INDENT}"
        content_headers += f"{HTTPHeaders.CONTENT_LENGTH}: {len(str(self.body))}{INDENT}"

        return content_headers

    def _create_request_headers_str(self) -> str:
        request_headers_str = f"{HTTPHeaders.HOST}: {self.hostname}{INDENT}"
        if self.body and self.method == HTTPMethods.POST:
            request_headers_str += self._create_headers_for_content_sending()

        for header, value in self.request_headers.items():
            request_headers_str += f"{header}: {value}{INDENT}"

        return request_headers_str

    def create_request_str(self) -> str:
        request_start_line_str = self._create_request_start_line_str()
        request_headers_str = self._create_request_headers_str()
        request_str = request_start_line_str + request_headers_str + INDENT + INDENT
        if self.body and self.method == HTTPMethods.POST:
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
        response_header, response_body = self.response.split(INDENT + INDENT)
        self.body = response_body

        response_header_lines = response_header.split(INDENT)
        http_version, status_code, *_ = response_header_lines[0].split()

        self.http_version = http_version
        self.status_code = int(status_code)

        for line in response_header_lines[1:]:
            header, *value = line.split(": ")
            self.headers[header] = "".join(value)


class HTTPClient:
    def __init__(self, recv_bytes: int = 4096, max_redirect_count: int = 5):
        self.recv_bytes = recv_bytes
        self.max_redirect_count = max_redirect_count

    @staticmethod
    def _get_port(http_request: HTTPRequest) -> int:
        return 80 if http_request.protocol == HTTPProtocols.HTTP else 443

    def _connect_and_send_request(self, sock_client: socket.socket, http_request: HTTPRequest, port: int):
        sock_client.connect((http_request.hostname, port))
        sock_client.send(http_request.request.encode())

        response = sock_client.recv(self.recv_bytes)
        return response.decode()

    @staticmethod
    def _check_if_need_to_redirect(http_response: HTTPResponse):
        location = None
        if http_response.status_code == HTTPStatusCodes.MOVED_PERMANENTLY:
            location = http_response.headers.get(HTTPHeaders.LOCATION)

        return location

    def _get_response(self, sock_client: socket.socket, http_request: HTTPRequest, port: int, redirect_count: int):

        response = self._connect_and_send_request(sock_client, http_request, port)
        http_response = HTTPResponse(response)
        location = self._check_if_need_to_redirect(http_response)
        if location:
            if redirect_count >= self.max_redirect_count:
                raise Exception("Too many redirects")
            print(location)
            print(redirect_count)
            redirect_request = HTTPRequest(location)
            return self.send_request(redirect_request, port, redirect_count + 1)

        return http_response

    def send_request(self, http_request: HTTPRequest, port: int | None = None, redirect_count: int = 0) -> HTTPResponse:
        if not port:
            port = self._get_port(http_request)

        with socket.socket() as sock_client:
            http_response = self._get_response(sock_client, http_request, port, redirect_count)

            return http_response
 