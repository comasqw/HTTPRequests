import json
import socket


INDENT = "\r\n"


def url_parse(url: str) -> tuple[str, str]:
    for protocol in ("https://", "http://"):
        if url.startswith(protocol):
            url = url[len(protocol):]
            break

    parsed_url = url.split("/")

    hostname = parsed_url[0]
    path = "/" + "/".join(parsed_url[1::]) if len(parsed_url) > 1 else "/"

    return hostname, path


class HTTPHeaders:
    USER_AGENT = "user-agent"
    ACCEPT = "accept"
    CONTENT_TYPE = "Content-Type"
    HOST = "Host"
    CONTENT_LENGTH = "Content-Length"


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
        self.hostname, self.path = url_parse(url)
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

    def _create_request_headers_str(self) -> str:
        request_headers_str = f"{HTTPHeaders.HOST}: {self.hostname}{INDENT}"
        if self.body and self.method == HTTPMethods.POST:
            content_type = ContentTypes.TEXT
            if isinstance(self.body, dict):
                content_type = ContentTypes.JSON
            request_headers_str += f"{HTTPHeaders.CONTENT_TYPE}: {content_type}{INDENT}"
            request_headers_str += f"{HTTPHeaders.CONTENT_LENGTH}: {len(str(self.body))}{INDENT}"

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
            header, *value = line.split(":")
            self.headers[header] = "".join(value)


class HTTPClient:

    @staticmethod
    def _connect_and_send_request(sock_client: socket.socket, host: tuple[str, int], data: str):
        sock_client.connect(host)
        sock_client.send(data.encode())

        response = sock_client.recv(4096)
        return response.decode()

    def send_request(self, http_request: HTTPRequest, port: int = 80) -> HTTPResponse:
        with socket.socket() as sock_client:
            response = self._connect_and_send_request(sock_client, (http_request.hostname, port), http_request.request)
            http_response = HTTPResponse(response)
            return http_response
