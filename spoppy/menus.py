import logging

from spotify import TrackAvailability

from . import responses
from .util import format_track, single_char_with_timeout

logger = logging.getLogger(__name__)


class Options(dict):
    def __init__(self, *args, **kwargs):
        super(Options, self).__init__(*args, **kwargs)
        self._cached_matches = {}
        self._stripped_keys_mapper = {
            key.replace(' ', ''): key
            for key in self
        }

    def __setitem__(self, key, value):
        super(Options, self).__setitem__(key, value)
        if hasattr(self, '_stripped_keys_mapper'):
            self._stripped_keys_mapper[key.replace(' ', '')] = key

    def get_possibilities(self, pattern):
        if pattern in self._cached_matches:
            logger.debug('Pattern %s found in cache' % pattern)
        else:
            logger.debug('Trying to match %s' % pattern)
            possibilities_key = []
            possibilities_name = []
            pattern = pattern.lower()
            for key, (name, destination) in self.items():
                if key.lstrip(' ').startswith(pattern):
                    possibilities_key.append(key)
                if (
                    # Only match start of words
                    name.lower().startswith(pattern) or
                    ' %s' % pattern in name.lower()
                ):
                    possibilities_name.append(key)
            logger.debug('possibilities_key: %s' % possibilities_key)
            logger.debug('possibilities_name: %s' % possibilities_name)
            self._cached_matches[pattern] = (
                list(set(possibilities_key + possibilities_name))
            )
        return self._cached_matches[pattern]

    def filter(self, pattern):
        possibilities = self.get_possibilities(pattern)

        return Options({
            key: value
            for key, value in
            self.items()
            if key in possibilities
        })

    def match_best_or_none(self, pattern):
        logger.debug('Trying to match (%s)' % pattern)
        possibilities = self.get_possibilities(pattern)
        logger.debug('Available possibilities: %s' % possibilities)
        if len(possibilities) == 1:
            logger.debug('Exactly one possibility, returning that!')
            return self[possibilities[0]]
        if pattern in self._stripped_keys_mapper:
            logger.debug('Pattern matches stripped key, returning key %s' % (
                self._stripped_keys_mapper[pattern]
            ))
            return self[self._stripped_keys_mapper[pattern]]


class Menu(object):
    INCLUDE_UP_ITEM = True

    BACKSPACE = b'\x7f'

    def __init__(self, navigator):
        self.navigator = navigator

    def initialize(self):
        self._options = getattr(self, 'get_options', lambda: {})()
        if not isinstance(self._options, Options):
            self._options = Options(self._options)
        self._options['q'] = ('quit', responses.QUIT)
        if self.INCLUDE_UP_ITEM:
            self._options['u'] = ('..', responses.UP)
        if self.navigator.player.has_been_loaded():
            self._options['p'] = ('player', responses.PLAYER)
        self.filter = ''

    def get_response(self):
        response = None
        while response is None:
            response = single_char_with_timeout(60)
        if response == Menu.BACKSPACE:
            self.filter = self.filter[:-1]
            return responses.NOOP
        self.filter += response.decode('utf-8')
        if self.filter.endswith('\n'):
            # The user wants to go someplace...
            self.filter = self.filter.replace('\n', '')
            # Gets set as the item to navigate to if we only found one
            is_valid = self.is_valid_response()
            if is_valid:
                # Ok, return
                return is_valid[1]
        # Trigger redraw!
        return responses.NOOP

    def is_valid_response(self):
        return self._options.match_best_or_none(self.filter)

    def get_ui(self):
        if self.filter:
            items = sorted(self._options.filter(self.filter).items())
        else:
            items = sorted(self._options.items())
        if not items:
            menu_items = ('No matches for "%s"' % self.filter, )
        else:
            menu_items = tuple(
                self.get_menu_item(key, value[0]) for key, value in
                items
            )
            if self.filter:
                is_valid = self.is_valid_response()
                if is_valid:
                    menu_items += (
                        '',
                        'Press [return] to go to (%s)' % is_valid[0]
                    )

        above_menu_items = self.get_header()
        return '\n'.join(
            (above_menu_items, '') +
            menu_items +
            ('', 'Query: %s' % self.filter, )
        )

    def get_menu_item(self, key, value):
        return '[%s]: %s' % (key, value)

    def get_header(self):
        return ''


class MainMenu(Menu):
    INCLUDE_UP_ITEM = False

    def get_options(self):
        return {
            'vp': ('View playlists', PlayListOverview(self.navigator)),
            's': ('Search', Search(self.navigator))
        }


class PlayListOverview(Menu):

    def get_options(self):
        results = {}
        playlists = self.navigator.session.playlist_container
        playlists = enumerate(
            sorted(
                (
                    playlist for playlist in playlists
                    if playlist.name and hasattr(playlist, 'link')
                ),
                key=lambda x: x.name
            )
        )
        for i, playlist in playlists:
            menu_item = PlayListSelected(self.navigator)
            menu_item.playlist = playlist.link.as_playlist()
            results[str(i+1).rjust(4)] = (menu_item.playlist.name, menu_item)
        return results

    def get_header(self):
        return 'Select a playlist'


class Search(Menu):
    is_searching = False
    search_pattern = ''
    search = None

    def get_search_results(self):
        self.search_pattern = self.filter
        # TODO: Hopefully remove this sometime...
        from .search import search
        self.search = search(self.navigator.session, self.search_pattern)
        # self.search = self.navigator.session.search(self.search_pattern)
        self.is_searching = True
        return self

    def get_response(self):
        if self.is_searching:
            self.search.loaded_event.wait()
            self.is_searching = False

            search_results = SearchResults(self.navigator)
            search_results.search = self.search

            self.is_searching = False
            self.search_pattern = ''
            self.search = None

            return search_results
        return super(Search, self).get_response()

    def is_valid_response(self):
        return super(Search, self).is_valid_response() or (
            None, self.get_search_results
        )

    def get_ui(self):
        if self.is_searching:
            return 'Searching for %s' % self.search_pattern
        else:
            return '\n'.join((
                'Search query: %s' % self.filter,
                '',
                'Press [return] to search',
                '(Pro tip: you can also input "u" to go up or "q" to quit)'
            ))


class SearchResults(Menu):
    search = None

    def select_song(self, track_idx):
        def song_selected():
            track = self.search.tracks[track_idx]
            if self.navigator.player.is_playing():
                # If the user is currently playing we want him to have the
                # choice to add this song to the list of current songs or
                # start playing this playlist from this song
                menu = SongSelectedWhilePlaying(self.navigator)
                menu.track = track
                return menu
            else:
                self.navigator.player.clear()
                self.navigator.player.add_to_queue(track)
                self.navigator.player.play_track(0)
                return self.navigator.player
        return song_selected

    def get_options(self):
        results = {}
        for i, track in enumerate(
            track for track in
            self.search.tracks
            if track.availability != TrackAvailability.UNAVAILABLE
        ):
            results[str(i+1).rjust(4)] = (
                format_track(track), self.select_song(i)
            )
        return results


class PlayListSelected(Menu):
    playlist = None

    def shuffle_play(self):
        self.navigator.player.load_playlist(
            self.playlist,
            shuffle=True
        )
        self.navigator.player.play_current_song()
        return self.navigator.player

    def select_song(self, track_idx):
        def song_selected():
            if self.navigator.player.is_playing():
                # If the user is currently playing we want him to have the
                # choice to add this song to the list of current songs or
                # start playing this playlist from this song
                menu = SongSelectedWhilePlaying(self.navigator)
                menu.playlist = self.playlist
                menu.track = self.playlist.tracks[track_idx]
                return menu
            else:
                self.navigator.player.load_playlist(
                    self.playlist
                )
                self.navigator.player.play_track(track_idx)
                return self.navigator.player
        return song_selected

    def get_options(self):
        results = {}
        for i, track in enumerate(
            track for track in
            self.playlist.tracks
            if track.availability != TrackAvailability.UNAVAILABLE
        ):
            results[str(i+1).rjust(4)] = (
                format_track(track), self.select_song(i)
            )
        if results:
            results['sp'] = ('Shuffle play', self.shuffle_play)
        else:
            logger.debug('There are no songs in this playlist!')

        return results

    def get_header(self):
        return 'Playlist [%s] selected' % self.playlist.name


class SongSelectedWhilePlaying(Menu):
    playlist = None
    track = None

    def add_to_queue(self):
        self.navigator.player.add_to_queue(self.track)
        return responses.UP

    def replace_current(self):
        self.navigator.player.load_playlist(
            self.playlist
        )
        self.navigator.player.play_track(
            self.playlist.tracks.index(self.track)
        )
        return self.navigator.player

    # Only thing we know here is that the player is currently playing something
    def get_options(self):
        results = {}
        if self.playlist:
            results['replace'] = (
                'Replace currently playing with %s' % (self.playlist.name),
                self.replace_current
            )
        results['add_to_queue'] = (
            'Add %s to queue' % format_track(self.track),
            self.add_to_queue
        )
        return results

    def get_header(self):
        if self.playlist:
            return 'Song [%s] from playlist [%s] selected' % (
                format_track(self.track), self.playlist.name
            )
        else:
            return 'Song [%s] selected'
