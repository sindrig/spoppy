import logging
import random
import threading

from spotify.track import Track

from .search import Search

logger = logging.getLogger(__name__)


class RadioResults(object):
    def __init__(self, results, message=''):
        self.term = None
        self.results = results
        self.total = len(results)
        self.offset = 0
        self.previous_page = None
        self.next_page = None
        self.message = message

    def __iter__(self):
        return iter(self.results)

    def __getitem__(self, key):
        return self.results[key]


AUTH_ERROR_MESSAGE = (
    'While accessing spotify, we encountered a 401 access denied error, '
    'probably due to your access token being expired. At this moment, this can'
    ' only be fixed by restarting spoppy. If that doesn\'t work, try removing '
    'the file ~/.cache/spoppy/spotipy_token.cache, restart spoppy and log in '
    'to spotify web API again. For more information on this issue, see '
    'https://github.com/sindrig/spoppy/issues/127'
)


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
        except Exception as e:
            if getattr(e, 'http_status', None) == 401:
                logger.debug(
                    'Access token for spotipy expired, or unknown auth error'
                )
                self.results = self.get_empty_results(
                    message=AUTH_ERROR_MESSAGE
                )
            else:
                logger.exception(
                    'Something weird happened when getting recommendations'
                )
                self.results = self.get_empty_results()
        else:
            logger.debug('Got these keys: %s', response_data.keys())

            self.handle_results(response_data['tracks'])
        finally:
            self.loaded_event.set()

    def get_empty_results(self, message=''):
        return RadioResults([], message)

    def handle_results(self, response_data):
        logger.debug('Got %d songs', len(response_data))
        item_results = self.manipulate_items([
            self.item_cls(self.session, item['uri'])
            for item in response_data
        ])

        self.results = RadioResults(item_results)
