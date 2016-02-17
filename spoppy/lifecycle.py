import logging
import os
import threading
# import time
# import webbrowser

# import click
import spotify
# from appdirs import user_data_dir
# from spotipy import Spotify, SpotifyException, oauth2

# from .oauth_receiver import run as run_oauth_server

logger = logging.getLogger(__name__)


class LifeCycle(object):

    # user_data_dir = user_data_dir(appname='spoppy')

    def __init__(self, username, password):
        # if not os.path.isdir(self.user_data_dir):
        #     os.makedirs(self.user_data_dir)
        self.username = username
        self.password = password

    # def get_spotipy_client(self):
    #     return Spotify(auth=self._spotipy_token)

    def get_pyspotify_client(self):
        return self._pyspotify_session

    # def _check_spotipy_logged_in(self):
    #     client_id = os.getenv('SPOTIPY_CLIENT_ID')
    #     client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
    #     redirect_uri = 'http://localhost:8157/'

    #     if not client_id:
    #         click.echo('''
    #             You need to set your Spotify API credentials. You can do this
    #             by setting environment variables like so:
    #             export SPOTIPY_CLIENT_ID='your-spotify-client-id'
    #             export SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'
    #             Get your credentials at
    #                 https://developer.spotify.com/my-applications
    #         ''')
    #         raise SpotifyException(550, -1, 'no credentials set')

    #     sp_oauth = oauth2.SpotifyOAuth(
    #         client_id, client_secret, redirect_uri,
    #         scope=None,
    #         cache_path=os.path.join(
    #             self.user_data_dir, 'spotipy_token.cache'
    #         )
    #     )
    #     token_info = sp_oauth.get_cached_token()

    #     if token_info:
    #         click.echo('Spotipy token received from cache')
    #     else:
    #         click.echo(
    #             'Could not get token from cache, please sign in to Spotify'
    #         )

    #         auth_url = sp_oauth.get_authorize_url()
    #         click.echo(
    #             'Opening %s in your browser, please follow the'
    #             ' instructions on the screen'
    #         )
    #         webbrowser.open(auth_url)

    #         self._spotipy_response_parts = None

    #         def response_callback(parts):
    #             self._spotipy_response_parts = parts
    #             logger.debug('Got response %s from http server', parts)
    #         run_oauth_server(response_callback)
    #         while not self._spotipy_response_parts:
    #             time.sleep(0.5)
    #         if 'error' in self._spotipy_response_parts:
    #             click.echo(
    #                 'Error logging in to spotipy: %s' %
    #                 self._spotipy_response_parts['error']
    #             )
    #             return False
    #         elif 'code' in self._spotipy_response_parts:
    #             code = self._spotipy_response_parts['code'][0]
    #             click.echo('Received code %s' % code)
    #             token_info = sp_oauth.get_access_token(code)
    #         else:
    #             msg = (
    #                 'No code and no error in %s' %
    #                 self._spotipy_response_parts
    #             )
    #             logger.error(msg)
    #             click.echo(msg)
    #             return False
    #     if token_info:
    #         self._spotipy_token = token_info['access_token']
    #         return True
    #     else:
    #         return False

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
