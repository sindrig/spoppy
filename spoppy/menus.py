import logging
from collections import namedtuple

from spotify import TrackAvailability
from .search import search
from . import responses
from .util import (format_album, format_track, single_char_with_timeout,
                   sorted_menu_items)

logger = logging.getLogger(__name__)

MenuValue = namedtuple('MenuValue', ('name', 'destination'))
MockPlaylist = namedtuple('Playlist', ('name', 'tracks'))


class Options(dict):
    def __init__(self, *args, **kwargs):
        super(Options, self).__init__(*args, **kwargs)
        self._cached_matches = {}
        self._stripped_keys_mapper = {
            key.replace(' ', ''): key
            for key in self
        }
        self.check_unique_keys()

    def __setitem__(self, key, value):
        super(Options, self).__setitem__(key, value)
        self._stripped_keys_mapper[key.replace(' ', '')] = key
        self.check_unique_keys()

    def check_unique_keys(self):
        if not len(self) == len(self._stripped_keys_mapper):
            raise TypeError('Two keys cannot be the same')

    def get_possibilities_from_cache(self, pattern):
        return self._cached_matches.get(pattern)

    def get_possibilities(self, pattern):
        cached_match = self.get_possibilities_from_cache(pattern)
        if cached_match:
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
            cached_match = self._cached_matches[pattern] = (
                list(set(possibilities_key + possibilities_name))
            )
        return cached_match

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
    UP_ARROW = b'\x1b[A'
    DOWN_ARROW = b'\x1b[B'
    PAGE = 0

    def __init__(self, navigator):
        self.navigator = navigator

    def get_options(self):
        raise NotImplementedError('Subclass must define this method')

    def initialize(self):
        self._options = Options(self.get_options())
        self._options['q'] = MenuValue('quit', responses.QUIT)
        if self.INCLUDE_UP_ITEM:
            self._options['u'] = MenuValue('..', responses.UP)
        if self.navigator.player.has_been_loaded():
            self._options['p'] = MenuValue('player', responses.PLAYER)
        self.filter = ''

    def get_response(self):
        response = None
        while response is None:
            response = single_char_with_timeout(60)
            self.navigator.player.check_end_of_track()
        if response == Menu.BACKSPACE:
            self.filter = self.filter[:-1]
            return responses.NOOP
        elif response == Menu.UP_ARROW:
            logger.debug('Got UP_ARROW')
            self.PAGE = max([self.PAGE - 1, 0])
            return responses.NOOP
        elif response == Menu.DOWN_ARROW:
            logger.debug('Got DOWN_ARROW')
            self.PAGE += 1
            return responses.NOOP

        self.filter += response.decode('utf-8')
        if self.filter.endswith('\n'):
            # The user wants to go someplace...
            self.filter = self.filter.replace('\n', '')
            # Gets set as the item to navigate to if we only found one
            is_valid = self.is_valid_response()
            if is_valid:
                # Ok, return
                return is_valid.destination
        # Trigger redraw!
        return responses.NOOP

    def is_valid_response(self):
        return self._options.match_best_or_none(self.filter)

    def get_ui(self):
        if self.filter:
            items = sorted_menu_items(
                self._options.filter(self.filter).items()
            )
        else:
            items = sorted_menu_items(
                self._options.items()
            )
        if not items:
            menu_items = ('No matches for "%s"' % self.filter, )
        else:
            menu_items = tuple(
                self.get_menu_item(key, value.name) for key, value in
                items
            )
            if self.filter:
                is_valid = self.is_valid_response()
                if is_valid:
                    menu_items += (
                        '',
                        'Press [return] to go to (%s)' % is_valid.name
                    )
        if menu_items:
            number_of_menu_items = self.navigator.get_ui_height() - 4
            if len(menu_items) >= number_of_menu_items:
                paginated_menu_items = []
                while not paginated_menu_items:
                    start_idx = self.PAGE * number_of_menu_items
                    end_idx = (self.PAGE + 1) * number_of_menu_items
                    paginated_menu_items = menu_items[start_idx:end_idx]
                    if not paginated_menu_items:
                        self.PAGE -= 1
                menu_items = paginated_menu_items
            else:
                self.PAGE = 0

        above_menu_items = self.get_header()
        return (
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
            'vp': MenuValue(
                'View playlists', PlayListOverview(self.navigator)
            ),
            'st': MenuValue('Search for tracks', TrackSearch(self.navigator)),
            'sa': MenuValue('Search for albums', AlbumSearch(self.navigator)),
        }


class PlayListOverview(Menu):

    def get_options(self):
        def include_playlist(playlist):
            return (
                playlist.name and
                hasattr(playlist, 'link') and
                any([
                    track for track in playlist.tracks
                    if track.availability != TrackAvailability.UNAVAILABLE
                ])
            )
        results = {}
        playlists = self.navigator.session.playlist_container
        playlists = enumerate(
            sorted(
                (
                    playlist for playlist in playlists
                    if include_playlist(playlist)
                ),
                key=lambda x: x.name
            )
        )
        for i, playlist in playlists:
            menu_item = PlayListSelected(self.navigator)
            menu_item.playlist = playlist.link.as_playlist()
            results[str(i+1).rjust(4)] = MenuValue(
                menu_item.playlist.name, menu_item
            )
        return results

    def get_header(self):
        return 'Select a playlist'


class TrackSearchResults(Menu):
    search = None
    paginating = False
    _cached_search_results = []

    def set_initial_results(self, search):
        self.search = search
        self.update_cache()

    def update_cache(self):
        self._cached_search_results.append(self.search)

    def get_response(self):
        if self.paginating:
            self.search.loaded_event.wait()
            self.paginating = False
            return self
        return super(TrackSearchResults, self).get_response()

    def go_to(self, up_down):
        if up_down > 0:
            destination = 'next_page'
        else:
            destination = 'previous_page'

        def inner():
            self.paginating = True

            new_cache_idx = (
                self._cached_search_results.index(self.search) + up_down
            )

            try:
                self.search = self._cached_search_results[new_cache_idx]
                logger.debug('Got search from cache, yahoo!')
            except IndexError:
                direct_endpoint = getattr(
                    self.search.results, destination
                )
                logger.debug('Initiating new search')
                self.search = search(
                    self.navigator.session, self.search.query,
                    search_type=self.search.search_type,
                    direct_endpoint=direct_endpoint
                )
                self.update_cache()
            return self
        return inner

    def select_song(self, track_idx):
        def song_selected():
            track = self.search.results[track_idx]
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

    def get_header(self):
        return 'Search results for %s (total %d results)' % (
            self.search.results.term, self.search.results.total
        )

    def get_res_idx(self, i):
        return i + 1 + self.search.results.offset

    def get_ui(self):
        if self.paginating:
            return 'Loading...'
        return super(TrackSearchResults, self).get_ui()

    def get_options(self):
        if self.paginating:
            return {}
        results = self.get_options_from_search()
        if self.search.results.previous_page:
            results['p'] = MenuValue(
                'Previous', self.go_to(-1)
            )
        if self.search.results.next_page:
            results['n'] = MenuValue(
                'Next', self.go_to(1)
            )
        return results

    def get_options_from_search(self):
        results = {}
        for i, track in enumerate(
            track for track in
            self.search.results
            if track.availability != TrackAvailability.UNAVAILABLE
        ):
            results[str(self.get_res_idx(i)).rjust(4)] = MenuValue(
                format_track(track), self.select_song(i)
            )
        return results


class AlbumSearchResults(TrackSearchResults):
    search = None

    def select_album(self, track_idx):
        def album_selected():
            res = AlbumSelected(self.navigator)
            res.album = self.search.results[track_idx]
            return res
        return album_selected

    def get_options_from_search(self):
        results = {}
        for i, album in enumerate(
            album for album in
            self.search.results
        ):
            results[str(self.get_res_idx(i)).rjust(4)] = MenuValue(
                format_album(album), self.select_album(i)
            )
        return results


class TrackSearch(Menu):
    is_searching = False
    search_pattern = ''
    search = None
    search_type = 'tracks'
    result_cls = TrackSearchResults

    def get_options(self):
        return {}

    def get_search_results(self):
        self.search_pattern = self.filter
        self.search = search(
            self.navigator.session, self.search_pattern,
            search_type=self.search_type
        )
        self.is_searching = True
        return self

    def get_response(self):
        if self.is_searching:
            self.search.loaded_event.wait()
            self.is_searching = False

            search_results = self.result_cls(self.navigator)
            search_results.set_initial_results(self.search)

            self.is_searching = False
            self.search_pattern = ''
            self.search = None

            return search_results
        return super(TrackSearch, self).get_response()

    def is_valid_response(self):
        return super(TrackSearch, self).is_valid_response() or MenuValue(
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


class AlbumSearch(TrackSearch):
    search_type = 'albums'
    result_cls = AlbumSearchResults


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
                menu.track = self.get_tracks()[track_idx]
                return menu
            else:
                self.navigator.player.load_playlist(
                    self.playlist
                )
                self.navigator.player.play_track(track_idx)
                return self.navigator.player
        return song_selected

    def add_to_queue(self):
        self.navigator.player.add_to_queue(self.playlist)
        return self.navigator.player

    def get_tracks(self):
        return self.playlist.tracks

    def get_name(self):
        return self.playlist.name

    def get_options(self):
        results = {}
        for i, track in enumerate(
            track for track in
            self.get_tracks()
            if track.availability != TrackAvailability.UNAVAILABLE
        ):
            results[str(i+1).rjust(4)] = MenuValue(
                format_track(track), self.select_song(i)
            )
        if results:
            results['sp'] = MenuValue('Shuffle play', self.shuffle_play)
            if self.navigator.player.is_playing():
                results['add_to_queue'] = MenuValue(
                    'Add %s to queue' % self.get_name(),
                    self.add_to_queue
                )
        else:
            logger.debug('There are no songs in this playlist!')

        return results

    def get_header(self):
        return 'Playlist [%s] selected' % self.get_name()


class AlbumSelected(PlayListSelected):
    album = None
    _tracks = None

    def initialize(self):
        super(AlbumSelected, self).initialize()
        self.playlist = MockPlaylist(self.get_name(), self.get_tracks())

    def get_tracks(self):
        if not self._tracks:
            self._tracks = self.album.tracks
        return self._tracks

    def get_name(self):
        return format_album(self.album)

    def get_header(self):
        return 'Album [%s] selected' % self.get_name()


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
            results['replace'] = MenuValue(
                'Replace currently playing with %s' % (self.playlist.name),
                self.replace_current
            )
        results['add_to_queue'] = MenuValue(
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
