import logging
from collections import defaultdict
import random
import threading
import time
import _thread

import spotify

from .responses import NOOP, UP
from .util import single_char_with_timeout, format_track

logger = logging.getLogger(__name__)


class Player(object):

    REPEAT_OPTIONS = ['all', 'one']

    shuffle = False
    repeat = REPEAT_OPTIONS[0]

    # Initialization and external helpers
    def __init__(self, navigator):
        '''
        Initialize the player. Navigator must be an instance of
        `spoppy.navigation.Leifur`.
        '''
        self.navigator = navigator
        self._initialized = False
        self.end_of_track = None

        self.clear()
        self.actions = {
            b'n': self.next_song,
            b'\xc3\xa6': self.next_song,
            b'p': self.previous_song,
            b'j': self.previous_song,
            b' ': self.play_pause,
            b'u': UP,
            b'q': self.stop_and_clear,
            b'd': self.debug,
            b's': self.toggle_shuffle,
            b'r': self.toggle_repeat,
            b'k': self.backward_10s,
            b'l': self.forward_10s,
            b'h': self.get_help,
            b'x': self.remove_current_song,
        }
        key_names = {
            b' ': 'space'
        }
        self.reversed_actions = defaultdict(list)
        for key, value in self.actions.items():
            if isinstance(value, str):
                action_name = value
            else:
                action_name = value.__name__
            self.reversed_actions[action_name].append(
                key_names.get(key) or key.decode('utf-8')
            )

    def clear(self):
        '''
        Resets all variables used for playlist/queue handling to their default
        values.
        :returns: None
        '''
        self.current_track_idx = 0
        self.current_track = None
        self.seconds_played = 0
        self.play_timestamp = None
        self.song_order = []
        self.current_track_duration = ''
        self.repeat = self.REPEAT_OPTIONS[0]
        self.shuffle = False
        self.show_help = False
        self.playlist = None
        self.song_list = []
        self._trigger_redraw = False

    def has_been_loaded(self):
        '''
        Used to determine if some songs are loaded in the player
        :returns: True if there are any songs in the player's queue
        '''
        return bool(len(self.song_list))

    def initialize(self):
        '''
        Initializes some class variables for simpler access to the spotify
        player. `PySpotify` session must have been initialized before calling
        initialize, and initialize must be called before playing anything.
        :returns: None
        '''
        if not self._initialized:
            # For quicker access
            self.session = self.navigator.session
            self.player = self.session.player
            self._initialized = True

    def is_playing(self):
        '''
        Used to determine if the `PySpotify` player is is currently playing
        :returns: True if the player is currently playing
        '''
        return self.player.state == 'playing'

    # UI specific
    def get_duration_from_s(self, s):
        '''
        Formats seconds as "%M:%S"
        :param s: Seconds in int/float
        :returns: s formatted as "%M:%S"
        '''
        return '%s:%s' % (
            str(int(s / 60)).zfill(2),
            str(int(s % 60)).zfill(2)
        )

    def get_help_ui(self):
        '''
        Gets menu items explaining the use of hotkeys within the player
        :returns: List of hotkeys and their corresponding actions
        '''
        res = []
        res.append('')
        for action, hotkeys in sorted(self.reversed_actions.items()):
            res.append(
                '[%s]: %s' % (
                    '/'.join(hotkeys),
                    action
                )
            )
        return res

    def get_progress(self):
        '''
        Get the progress of the currently playing song
        :returns: 4-item tuple, (player_state,
                                 minutes_played,
                                 percent_played,
                                 current_track_duration)
        '''
        seconds_played = self.seconds_played
        if self.play_timestamp:
            # We are actually playing and we have to calculate the number of
            # seconds since we last pressed play
            seconds_played += time.time() - self.play_timestamp

        # pyspotify's duration is in ms
        percent_played = (seconds_played * 1000) / self.current_track.duration
        mins_played = self.get_duration_from_s(seconds_played)

        return (
            self.player.state,
            mins_played,
            percent_played,
            self.current_track_duration
        )

    def get_response(self):
        # This is actually our game loop... because fuck you that's why
        response = NOOP
        while response == NOOP:
            self.session.process_events()
            end_of_track_response = self.check_end_of_track()
            if end_of_track_response:
                return end_of_track_response
            if self.current_track:
                self.navigator.update_progress(*self.get_progress())
            char = single_char_with_timeout(timeout=1.5)
            if char:
                logger.debug('Got some char: %s' % char)
            response = self.actions.get(char, NOOP)
            if response != NOOP:
                if callable(response):
                    evaluated_response = response()
                    if evaluated_response:
                        return evaluated_response
                    # We have handled the response ourselves
                    response = NOOP
                else:
                    return response
            if self._trigger_redraw:
                self._trigger_redraw = False
                return NOOP

    def get_ui(self):
        res = []
        res.append('Press h for help')
        if self.playlist:
            res.append('Playing playlist: %s' % self.playlist.name)
        if self.show_help:
            res += self.get_help_ui()

        res.append('')

        if self.current_track:
            # We can show number of items - current items - currently playing
            max_number_of_items = self.navigator.get_ui_height() - len(res) - 3
            if self.current_track_idx == 0:
                max_number_of_items += 1
            if self.current_track_idx == len(self.song_list) - 1:
                max_number_of_items += 1
            previous_items_to_show = min([
                int(max_number_of_items / 2),
                self.current_track_idx
            ])
            next_items_to_show = min([
                max_number_of_items - previous_items_to_show,
                len(self.song_list[self.current_track_idx:])
            ])
            total_number_to_show = previous_items_to_show + next_items_to_show
            if total_number_to_show < max_number_of_items:
                previous_items_to_show = min([
                    max_number_of_items - next_items_to_show,
                    len(self.song_list[:self.current_track_idx])

                ])
            right_side_items = [
                'Shuffle on' if self.shuffle else '',
                'Repeat: %s' % self.repeat,
            ]
            songs_to_show = (
                list(range(
                    self.current_track_idx - previous_items_to_show,
                    self.current_track_idx
                )) +
                [self.current_track_idx] +
                list(range(
                    self.current_track_idx + 1,
                    self.current_track_idx + next_items_to_show
                ))
            )
            for song_idx in songs_to_show:
                song = self.get_track_by_idx(song_idx)
                right_side = right_side_items and right_side_items.pop()
                if song_idx == self.current_track_idx:
                    if song_idx != songs_to_show[0]:
                        # Small spacing around current...
                        res.append(('', right_side or ''))
                        right_side = (
                            right_side_items and right_side_items.pop()
                        )
                    formatted_song = '>>>%s' % format_track(song)
                else:
                    formatted_song = format_track(song)
                res.append((formatted_song, right_side or ''))
                if song_idx == self.current_track_idx:
                    if song_idx != songs_to_show[-1]:
                        # Small spacing around current...
                        right_side = (
                            right_side_items and right_side_items.pop()
                        )
                        res.append(('', right_side or ''))
            while right_side_items:
                # This can happend f.x. when we have one song...
                res.append(('', right_side_items.pop()))
        else:
            res.append('No songs found in playlist!')

        return res

    def trigger_redraw(self):
        self._trigger_redraw = True

    # Event handlers
    def backward_10s(self):
        if self.play_timestamp:
            self.seconds_played += time.time() - self.play_timestamp
            self.play_timestamp = time.time()
        self.seconds_played -= 10
        self.player.seek(int(self.seconds_played * 1000))

    def debug(self):
        import pdb
        pdb.set_trace()

    def forward_10s(self):
        if self.play_timestamp:
            self.seconds_played += time.time() - self.play_timestamp
            self.play_timestamp = time.time()
        self.seconds_played += 10
        self.player.seek(int(self.seconds_played * 1000))

    def get_help(self):
        self.show_help = not self.show_help
        return NOOP

    def next_song(self):
        self.current_track_idx = self.get_next_idx()
        self.play_current_song()
        return NOOP

    def play_pause(self):
        if not self.is_playing():
            self.player.play()
            self.play_timestamp = time.time()
        else:
            self.player.pause()
            self.seconds_played += time.time() - self.play_timestamp
            self.play_timestamp = None
        return NOOP

    def previous_song(self):
        self.current_track_idx = self.get_prev_idx()
        self.play_current_song()
        return NOOP

    def remove_current_song(self):
        idx_in_song_list = self.song_order[self.current_track_idx]
        del self.song_order[self.current_track_idx]

        del self.song_list[idx_in_song_list]

        for idx, item in enumerate(self.song_order):
            if item > idx_in_song_list:
                self.song_order[idx] -= 1

        if self.current_track_idx >= len(self.song_order):
            self.previous_song()
        else:
            self.play_current_song()
        self.playlist = None
        return NOOP

    def stop_and_clear(self):
        self.player.unload()
        self.clear()
        return UP

    def toggle_shuffle(self):
        # We also have to update the current_track_idx too here since
        # the order is changing
        self.shuffle = not self.shuffle
        if self.current_track_idx <= len(self.song_order):
            currently_playing = self.song_order[self.current_track_idx]
        self.set_song_order_by_shuffle()
        if currently_playing in self.song_order:
            self.current_track_idx = self.song_order.index(currently_playing)
        return NOOP

    def toggle_repeat(self):
        new_idx = self.REPEAT_OPTIONS.index(self.repeat) + 1
        if new_idx >= len(self.REPEAT_OPTIONS):
            new_idx = 0
        self.repeat = self.REPEAT_OPTIONS[new_idx]
        return NOOP

    # Song handling
    def add_to_queue(self, item):
        if isinstance(item, spotify.Track):
            # Add the newest track_idx to the song order
            self.song_order.append(len(self.song_order))
            # Add the song to the current song list
            self.song_list.append(item)
        elif isinstance(item, spotify.Playlist):
            for track in item.tracks:
                if track.availability != spotify.TrackAvailability.UNAVAILABLE:
                    self.add_to_queue(track)
        self.playlist = None

    def check_end_of_track(self):
        if self.end_of_track and self.end_of_track.is_set():
            if self.repeat == 'all':
                self.next_song()
                return NOOP
            elif self.repeat == 'one':
                self.play_current_song()

    def get_next_idx(self):
        current_track_idx = self.current_track_idx + 1
        if current_track_idx >= len(self.song_order):
            current_track_idx = 0
        return current_track_idx

    def get_prev_idx(self):
        current_track_idx = self.current_track_idx - 1
        if current_track_idx < 0:
            current_track_idx = len(self.song_order) - 1
        return current_track_idx

    def get_track_by_idx(self, idx):
        try:
            song_index = self.song_order[idx]
            return self.song_list[song_index]
        except IndexError:
            return None

    def load_playlist(self, playlist, shuffle=None):
        self.clear()
        self.song_list = [
            track for track in
            playlist.tracks
            if track.availability != spotify.TrackAvailability.UNAVAILABLE
        ]
        self.playlist = playlist
        if shuffle is not None:
            self.shuffle = shuffle
        self.set_song_order_by_shuffle()

    def on_end_of_track(self, session):
        self.end_of_track.set()
        _thread.interrupt_main()

    def play_current_song(self):
        self.player.unload()
        self.end_of_track = threading.Event()

        current_track = self.get_track_by_idx(self.current_track_idx)
        if not current_track:
            self.current_track = None
            return
        self.current_track = current_track.load()

        self.current_track_duration = self.get_duration_from_s(
            self.current_track.duration / 1000
        )

        self.player.load(self.current_track)
        self.play_pause()

        self.seconds_played = 0

        logger.debug('Playing track %s' % self.current_track.name)

        # Register event listeners
        self.session.on(
            spotify.SessionEvent.END_OF_TRACK,
            self.on_end_of_track
        )

    def play_track(self, track_idx):
        self.current_track_idx = self.song_order.index(track_idx)
        self.play_current_song()

    def set_song_order_by_shuffle(self):
        self.song_order = list(range(len(self.song_list)))
        if self.shuffle:
            random.shuffle(self.song_order)
