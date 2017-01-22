import logging

from spotify.track import Track

from .loader import Loader

logger = logging.getLogger(__name__)


class TrackLoader(Loader):
    search_type = 'tracks'

    def __init__(self, navigator, tracks=[], url=''):
        self.tracks = tracks
        self.url = url
        super(TrackLoader, self).__init__(navigator)

    def get_data(self):
        if self.tracks:
            return self.navigator.spotipy_client.tracks(
                self.tracks
            )
        else:
            return self.navigator.spotipy_client._get(self.url)

    def get_item(self, session, item):
        return Track(session, item['track']['uri'])
