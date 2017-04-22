import logging
import threading

from appdirs import user_cache_dir
from .search import Search

logger = logging.getLogger(__name__)


class Results(object):
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
    'probably due to your access token being expired. I\'ve attempted to '
    'automatically refresh you access, so you can retry this operation. '
    'If that didn\'t work, try restarting spoppy, and if that doesn\'t work '
    'try removing the file %s/spotipy_token.cache, restart '
    'spoppy and log in to spotify web API again. For more information on this '
    'issue, see https://github.com/sindrig/spoppy/issues/127'
) % (user_cache_dir(appname='spoppy'), )


class Loader(Search):

    def __init__(self, navigator):
        self.navigator = navigator
        self.session = navigator.session

        self.loaded_event = threading.Event()

        super(Search, self).__init__()

        self.start()

    def run(self):
        logger.debug('Getting playlists for %s' % self.navigator.username)
        try:
            response_data = self.get_data()
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

            self.handle_results(response_data['items'])
        finally:
            self.loaded_event.set()

    def get_empty_results(self, message=''):
        return Results([], message)

    def handle_results(self, response_data):
        logger.debug('Got %d items', len(response_data))

        item_results = self.manipulate_items([
            self.get_item(self.session, item)
            for item in response_data
        ])
        self.results = Results(item_results)
