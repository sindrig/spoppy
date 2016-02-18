import threading
import shutil
from collections import namedtuple
import logging

logger = logging.getLogger(__name__)

TerminalSize = namedtuple('TerminalSize', ('width', 'height'))


def get_terminal_size():
    size = shutil.get_terminal_size((120, 40))
    return TerminalSize(size.columns, size.lines)


class ResizeChecker(threading.Thread):
    CHECK_INTERVAL = .5

    def __init__(self, lifecycle, stop_event, *args):
        self.lifecycle = lifecycle
        self.stop_event = stop_event
        self.last_size = get_terminal_size()
        self.should_run = True
        super(ResizeChecker, self).__init__()

    def run(self):
        logger.debug('ResizeChecker started')
        while not self.stop_event.wait(self.CHECK_INTERVAL):
            new_size = get_terminal_size()
            if self.last_size != get_terminal_size():
                logger.debug('Terminal size changed to %s' % (new_size, ))
                self.lifecycle.player.trigger_redraw()
                self.last_size = new_size
