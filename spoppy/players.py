import logging
from collections import defaultdict
import random
import threading
import time

import spotify

from .responses import NOOP, QUIT, UP
from .util import single_char_with_timeout, format_track

logger = logging.getLogger(__name__)


class Player(object):

    REPEAT_OPTIONS = ['all', 'one']

    shuffle = False
    repeat = REPEAT_OPTIONS[0]

    def __init__(self, navigator):
        self.navigator = navigator
        self.clear()
        self.actions = {
            b'n': self.next_song,
            b'\xc3\xa6': self.next_song,
            b'p': self.previous_song,
            b'j': self.previous_song,
            b' ': self.play_pause,
            b'u': UP,
            b'q': QUIT,
            b'd': self.debug,
            b's': self.toggle_shuffle,
            b'r': self.toggle_repeat,
            b'k': self.backward_10s,
            b'l': self.forward_10s,
            b'h': self.get_help,
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

    def debug(self):
        import pdb
        pdb.set_trace()

    def initialize(self):
        pass

    def clear(self):
        self.current_track_idx = 0
        self.current_track = None
        self.seconds_played = 0
        self.play_timestamp = None
        self.song_order = []
        self.current_track_duration = ''
        self.repeat = self.REPEAT_OPTIONS[0]
        self.show_help = False

    def get_ui(self):
        res = []
        res.append((
            'Press h for help'
        ))
        if self.current_track:
            res.append(
                (
                    'Current song: %s' % format_track(self.current_track),
                    'Repeat: %s' % self.repeat
                )
            )
            next_track = self.get_track_by_idx(self.get_next_idx())
            res.append(
                (
                    'Next song: %s' % format_track(next_track),
                    'Shuffle on' if self.shuffle else ''
                )
            )
            previous_track = self.get_track_by_idx(self.get_prev_idx())
            res.append('Previous song: %s' % format_track(previous_track))
        if self.show_help:
            res.append('')
            for action, hotkeys in sorted(self.reversed_actions.items()):
                res.append(
                    '[%s]: %s' % (
                        '/'.join(hotkeys),
                        action
                    )
                )

        return res

    def get_help(self):
        self.show_help = not self.show_help
        return NOOP

    def next_song(self):
        self.current_track_idx = self.get_next_idx()
        self.play_current_song()
        return NOOP

    def get_next_idx(self):
        current_track_idx = self.current_track_idx + 1
        if current_track_idx >= len(self.song_order):
            current_track_idx = 0
        return current_track_idx

    def previous_song(self):
        self.current_track_idx = self.get_prev_idx()
        self.play_current_song()
        return NOOP

    def get_prev_idx(self):
        current_track_idx = self.current_track_idx - 1
        if current_track_idx < 0:
            current_track_idx = len(self.song_order) - 1
        return current_track_idx

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.song_order = list(range(len(self.song_list)))
        if self.shuffle:
            random.shuffle(self.song_order)
        return NOOP

    def toggle_repeat(self):
        new_idx = self.REPEAT_OPTIONS.index(self.repeat) + 1
        if new_idx >= len(self.REPEAT_OPTIONS):
            new_idx = 0
        self.repeat = self.REPEAT_OPTIONS[new_idx]
        return NOOP

    def play_pause(self):
        if self.navigator.session.player.state != 'playing':
            self.navigator.session.player.play()
            self.play_timestamp = time.time()
        else:
            self.navigator.session.player.pause()
            self.seconds_played += time.time() - self.play_timestamp
            self.play_timestamp = None
        return NOOP

    def get_track_by_idx(self, idx):
        song_index = self.song_order[idx]
        return self.song_list[song_index]

    def load_playlist(self, playlist, shuffle=False):
        self.clear()
        self.song_list = playlist.tracks
        self.playlist = playlist
        self.song_order = list(range(len(self.song_list)))
        if shuffle:
            logger.debug('Song order before: %s' % self.song_order)
            self.toggle_shuffle()
            logger.debug('Song order after: %s' % self.song_order)

    def play_track(self, track_idx):
        self.current_track_idx = track_idx
        self.play_current_song()

    def on_end_of_track(self, session):
        self.end_of_track.set()

    def backward_10s(self):
        if self.play_timestamp:
            self.seconds_played += time.time() - self.play_timestamp
            self.play_timestamp = time.time()
        self.seconds_played -= 10
        self.navigator.session.player.seek(int(self.seconds_played * 1000))
        return NOOP

    def forward_10s(self):
        if self.play_timestamp:
            self.seconds_played += time.time() - self.play_timestamp
            self.play_timestamp = time.time()
        self.seconds_played += 10
        self.navigator.session.player.seek(int(self.seconds_played * 1000))
        return NOOP

    def play_current_song(self):
        self.navigator.session.player.unload()
        self.end_of_track = threading.Event()

        current_track = self.get_track_by_idx(self.current_track_idx)
        self.current_track = current_track.load()

        self.current_track_duration = self.get_duration_from_s(
            self.current_track.duration / 1000
        )

        self.navigator.session.player.load(self.current_track)
        self.play_pause()

        self.seconds_played = 0

        logger.debug('Playing track %s' % self.current_track.name)

        # Register event listeners
        self.navigator.session.on(
            spotify.SessionEvent.END_OF_TRACK,
            self.on_end_of_track
        )

    def get_response(self):
        # This is actually our game loop... because fuck you that's why
        response = NOOP
        while response == NOOP:
            self.navigator.session.process_events()
            if self.end_of_track.is_set():
                if self.repeat == 'all':
                    self.next_song()
                    return NOOP
                elif self.repeat == 'one':
                    self.play_current_song()
            self.navigator.update_progress(*self.get_progress())
            char = single_char_with_timeout(timeout=1.5)
            if char:
                logger.debug('Got some char: %s' % char)
            response = self.actions.get(char, NOOP)
            if response != NOOP:
                if callable(response):
                    if response():
                        return NOOP
                    # We have handled the response ourselves
                    response = NOOP
                else:
                    return response

    def get_progress(self):
        seconds_played = self.seconds_played
        if self.play_timestamp:
            # We are actually playing and we have to calculate the number of
            # seconds since we last pressed play
            seconds_played += time.time() - self.play_timestamp

        # pyspotify's duration is in ms
        percent_played = (seconds_played * 1000) / self.current_track.duration
        mins_played = self.get_duration_from_s(seconds_played)

        return (
            self.navigator.session.player.state,
            mins_played,
            percent_played,
            self.current_track_duration
        )

    def get_duration_from_s(self, s):
        return '%s:%s' % (
            str(int(s / 60)).zfill(2),
            str(int(s % 60)).zfill(2)
        )
