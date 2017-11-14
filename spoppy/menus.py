import logging
import threading
import webbrowser
from collections import namedtuple
from itertools import chain

from spotify import TrackAvailability
from spotify.playlist import Playlist

from . import responses
from .http_server import oAuthServerThread
from .radio import Recommendations
from .loaders.playlists import PlaylistLoader
from .loaders.tracks import TrackLoader
from .loaders.search import search
from .util import (format_album, format_track, get_duration_from_s,
                   single_char_with_timeout, sorted_menu_items)

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
                elif self.fuzzy_match(pattern, name.lower()):
                    possibilities_name.append(key)

            logger.debug('possibilities_key: %s' % possibilities_key)
            logger.debug('possibilities_name: %s' % possibilities_name)
            cached_match = self._cached_matches[pattern] = (
                list(set(possibilities_key + possibilities_name))
            )
        return cached_match

    def fuzzy_match(self, pattern, name):
        try:
            for key in pattern:
                name = name[name.index(key) + 1:]
            return True
        except ValueError:
            return False

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
    PAGE_UP = b'\x1b[5~'
    PAGE_DOWN = b'\x1b[6~'
    PAGE = 0

    num_iterations = 0
    loaded = False
    loader_enabled = True

    def __init__(self, navigator):
        self.navigator = navigator

    def is_loader_enabled(self):
        return self.loader_enabled and hasattr(self, 'loader')

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

    def handle_results(self):
        pass

    def get_response(self):
        if self.is_loader_enabled():
            if not self.loader:
                if not hasattr(self, 'get_loader'):
                    raise TypeError('Missing get_loader')
                self.loader = self.get_loader()
            if self.loader:
                self.loader.loaded_event.wait(1)
                if not self.loader.loaded_event.is_set():
                    self.num_iterations += 1
                    return responses.NOOP
                elif not self.loaded:
                    self.handle_results()
                    self.loaded = True
                    return self
            else:
                logger.info(
                    'No loader set after request, returning noop '
                    'and re-initializing'
                )
                self.initialize()
                return responses.NOOP
        response = None
        while response is None:
            response = single_char_with_timeout(60)
            self.navigator.player.check_end_of_track()
        if response == Menu.BACKSPACE:
            self.filter = self.filter[:-1]
            return responses.NOOP
        elif response in (Menu.UP_ARROW, Menu.PAGE_UP):
            logger.debug('Got UP_ARROW/PAGE_UP')
            self.PAGE = max([self.PAGE - 1, 0])
            return responses.NOOP
        elif response in (Menu.DOWN_ARROW, Menu.PAGE_DOWN):
            logger.debug('Got DOWN_ARROW/PAGE_DOWN')
            self.PAGE += 1
            return responses.NOOP
        elif response.startswith(b'\x1b'):
            logger.debug('Got unknown character %s' % repr(response))
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
        if self.is_loader_enabled() and not (
            self.loader and
            self.loader.loaded_event.is_set()
        ):
            return 'Loading...' + '.' * self.num_iterations

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

        above_menu_items = self._get_header()
        return (
            (above_menu_items, '') +
            menu_items +
            ('', 'Query: %s' % self.filter, )
        )

    def get_menu_item(self, key, value):
        return '[%s]: %s' % (key, value)

    def _get_header(self):
        if self.is_loader_enabled():
            if (
                getattr(self, 'loader', None) and
                getattr(self.loader.results, 'message')
            ):
                return self.loader.results.message
        return self.get_header()

    def get_header(self):
        return ''

    def loader_done(self):
        if self.is_loader_enabled():
            return hasattr(self, 'loader') and (
                self.loader and
                self.loader.loaded_event.is_set()
            )
        return True

    def disable_loader(self):
        self.loader_enabled = False


class MainMenu(Menu):
    INCLUDE_UP_ITEM = False

    def get_options(self):
        if self.navigator.spotipy_client.is_authenticated():
            return {
                'st': MenuValue(
                    'Search for tracks',
                    TrackSearch(self.navigator)
                ),
                'sa': MenuValue(
                    'Search for albums',
                    AlbumSearch(self.navigator)
                ),
                'sp': MenuValue(
                    'Search for playlists',
                    PlaylistSearch(self.navigator)
                ),
                'ss': MenuValue(
                    'Search for artists',
                    ArtistSearch(self.navigator)
                ),
                'vp': MenuValue(
                    'View playlists',
                    MyPlaylists(self.navigator)
                ),
                'fp': MenuValue(
                    'Featured playlists',
                    FeaturedPlaylists(self.navigator)
                ),
            }
        else:
            return {
                'li': MenuValue(
                    'Log in to spotify web api',
                    LogIntoSpotipy(self.navigator)
                )
            }


class PlayListOverview(Menu):

    loader = None

    def get_loader(self):
        raise NotImplementedError('Subclass must implement!')

    def get_options(self):
        if not self.loader_done():
            return {}

        def get_name(x):
            if x[0].is_loaded:
                return x[0].name
            return x[1]['name']
        results = {}
        playlists = sorted(
            self.loader.results,
            key=get_name
        )
        for i, (playlist, response) in enumerate(playlists):
            menu_item = PlayListSelected(self.navigator)
            menu_item.playlist = playlist
            if playlist.is_loaded:
                menu_item.disable_loader()
            menu_item.response = response
            results[str(i + 1).rjust(4)] = MenuValue(
                get_name((playlist, response)), menu_item
            )
        return results


class MyPlaylists(PlayListOverview):

    def get_loader(self):
        return PlaylistLoader(self.navigator)


class FeaturedPlaylists(PlayListOverview):

    def get_loader(self):
        loader = PlaylistLoader(self.navigator)
        loader.playlist_type = 'featured'
        return loader


class TrackSearchResults(Menu):
    search = None
    paginating = False
    support_shuffle_page = True
    _cached_search_results = []

    def set_initial_results(self, search):
        self.search = search
        self.update_cache()

    def update_cache(self):
        self._cached_search_results.append(self.search)

    def get_cache(self):
        return self._cached_search_results

    def get_response(self):
        if self.paginating:
            self.search.loaded_event.wait()
            self.paginating = False
            return self
        return super(TrackSearchResults, self).get_response()

    def go_to(self, up_down):
        def inner():
            self.paginating = True

            new_cache_idx = self.get_cache().index(self.search) + up_down

            try:
                self.search = self.get_cache()[new_cache_idx]
                logger.debug('Got search from cache, yahoo!')
            except IndexError:
                logger.debug('Initiating new search')
                kwargs = dict(
                    navigator=self.navigator,
                    query=self.search.query,
                    search_type=self.search.search_type,
                )
                if up_down > 0:
                    kwargs['next_from'] = self.search.results
                else:
                    kwargs['prev_from'] = self.search.results
                self.search = search(**kwargs)
                self.update_cache()
            return self
        return inner

    def select_song(self, track_idx):
        def song_selected():
            track = self.search.results.results[track_idx]
            menu = SongSelectedWhilePlaying(self.navigator)
            menu.track = track
            menu.playlist = self.get_mock_playlist()
            return menu
        return song_selected

    def get_mock_playlist(self):
        return MockPlaylist(
            self.get_mock_playlist_name(), self.search.results.results
        )

    def get_mock_playlist_name(self):
        return 'Search for %s' % self.search.results.term

    def shuffle_play(self):
        self.navigator.player.load_playlist(
            self.get_mock_playlist(),
            shuffle=True
        )
        self.navigator.player.play_current_song()
        return self.navigator.player

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
                'Previous page', self.go_to(-1)
            )
        if self.search.results.next_page:
            results['n'] = MenuValue(
                'Next page', self.go_to(1)
            )
        if self.support_shuffle_page and len(self.search.results.results):
            results['sp'] = MenuValue(
                'Shuffle play current page', self.shuffle_play
            )
        return results

    def get_options_from_search(self):
        results = {}
        for i, track in enumerate(
            track for track in
            self.search.results.results
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
            res.album = self.search.results.results[track_idx]
            return res
        return album_selected

    def get_options_from_search(self):
        results = {}
        for i, album in enumerate(
            self.search.results.results
        ):
            results[str(self.get_res_idx(i)).rjust(4)] = MenuValue(
                format_album(album), self.select_album(i)
            )
        return results

    def get_mock_playlist(self):
        track_results = list(chain(*[
            album.tracks for album in self.search.results.results
        ]))
        return MockPlaylist(
            self.get_mock_playlist_name(), track_results
        )


class ArtistSearchResults(TrackSearchResults):
    search = None

    def select_artist(self, artist_idx):
        def artist_selected():
            res = ArtistSelected(self.navigator)
            res.artist = self.search.results.results[artist_idx]
            return res
        return artist_selected

    def get_options_from_search(self):
        results = {}
        for i, artist_browser in enumerate(
            self.search.results.results
        ):
            results[str(self.get_res_idx(i)).rjust(4)] = MenuValue(
                artist_browser.artist.name, self.select_artist(i)
            )
        return results

    def get_mock_playlist(self):
        track_results = list(chain(*[
            artist.tracks for
            artist in self.search.results.results
        ]))
        return MockPlaylist(
            self.get_mock_playlist_name(), track_results
        )


class PlaylistSearchResults(TrackSearchResults):
    search = None
    support_shuffle_page = False

    def select_playlist(self, playlist_idx):
        def artist_selected():
            playlist, response = self.search.results.results[playlist_idx]
            menu_item = PlayListSelected(self.navigator)
            menu_item.playlist = playlist
            if playlist.is_loaded:
                menu_item.disable_loader()
            menu_item.response = response
            return menu_item
        return artist_selected

    def get_options_from_search(self):
        results = {}
        for i, (playlist, response) in enumerate(
            self.search.results.results
        ):
            name = '%s (%s)' % (
                playlist.name or response['name'],
                response['owner']['id']
            )
            results[str(self.get_res_idx(i)).rjust(4)] = MenuValue(
                name, self.select_playlist(i)
            )
        return results


class TrackSearch(Menu):
    is_searching = False
    search_pattern = ''
    search = None
    search_type = 'tracks'
    result_cls = TrackSearchResults
    num_iterations = 0

    def get_options(self):
        return {}

    def get_search_results(self):
        self.search_pattern = self.filter
        self.search = search(
            self.navigator, self.search_pattern,
            search_type=self.search_type
        )
        self.is_searching = True
        return self

    def get_response(self):
        if self.is_searching:
            self.search.loaded_event.wait(1)
            if not self.search.loaded_event.is_set():
                self.num_iterations += 1
                return responses.NOOP
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
            return (
                ('Searching for [%s]..' % self.search_pattern) +
                '.' * self.num_iterations
            )
        else:
            return [
                'Search query: %s' % self.filter,
                '',
                'Press [return] to search',
                '(Pro tip: you can also input "u" to go up or "q" to quit)'
            ]


class AlbumSearch(TrackSearch):
    search_type = 'albums'
    result_cls = AlbumSearchResults


class ArtistSearch(TrackSearch):
    search_type = 'artists'
    result_cls = ArtistSearchResults


class PlaylistSearch(TrackSearch):
    search_type = 'playlists'
    result_cls = PlaylistSearchResults


class PlayListSelected(Menu):
    playlist = None
    response = {
        'name': ''
    }
    deleting = False
    loader = None

    def handle_results(self):
        self.playlist = MockPlaylist(
            self.response['name'], self.loader.results
        )

    def get_loader(self):
        if isinstance(self.playlist, MockPlaylist):
            self.disable_loader()
            return None
        return TrackLoader(
            self.navigator,
            url=self.response['tracks']['href']
        )

    def shuffle_play(self):
        self.navigator.player.load_playlist(
            self.playlist,
            shuffle=True
        )
        self.navigator.player.play_current_song()
        return self.navigator.player

    def select_song(self, track_idx):
        def song_selected():
            menu = SongSelectedWhilePlaying(self.navigator)
            menu.playlist = self.playlist
            menu.track = self.get_tracks()[track_idx]
            return menu
        return song_selected

    def add_to_queue(self):
        self.navigator.player.add_to_queue(self.playlist)
        return self.navigator.player

    def delete_playlist(self):
        self.deleting = True
        return self

    def do_delete_playlist(self):
        p_idx = self.navigator.session.playlist_container.index(
            self.playlist
        )
        self.navigator.session.playlist_container.remove_playlist(p_idx)
        return responses.UP

    def cancel_delete_playlist(self):
        self.deleting = False
        return self

    def get_tracks(self):
        return [
            track for track in
            (self.loader.results if self.loader else self.playlist.tracks)
            if track.availability != TrackAvailability.UNAVAILABLE
        ]

    def get_name(self):
        return self.playlist.name or self.response['name']

    def get_options(self):
        if not self.loader_done():
            return {}
        results = {}
        if self.deleting:
            results['y'] = MenuValue('Yes', self.do_delete_playlist)
            results['n'] = MenuValue('No', self.cancel_delete_playlist)
        else:
            for i, track in enumerate(self.get_tracks()):
                results[str(i + 1).rjust(4)] = MenuValue(
                    format_track(track), self.select_song(i)
                )
            if results:
                results['sp'] = MenuValue('Shuffle play', self.shuffle_play)
                if self.navigator.player.is_playing():
                    results['aq'] = MenuValue(
                        'Add [%s] to queue' % self.get_name(),
                        self.add_to_queue
                    )
            else:
                logger.debug('There are no songs in this playlist!')
            if self.playlist in self.navigator.session.playlist_container:
                results['x'] = MenuValue(
                    'Delete playlist',
                    self.delete_playlist
                )

        if self.navigator.spotipy_client:
            start_radio = StartRadio(self.navigator)
            start_radio.seeds = self.get_tracks()
            start_radio.seed_type = 'tracks'
            start_radio.verbose_name = self.get_name()
            results['rt'] = MenuValue(
                'Start radio based on [%s]' % self.get_name(),
                start_radio
            )

        return results

    def get_header(self):
        if self.deleting:
            return 'Are you sure you want to delete playlist [%s]' % (
                self.get_name()
            )
        return '%s (total %d tracks)' % (
            self.get_header_text(),
            len(self.get_tracks())
        )

    def get_header_text(self):
        return 'Playlist [%s] selected' % self.get_name()


class AlbumSelected(PlayListSelected):
    album = None
    _tracks = None

    def initialize(self):
        self.playlist = MockPlaylist(self.get_name(), self.get_tracks())
        super(AlbumSelected, self).initialize()

    def get_tracks(self):
        if not self._tracks:
            self._tracks = self.album.tracks
        return self._tracks

    def get_name(self):
        return format_album(self.album)

    def get_header_text(self):
        return 'Album [%s] selected' % self.get_name()


class BanArtistMixin(object):
    def get_ban_options(self):
        results = {}
        artist = self.get_artist()
        if artist:
            if self.navigator.is_artist_banned(artist):
                results['ub'] = MenuValue(
                    "Unban artist",
                    self.unban_artist()
                )
            else:
                results['ba'] = MenuValue(
                    "Ban artist (you won't be able to "
                    "play songs by this artist)",
                    self.ban_artist()
                )
        return results

    def ban_artist(self):
        def do_ban_artist():
            self.navigator.ban_artist(self.get_artist())
            return self
        return do_ban_artist

    def unban_artist(self):
        def do_unban_artist():
            self.navigator.unban_artist(self.get_artist())
            return self
        return do_unban_artist


class ArtistSelected(BanArtistMixin, AlbumSelected):
    artist = None
    _tracks = None

    def get_tracks(self):
        if not self._tracks:
            self._tracks = self.artist.tracks
            logger.debug('Artist has %d tracks' % len(self._tracks))
        return self._tracks

    def get_name(self):
        return self.artist.artist.name

    def get_header_text(self):
        return 'Artist [%s] selected' % self.get_name()

    def get_artist(self):
        return self.artist

    def get_options(self):
        results = self.get_ban_options()
        results.update(super(ArtistSelected, self).get_options())
        return results


class SongSelectedWhilePlaying(BanArtistMixin, Menu):
    playlist = None
    track = None

    def add_to_queue(self):
        self.navigator.player.add_to_queue(self.track)
        return responses.UP

    def add_to_temp_queue(self):
        self.navigator.player.add_play_then_remove(self.track)
        return self.navigator.player

    def replace_current(self):
        self.navigator.player.load_playlist(
            self.playlist
        )
        tracks = self.playlist.tracks
        if hasattr(tracks, 'results'):
            tracks = tracks.results
        self.navigator.player.play_track(
            tracks.index(self.track)
        )
        return self.navigator.player

    # Only thing we know here is that the player is currently playing something
    def get_options(self):
        results = self.get_ban_options()
        if self.playlist:
            if self.navigator.player.is_playing():
                msg = 'Replace currently playing with [%s]' % (
                    self.playlist.name
                )
            else:
                msg = ('Play [%s]' % self.playlist.name)
            results['pl'] = MenuValue(
                msg,
                self.replace_current
            )
        formatted_track = format_track(self.track)
        results['aq'] = MenuValue(
            'Add [%s] to queue' % formatted_track,
            self.add_to_queue
        )
        results['tmp'] = MenuValue(
            'Add [%s] temporary to playlist' % formatted_track,
            self.add_to_temp_queue
        )
        if self.track.album:
            res = AlbumSelected(self.navigator)
            res.album = self.track.album.browse().load()
            results['ga'] = MenuValue(
                'Go to track\'s album [%s]' % self.track.album.name,
                res
            )
        if self.navigator.spotipy_client:
            start_radio = StartRadio(self.navigator)
            start_radio.seeds = self.track.artists
            start_radio.seed_type = 'artists'
            start_radio.verbose_name = self.get_artist_names()
            results['ra'] = MenuValue(
                'Start radio based on [%s]' % self.get_artist_names(),
                start_radio

            )
            start_radio = StartRadio(self.navigator)
            start_radio.seeds = [self.track]
            start_radio.seed_type = 'tracks'
            start_radio.verbose_name = format_track(self.track)
            results['rt'] = MenuValue(
                'Start radio based on [%s]' % format_track(self.track),
                start_radio
            )
        return results

    def get_header(self):
        info = [
            'Song: %s' % format_track(self.track),
            'Duration: %s' % get_duration_from_s(self.track.duration / 1000.0)
        ]
        if self.playlist:
            info.append('Playlist: %s' % self.playlist.name)
        if self.track.album:
            info.append('Album: %s' % self.track.album.name)
            info.append('Released: %s' % self.track.album.year)
        info.append(
            self.get_artist_names()
        )
        return '\n'.join(info)

    def get_artist_names(self):
        return ' & '.join(
            artist.name for artist in self.track.artists
            if artist.name
        )

    def get_artist(self):
        if len(self.track.artists) == 1:
            return self.track.artists[0]


class SavePlaylist(Menu):
    song_list = []
    is_saving = False
    callback = None
    original_playlist_name = None

    def get_options(self):
        return {}

    def save_playlist(self):
        self.new_playlist_name = (
            self.filter.strip()
        )
        self.is_saving = True
        return self

    def get_response(self):
        if self.is_saving:
            spotipy = self.navigator.spotipy_client
            user = self.navigator.spotipy_me['id']
            playlist_name = (
                self.new_playlist_name or
                self.original_playlist_name
            )
            user_playlists = spotipy.current_user_playlists()['items']
            try:
                playlist = [
                    playlist for playlist in
                    user_playlists
                    if playlist['name'] == playlist_name
                ][0]
            except IndexError:
                # Creating a new playlist
                playlist = spotipy.user_playlist_create(
                    user=user,
                    name=playlist_name
                )
                track_ids = [
                    track.link.uri for track in self.song_list
                ]
                spotipy.user_playlist_add_tracks(
                    user=user,
                    playlist_id=playlist['id'],
                    tracks=track_ids,
                )
            else:
                # Modifying a playlist
                spotipy.user_playlist_replace_tracks(
                    user=user,
                    playlist_id=playlist['id'],
                    tracks=[
                        song.link.uri for song in self.song_list
                    ],
                )
            spotify_playlist = Playlist(
                self.navigator.session,
                playlist['uri']
            )
            spotify_playlist.load()
            self.is_saving = False
            if self.callback:
                self.callback(spotify_playlist)
            return responses.UP
        return super(SavePlaylist, self).get_response()

    def is_valid_response(self):
        return super(SavePlaylist, self).is_valid_response() or (
            (
                self.filter.strip() or self.original_playlist_name
            ) and
            MenuValue(
                None, self.save_playlist
            )
        )

    def get_ui(self):
        if self.is_saving:
            return 'Saving playlist as %s' % self.new_playlist_name
        else:
            return '\n'.join((
                '%d songs to be added to new playlist' % len(self.song_list),
                'The original playlist name was [%s]. Leave the name empty '
                'to replace [%s] with the current song list' % (
                    self.original_playlist_name, self.original_playlist_name
                ) if self.original_playlist_name else '',
                'Playlist name: %s' % self.filter,
                '',
                'Press [return] to save your playlist',
                '(Pro tip: you can also input "u" to go up or "q" to quit)'
            ))


class LogIntoSpotipy(Menu):
    _spotipy_response_parts = None
    message_from_spotipy = None

    def initialize(self):
        self.sp_oauth = self.navigator.lifecycle.get_spotipy_oauth()
        auth_url = self.sp_oauth.get_authorize_url()

        def response_callback(parts):
            logger.debug('Got response %s from http server', parts)
            self._spotipy_response_parts = parts

        server_started_event = threading.Event()
        self.oauth_server = oAuthServerThread(
            response_callback, server_started_event
        )
        self.oauth_server.start()
        server_started_event.wait()
        if not self.oauth_server.server:
            # Probably we could not bind
            self.message_from_spotipy = (
                'Could not start the callback server, check your logs'
            )
        else:
            webbrowser.open(auth_url)

    def get_response(self):
        logger.debug('Getting response from user in spotipy login')
        response = single_char_with_timeout(3)
        logger.debug('Got this response: %s' % response)
        if response in (b'u', b'q'):
            self.oauth_server.shutdown()
            return responses.UP
        if self._spotipy_response_parts:
            self.oauth_server.shutdown()
            logger.debug(
                'Have this to handle from http request: %s',
                self._spotipy_response_parts
            )
            if 'code' in self._spotipy_response_parts:
                code = self._spotipy_response_parts['code'][0]
                self.navigator.lifecycle.set_spotipy_token(
                    self.sp_oauth.get_access_token(code)
                )
                self.navigator.refresh_spotipy_client()
                return responses.UP
            elif 'error' in self._spotipy_response_parts:
                self.message_from_spotipy = (
                    'Error logging in to spotipy: %s' %
                    self._spotipy_response_parts['error']
                )
            else:
                self.message_from_spotipy = (
                    'No code and no error in %s' %
                    self._spotipy_response_parts
                )
                logger.error(self.message_from_spotipy)
        return responses.NOOP

    def get_ui(self):
        if self.message_from_spotipy:
            res = [self.message_from_spotipy]
        else:
            res = [
                (
                    'Opening an authorization page in your browser, please '
                    'follow the instructions there to finalize the '
                    'authorization process'
                )
            ]
        res += [
            '',
            'You can cancel at any time by typing "q" or "u"'
        ]
        return res


class StartRadio(Menu):
    seed_type = None
    seeds = None
    recommendations = None
    verbose_name = None
    num_iterations = 0

    def get_options(self):
        return {}

    def get_response(self):
        if self.recommendations:
            if self.recommendations.loaded_event.is_set():
                return responses.UP
        else:
            self.recommendations = Recommendations(
                self.navigator, self.seeds, self.seed_type
            )
        self.recommendations.loaded_event.wait(1)
        if not self.recommendations.loaded_event.is_set():
            self.num_iterations += 1
            return responses.NOOP
        radio_results = RadioSelected(self.navigator)
        radio_results.set_initial_results(self.recommendations)
        radio_results.radio_name = 'Spoppy Radio based on [%s]' % (
            self.verbose_name
        )
        return radio_results

    def get_ui(self):
        res = [(
            'Querying spotify for radio, one moment..' +
            '.' * self.num_iterations
        )]
        if self.num_iterations > 4:
            res.append('')
            res.append("(It's not my fault this is taking so long)")
        return res


class RadioSelected(TrackSearchResults):
    radio_name = ''

    def get_header(self):
        if getattr(self.search.results, 'message'):
            return self.search.results.message
        if not self.search.results.total:
            return 'Song cannot be played in radio, sorry!'
        return 'Radio list "%s" generated:' % self.get_mock_playlist_name()

    def get_mock_playlist_name(self):
        return self.radio_name or 'Spoppy Radio'
