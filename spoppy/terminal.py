import threading
import shutil
from collections import namedtuple
import logging

logger = logging.getLogger(__name__)

TerminalSize = namedtuple('TerminalSize', ('width', 'height'))

if hasattr(shutil, 'get_terminal_size'):
    # py3.3+
    get_terminal_dimensions = shutil.get_terminal_size
else:
    # py2.7
    import os
    TerminalDimensions = namedtuple('TerminalDimensions', ('columns', 'lines'))

    def get_terminal_dimensions(fallback):
        rows = os.getenv('LINES')
        cols = os.getenv('COLUMNS')
        if not rows or not cols:
            stty = os.popen('stty size', 'r').read().split()
            if stty and len(stty) == 2:
                rows, cols = stty
            else:
                cols, rows = fallback
        return TerminalDimensions(int(cols), int(rows))


def get_terminal_size():
    size = get_terminal_dimensions((120, 40))
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
