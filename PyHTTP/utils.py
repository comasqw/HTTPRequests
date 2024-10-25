from .constants import *
from .validation import protocol_validation, port_validation


def get_default_port(http_protocol: str):
    protocol_validation(http_protocol)
    return 80 if http_protocol == HTTPProtocols.HTTP else 443


def url_parse(url: str) -> tuple[str, str, str, int | None]:
    http_protocol = HTTPProtocols.HTTP

    for protocol in PROTOCOLS_TUPLE:
        protocol_str = f"{protocol}://"
        if url.startswith(protocol_str):
            url = url[len(protocol_str):]
            http_protocol = protocol
            break

    parsed_url = url.split("/")
    hostname_with_port = parsed_url[0].split(":")

    hostname = hostname_with_port[0]
    port = int(hostname_with_port[1]) if len(hostname_with_port) == 2 else None

    if port is None:
        port = get_default_port(http_protocol)
    else:
        port_validation(port)

    path = "/" + "/".join(parsed_url[1:]) if len(parsed_url) > 1 else "/"

    return hostname, path, http_protocol, port


def join_dict(dct: dict[any, any], sep: str) -> str:
    return sep.join([f"{key}={value}" for key, value in dct.items()])


def parse_cookie(cookie: str):
    cookie_dct = {}
    cookie_attrs = cookie.split("; ")
    cookie_name, cookie_value = cookie_attrs[0].split("=", 1)
    cookie_dct["name"] = cookie_name
    cookie_dct["value"] = cookie_value

    for attr in cookie_attrs[1:]:
        if "=" in attr:
            attr_name, attr_value = attr.split("=", 1)
            cookie_dct[attr_name] = attr_value
        else:
            cookie_dct[attr] = True

    return cookie_dct
