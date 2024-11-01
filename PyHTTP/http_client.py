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
    def __init__(self, buff_size: int = 8192, redirect_allow: bool = True, max_redirects_count: int = 5):
        self.buff_size = buff_size
        self.redirect_allow = redirect_allow
        self.max_redirects_count = max_redirects_count

    def _connect_send_request_and_get_response(self, sock: socket.socket | ssl.SSLSocket, http_request: HTTPRequest)\
            -> HTTPResponse:
        # todo: add Transfer-Encoding: chunked supporting
        sock.sendall(http_request.request.encode())

        first_recv_bytes = sock.recv(self.buff_size).decode()
        if not first_recv_bytes:
            sock.close()
            raise Exception("Empty Response")

        http_response = HTTPResponse(hand_init=True)

        splited_response = first_recv_bytes.split(DOUBLE_INDENT)
        http_response.initialize_headers(splited_response[0])
        if len(splited_response) > 1:
            response_body = splited_response[1]
        else:
            http_response.response = first_recv_bytes
            return http_response

        content_length = http_response.headers.get(HTTPHeaders.CONTENT_LENGTH)
        if content_length:
            content_length = int(content_length)
            if len(response_body.encode()) == content_length:
                http_response.body = response_body
                http_response.response = first_recv_bytes
                return http_response

            while len(response_body.encode()) != content_length:
                recv_response = sock.recv(self.buff_size)
                if not recv_response:
                    break
                response_body += recv_response.decode()

        http_response.body = response_body
        http_response.response = splited_response[0] + DOUBLE_INDENT + response_body

        http_response.initialize_cookies()
        return http_response

    def _get_response(self, http_request: HTTPRequest) -> HTTPResponse:
        with socket.create_connection((http_request.hostname, http_request.port)) as sock:
            if http_request.protocol == HTTPProtocols.HTTP:
                return self._connect_send_request_and_get_response(sock, http_request)
            else:
                context = ssl.create_default_context()
                with context.wrap_socket(sock, server_hostname=http_request.hostname) as ssl_sock:
                    return self._connect_send_request_and_get_response(ssl_sock, http_request)

    def request(self, http_request: HTTPRequest) -> HTTPResponse:
        redirects_count = 0

        request = http_request

        while True:
            response = self._get_response(request)

            if self.redirect_allow:
                location = self._check_if_need_to_redirect(response)
                if location:
                    if redirects_count >= self.max_redirects_count:
                        raise Exception("To many redirects")

                    request = HTTPRequest(location,
                                          request_headers=http_request.request_headers,
                                          body=http_request.body,
                                          form=http_request.form,
                                          query_string=http_request.query_string)
                    redirects_count += 1
                    continue
            break

        return response
