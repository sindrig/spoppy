import logging
from collections import namedtuple

from spotify.playlist import Playlist

from . import utils
from .loader import Loader

logger = logging.getLogger(__name__)
MockPlaylist = namedtuple('Playlist', ('name', 'tracks'))


class PlaylistLoader(Loader):
    search_type = 'playlists'
    playlist_type = 'mine'

    def get_data(self):
        logger.info('Playlist type: %s' % self.playlist_type)
        if self.playlist_type == 'mine':
            return self.navigator.spotipy_client.user_playlists(
                self.navigator.username
            )
        elif self.playlist_type == 'featured':
            return (
                self.navigator.spotipy_client.featured_playlists()['playlists']
            )
        elif self.playlist_type == 'problematic':
            links = [
                utils.get_link_from_unloaded_playlist(
                    self.navigator.session,
                    playlist,
                )
                for playlist in self.navigator.session.playlist_container
                if hasattr(playlist, 'is_loaded') and not playlist.is_loaded
            ]
            # Filter out those that we couldn't load links for
            # links = list(filter(bool, links))
            import pdb; pdb.set_trace()
        else:
            raise ValueError('Unknown playlist type %s' % self.playlist_type)

    def get_item(self, session, item):
        return Playlist(session, item['uri']), item
