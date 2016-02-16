import logging
import sys

import click

from . import menus
from .lifecycle import LifeCycle
from .players import Player

logger = logging.getLogger(__name__)


class Leifur(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.lifecycle = LifeCycle(username, password)
        self.player = Player(self)
        logger.debug('Leifur initialized')

    def start(self):
        # logged_in = (
        #     self.lifecycle._check_spotipy_logged_in() and
        #     self.lifecycle._check_pyspotify_logged_in()
        # )
        if self.lifecycle.check_pyspotify_logged_in():
            # self.info = self.lifecycle.get_spotipy_client()
            self.session = self.lifecycle.get_pyspotify_client()
            logger.debug('All tokens are a-OK')
            main_menu = menus.MainMenu(self)
            while True:
                self.navigate_to(main_menu)
        else:
            logger.debug('Something went wrong, not logged in...')

    def navigate_to(self, going):
        if callable(going):
            return self.navigate_to(going())
        going.initialize()
        while True:
            click.clear()
            self.print_header()
            self.print_menu(going.get_menu())
            response = going.get_response()
            if response == menus.QUIT:
                click.echo('Thanks, bye!')
                sys.exit(0)
            elif response == menus.UP:
                break
            else:
                self.navigate_to(response)

    def print_header(self):
        click.echo('Hi there %s' % self.username)

    def print_menu(self, menu):
        click.echo(menu)
