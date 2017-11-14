import logging
from collections import namedtuple

from spotify.playlist import Playlist

from .loader import Loader

logger = logging.getLogger(__name__)
MockPlaylist = namedtuple('Playlist', ('name', 'tracks'))


class PlaylistLoader(Loader):
    search_type = 'playlists'
    playlist_type = 'mine'

    def get_data(self):
        logger.info('Playlist type: %s' % self.playlist_type)
        if self.playlist_type == 'mine':
            return self.navigator.spotipy_client.current_user_playlists()
        elif self.playlist_type == 'featured':
            return (
                self.navigator.spotipy_client.featured_playlists()['playlists']
            )
        else:
            raise ValueError('Unknown playlist type %s' % self.playlist_type)

    def get_item(self, session, item):
        return Playlist(session, item['uri']), item
