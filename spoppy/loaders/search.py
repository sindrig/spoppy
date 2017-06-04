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
from spotify.playlist import Playlist

logger = logging.getLogger(__name__)


def search(*args, **kwargs):
    return Search(*args, **kwargs)


class SearchResults(object):
    def __init__(self, response, term, results, offset, total,
                 previous_page=None, next_page=None):
        self.response = response
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
            'track',
            Track
        ),
        'albums': (
            'album',
            Album
        ),
        'artists': (
            'artist',
            Artist
        ),
        'playlists': (
            'playlist',
            Playlist
        ),
    }
    BASE_URL = 'https://api.spotify.com'

    def __init__(self, navigator, query='', callback=None,
                 track_offset=0, track_count=20,
                 album_offset=0, album_count=20,
                 artist_offset=0, artist_count=20,
                 playlist_offset=0, playlist_count=20,
                 search_type=None,
                 sp_search=None, add_ref=True, next_from=None, prev_from=None):
        self.navigator = navigator
        self.query = query
        self.search_type = search_type

        # next from and prev from are SearchResult items
        self.next_from = next_from and next_from.response
        self.prev_from = prev_from and prev_from.response

        self.loaded_event = threading.Event()

        self.type, self.item_cls = self.ENDPOINTS[self.search_type]

        self.results = self.get_empty_results()

        super(Search, self).__init__()

        self.start()

    def run(self):
        try:
            logger.debug('Getting %s: %s', self.type, self.query)
            if self.next_from:
                results = self.navigator.spotipy_client.next(
                    self.next_from
                )
            elif self.prev_from:
                results = self.navigator.spotipy_client.previous(
                    self.prev_from
                )
            else:
                results = self.navigator.spotipy_client.search(
                    self.query, limit=20, type=self.type
                )
            response_data = results[self.search_type]
            self.results = self.handle_results(response_data)
        except requests.exceptions.RequestException:
            logger.exception('RequestException')
        except Exception:
            logger.exception('Something went wrong while handling results')
        finally:
            self.loaded_event.set()

    def get_empty_results(self):
        return SearchResults(None, self.query, [], 0, 0)

    def handle_results(self, response_data):
        item_results = self.manipulate_items([
            (self.item_cls(self.navigator.session, item['uri']), item)
            for item in response_data['items']
        ])

        return SearchResults(
            response_data,
            self.query,
            item_results,
            response_data['offset'],
            response_data['total'],
            response_data['previous'],
            response_data['next']
        )

    def manipulate_items(self, items):
        items = [
            item if isinstance(item, tuple) else (item, {})
            for item in items
        ]
        if self.search_type == 'albums':
            # Not my fault....
            # See: https://github.com/mopidy/pyspotify/issues/119
            return [
                item[0].browse().load() for item in items
            ]
        elif self.search_type == 'tracks':
            return [
                item[0].load() for item in items
                if item[0].availability != TrackAvailability.UNAVAILABLE
            ]
        elif self.search_type == 'artists':
            return [
                item[0].browse().load() for item in items
            ]
        elif self.search_type == 'playlists':
            return items
        raise TypeError('Unknown search type %s' % self.search_type)
