import logging
import os
import threading

import spotify
from appdirs import user_cache_dir

from .dbus_listener import DBusListener
from .terminal import ResizeChecker

logger = logging.getLogger(__name__)


class LifeCycle(object):

    user_cache_dir = user_cache_dir(appname='spoppy')

    def __init__(self, username, password, player):
        if not os.path.isdir(self.user_cache_dir):
            os.makedirs(self.user_cache_dir)
        self.player = player
        self.username = username
        self.password = password
        self._pyspotify_session = None
        self._pyspotify_session_loop = None
        self.service_stop_event = threading.Event()
        self.services = [
            DBusListener(self, self.service_stop_event),
            ResizeChecker(self, self.service_stop_event)
        ]

    def start_lifecycle_services(self):
        for service in self.services:
            if service.should_run:
                service.start()
                logger.debug('%s started!' % service)
            else:
                logger.debug('Not running %s' % service)

    def shutdown(self):
        if self._pyspotify_session:
            logger.debug('Logging user out after quit...')
            self._pyspotify_session.logout()
        logger.debug('Closing dbus_listener')
        self.service_stop_event.set()
        while self.services:
            logger.debug('Joining %s' % self.services[0])
            if self.services[0].is_alive():
                # Give it half a second to die
                self.services[0].join(0.5)
            if not self.services[0].is_alive():
                del self.services[0]
        logger.debug('All services joined')
        if self._pyspotify_session_loop:
            self._pyspotify_session_loop.stop()
        logger.debug('Pyspotify session loop stopped')

    def get_pyspotify_client(self):
        return self._pyspotify_session

    def check_pyspotify_logged_in(self):
        logger.debug('Checking if pyspotify is logged in...')
        config = spotify.Config()
        config.user_agent = 'Spoppy'
        config.cache_location = os.path.join(self.user_cache_dir, 'cache')
        config.settings_location = os.path.join(self.user_cache_dir, 'cache')
        config.load_application_key_file(
            os.path.join(os.path.dirname(__file__), 'spotify_appkey.key')
        )
        self._pyspotify_session = spotify.Session(config)
        self._pyspotify_session_loop = spotify.EventLoop(
            self._pyspotify_session
        )
        self._pyspotify_session_loop.start()

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
