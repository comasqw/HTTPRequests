INDENT = "\r\n"
DOUBLE_INDENT = INDENT + INDENT


class HTTPProtocols:
    HTTP = "http"
    HTTPS = "https"


PROTOCOLS_TUPLE = (HTTPProtocols.HTTPS, HTTPProtocols.HTTP)


class HTTPHeaders:
    USER_AGENT = "user-agent"
    ACCEPT = "accept"
    CONTENT_TYPE = "Content-Type"
    HOST = "Host"
    CONTENT_LENGTH = "Content-Length"
    LOCATION = "Location"
    COOKIE = "Cookie"
    SET_COOKIE = "Set-Cookie"
    TRANSFER_ENCODING = "Transfer-Encoding"


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


HTTP_METHODS_TUPLE = (HTTPMethods.GET, HTTPMethods.POST, HTTPMethods.PUT, HTTPMethods.DELETE)


class ContentTypes:
    JSON = "application/json"
    TEXT = "text/plain"
    FORM = "application/x-www-form-urlencoded"


class TransferEncodingValues:
    CHUNKED = "chunked"


class CookieSettings:
    SECURE = "Secure"
    MAX_AGE = "Max-Age"
    EXPIRES = "Expires"
    DOMAIN = "Domain"
    PATH = "path"
    SAME_SITE = "SameSite"
