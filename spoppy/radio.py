import logging
import random
import threading

from spotify.track import Track

from .search import Search

logger = logging.getLogger(__name__)


class RadioResults(object):
    def __init__(self, results):
        self.term = None
        self.results = results
        self.total = len(results)
        self.offset = 0
        self.previous_page = None
        self.next_page = None

    def __iter__(self):
        return iter(self.results)

    def __getitem__(self, key):
        return self.results[key]


class Recommendations(Search):
    item_cls = Track
    search_type = 'tracks'

    def __init__(self, navigator, seeds, seed_type):
        self.navigator = navigator
        self.session = navigator.session
        self.seed_type = seed_type

        if len(seeds) > 5:
            seeds = random.sample(seeds, 5)
        self.seeds = [
            item.uri if hasattr(item, 'uri') else item.link.uri
            for item in seeds
        ]
        self.loaded_event = threading.Event()

        super(Search, self).__init__()

        self.start()

    def run(self):

        kwargs = {}
        if self.seed_type == 'artists':
            kwargs['seed_artists'] = self.seeds
        else:
            kwargs['seed_tracks'] = self.seeds
        try:
            response_data = self.navigator.spotipy_client.recommendations(
                **kwargs
            )
        except Exception:
            logger.exception(
                'Something weird happened when getting recommendations'
            )
            self.results = self.get_empty_results()
        else:
            logger.debug('Got these keys: %s', response_data.keys())

            self.handle_results(response_data['tracks'])

        self.loaded_event.set()

    def get_empty_results(self):
        return RadioResults([])

    def handle_results(self, response_data):
        logger.debug('Got %d songs', len(response_data))
        item_results = self.manipulate_items([
            self.item_cls(self.session, item['uri'])
            for item in response_data
        ])

        self.results = RadioResults(item_results)
