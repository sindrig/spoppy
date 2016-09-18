import logging
import os
import select
import sys
import threading

import termios
import tty
from appdirs import user_cache_dir

from . import responses

try:
    import thread
except ImportError:
    import _thread as thread


logger = logging.getLogger(__name__)
artist_db_location = os.path.join(
    user_cache_dir(appname='spoppy'), 'banned_spoppy_artists.txt'
)


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


def format_track(track, extra_text=None):
    return '%s by %s %s' % (
        track.name,
        ' & '.join(
            artist.name for artist in track.artists
            if artist.name
        ),
        extra_text or ''
    )


def artist_banned_text(navigator, track):
    for artist in track.artists:
        if navigator.is_artist_banned(artist):
            return '[[~~~ARTIST IS BANNED~~~]'
    return ''


def format_album(album_browser):
    return '%s by %s [%s]' % (
        album_browser.album.name,
        album_browser.artist.name,
        album_browser.album.year
    )


def get_sort_key_for_menu(item):
    if item[0].lstrip().isdigit():
        # Force digits at the end of the list
        return '~{}'.format(item[0])
    return item[0]


def sorted_menu_items(items):
    global_items = []
    for key, value in sorted(items, key=get_sort_key_for_menu):
        if value.destination in responses.ALL:
            global_items.append((key, value))
        else:
            yield key, value
    for key, value in global_items:
        yield key, value


def get_duration_from_s(s, max_length=59 * 60 + 59):
    '''
    Formats seconds as "%M:%S"
    If max_length exceed 60, give format in "%H:%M:%S"
    :param s: Seconds in int/float
    :param max_length: Max length in seconds. Default is 59 minutes, 59 seconds
    :returns: s formatted as "%M:%S"
    '''
    if not isinstance(s, (int, float)):
        raise TypeError('Seconds must be int/float')
    elif s < 0:
        raise TypeError('Seconds must be positive')
    elif max_length and s > max_length:
        s = max_length
    m = s / 60
    h = ''
    if m > 60:
        h = ('%s:' % int(m / 60)).zfill(3)
        m = m % 60
    return '%s%s:%s' % (
        h,
        str(int(m)).zfill(2),
        str(int(s % 60)).zfill(2)
    )


def get_artist_uri(artist):
    if hasattr(artist, 'artist'):
        artist = artist.artist
    return artist.link.uri


def ban_artist(uri):
    logger.debug('Banning artist {}'.format(uri))
    with open(artist_db_location, 'a') as f:
        f.write('{}\n'.format(uri))


def unban_artist(uri):
    logger.debug('Unbanning artist {}'.format(uri))
    banned_artists = []
    try:
        with open(artist_db_location, 'r') as f:
            for line in f.readlines():
                if line.strip() != uri:
                    banned_artists.append(line)
    except IOError:
        pass
    with open(artist_db_location, 'w') as f:
        for artist in banned_artists:
            f.write('{}\n'.format(artist))


def get_banned_artist_uris():
    try:
        with open(artist_db_location, 'r') as f:
            return [line.strip() for line in f.readlines()]
    except IOError:
        return []


if __name__ == '__main__':
    if sys.argv[-1] == 'wrapper':
        print(single_char_with_timeout())
    else:
        char = readchar(10)
        print(char)
        print(char.decode('utf-8'))
