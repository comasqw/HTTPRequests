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

    @staticmethod
    def _get_all_data_from_buffer_with_length(sock: socket.socket | ssl.SSLSocket, data: str, length: int)\
            -> str:
        while len(data.encode()) != length:
            data += sock.recv(length - len(data.encode())).decode()

        return data

    def _get_response_body_with_chunked(self, sock: socket.socket | ssl.SSLSocket, chunk_data: str) -> str:
        response_body = chunk_data
        while True:
            chunk_size_str = ""
            while not chunk_size_str.endswith(INDENT):
                chunk_size_str += sock.recv(1).decode()

            chunk_size = int(chunk_size_str, 16)
            if chunk_size == 0:
                break

            chunk_data = self._get_all_data_from_buffer_with_length(sock, "", chunk_size)

            response_body += chunk_data
            sock.recv(2)
        return response_body

    @staticmethod
    def _check_if_data_eq_to_length(http_response: HTTPResponse, first_recv_data: str, data: str, length: int) \
            -> HTTPResponse | None:

        if len(data.encode()) == length:
            http_response.body = data
            http_response.response = first_recv_data
            return http_response
        return None

    def _get_response_body(self, sock: socket.socket | ssl.SSLSocket,
                           http_response: HTTPResponse, first_recv_data: str, response_body: str) -> str | HTTPResponse:

        content_length = http_response.headers.get(HTTPHeaders.CONTENT_LENGTH)
        transfer_encoding_value = http_response.headers.get(HTTPHeaders.TRANSFER_ENCODING)
        if content_length:
            content_length = int(content_length)

            check_if_data_eq_to_length_result = self._check_if_data_eq_to_length(http_response, first_recv_data,
                                                                                 response_body, content_length)
            if isinstance(check_if_data_eq_to_length_result, HTTPResponse):
                return check_if_data_eq_to_length_result

            return self._get_all_data_from_buffer_with_length(sock, response_body, content_length)
        elif transfer_encoding_value and transfer_encoding_value == TransferEncodingValues.CHUNKED:
            chunk_size, chunk_data = response_body.split(INDENT)
            chunk_size = int(chunk_size, 16)
            check_if_data_eq_to_length_result = self._check_if_data_eq_to_length(http_response, first_recv_data,
                                                                                 chunk_data, chunk_size)
            if isinstance(check_if_data_eq_to_length_result, HTTPResponse):
                return check_if_data_eq_to_length_result

            chunk_data = self._get_all_data_from_buffer_with_length(sock, chunk_data, chunk_size)
            sock.recv(2)

            return self._get_response_body_with_chunked(sock, chunk_data)

    def _connect_send_request_and_get_response(self, sock: socket.socket | ssl.SSLSocket, http_request: HTTPRequest)\
            -> HTTPResponse:
        sock.sendall(http_request.request.encode())

        first_recv_data = sock.recv(self.buff_size).decode()
        if not first_recv_data:
            sock.close()
            raise Exception("Empty Response")

        while DOUBLE_INDENT not in first_recv_data:
            first_recv_data += sock.recv(self.buff_size).decode()

        http_response = HTTPResponse(hand_init=True)

        split_response = first_recv_data.split(DOUBLE_INDENT)
        http_response.initialize_headers(split_response[0])
        if len(split_response) > 1:
            response_body = split_response[1]
        else:
            http_response.response = first_recv_data
            return http_response

        get_response_body_result = self._get_response_body(sock, http_response, first_recv_data, response_body)
        if isinstance(get_response_body_result, HTTPResponse):
            return get_response_body_result

        http_response.body = get_response_body_result
        http_response.response = split_response[0] + DOUBLE_INDENT + get_response_body_result

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
