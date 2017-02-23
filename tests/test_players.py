import unittest
from collections import namedtuple
from mock import MagicMock, Mock, patch

import spotify
from spoppy import players, responses

from . import utils


class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.navigation = Mock()
        self.player = players.Player(self.navigation)
        self.player.initialize()

    def tearDown(self):
        del self.player
        del self.navigation

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

    @patch('spoppy.players.time')
    def test_get_progress_while_playing(self, patched_time):
        self.player.player = Mock()
        self.player.player.state = 'playing'
        # This would amount to 60 seconds played
        patched_time.time.return_value = 30
        self.player.play_timestamp = 0
        self.player.seconds_played = 30
        self.player.current_track = Mock()
        self.player.current_track.duration = 120 * 1000

        state, mins_played, perc_played, duration = self.player.get_progress()
        self.assertEqual(state, self.player.player.state)
        self.assertEqual(mins_played, '01:00')
        self.assertEqual(perc_played, 0.5)

    def test_get_progress_while_paused(self):
        self.player.player = Mock()
        self.player.player.state = 'paused'
        # This would amount to 30 seconds played
        self.player.seconds_played = 30
        self.player.current_track = Mock()
        self.player.current_track.duration = 120 * 1000

        state, mins_played, perc_played, duration = self.player.get_progress()
        self.assertEqual(state, self.player.player.state)
        self.assertEqual(mins_played, '00:30')
        self.assertEqual(perc_played, 0.25)

    @patch('spoppy.players.time')
    def test_seek_backwards(self, patched_time):
        patched_time.time.return_value = 30

        self.player.player = Mock()
        self.player.play_timestamp = 0

        self.assertIsNone(self.player.backward_10s())

        self.assertEqual(self.player.play_timestamp, 30)
        self.assertEqual(self.player.seconds_played, 20)
        self.player.player.seek.assert_called_once_with(20 * 1000)

    def test_seek_backwards_doesnt_seek_negative(self):
        self.player.seconds_played = 1

        self.player.backward_10s()

        self.assertEqual(self.player.seconds_played, 0)
        self.player.player.seek.assert_called_once_with(0)

    @patch('spoppy.players.time')
    def test_seek_forwards(self, patched_time):
        patched_time.time.return_value = 30

        self.player.player = Mock()
        self.player.play_timestamp = 0

        self.assertIsNone(self.player.forward_10s())

        self.assertEqual(self.player.play_timestamp, 30)
        self.assertEqual(self.player.seconds_played, 40)
        self.player.player.seek.assert_called_once_with(40 * 1000)

    def test_seek_doesnt_set_play_timestamp_if_paused(self):
        self.player.play_timestamp = None
        self.player.forward_10s()
        self.assertIsNone(self.player.play_timestamp)

    @patch('spoppy.players.Player.is_playing')
    @patch('spoppy.players.time')
    def test_plays_when_paused(self, patched_time, patched_is_playing):
        self.player.player = Mock()
        patched_is_playing.return_value = False
        patched_time.time.return_value = 100

        self.assertEqual(self.player.play_pause(), responses.NOOP)

        self.player.player.play.assert_called_once_with()
        self.player.player.pause.assert_not_called()

    @patch('spoppy.players.Player.is_playing')
    @patch('spoppy.players.time')
    def test_pauses_when_playing(self, patched_time, patched_is_playing):
        self.player.player = Mock()
        self.player.play_timestamp = 0
        patched_is_playing.return_value = True
        patched_time.time.return_value = 100

        self.assertEqual(self.player.play_pause(), responses.NOOP)

        self.player.player.pause.assert_called_once_with()
        self.player.player.play.assert_not_called()

        self.assertEqual(self.player.seconds_played, 100)
        self.assertIsNone(self.player.play_timestamp)

    @patch('spoppy.players.Player.play_current_song')
    @patch('spoppy.players.Player.get_prev_idx')
    def test_play_prev_song(self, patched_get_prev_idx, patched_play_current):
        patched_get_prev_idx.return_value = 7
        self.assertEqual(self.player.previous_song(), responses.NOOP)

        self.assertEqual(self.player.current_track_idx, 7)
        patched_play_current.assert_called_once_with()

    @patch('spoppy.players.Player.get_played_seconds')
    @patch('spoppy.players.Player.play_current_song')
    @patch('spoppy.players.Player.get_prev_idx')
    def test_prev_restarts_after_some_time(
        self,
        patched_get_prev_idx,
        patched_play_current,
        patched_get_played_seconds
    ):
        patched_get_played_seconds.return_value = 6
        patched_get_prev_idx.return_value = 7
        self.player.current_track_idx = 1
        self.assertEqual(self.player.previous_song(), responses.NOOP)

        self.assertEqual(self.player.current_track_idx, 1)
        patched_play_current.assert_called_once_with(clean_temporary=False)

    @patch('spoppy.players.Player.play_current_song')
    @patch('spoppy.players.Player.get_next_idx')
    def test_play_next_song(self, patched_get_next_idx, patched_play_current):
        patched_get_next_idx.return_value = 7

        self.assertEqual(self.player.next_song(), responses.NOOP)

        self.assertEqual(self.player.current_track_idx, 7)
        patched_play_current.assert_called_once_with()

    @patch('spoppy.players.Player.play_current_song')
    def test_remove_current_track(self, patched_play_current):
        track_to_remove = utils.Track('foo', ['bar'])
        song_list = [
            utils.Track('A', ['A']),
            utils.Track('B', ['B']),
            track_to_remove,
            utils.Track('C', ['C']),
            utils.Track('D', ['D']),
        ]
        playlist = utils.Playlist('Playlist 1', song_list)

        self.player.load_playlist(playlist)

        self.assertEqual(len(self.player.song_list), len(song_list))
        self.assertEqual(len(self.player.song_order), len(song_list))
        self.assertIsNotNone(self.player.playlist)

        self.player.current_track_idx = song_list.index(track_to_remove)

        self.assertIn(track_to_remove, self.player.song_list)

        self.assertEqual(self.player.remove_current_song(), responses.NOOP)

        self.assertNotIn(track_to_remove, self.player.song_list)

        self.assertEqual(len(self.player.song_list), len(song_list) - 1)
        self.assertEqual(len(self.player.song_order), len(song_list) - 1)

        patched_play_current.assert_called_once_with()
        self.assertIsNone(self.player.playlist)

    @patch('spoppy.players.Player.play_current_song')
    def test_starts_beginning_if_last_song_removed(self, patched_play_current):
        track_to_remove = utils.Track('foo', ['bar'])
        song_list = [
            utils.Track('A', ['A']),
            utils.Track('B', ['B']),
            utils.Track('C', ['C']),
            utils.Track('D', ['D']),
            track_to_remove,
        ]
        playlist = utils.Playlist('Playlist 1', song_list)

        self.player.load_playlist(playlist)

        self.player.current_track_idx = song_list.index(track_to_remove)

        self.assertEqual(self.player.remove_current_song(), responses.NOOP)

        patched_play_current.assert_called_once_with()
        self.assertEqual(self.player.current_track_idx, 0)

    @patch('spoppy.players.Player.play_current_song')
    def test_remove_song_doesnt_raise_with_empty_q(self, patched_play_current):
        song_list = [
        ]
        playlist = utils.Playlist('Playlist 1', song_list)

        self.player.load_playlist(playlist)
        self.player.current_track_idx = 0
        self.assertEqual(self.player.remove_current_song(), responses.NOOP)

        patched_play_current.assert_not_called()
        self.assertEqual(self.player.current_track_idx, 0)

    def test_shuffle(self):
        # Testing that shuffle maintains the currently playing song
        # is kind of impossible, just testing that the shuffle flag toggles
        self.assertEqual(self.player.shuffle, False)
        self.assertEqual(self.player.toggle_shuffle(), responses.NOOP)
        self.assertEqual(self.player.shuffle, True)
        self.assertEqual(self.player.toggle_shuffle(), responses.NOOP)
        self.assertEqual(self.player.shuffle, False)

    @patch('spoppy.players.Player.clear')
    def test_stop_and_clear(self, patched_clear):
        self.player.player = Mock()
        self.assertEqual(self.player.stop_and_clear(), responses.UP)
        patched_clear.assert_called_once_with()
        self.player.player.unload.assert_called_once_with()

    def test_toggle_repeat(self):
        seen_repeat_flags = []
        for i in range(len(players.Player.REPEAT_OPTIONS)):
            self.assertEqual(self.player.toggle_repeat(), responses.NOOP)
            seen_repeat_flags.append(self.player.repeat)
        self.assertEqual(
            sorted(players.Player.REPEAT_OPTIONS),
            sorted(seen_repeat_flags)
        )

    @patch('spoppy.players.Player.play_current_song')
    def test_add_track_to_queue(self, patched_play_current_song):
        track = MagicMock(spec=spotify.Track)
        self.player.playlist = 'foo'
        self.assertIsNone(self.player.current_track)
        self.assertIsNone(self.player.add_to_queue(track))
        self.assertIn(track, self.player.song_list)
        self.assertIsNone(self.player.playlist)
        patched_play_current_song.assert_called_once_with(start_playing=False)

    @patch('spoppy.players.Player.play_current_song')
    def test_add_playlist_to_queue(self, patched_play_current_song):
        tracks = [
            MagicMock(spec=spotify.Track),
            MagicMock(spec=spotify.Track),
            MagicMock(spec=spotify.Track),
        ]
        for track in tracks:
            track.availability = spotify.TrackAvailability.AVAILABLE
        playlist = MagicMock(spec=spotify.Playlist)
        playlist.tracks = tracks
        self.player.playlist = 'foo'
        self.assertIsNone(self.player.add_to_queue(playlist))
        for track in tracks:
            self.assertIn(track, self.player.song_list)
        self.assertIsNone(self.player.playlist)
        self.assertEqual(patched_play_current_song.call_count, 3)
        patched_play_current_song.assert_called_with(start_playing=False)

    @patch('spoppy.players.Player.next_song')
    @patch('spoppy.players.Player.play_current_song')
    def test_check_end_of_track_doesnt_do_anything_if_song_is_playing(
        self, patched_play_current, patched_next_song
    ):
        self.player.end_of_track = Mock()
        self.player.end_of_track.is_set.return_value = False
        self.player.check_end_of_track()
        patched_play_current.assert_not_called()
        patched_next_song.assert_not_called()

    @patch('spoppy.players.Player.next_song')
    @patch('spoppy.players.Player.play_current_song')
    def test_check_end_of_track_plays_next_song(
        self, patched_play_current, patched_next_song
    ):
        self.player.end_of_track = Mock()
        self.player.end_of_track.is_set.return_value = True
        self.player.repeat = 'all'
        self.player.check_end_of_track()
        patched_play_current.assert_not_called()
        patched_next_song.assert_called_once_with()

    @patch('spoppy.players.Player.next_song')
    @patch('spoppy.players.Player.play_current_song')
    def test_check_end_of_track_plays_current_song(
        self, patched_play_current, patched_next_song
    ):
        self.player.end_of_track = Mock()
        self.player.end_of_track.is_set.return_value = True
        self.player.repeat = 'one'
        self.player.check_end_of_track()
        patched_play_current.assert_called_once_with()
        patched_next_song.assert_not_called()

    def test_get_next_prev_idx_raises_with_empty_queue(self):
        with self.assertRaises(RuntimeError):
            self.player.get_next_idx()
        with self.assertRaises(RuntimeError):
            self.player.get_prev_idx()

    def test_get_next_idx_wraps(self):
        self.player.song_order = [1, 2, 3]
        self.player.current_track_idx = 2
        self.assertEqual(self.player.get_next_idx(), 0)

    def test_get_prev_idx_wraps(self):
        self.player.song_order = [1, 2, 3]
        self.player.current_track_idx = 0
        self.assertEqual(self.player.get_prev_idx(), 2)

    @patch('spoppy.players.Player.set_song_order_by_shuffle')
    def test_load_playlist(self, patched_set_shuffle):
        song_list = [
            utils.Track('A', ['A']),
            utils.Track('B', ['B']),
            utils.Track('C', ['C']),
            utils.Track('D', ['D']),
        ]
        playlist = utils.Playlist('Playlist 1', song_list)

        self.player.load_playlist(playlist)

        self.assertEqual(self.player.playlist, playlist)
        self.assertEqual(len(self.player.song_list), len(song_list))

        for i in range(len(song_list)):
            # Test that order is maintained
            self.assertEqual(song_list[i], self.player.song_list[i])

    def test_load_playlist_sets_shuffle(self):
        self.player.load_playlist(utils.Playlist('foo', []), shuffle=True)
        self.assertEqual(self.player.shuffle, True)
        self.player.load_playlist(utils.Playlist('foo', []))
        self.assertEqual(self.player.shuffle, True)
        self.player.load_playlist(utils.Playlist('foo', []), shuffle=False)
        self.assertEqual(self.player.shuffle, False)
        self.player.load_playlist(utils.Playlist('foo', []))
        self.assertEqual(self.player.shuffle, False)

    def test_load_playlist_does_not_load_unplayable_tracks(self):
        track_a = utils.Track('A', ['A'])
        track_b = utils.Track('C', ['C'])
        song_list = [
            track_a,
            utils.Track('B', ['B'], available=False),
            track_b,
            utils.Track('D', ['D'], available=False),
        ]
        playlist = utils.Playlist('Playlist 1', song_list)

        self.player.load_playlist(playlist)

        self.assertEqual(self.player.playlist, playlist)
        self.assertEqual(len(self.player.song_list), 2)
        self.assertIn(track_a, self.player.song_list)
        self.assertIn(track_b, self.player.song_list)

    @patch('spoppy.players.thread')
    def test_on_end_of_track(self, patched__thread):
        self.player.end_of_track = Mock()
        self.player.on_end_of_track()
        self.player.end_of_track.set.assert_called_once_with()
        patched__thread.interrupt_main.assert_called_once_with()

    @patch('spoppy.players.threading')
    @patch('spoppy.players.Player.get_track_by_idx')
    @patch('spoppy.players.get_duration_from_s')
    @patch('spoppy.players.Player.play_pause')
    def test_play_current_song(
        self, patched_play_pause, patched_get_duration, patched_get_track,
        patched_threading
    ):
        self.player.player = Mock()
        self.player.session = Mock()
        patched_track = Mock()
        TrackLoaded = namedtuple('TrackLoaded', ('duration', 'name'))
        track_loaded = TrackLoaded(1, 'foo')
        patched_track.load.return_value = track_loaded
        patched_track.artists = []
        patched_threading.Event.return_value = 'Event'
        patched_get_track.return_value = patched_track
        patched_get_duration.return_value = 'Duration'

        self.assertIsNone(self.player.play_current_song())

        # Unloads previously playing song
        self.player.player.unload.assert_called_once_with()

        self.assertEqual(self.player.end_of_track, 'Event')
        patched_track.load.assert_called_once_with()
        self.assertEqual(self.player.current_track, track_loaded)
        self.assertEqual(self.player.current_track_duration, 'Duration')

        patched_play_pause.assert_called_once_with()
        self.assertEqual(self.player.seconds_played, 0)

        self.player.session.on.assert_called_once_with(
            spotify.SessionEvent.END_OF_TRACK,
            self.player.on_end_of_track
        )

    @patch('spoppy.players.threading')
    @patch('spoppy.players.Player.get_track_by_idx')
    def test_play_current_song_handles_empty_queue(
        self, patched_get_track, patched_threading
    ):
        self.player.player = Mock()
        patched_get_track.return_value = None
        self.player.play_current_song()
        self.assertIsNone(self.player.current_track)
        patched_threading.Event.assert_not_called()

    @patch('spoppy.players.random')
    def test_set_song_order_by_shuffle(self, patched_random):
        original = [1, 2, 3, 4, 5]
        self.player.song_list = [1, 2, 3, 4, 5]
        self.player.shuffle = False
        self.player.set_song_order_by_shuffle()

        self.assertEqual(
            len(self.player.song_list), len(self.player.song_order)
        )
        self.assertEqual(
            len(original), len(self.player.song_order)
        )

        patched_random.shuffle.assert_not_called()

        self.player.shuffle = True

        self.player.set_song_order_by_shuffle()

        self.assertEqual(
            len(self.player.song_list), len(self.player.song_order)
        )
        self.assertEqual(
            len(original), len(self.player.song_order)
        )

        patched_random.shuffle.assert_called_once_with(self.player.song_order)

    @patch('spoppy.players.Player.play_current_song')
    def test_play_track_by_idx(self, patched_play_current):
        self.player.song_order = [0, 1, 2, 3]

        self.player.play_track(0)
        patched_play_current.assert_called_once_with()
        self.assertEqual(self.player.current_track_idx, 0)

        patched_play_current.reset_mock()

        self.player.song_order = [2, 1, 3, 0]

        self.player.play_track(0)
        patched_play_current.assert_called_once_with()
        self.assertEqual(self.player.current_track_idx, 3)

        with self.assertRaises(ValueError):
            self.player.play_track(None)

    @patch('spoppy.players.SavePlaylist')
    def test_save_as_playlist(self, patched_saveplaylist):
        SavePlaylist = Mock()
        patched_saveplaylist.return_value = SavePlaylist
        self.player.playlist = 'Something'

        self.assertEqual(self.player.save_as_playlist(), SavePlaylist)
        self.assertEqual(self.player.song_list, SavePlaylist.song_list)
        self.assertTrue(callable(SavePlaylist.callback))

        playlist = Mock()
        playlist.name = 'foobar'
        SavePlaylist.callback(playlist)
        self.assertEqual(self.player.playlist, playlist)
        self.assertEqual(self.player.original_playlist_name, 'foobar')

        self.player.playlist = None

        self.assertEqual(self.player.save_as_playlist(), SavePlaylist)
        self.assertEqual(self.player.song_list, SavePlaylist.song_list)

        self.assertTrue(callable(SavePlaylist.callback))

        SavePlaylist.callback(playlist)
        self.assertEqual(self.player.playlist, playlist)
        self.assertEqual(self.player.original_playlist_name, 'foobar')

    @patch('spoppy.players.get_duration_from_s')
    def test_get_total_playlist_length(self, patched_get_duration_from_s):
        # total length of list is 71000 ms = 71 s
        expected_duration = 'Expected this duration message'
        patched_get_duration_from_s.return_value = expected_duration
        self.player.song_list = [
            utils.Track('', '', duration=1000),
            utils.Track('', '', duration=10000),
            utils.Track('', '', duration=60000),
        ]
        result = self.player.get_total_playlist_length()
        patched_get_duration_from_s.assert_called_once_with(
            71, max_length=None
        )
        self.assertEquals(result, expected_duration)

    def test_clean_temporary_song_does_nothing_when_no_temp_song(self):
        self.assertIsNone(self.player.clean_temporary_song())

    def test_song_is_removed_if_is_temporary(self):
        track_should_be_there = [utils.Track('Hey im here', 'duran')]
        track_2_should_be_there = [utils.Track('Hey im here also', 'duran')]
        track_should_not_be_there = [utils.Track('Im gone', 'Brynja')]
        self.player.song_list = [
            track_should_be_there,
            track_should_not_be_there,
            track_2_should_be_there
        ]
        self.player.current_track_idx = 1
        self.player.temporary_song = 1
        self.player.song_order = [0, 1, 2]

        # We want track_2_should_be_there to be selected after removal
        self.assertIsNone(self.player.clean_temporary_song())
        self.assertEquals(len(self.player.song_order), 2)
        self.assertEquals(len(self.player.song_list), 2)
        self.assertIn(track_should_be_there, self.player.song_list)
        self.assertIn(track_2_should_be_there, self.player.song_list)
        self.assertNotIn(track_should_not_be_there, self.player.song_list)
        self.assertEquals(self.player.current_track_idx, 1)

    @patch('spoppy.players.Player.play_current_song')
    def test_duplicate_current_track(self, patched_play_current):
        track_to_duplicate = utils.Track('foo', ['bar'])
        song_list = [
            utils.Track('A', ['A']),
            utils.Track('B', ['B']),
            track_to_duplicate,
            utils.Track('C', ['C']),
            utils.Track('D', ['D']),
        ]
        playlist = utils.Playlist('Playlist 1', song_list)

        self.player.load_playlist(playlist)

        self.assertEqual(len(self.player.song_list), len(song_list))
        self.assertEqual(len(self.player.song_order), len(song_list))
        self.assertIsNotNone(self.player.playlist)

        self.player.current_track_idx = song_list.index(track_to_duplicate)
        current_track_before = self.player.current_track_idx

        self.assertIn(track_to_duplicate, self.player.song_list)

        self.assertEqual(self.player.duplicate_current_song(), responses.NOOP)

        self.assertEquals(len(self.player.song_list), len(song_list) + 1)
        self.assertEquals(self.player.song_list.count(track_to_duplicate), 2)
        self.assertEquals(self.player.current_track_idx, current_track_before)
        patched_play_current.assert_not_called()

        self.assertIsNone(self.player.playlist)
