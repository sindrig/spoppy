import logging
import os
import threading

import click
import spotify
from appdirs import user_cache_dir
from spotipy import Spotify, SpotifyException, oauth2

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
        self._spotipy_client = None
        self._spotipy_token = None
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
            KNOWN_STATES = (
                'DISCONNECTED',
                'LOGGED_IN',
                'LOGGED_OUT',
                'OFFLINE',
                'UNDEFINED',
            )
            logger.debug(
                'Checking connection state %s' % session.connection.state
            )
            for state in KNOWN_STATES:
                if (
                    session.connection.state == getattr(
                        spotify.ConnectionState, state
                    )
                ):
                    logger.debug('Received connection state %s' % state)
            if session.connection.state == spotify.ConnectionState.LOGGED_IN:
                logged_in.set()
            disconnect_state = spotify.ConnectionState.DISCONNECTED
            if session.connection.state == disconnect_state:
                if self.player.is_playing():
                    self.player.play_pause()
                self.player.state = self.player.DISCONNECTED_INDICATOR
                logger.warning(
                    'Spoppy has been disconnected. DO YOU HAVE INTERNET?'
                )

            else:
                if (
                    self.player.state == self.player.DISCONNECTED_INDICATOR and
                    not self.player.is_playing()
                ):
                    logger.debug('We got internet back, playing!')
                    self.player.play_pause()
                self.player.state = None

        def on_lost_play_token(session):
            if self.player.is_playing():
                self.player.play_pause()
                logger.warning(
                    'Spoppy has been paused. Spotify is probably playing '
                    'somewhere else?'
                )

        # Register event listeners
        self._pyspotify_session.on(
            spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            on_connection_state_updated
        )

        self._pyspotify_session.on(
            spotify.SessionEvent.PLAY_TOKEN_LOST,
            on_lost_play_token
        )

        logger.debug('Actually logging in now...')
        self._pyspotify_session.login(self.username, self.password)

        logged_in.wait(5)
        if logged_in.is_set():
            logger.debug('PySpotify logged in!')
            return True
        else:
            logger.warning('PySpotify login failed!')
            return False

    def get_spotipy_oauth(self):
        client_id = 'ce333851d4db4ba1b6ccf9eaa52345fc'
        client_secret = '549ec6a308cc4836b7144fc42277a6b2'
        redirect_uri = 'http://localhost:8157/'

        cache_location = os.path.join(
            self.user_cache_dir, 'spotipy_token.cache'
        )
        return oauth2.SpotifyOAuth(
            client_id, client_secret, redirect_uri,
            scope=None,
            cache_path=cache_location
        )

    def check_spotipy_logged_in(self):
        sp_oauth = self.get_spotipy_oauth()
        token_info = sp_oauth.get_cached_token()

        if token_info:
            self.set_spotipy_token(token_info)

    def get_spotipy_client(self):
        if self._spotipy_token:
            if not self._spotipy_client:
                self._spotipy_client = Spotify(auth=self._spotipy_token)
            return self._spotipy_client

    def set_spotipy_token(self, token):
        self._spotipy_token = token['access_token']
