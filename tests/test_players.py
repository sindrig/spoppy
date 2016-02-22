import unittest
from unittest.mock import Mock, patch

from spoppy import players

from . import utils


class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.navigation = Mock()
        self.player = players.Player(self.navigation)
        self.player.initialize()

    def test_has_been_loaded(self):
        self.assertFalse(self.player.has_been_loaded())
        self.player.song_list = [
            utils.Track('', '')
        ]
        self.assertTrue(self.player.has_been_loaded())

    def test_shows_playlist_name(self):
        playlist_name = 'Playlist 1'
        ui = self.player.get_ui()
        self.assertEqual(
            len([line for line in ui if playlist_name in line]),
            0
        )
        self.player.playlist = utils.Playlist(playlist_name, [])
        ui = self.player.get_ui()
        self.assertEqual(
            len([line for line in ui if playlist_name in line]),
            1
        )

    @patch('spoppy.players.Player.get_help_ui')
    def test_shows_help(self, patched_show_help):
        self.player.get_ui()
        self.assertEqual(patched_show_help.call_count, 0)
        self.player.get_help()
        self.player.get_ui()
        self.assertEqual(patched_show_help.call_count, 1)

    def test_shows_all_available_actions_in_help(self):
        help_items = self.player.get_help_ui()
        actions = []
        for item in help_items:
            if '[' in item and ']' in item:
                actions.append(item.split(':')[-1].lstrip(' '))
        for action in self.player.reversed_actions:
            self.assertIn(action, actions)
