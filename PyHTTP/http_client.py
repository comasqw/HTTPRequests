import socket
import ssl

from .constants import *
from .http_request import HTTPRequest
from .http_response import HTTPResponse


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
