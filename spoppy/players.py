import spotify
import threading
import random
import logging

logger = logging.getLogger(__name__)

class Player(object):

    shuffle = False

    def __init__(self, navigator):
        self.navigator = navigator
        self.current_track = 0
        self.current_pos = None
        self.song_order = []

    def set_options(self, **options):
        for key, value in options.items():
            setattr(self, key, value)

    def clear(self):
        self.current_track = 0
        self.current_pos = None

    def play_playlist(self, playlist, **options):
        self.clear()
        self.set_options(**options)
        self.song_list = playlist.tracks
        self.playlist = playlist
        self.song_order = list(range(len(self.song_list)))
        if self.shuffle:
            logger.debug('Song order before: %s' % self.song_order)
            random.shuffle(self.song_order)
            logger.debug('Song order after: %s' % self.song_order)
        self.play()

    def play(self):
        end_of_track = threading.Event()
        song_index = self.song_order[self.current_track]
        track = self.song_list[song_index].load()
        self.navigator.session.player.load(track)
        self.navigator.session.player.play()

        logger.debug('Playing track %s' % track.name)

        def on_end_of_track(session):
            end_of_track.set()

        # Register event listeners
        self.navigator.session.on(
            spotify.SessionEvent.END_OF_TRACK, on_end_of_track
        )
        try:
            while not end_of_track.wait(0.2):
                pass
        except KeyboardInterrupt:
            return
