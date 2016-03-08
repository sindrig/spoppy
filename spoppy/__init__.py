import logging

try:
    import click
    from lockfile import LockFile, LockTimeout
except ImportError:
    click = None

logger = logging.getLogger('spoppy.main')


def get_version():
    return '1.2.2'

if click:
    @click.command()
    @click.argument('username', required=False)
    @click.argument('password', required=False)
    def main(username, password):
        # Ignore error, logging set up in logging utils
        from . import logging_utils
        from .navigation import Leifur
        from .config import get_config, set_config, get_config_from_user

        lock = LockFile('/tmp/spoppy.lock')
        try:
            # Try for 5s to acquire the lock
            lock.acquire(5)
        except LockTimeout:
            click.echo('Could not acquire lock, is spoppy running?')
        else:

            if username and password:
                set_config(username, password)
            else:
                username, password = get_config()
            if not (username and password):
                username, password = get_config_from_user()
            try:
                navigator = Leifur(username, password)
                navigator.start()
            finally:
                navigator.shutdown()
                logger.debug('Finally, bye!')
        finally:
            if lock.i_am_locking():
                lock.release()
else:
    def main(*args, **kwargs):
        print('Something went horribly wrong, missing requirements...')
