import logging
import threading

try:
    import thread
except ImportError:
    import _thread as thread

from .util import format_track

logger = logging.getLogger(__name__)

try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
    DBusServiceObject = dbus.service.Object
except ImportError:
    DBusServiceObject = object
    dbus = None
    logger.warning(
        'DBus not installed, you won\'t be able to control the '
        'player via DBus'
    )

try:
    from gi.repository import GObject
except ImportError:
    GObject = None
    logger.warning(
        'gobject not installed, you won\'t be able to control the '
        'player via DBus'
    )

if dbus:
    class SpoppyDBusService(DBusServiceObject):

        def __init__(self, lifecycle):
            self.lifecycle = lifecycle

        def run(self):
            GObject.threads_init()
            dbus.mainloop.glib.threads_init()
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            bus_name = dbus.service.BusName(
                "com.spoppy",
                dbus.SessionBus()
            )
            super(SpoppyDBusService, self).__init__(
                bus_name, "/com/spoppy"
            )

            self._loop = GObject.MainLoop()
            self._loop.run()

        def stop(self):
            self._loop.quit()

        @dbus.service.method(
            "com.spoppy",
            in_signature='', out_signature='b'
        )
        def PlayPause(self):
            self.lifecycle.player.play_pause()
            return True

        @dbus.service.method(
            "com.spoppy",
            in_signature='', out_signature='s'
        )
        def Previous(self):
            try:
                self.lifecycle.player.previous_song()
            except RuntimeError as e:
                return ', '.join(e.args)
            self.lifecycle.player.trigger_redraw()
            thread.interrupt_main()
            return format_track(self.lifecycle.player.current_track)

        @dbus.service.method(
            "com.spoppy",
            in_signature='', out_signature='s'
        )
        def Next(self):
            try:
                self.lifecycle.player.next_song()
            except RuntimeError as e:
                return ', '.join(e.args)
            self.lifecycle.player.trigger_redraw()
            thread.interrupt_main()
            return format_track(self.lifecycle.player.current_track)

        @dbus.service.method(
            "com.spoppy",
            in_signature='', out_signature='s'
        )
        def Current(self):
            if self.lifecycle.player.current_track:
                return format_track(self.lifecycle.player.current_track)
            return ''


class DBusListener(threading.Thread):
    def __init__(self, lifecycle, stop_event, *args):
        self.lifecycle = lifecycle
        self.stop_event = stop_event
        self.should_run = dbus and GObject
        if not self.should_run:
            logger.warning(
                'DBusListener thread aborting because of missing dependencies'
            )
        super(DBusListener, self).__init__()

    def run(self):
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
