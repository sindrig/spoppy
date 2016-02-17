import logging
import os
import select
import sys
import threading

import _thread
import termios
import tty

logger = logging.getLogger(__name__)


# Initially taken from https://github.com/magmax/python-readchar
def readchar(wait_for_char=0.1):
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    try:
        if select.select([sys.stdin, ], [], [], wait_for_char)[0]:
            return os.read(sys.stdin.fileno(), 1)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    return None


def single_char_with_timeout(timeout=5):
    timer = threading.Timer(timeout, _thread.interrupt_main)
    response = None
    try:
        timer.start()
        while response is None:
            response = readchar()
    except KeyboardInterrupt:
        pass
    timer.cancel()
    return response


def format_track(track):
    return '%s by %s' % (
        track.name,
        ' & '.join(
            artist.name for artist in track.artists
        )
    )
