import logging
try:
    from urllib.parse import parse_qs, urlparse
except ImportError:
    from urlparse import parse_qs, urlparse

import threading
try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)
HTTP_ADDRESS = '0.0.0.0'
HTTP_PORT = 8157


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
            self.write(
                "<p>Check spoppy, if everything went well you're logged in "
                "now!</p>"
            )
            self.write("</body></html>")
            if parts:
                logger.debug('Got parts %s, calling callback', parts)
                callback_on_token(parts)

        def write(self, line):
            self.wfile.write(line.encode('utf-8'))

    return HTTPHandler


class oAuthServerThread(threading.Thread):
    def __init__(self, ready_callback, started_event, *args, **kwargs):
        self.ready_callback = ready_callback
        self.server = None
        self.started_event = started_event
        super(oAuthServerThread, self).__init__(*args, **kwargs)

    def run(self):
        def on_ready_callback(parts):
            logger.debug(
                'On ready called with parts %s, calling my callback', parts
            )
            self.ready_callback(parts)
            logger.debug('Request finished')
        logger.debug(
            'Starting http server on %s:%s' % (HTTP_ADDRESS, HTTP_PORT)
        )
        try:
            self.server = HTTPServer(
                (
                    HTTP_ADDRESS,
                    HTTP_PORT
                ),
                get_handler(on_ready_callback))
        except OSError:
            logger.exception('Could not bind to address')
            self.started_event.set()
        else:
            self.started_event.set()
            logger.debug('Serving forever...')
            self.server.serve_forever()
            logger.debug('Server has shut down')

    def shutdown(self):
        if self.server:
            logger.debug('Shutting down server...')
            self.server.shutdown()
            self.server = None
