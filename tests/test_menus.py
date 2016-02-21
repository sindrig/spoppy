import unittest
import uuid
from unittest.mock import Mock, patch

from spoppy import menus, responses

from . import utils


class OptionTests(unittest.TestCase):

    def setUp(self):
        self.dct = {
            '1': menus.MenuValue('A', Mock()),
            '2': menus.MenuValue('B', Mock()),
            '3': menus.MenuValue('C', Mock()),
            's': menus.MenuValue('Search', Mock()),
            'kk': menus.MenuValue('þþ', Mock()),
            'ko': menus.MenuValue('þ', Mock()),
            'q': menus.MenuValue('o', Mock()),
            'o': menus.MenuValue('q', Mock()),
        }
        self.op = menus.Options(self.dct)

    def test_options_filter_empty(self):
        self.assertEqual(self.op, self.op.filter(''))

    def test_filter_by_key(self):
        tc = self.op.filter('1')
        self.assertEqual(len(tc), 1)
        self.assertIn('1', tc)
        tc = self.op.filter('k')
        self.assertEqual(len(tc), 2)
        self.assertIn('kk', tc)
        self.assertIn('ko', tc)
        tc = self.op.filter('s')
        self.assertEqual(len(tc), 1)
        self.assertIn('s', tc)

    def test_filter_by_name(self):
        tc = self.op.filter('þ')
        self.assertEqual(len(tc), 2)
        self.assertIn('kk', tc)
        self.assertIn('ko', tc)
        tc = self.op.filter('þþ')
        self.assertEqual(len(tc), 1)
        self.assertIn('kk', tc)
        tc = self.op.filter('Sea')
        self.assertEqual(len(tc), 1)
        self.assertIn('s', tc)

    def test_filter_is_case_insensitive(self):
        self.assertEqual(self.op.filter('Search'), self.op.filter('search'))

    def test_filter_returns_empty_if_no_match(self):
        self.assertEqual(len(self.op.filter('asdf')), 0)

    def test_get_possibilities_from_name_and_key(self):
        tc = self.op.get_possibilities('q')
        self.assertEqual(len(tc), 2)
        self.assertEqual(sorted(tc), sorted(['q', 'o']))

    def test_possibility_not_duplicated(self):
        tc = self.op.get_possibilities('s')
        self.assertEqual(len(tc), 1)
        self.assertIn('s', tc)

    def test_possiblities_with_spaces(self):
        op = menus.Options({
            '    a': menus.MenuValue('þ', Mock()),
            'b    ': menus.MenuValue('þ', Mock()),
            '    c    ': menus.MenuValue('þ', Mock()),
        })
        for key in 'a', 'b', 'c':
            tc = op.get_possibilities(key)
            self.assertEqual(len(tc), 1)
            self.assertNotEqual(tc, [key])
            self.assertIn(key, tc[0])

    def test_possibilities_only_start_of_words(self):
        # Also testing for case insesitivity
        op = menus.Options({
            'match1': menus.MenuValue('Sindri', Mock()),
            'not1': menus.MenuValue('iSindri', Mock()),
            'match2': menus.MenuValue('This is sindri', Mock()),
            'not2': menus.MenuValue('This is notSindri', Mock()),
        })
        possibilities = op.get_possibilities('Sindri')
        self.assertEqual(sorted(possibilities), sorted(['match1', 'match2']))

    def test_matches_by_correct_key(self):
        op = menus.Options({
            'k': menus.MenuValue('1', Mock()),
            'kk': menus.MenuValue('2', Mock()),
            'kkk': menus.MenuValue('3', Mock()),
        })
        best = op.match_best_or_none('k')
        self.assertEqual(best.name, '1')
        best = op.match_best_or_none('kk')
        self.assertEqual(best.name, '2')
        best = op.match_best_or_none('kkk')
        self.assertEqual(best.name, '3')

    def test_matches_by_correct_padded_key(self):
        op = menus.Options({
            '    a': menus.MenuValue('1', Mock()),
            'b    ': menus.MenuValue('2', Mock()),
            '    c    ': menus.MenuValue('3', Mock()),
            ' s i ': menus.MenuValue('4', Mock()),
        })
        best = op.match_best_or_none('a')
        self.assertEqual(best.name, '1')
        best = op.match_best_or_none('b')
        self.assertEqual(best.name, '2')
        best = op.match_best_or_none('c')
        self.assertEqual(best.name, '3')
        best = op.match_best_or_none('si')
        self.assertEqual(best.name, '4')

    def test_check_unique_keys(self):
        with self.assertRaises(TypeError):
            menus.Options({
                'a': menus.MenuValue('þ', Mock()),
                ' a': menus.MenuValue('k', Mock())
            })
        with self.assertRaises(TypeError):
            self.op['   1'] = menus.MenuValue('1', Mock())


class MenuTests(unittest.TestCase):

    def setUp(self):
        self.navigator = Mock()
        self.navigator.get_ui_height.return_value = 100

        class SubMenu(menus.Menu):
            def get_options(self):
                return {}

        self.submenu = SubMenu(self.navigator)

    def test_must_be_subclassed(self):
        m = menus.Menu(self.navigator)
        with self.assertRaises(NotImplementedError):
            m.get_options()

    def test_global_options_correct(self):
        self.submenu.INCLUDE_UP_ITEM = False
        self.navigator.player.has_been_loaded.return_value = False
        self.submenu.initialize()
        included_items = [
            value.destination for value in self.submenu._options.values()
        ]
        self.assertEqual(len(included_items), 1)
        self.assertIn(responses.QUIT, included_items)
        self.assertNotIn(responses.UP, included_items)
        self.assertNotIn(responses.PLAYER, included_items)

        self.submenu.INCLUDE_UP_ITEM = True
        self.navigator.player.has_been_loaded.return_value = False
        self.submenu.initialize()
        included_items = [
            value.destination for value in self.submenu._options.values()
        ]
        self.assertEqual(len(included_items), 2)
        self.assertIn(responses.QUIT, included_items)
        self.assertIn(responses.UP, included_items)
        self.assertNotIn(responses.PLAYER, included_items)

        self.submenu.INCLUDE_UP_ITEM = False
        self.navigator.player.has_been_loaded.return_value = True
        self.submenu.initialize()
        included_items = [
            value.destination for value in self.submenu._options.values()
        ]
        self.assertEqual(len(included_items), 2)
        self.assertIn(responses.QUIT, included_items)
        self.assertNotIn(responses.UP, included_items)
        self.assertIn(responses.PLAYER, included_items)

        self.submenu.INCLUDE_UP_ITEM = True
        self.navigator.player.has_been_loaded.return_value = True
        self.submenu.initialize()
        included_items = [
            value.destination for value in self.submenu._options.values()
        ]
        self.assertEqual(len(included_items), 3)
        self.assertIn(responses.QUIT, included_items)
        self.assertIn(responses.UP, included_items)
        self.assertIn(responses.PLAYER, included_items)

    def test_filter_initialized_correctly(self):
        self.assertFalse(hasattr(self.submenu, 'filter'))
        self.submenu.initialize()
        self.assertTrue(hasattr(self.submenu, 'filter'))
        self.assertEqual(self.submenu.filter, '')

    @patch('spoppy.menus.single_char_with_timeout')
    def test_pagination_keys(self, patched_chargetter):
        self.assertEqual(self.submenu.PAGE, 0)

        patched_chargetter.return_value = menus.Menu.DOWN_ARROW
        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.PAGE, 1)

        patched_chargetter.return_value = menus.Menu.UP_ARROW
        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.PAGE, 0)

        patched_chargetter.return_value = menus.Menu.UP_ARROW
        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.PAGE, 0)

    @patch('spoppy.menus.single_char_with_timeout')
    def test_backspace(self, patched_chargetter):
        self.submenu.initialize()

        patched_chargetter.return_value = b'a'
        self.assertEqual(self.submenu.filter, '')
        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.filter, 'a')
        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.filter, 'aa')
        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.filter, 'aaa')

        patched_chargetter.return_value = menus.Menu.BACKSPACE
        self.assertEqual(self.submenu.filter, 'aaa')
        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.filter, 'aa')
        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.filter, 'a')
        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.filter, '')

    @patch('spoppy.menus.Menu.is_valid_response')
    @patch('spoppy.menus.single_char_with_timeout')
    def test_return(self, patched_chargetter, patched_is_valid):
        destination = 'DESTINATION'
        patched_is_valid.return_value = menus.MenuValue('TEST', destination)
        self.submenu.initialize()

        patched_chargetter.return_value = b'\n'
        self.assertEqual(self.submenu.get_response(), destination)
        patched_is_valid.assert_called_once_with()

    @patch('spoppy.menus.single_char_with_timeout')
    def test_checks_for_end_of_track(self, patched_chargetter):
        patched_chargetter.side_effect = [None, None, b'a']

        self.submenu.initialize()

        self.assertEqual(self.submenu.get_response(), responses.NOOP)
        self.assertEqual(self.submenu.filter, 'a')
        self.assertEqual(
            self.navigator.player.check_end_of_track.call_count, 3
        )

    @patch('spoppy.menus.Options.match_best_or_none')
    def test_is_valid_uses_options(self, patched_match_best_or_none):
        patched_match_best_or_none.return_value = 'RETVAL'
        self.submenu.initialize()
        self.submenu.filter = 'ASDF'
        self.assertEqual(self.submenu.is_valid_response(), 'RETVAL')
        patched_match_best_or_none.assert_called_once_with('ASDF')

    @patch('spoppy.menus.Options.filter')
    def test_ui_filters_items(self, patched_filter):
        self.submenu.initialize()
        patched_filter.return_value = self.submenu._options
        self.submenu.get_ui()
        patched_filter.assert_not_called()
        self.submenu.filter = 'a'
        self.submenu.get_ui()
        patched_filter.assert_called_once_with('a')

    @patch('spoppy.menus.sorted_menu_items')
    def test_no_matches_warning_shown(self, patched_sorter):
        self.submenu.initialize()
        self.submenu.filter = ''
        patched_sorter.return_value = []
        ui = self.submenu.get_ui()
        has_filter_in_line = [line for line in ui if 'No matches' in line]
        self.assertEqual(len(has_filter_in_line), 1)

    @patch('spoppy.menus.Menu.get_menu_item')
    def test_uses_get_menu_item(self, patched_get_menu_item):
        self.submenu.initialize()
        self.submenu.filter = ''
        patched_get_menu_item.return_value = 'OHAI'

        ui = self.submenu.get_ui()

        self.assertEqual(
            patched_get_menu_item.call_count,
            len([line for line in ui if line == 'OHAI'])
        )

    def test_shows_indicator_if_one_match(self):
        self.submenu.filter = 'a'
        self.submenu.get_options = Mock()
        self.submenu.get_options.return_value = menus.Options({
            'the_key': menus.MenuValue('sindri', Mock()),
            'foo': menus.MenuValue('foo', Mock()),
            'bar': menus.MenuValue('bar', Mock()),
        })
        self.submenu.initialize()

        ui = self.submenu.get_ui()
        self.assertEqual(len([line for line in ui if 'sindri' in line]), 1)
        self.submenu.filter = 'the_key'
        ui = self.submenu.get_ui()
        self.assertEqual(len([line for line in ui if 'sindri' in line]), 2)

    def test_pagination_ui(self):
        option_indicator = 'THIS IS AN OPTION'

        random_options = {
            str(uuid.uuid4()): menus.MenuValue(option_indicator, Mock())
            for i in range(1000)
        }
        get_options = Mock()
        get_options.return_value = random_options
        self.submenu.get_options = get_options
        self.submenu.initialize()

        seen_options = 0

        last_page = -1
        while last_page != self.submenu.PAGE:
            ui = self.submenu.get_ui()
            if self.submenu.PAGE == last_page:
                break
            seen_options += len([
                line for line in ui
                if option_indicator in line
            ])

            last_page = self.submenu.PAGE
            self.submenu.PAGE += 1

        self.assertEqual(seen_options, len(random_options))


class TestSubMenus(unittest.TestCase):

    def setUp(self):
        self.navigator = Mock()

    def get_playlist_selected(self):
        ps = menus.PlayListSelected(self.navigator)
        tracks = [
            utils.Track('Lazarus', ['David Bowie']),
            utils.Track('Best song ever', ['Sindri'], False),
            utils.Track('Blackstar', ['David Bowie']),
            utils.Track('Ziggy Stardust', ['David Bowie']),
        ]
        ps.playlist = utils.Playlist('Playlist', tracks)
        return ps

    def test_playlist_overview_shows_all_playlists(self):
        self.playlists = [
            utils.Playlist('A', []),
            utils.Playlist('B', []),
            utils.Playlist('C', []),
        ]

        class Session(object):
            playlist_container = self.playlists
        self.navigator.session = Session()
        pov = menus.PlayListOverview(self.navigator)
        options = menus.Options(pov.get_options())
        self.assertTrue(
            all(
                isinstance(value.destination, menus.PlayListSelected)
                for value in options.values()
            )
        )
        for playlist in self.playlists:
            self.assertIsNotNone(options.match_best_or_none(playlist.name))

    def test_playlist_overview_does_not_show_invalid_playlists(self):
        self.playlists = [
            utils.Playlist('A', []),
            utils.Playlist('B', []),
            utils.Playlist('', []),
        ]
        del self.playlists[1].link

        class Session(object):
            playlist_container = self.playlists
        self.navigator.session = Session()
        pov = menus.PlayListOverview(self.navigator)
        options = menus.Options(pov.get_options())
        self.assertEqual(len(options), 1)
        self.assertEqual(
            list(options.values())[0].destination.playlist,
            self.playlists[0]
        )

    def test_playlist_selected_does_not_fail_on_empty_playlist(self):
        ps = menus.PlayListSelected(self.navigator)
        ps.playlist = utils.Playlist('asdf', [])
        self.assertEqual(len(ps.get_options()), 0)

    def test_playlist_selected_contains_only_valid_tracks(self):
        ps = self.get_playlist_selected()
        options = menus.Options(ps.get_options())

        self.assertIsNotNone(options.match_best_or_none('1'))
        self.assertIsNotNone(options.match_best_or_none('2'))
        self.assertIsNotNone(options.match_best_or_none('3'))
        self.assertIsNone(options.match_best_or_none('4'))

    def test_shows_shuffle_play(self):
        ps = self.get_playlist_selected()
        options = menus.Options(ps.get_options())

        destinations = [value.destination for value in options.values()]
        self.assertIn(ps.shuffle_play, destinations)

    def test_shows_add_to_queue_if_playing(self):
        ps = self.get_playlist_selected()

        self.navigator.player.is_playing.return_value = False
        options = menus.Options(ps.get_options())

        destinations = [value.destination for value in options.values()]
        self.assertNotIn(ps.add_to_queue, destinations)

        self.navigator.player.is_playing.return_value = True
        options = menus.Options(ps.get_options())

        destinations = [value.destination for value in options.values()]
        self.assertIn(ps.add_to_queue, destinations)

    def test_select_song(self):
        ps = self.get_playlist_selected()
        song_selected = ps.select_song(0)

        self.navigator.player.is_playing.return_value = False
        self.assertEqual(song_selected(), self.navigator.player)
        self.navigator.player.play_track.assert_called_once_with(0)

        self.navigator.player.is_playing.return_value = True
        song_selected_result = song_selected()
        self.assertIsInstance(
            song_selected_result, menus.SongSelectedWhilePlaying
        )
        self.assertEqual(song_selected_result.playlist, ps.playlist)
        self.assertEqual(song_selected_result.track, ps.playlist.tracks[0])
        self.assertEqual(self.navigator.player.play_track.call_count, 1)
