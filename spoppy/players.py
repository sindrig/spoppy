class Player(object):
    def __init__(self, navigator, item):
        self.navigator = navigator
        self.item = item

    def play(self):
        pass


class PlaylistPlayer(Player):
    shuffle = False
    repeat = False

    def play(self):
       pass