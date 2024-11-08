from unittest import TestCase, main
from datetime import datetime

from PyHTTP.utils import *


class URLParseTest(TestCase):
    def test_equals(self):
        self.assertEqual(url_parse("google.com"), ('google.com', '/', 'http', 80))
        self.assertEqual(url_parse("https://google.com"), ('google.com', '/', 'https', 443))
        self.assertEqual(url_parse("google.com:8000"), ('google.com', '/', 'http', 8000))
        self.assertEqual(url_parse("https://google.com:8000"), ('google.com', '/', 'https', 8000))
        self.assertEqual(url_parse("https://google.com/test"), ('google.com', '/test', 'https', 443))
        self.assertEqual(url_parse("google.com:8000/test"), ('google.com', '/test', 'http', 8000))


class ParseCookieTest(TestCase):
    def test_equals(self):
        result = parse_cookie("sessionId=abc123")
        self.assertEqual(result, {'name': 'sessionId', 'value': 'abc123'})

        result = parse_cookie("sessionId=abc123; Path=/; HttpOnly; Secure")
        self.assertEqual(result, {'HttpOnly': True,
                                  'Path': '/',
                                  'Secure': True,
                                  'name': 'sessionId',
                                  'value': 'abc123'})

        result = parse_cookie("Set-Cookie: sessionId=abc123; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=3600")
        self.assertEqual(result, {'HttpOnly': True,
                                  'Max-Age': 3600,
                                  'Path': '/',
                                  'SameSite': 'Strict',
                                  'Secure': True,
                                  'name': 'Set-Cookie: sessionId',
                                  'set_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  'value': 'abc123'})


if __name__ == '__main__':
    main()
