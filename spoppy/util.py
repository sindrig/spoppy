import logging
import os
import select
import sys
import threading

try:
    import thread
except ImportError:
    import _thread as thread
import termios
import tty

from . import responses

logger = logging.getLogger(__name__)


# Initially taken from https://github.com/magmax/python-readchar
def readchar(wait_for_char=0.1):
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    res = b''
    try:
        if select.select([sys.stdin, ], [], [], wait_for_char)[0]:
            res = os.read(sys.stdin.fileno(), 1)
        while select.select([sys.stdin, ], [], [], 0.0)[0]:
            res += os.read(sys.stdin.fileno(), 1)
        if res:
            return res
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    return None


def single_char_with_timeout(timeout=5):
    timer = threading.Timer(timeout, thread.interrupt_main)
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
            if artist.name
        )
    )


def format_album(album_browser):
    return '%s by %s [%s]' % (
        album_browser.album.name,
        album_browser.artist.name,
        album_browser.album.year
    )


def sorted_menu_items(items):
    global_items = []
    for key, value in sorted(items):
        if value.destination in responses.ALL:
            global_items.append((key, value))
        else:
            yield key, value
    for key, value in global_items:
        yield key, value


def get_duration_from_s(s):
    '''
    Formats seconds as "%M:%S"
    :param s: Seconds in int/float
    :returns: s formatted as "%M:%S"
    '''
    # Max length is 59 minutes, 59 seconds
    MAX_LENGTH = 59 * 60 + 59
    if not isinstance(s, (int, float)):
        raise TypeError('Seconds must be int/float')
    elif s < 0:
        raise TypeError('Seconds must be positive')
    elif s > MAX_LENGTH:
        s = MAX_LENGTH
    return '%s:%s' % (
        str(int(s / 60)).zfill(2),
        str(int(s % 60)).zfill(2)
    )

if __name__ == '__main__':
    if sys.argv[-1] == 'wrapper':
        print(single_char_with_timeout())
    else:
        char = readchar(10)
        print(char)
        print(char.decode('utf-8'))
