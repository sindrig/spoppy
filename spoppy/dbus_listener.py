import logging
import threading

import _thread

from .util import format_track

logger = logging.getLogger(__name__)

try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
    DBusServiceObject = dbus.service.Object
except ImportError:
    DBusServiceObject = None
    logger.warning(
        'DBus not installed, you won\'t be able to control the '
        'player via DBus'
    )

try:
    import gobject
except ImportError:
    gobject = None
    logger.warning(
        'gobject not installed, you won\'t be able to control the '
        'player via DBus'
    )


class SpoppyDBusService(DBusServiceObject):

    def __init__(self, lifecycle):
        self.lifecycle = lifecycle

    def run(self):
        gobject.threads_init()
        dbus.mainloop.glib.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus_name = dbus.service.BusName(
            "com.spoppy",
            dbus.SessionBus()
        )
        super(SpoppyDBusService, self).__init__(
            bus_name, "/com/spoppy"
        )

        self._loop = gobject.MainLoop()
        self._loop.run()

    def stop(self):
        self._loop.quit()

    @dbus.service.method(
        "com.spoppy",
        in_signature='', out_signature='b'
    )
    def PlayPause(self):
        self.lifecycle.navigator.player.play_pause()
        return True

    @dbus.service.method(
        "com.spoppy",
        in_signature='', out_signature='s'
    )
    def Previous(self):
        self.lifecycle.navigator.player.previous_song()
        self.lifecycle.navigator.player.trigger_redraw()
        _thread.interrupt_main()
        return format_track(self.lifecycle.navigator.player.current_track)

    @dbus.service.method(
        "com.spoppy",
        in_signature='', out_signature='s'
    )
    def Next(self):
        self.lifecycle.navigator.player.next_song()
        self.lifecycle.navigator.player.trigger_redraw()
        _thread.interrupt_main()
        return format_track(self.lifecycle.navigator.player.current_track)

    @dbus.service.method(
        "com.spoppy",
        in_signature='', out_signature='s'
    )
    def Current(self):
        if self.lifecycle.navigator.player.current_track:
            return format_track(self.lifecycle.navigator.player.current_track)
        return ''


class Listener(threading.Thread):
    def __init__(self, lifecycle, stop_event, *args):
        self.lifecycle = lifecycle
        self.stop_event = stop_event
        super(Listener, self).__init__()

    def run(self):
        if not (DBusServiceObject and gobject):
            logger.warning(
                'Listener thread aborting because of missing dependencies'
            )
            return
        self.service = SpoppyDBusService(self.lifecycle)
        self.service_thread = threading.Thread(
            target=self.service.run
        )
        self.service_thread.start()

        logger.debug('Service started, waiting for kill signal')
        self.stop_event.wait()
        logger.debug('Kill signal received, stopping service')
        self.service.stop()
        while True:
            logger.debug('Joining service thread with timeout 10s')
            self.service_thread.join(10)
            if not self.service_thread.is_alive():
                break
