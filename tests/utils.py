from spotify import TrackAvailability
from collections import namedtuple

from mock import Mock

Artist = namedtuple('Artist', ('name', ))


class Track(object):
    def __init__(self, name, artists, available=True):
        self.artists = [Artist(artist) for artist in artists]
        self.name = name
        if available:
            self.availability = TrackAvailability.AVAILABLE
        else:
            self.availability = TrackAvailability.UNAVAILABLE


class Playlist(object):
    def __init__(self, name, tracks):
        self.link = Mock()
        self.link.as_playlist.return_value = self
        self.name = name
        self.tracks = tracks
