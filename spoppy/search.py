# NOTE: As seen here in https://github.com/mopidy/pyspotify/issues/183
# libspotify's search is broken. Until it either gets fixed (improbable)
# this will have to wrap it up. The goal is to mimick pyspotify's
# search class as best as I can.

import logging
import threading

import requests
from spotify.track import Track, TrackAvailability
from spotify.album import Album

logger = logging.getLogger(__name__)


def search(*args, **kwargs):
    return Search(*args, **kwargs)


class Search(threading.Thread):
    # ATM this class does not paginate. I might look into that later...

    ENDPOINTS = {
        'track': '/v1/search?q={query}&type=track',
        'album': '/v1/search?q={query}&type=album',
        'artist': '/v1/search?q={query}&type=artist',
    }
    BASE_URL = 'https://api.spotify.com'

    def __init__(self, session, query='', callback=None,
                 track_offset=0, track_count=20,
                 album_offset=0, album_count=20,
                 artist_offset=0, artist_count=20,
                 playlist_offset=0, playlist_count=20,
                 search_type=None,
                 sp_search=None, add_ref=True):
        self.session = session
        self.query = query
        self.search_type = search_type
        self.loaded_event = threading.Event()
        super(Search, self).__init__()

        self.start()

    def run(self):
        try:
            r = requests.get(
                self.BASE_URL +
                self.ENDPOINTS[self.search_type].format(query=self.query)
            )
        except requests.exceptions.ConnectionError:
            self.search_results = []
        else:
            r.raise_for_status()
            response_json = r.json()
            if 'tracks' in response_json:
                self.search_results = [
                    Track(self.session, track['uri'])
                    for track in response_json['tracks']['items']
                ]
                self.search_results = [
                    track for track in self.search_results if
                    track.availability != TrackAvailability.UNAVAILABLE
                ]
                for item in self.search_results:
                    item.load()
            elif 'albums' in response_json:
                self.search_results = [
                    Album(self.session, album['uri'])
                    for album in response_json['albums']['items']
                ]
                for item in self.search_results:
                    # Not my fault....
                    # See: https://github.com/mopidy/pyspotify/issues/119
                    item.browse().load()

        self.loaded_event.set()
