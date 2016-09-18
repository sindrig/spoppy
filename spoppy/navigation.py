import logging

import click

from . import get_version, menus, responses
from .lifecycle import LifeCycle
from .players import Player
from .terminal import get_terminal_size
from .config import clear_config
from .util import (
    ban_artist, unban_artist, get_banned_artist_uris, get_artist_uri
)

try:
    # py2.7+
    basestring
except NameError:
    # py3.3+
    basestring = str

logger = logging.getLogger(__name__)


class Leifur(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.player = Player(self)
        self.lifecycle = LifeCycle(username, password, self.player)
        self.session = None

        self.lifecycle.check_spotipy_logged_in()
        self.spotipy_client = self.lifecycle.get_spotipy_client()

        self.navigating = True
        logger.debug('Leifur initialized')

    def refresh_spotipy_client(self):
        self.spotipy_client = self.lifecycle.get_spotipy_client()

    def start(self):
        if self.lifecycle.check_pyspotify_logged_in():
            logger.debug('All tokens are a-OK')
            self.session = self.lifecycle.get_pyspotify_client()
            logger.debug('Starting LifeCycle services')
            self.lifecycle.start_lifecycle_services()
            logger.debug('LifeCycle services started')
            self.player.initialize()

            logger.debug('Getting banned artists')
            self.banned_artists = get_banned_artist_uris()
            logger.info('Banned artists are %s' % (self.banned_artists, ))

            main_menu = menus.MainMenu(self)
            self.navigate_to(main_menu)
        else:
            click.echo(
                'Could not log you in, please check your username (%s) '
                'and password are correct' % self.username
            )
            clear_config()
            logger.debug('Something went wrong, not logged in...')

    def shutdown(self):
        self.lifecycle.shutdown()
        logger.debug('Navigation shutdown complete')

    def navigate_to(self, going):
        logger.debug('navigating to: %s' % going)
        self.session.process_events()
        going.initialize()
        while self.navigating:
            click.clear()
            self.print_header()
            self.print_menu(going.get_ui())
            response = going.get_response()
            if callable(response):
                response = response()
                logger.debug('Got response %s after evaluation' % response)
            if response == responses.QUIT:
                click.clear()
                click.echo('Thanks, bye!')
                self.navigating = False
                return
            elif response == responses.UP:
                break
            elif response == responses.NOOP:
                continue
            elif response == responses.PLAYER:
                self.navigate_to(self.player)
            elif response != going:
                self.navigate_to(response)
            # This happens when the `going` instance gets control again. We
            # don't want to remember the query and we want to rebuild the
            # menu's options
            # (and possibly something else?)
            going.initialize()

    def print_header(self):
        click.echo('Spoppy v. %s' % get_version())
        click.echo('Hi there %s' % self.username)
        click.echo('')

    def print_menu(self, menu):
        if isinstance(menu, basestring):
            click.echo(menu)
        elif isinstance(menu, (list, tuple)):
            for item in menu:
                if isinstance(item, (list, tuple)):
                    if len(item) == 2:
                        click.echo(
                            ''.join((
                                item[0],
                                ' ' * (
                                    self.get_ui_width() -
                                    len(item[0]) -
                                    len(item[1])
                                ),
                                item[1]
                            ))
                        )
                    else:
                        click.echo(item[0])
                else:
                    click.echo(item)
            click.echo('')
        else:
            logger.error('I have no idea how to print menu %r' % menu)

    def update_progress(self, status, start, perc, end):
        s = '\r[%s] %s[%s]%s' % (
            status,
            start,
            '%s',
            end or ''
        )
        progress_width = self.get_ui_width() - len(s) + 2
        if perc > 1:
            perc = 1
        s = s % ('#' * int(perc * progress_width)).ljust(progress_width)

        click.echo(s, nl=False)

    def get_ui_width(self):
        return get_terminal_size().width

    def get_ui_height(self):
        # We want to return the height allocated to the menu
        return get_terminal_size().height - 4

    def is_artist_banned(self, artist):
        uri = get_artist_uri(artist)
        return uri in self.banned_artists

    def ban_artist(self, artist):
        uri = get_artist_uri(artist)
        logger.debug('Banning artist {}'.format(uri))
        self.banned_artists.append(uri)
        logger.info('{}'.format(self.banned_artists))
        return ban_artist(uri)

    def unban_artist(self, artist):
        uri = get_artist_uri(artist)
        logger.debug('Unbanning artist {}'.format(uri))
        self.banned_artists.remove(uri)
        logger.info('{}'.format(self.banned_artists))
        return unban_artist(uri)
