import logging
from collections import defaultdict
import random
import threading
import time

try:
    import thread
except ImportError:
    import _thread as thread

import spotify

from .responses import NOOP, UP
from .util import (
    single_char_with_timeout, format_track, get_duration_from_s,
    artist_banned_text
)
from .menus import SavePlaylist, SongSelectedWhilePlaying

logger = logging.getLogger(__name__)


class Player(object):

    REPEAT_OPTIONS = ['all', 'one']
    DISCONNECTED_INDICATOR = 'disconnected'

    shuffle = False
    repeat = REPEAT_OPTIONS[0]
    original_playlist_name = None

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
            b'l': self.next_song,
            b'p': self.previous_song,
            b'h': self.previous_song,
            b' ': self.play_pause,
            b'u': UP,
            b'q': self.stop_and_clear,
            b'd': self.debug,
            b's': self.toggle_shuffle,
            b'r': self.toggle_repeat,
            b'j': self.backward_10s,
            b'k': self.forward_10s,
            b'?': self.get_help,
            b'x': self.remove_current_song,
            b'w': self.save_as_playlist,
            b'i': self.show_song_info,
            b'\x1b[A': self.move_song_up,
            b'\x1b[B': self.move_song_down,
        }
        key_names = {
            b' ': 'space',
            b'\x1b[A': 'up arrow',
            b'\x1b[B': 'down arrow',
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
        self.state = None

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
        self.show_help = False
        self.playlist = None
        self.song_list = []
        self._trigger_redraw = False
        self.temporary_song = None

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
        return self.player.state == spotify.PlayerState.PLAYING

    # UI specific
    def get_help_ui(self):
        '''
        Gets menu items explaining the use of hotkeys within the player
        :returns: List of hotkeys and their corresponding actions
        '''
        res = []
        res.append('')
        for action, hotkeys in sorted(self.reversed_actions.items()):
            if self.shuffle and action.startswith('move_song'):
                # Moving songs is not available when we are shuffling
                continue
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
        if self.play_timestamp is not None:
            # We are actually playing and we have to calculate the number of
            # seconds since we last pressed play
            seconds_played += time.time() - self.play_timestamp

        # pyspotify's duration is in ms
        percent_played = (seconds_played * 1000) / float(
            self.current_track.duration
        )
        mins_played = get_duration_from_s(seconds_played)

        return (
            self.state or self.player.state,
            mins_played,
            percent_played,
            self.current_track_duration
        )

    def get_response(self):
        '''
        Get destination from user and dispatch the event.
        Possibly the event will be handled within the player itself and until
        there comes an event not handled by the player it will block.
        :returns: Destination for the user
        '''
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
                char = char.lower()
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
        '''
        Get the UI representing the player's current state
        :returns: List of lines that should be shown. If an item is a 2-item
                  tuple the first one should be left aligned and the second
                  one should be right aligned.
        '''
        res = []
        res.append('Press ? for help')
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
                '%d of %d' % (
                    self.current_track_idx + 1, len(self.song_order)
                ),
                'Total playlist length: %s' % self.get_total_playlist_length(),
                'Repeat: %s' % self.repeat,
                'Shuffle on' if self.shuffle else '',
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
                right_side = right_side_items and right_side_items.pop(0)
                extra_text = (
                    artist_banned_text(self.navigator, song) or
                    (
                        self.song_order[song_idx] == self.temporary_song and
                        '[temporary]'
                    )
                )
                if song_idx == self.current_track_idx:
                    if song_idx != songs_to_show[0]:
                        # Small spacing around current...
                        res.append(('', right_side or ''))
                        right_side = (
                            right_side_items and right_side_items.pop(0)
                        )
                    formatted_song = '>>>%s' % format_track(song, extra_text)
                else:
                    formatted_song = format_track(song, extra_text)
                res.append((formatted_song, right_side or ''))
                if song_idx == self.current_track_idx:
                    if song_idx != songs_to_show[-1]:
                        # Small spacing around current...
                        right_side = (
                            right_side_items and right_side_items.pop(0)
                        )
                        res.append(('', right_side or ''))
            while right_side_items:
                # This can happend f.x. when we have one song...
                res.append(('', right_side_items.pop(0)))
        else:
            res.append('No songs found in playlist!')

        return res

    def get_total_playlist_length(self):
        total_seconds = sum([song.duration for song in self.song_list]) / 1000
        return get_duration_from_s(total_seconds, max_length=None)

    def trigger_redraw(self):
        '''
        Tell the player to trigger a full redraw in the next loop.
        :returns: None
        '''
        self._trigger_redraw = True

    # Event handlers
    def backward_10s(self):
        '''
        Seeks the current song 10 seconds back
        :returns: None
        '''
        if self.play_timestamp is not None:
            self.seconds_played += time.time() - self.play_timestamp
            self.play_timestamp = time.time()
        self.seconds_played -= 10
        if self.seconds_played < 0:
            self.seconds_played = 0
        self.player.seek(int(self.seconds_played * 1000))

    def debug(self):
        '''
        Start a debugger to inspect the player's current state
        :returns: None
        '''
        import pdb
        pdb.set_trace()

    def forward_10s(self):
        '''
        Seeks the current song 10 seconds forward
        :returns: None
        '''
        if self.play_timestamp is not None:
            self.seconds_played += time.time() - self.play_timestamp
            self.play_timestamp = time.time()
        self.seconds_played += 10
        self.player.seek(int(self.seconds_played * 1000))

    def get_help(self):
        '''
        Tell the player to display the help section
        :returns: responses.NOOP
        '''
        self.show_help = not self.show_help
        return NOOP

    def move_song_down(self):
        '''
        Move the currently playing song up one place in the song order.
        If the player is in shuffle mode it does absolutely nothing!
        :returns: responses.NOOP
        '''
        if not self.shuffle:
            i = self.current_track_idx
            k = i + 1
            sl = self.song_list
            if k >= len(sl):
                k = 0
            sl[i], sl[k] = sl[k], sl[i]
            self.current_track_idx = k
        return NOOP

    def move_song_up(self):
        '''
        Move the currently playing song up one place in the song order.
        If the player is in shuffle mode it does absolutely nothing!
        :returns: responses.NOOP
        '''
        if not self.shuffle:
            i = self.current_track_idx
            k = i - 1
            sl = self.song_list
            if k < 0:
                k = len(sl) - 1
            sl[i], sl[k] = sl[k], sl[i]
            self.current_track_idx = k
        return NOOP

    def next_song(self):
        '''
        Plays the next song in the song list
        :returns: responses.NOOP
        '''
        self.current_track_idx = self.get_next_idx()
        self.play_current_song()
        return NOOP

    def play_pause(self):
        '''
        Pauses the current song if it's currently playing, otherwise pauses it.
        :returns: responses.NOOP
        '''
        if not self.is_playing():
            self.player.play()
            self.play_timestamp = time.time()
        else:
            self.player.pause()
            self.seconds_played += time.time() - self.play_timestamp
            self.play_timestamp = None
        return NOOP

    def previous_song(self):
        '''
        Plays the previous song in the song list
        :returns: responses.NOOP
        '''
        self.current_track_idx = self.get_prev_idx()
        self.play_current_song()
        return NOOP

    def remove_current_song(self):
        '''
        Removes the current song from the queue. Note that the song is not
        removed from the playlist itself.
        :returns: responses.NOOP
        '''
        if self.current_track_idx < len(self.song_order):
            idx_in_song_list = self.song_order[self.current_track_idx]
            del self.song_order[self.current_track_idx]

            del self.song_list[idx_in_song_list]

            for idx, item in enumerate(self.song_order):
                if item > idx_in_song_list:
                    self.song_order[idx] -= 1

            if self.current_track_idx >= len(self.song_order):
                self.current_track_idx = 0

            self.play_current_song()
            self.playlist = None
        return NOOP

    def save_as_playlist(self):
        '''
        Prompts the user for a name for a new playlist and allows him to
        save the queue as a new playlist.
        :returns: responses.NOOP if the queue has not been modified.
                  menus.SavePlaylist otherwise.
        '''
        def playlist_saved_callback(playlist):
            self.playlist = playlist
            self.original_playlist_name = playlist.name

        res = SavePlaylist(self.navigator)
        res.song_list = self.song_list
        res.original_playlist_name = self.original_playlist_name
        res.callback = playlist_saved_callback
        return res

    def show_song_info(self):
        '''
        Shows the same menu that would have been shown if the user selected
        the song from the menu
        :returns: menus.SongSelectedWhilePlaying if there is a song currently
                  playing, responses.NOOP otherwise
        '''
        if self.current_track:
            res = SongSelectedWhilePlaying(self.navigator)
            res.track = self.current_track
            res.playlist = self.playlist
            return res
        return NOOP

    def stop_and_clear(self):
        '''
        Stops the current song and clears the current song list, then exits
        the player.
        :returns: responses.UP
        '''
        self.player.unload()
        self.clear()
        return UP

    def toggle_shuffle(self):
        '''
        Puts shuffle mode on/off
        :returns: responses.NOOP
        '''
        # We also have to update the current_track_idx too here since
        # the order is changing
        self.shuffle = not self.shuffle
        currently_playing = None
        if self.current_track_idx < len(self.song_order):
            currently_playing = self.song_order[self.current_track_idx]
        self.set_song_order_by_shuffle()
        if currently_playing in self.song_order:
            self.current_track_idx = self.song_order.index(currently_playing)
        return NOOP

    def toggle_repeat(self):
        '''
        Toggles between available repeat options. See `Player.REPEAT_OPTIONS`
        :returns: responses.NOOP
        '''
        new_idx = self.REPEAT_OPTIONS.index(self.repeat) + 1
        if new_idx >= len(self.REPEAT_OPTIONS):
            new_idx = 0
        self.repeat = self.REPEAT_OPTIONS[new_idx]
        return NOOP

    # Song handling
    def add_play_then_remove(self, item):
        '''
        Adds item to the current queue temporary. After the song has been added
        it will start playing. Once it's finished or navigated from it, it will
        be removed and the song that was playing when it was added will start
        playing.
        temporary_song is the index to the currently temporary song in the
        song_list, not in song_order
        '''
        self.clean_temporary_song()
        idx_of_new_item = len(self.song_list)
        self.song_list.append(item)
        self.song_order.insert(self.current_track_idx, idx_of_new_item)
        self.temporary_song = idx_of_new_item
        self.play_current_song(start_playing=True, clean_temporary=False)

    def add_to_queue(self, item):
        '''
        Adds item to the end of the current song list. Item can be either
        a single track or a playlist.
        :returns: None
        '''
        if isinstance(item, spotify.Track):
            # Add the newest track_idx to the song order
            self.song_order.append(len(self.song_order))
            # Add the song to the current song list
            self.song_list.append(item)
            if not self.current_track:
                self.play_current_song(start_playing=False)
        elif hasattr(item, 'tracks'):
            for track in item.tracks:
                if track.availability != spotify.TrackAvailability.UNAVAILABLE:
                    self.add_to_queue(track)
        self.playlist = None

    def clean_temporary_song(self):
        '''
        If there is a temporary song in the queue, remove it from the song list
        and make sure that the song playing before it gets selected
        :returns: None
        '''
        if self.temporary_song:
            temporary_song_index = self.song_order.index(self.temporary_song)
            self.song_order.remove(self.temporary_song)
            del self.song_list[self.temporary_song]
            self.temporary_song = None
            if temporary_song_index < self.current_track_idx:
                # If the previous song came before the current (which happens
                # unless the user selected the previous song) we have to
                # select the previous song so we don't jump to the next one.
                self.current_track_idx = self.get_prev_idx()

    def check_end_of_track(self):
        '''
        Checks if the current song has finished playing and starts playing
        the next song according to the current repeat setting.
        :returns: None
        '''
        if self.end_of_track and self.end_of_track.is_set():
            if self.repeat == 'all':
                self.next_song()
                return NOOP
            elif self.repeat == 'one':
                self.play_current_song()

    def get_next_idx(self):
        '''
        Get the id of the next song. If currently on the last song it returns
        the first one.
        :returns: The id of the next song in queue.
        '''
        if not self.song_order:
            raise RuntimeError('No songs currently in queue')
        current_track_idx = self.current_track_idx + 1
        if current_track_idx >= len(self.song_order):
            current_track_idx = 0
        return current_track_idx

    def get_prev_idx(self):
        '''
        Get the id of the previous song. If currently on the first song it
        returns the last one.
        :returns: The id of the previous song in queue.
        '''
        if not self.song_order:
            raise RuntimeError('No songs currently in queue')
        current_track_idx = self.current_track_idx - 1
        if current_track_idx < 0:
            current_track_idx = len(self.song_order) - 1
        return current_track_idx

    def get_track_by_idx(self, idx):
        '''
        Get the track for the current idx. Uses the shuffle setting to
        determine the song.
        :param idx: The wanted track's position in the queue
        :returns: The `spotify.Track` that is number `idx` in the queue. If
                  `idx` is larger than the number of songs in the queue it
                  returns None
        '''
        try:
            song_index = self.song_order[idx]
            return self.song_list[song_index]
        except IndexError:
            return None

    def load_playlist(self, playlist, shuffle=None):
        '''
        Clears the current song list and replaces it with the playlists
        tracks
        :param playlist: A `spotify.Playlist` to load
        :param shuffle: Shuffle can be explicitly defined. Defaults to using
                        the shuffle setting that was set when the playlist
                        was loaded.
        :returns: None
        '''
        self.clear()
        self.song_list = [
            track for track in
            playlist.tracks
            if track.availability != spotify.TrackAvailability.UNAVAILABLE
        ]
        self.playlist = playlist
        self.original_playlist_name = self.playlist.name
        if shuffle is not None:
            self.shuffle = shuffle
        self.set_song_order_by_shuffle()

    def on_end_of_track(self, session=None):
        '''
        Sets the end of track event and signals the player something has
        happened.
        :param session: A `spotify.Session` (optional, not used)
        :returns: None
        '''
        self.end_of_track.set()
        thread.interrupt_main()
        return False

    def play_current_song(self, start_playing=True, clean_temporary=True):
        '''
        Plays the current song.
        Before playing these actions are performed:
            1. Removes the temporary song if there is one.
            2. If the current track's artist is banned, removes the current
               song.
        :returns: None
        '''
        self.player.unload()

        if clean_temporary:
            self.clean_temporary_song()

        current_track = self.get_track_by_idx(self.current_track_idx)
        if not current_track:
            self.current_track = None
            return

        for artist in current_track.artists:
            if self.navigator.is_artist_banned(artist):
                # Remove banned song from queue as soon as it's up
                return self.remove_current_song()

        self.end_of_track = threading.Event()
        self.current_track = current_track.load()

        self.current_track_duration = get_duration_from_s(
            self.current_track.duration / 1000
        )

        self.player.load(self.current_track)
        if start_playing and not self.state == self.DISCONNECTED_INDICATOR:
            self.play_pause()

        self.seconds_played = 0

        logger.debug('Playing track %s' % self.current_track.name)

        # Register event listeners
        self.session.on(
            spotify.SessionEvent.END_OF_TRACK,
            self.on_end_of_track
        )

    def play_track(self, track_idx):
        '''
        Plays the track that's number `track_idx` in the song list (note, not
        the song order)
        :param track_idx: The position of the desired track to play
        :returns: None
        '''
        self.current_track_idx = self.song_order.index(track_idx)
        self.play_current_song()

    def set_song_order_by_shuffle(self):
        '''
        Based on the current shuffle setting, shuffles the song list or not.
        :returns: None
        '''
        self.song_order = list(range(len(self.song_list)))
        if self.shuffle:
            random.shuffle(self.song_order)
