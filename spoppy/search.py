# NOTE: As seen here in https://github.com/mopidy/pyspotify/issues/183
# libspotify's search is broken. Until it either gets fixed (improbable)
# this will have to wrap it up. The goal is to mimick pyspotify's
# search class as best as I can.

import logging
import threading

import requests
from spotify.track import Track, TrackAvailability
from spotify.album import Album
from spotify.artist import Artist

logger = logging.getLogger(__name__)


def search(*args, **kwargs):
    return Search(*args, **kwargs)


class SearchResults(object):
    def __init__(self, term, results, offset, total,
                 previous_page=None, next_page=None):
        self.term = term
        self.results = results
        self.total = total
        self.offset = offset
        self.previous_page = previous_page
        self.next_page = next_page


class Search(threading.Thread):
    ENDPOINTS = {
        # Each entry is a tuple, (HTTP_ENDPOINT, CLS)
        'tracks': (
            u'/v1/search?query={query}&offset=0&limit=20&type=track',
            Track
        ),
        'albums': (
            u'/v1/search?query={query}&offset=0&limit=20&type=album',
            Album
        ),
        'artists': (
            u'/v1/search?query={query}&offset=0&limit=20&type=artist',
            Artist
        ),
    }
    BASE_URL = 'https://api.spotify.com'

    def __init__(self, session, query='', callback=None,
                 track_offset=0, track_count=20,
                 album_offset=0, album_count=20,
                 artist_offset=0, artist_count=20,
                 playlist_offset=0, playlist_count=20,
                 search_type=None,
                 sp_search=None, add_ref=True, direct_endpoint=None):
        self.session = session
        self.query = query
        self.search_type = search_type
        self.loaded_event = threading.Event()

        endpoint, self.item_cls = self.ENDPOINTS[self.search_type]

        self.endpoint = direct_endpoint or (
            self.BASE_URL + endpoint.format(query=self.query)
        )

        self.results = self.get_empty_results()

        super(Search, self).__init__()

        self.start()

    def run(self):
        try:
            logger.debug('Getting %s' % self.endpoint)
            r = requests.get(self.endpoint)
            r.raise_for_status()
            response_data = r.json()[self.search_type]
            self.results = self.handle_results(response_data)
        except requests.exceptions.RequestException:
            logger.exception('RequestException')
        except Exception:
            logger.exception('Something went wrong while handling results')
        finally:
            self.loaded_event.set()

    def get_empty_results(self):
        return SearchResults(self.query, [], 0, 0)

    def handle_results(self, response_data):
        item_results = self.manipulate_items([
            self.item_cls(self.session, item['uri'])
            for item in response_data['items']
        ])

        return SearchResults(
            self.query,
            item_results,
            response_data['offset'],
            response_data['total'],
            response_data['previous'],
            response_data['next']
        )

    def manipulate_items(self, items):
        if self.search_type == 'albums':
            # Not my fault....
            # See: https://github.com/mopidy/pyspotify/issues/119
            return [
                item.browse().load() for item in items
            ]
        elif self.search_type == 'tracks':
            return [
                item.load() for item in items
                if item.availability != TrackAvailability.UNAVAILABLE
            ]
        elif self.search_type == 'artists':
            return [
                item.browse().load() for item in items
            ]
        raise TypeError('Unknown search type %s' % self.search_type)
