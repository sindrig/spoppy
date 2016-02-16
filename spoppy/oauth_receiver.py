import logging
from urllib.parse import parse_qs, urlparse

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

logger = logging.getLogger(__name__)
HTTP_ADDRESS = '0.0.0.0'
HTTP_PORT = 8157


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def get_handler(callback_on_token):
    class HTTPHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            """Respond to a GET request."""
            logger.debug('Received GET request %s', self.path)
            parts = parse_qs(urlparse(self.path).query)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.write("<html><head><title>Spotify oAuth</title></head>")
            self.write("<body><p>This is a token response from Spotify.</p>")
            self.write('<p>%r</p>' % parts)
            self.write("<p>You accessed path: %s</p>" % self.path)
            self.write("</body></html>")
            if parts:
                logger.debug('Got parts %s, calling callback', parts)
                callback_on_token(parts)

        def write(self, line):
            self.wfile.write(line.encode('utf-8'))

    return HTTPHandler


def run(ready_callback):
    def on_ready_callback(parts):
        logger.debug('On ready called with parts %s, shutting down', parts)
        server.shutdown()
        ready_callback(parts)
    server = ThreadedHTTPServer(
        (
            HTTP_ADDRESS,
            HTTP_PORT
        ),
        get_handler(on_ready_callback))
    server.serve_forever()
