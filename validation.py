from constants import *


def protocol_validation(protocol: str):
    if protocol not in PROTOCOLS_TUPLE:
        raise ValueError(f"Unknown protocol: {protocol}. Available protocols: {', '.join(PROTOCOLS_TUPLE)}")


def method_validation(method: str):
    method_upper = method.upper()
    if method_upper not in HTTP_METHODS_TUPLE:
        raise ValueError(f"Unknown method: {method}. Available methods: {', '.join(HTTP_METHODS_TUPLE)}")


def port_validation(port: int):
    if not isinstance(port, int):
        raise ValueError("Port must be an integer.")
    if not (0 <= port <= 65535):
        raise ValueError("Port must be in the range 0-65535.")

