import logging
import os
import threading

import spotify
from appdirs import user_cache_dir

from .dbus_listener import Listener

logger = logging.getLogger(__name__)


class LifeCycle(object):

    user_cache_dir = user_cache_dir(appname='spoppy')

    def __init__(self, username, password, navigator):
        if not os.path.isdir(self.user_cache_dir):
            # TODO: Use this for pyspotify's cache
            os.makedirs(self.user_cache_dir)
        self.navigator = navigator
        self.username = username
        self.password = password
        self._pyspotify_session = None
        self.dbus_stop_event = threading.Event()
        self.dbus_listener = Listener(self, self.dbus_stop_event)

    def start_lifecycle_services(self):
        self.dbus_listener.start()

    def shutdown(self):
        if self._pyspotify_session:
            logger.debug('Logging user out after quit...')
            self._pyspotify_session.logout()
        logger.debug('Closing dbus_listener')
        self.dbus_stop_event.set()
        while self.dbus_listener.is_alive():
            logger.debug('Joining dbus_listener')
            self.dbus_listener.join(0.5)

    def get_pyspotify_client(self):
        return self._pyspotify_session

    def check_pyspotify_logged_in(self):
        logger.debug('Checking if pyspotify is logged in...')
        config = spotify.Config()
        config.user_agent = 'Spoppy'
        application_key = os.getenv('SPOPPY_LIBSPOTIFY_APP_KEY')
        if not os.path.isfile(application_key):
            raise ValueError(
                'SPOPPY_LIBSPOTIFY_APP_KEY env variable must be set '
                'for PySpotify to work'
            )
        with open(application_key, 'rb') as f:
            config.application_key = f.read()
        self._pyspotify_session = spotify.Session(config)
        loop = spotify.EventLoop(self._pyspotify_session)
        loop.start()

        # Connect an audio sink
        spotify.AlsaSink(self._pyspotify_session)

        # Events for coordination
        logged_in = threading.Event()
        # end_of_track = threading.Event()

        def on_connection_state_updated(session):
            if session.connection.state is spotify.ConnectionState.LOGGED_IN:
                logged_in.set()

        # Register event listeners
        self._pyspotify_session.on(
            spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            on_connection_state_updated
        )

        logger.debug('Actually logging in now...')
        self._pyspotify_session.login(self.username, self.password)

        logged_in.wait(6)
        if logged_in.is_set():
            logger.debug('PySpotify logged in!')
            return True
        else:
            logger.warning('PySpotify login failed!')
            return False
