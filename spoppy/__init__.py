import logging

try:
    import click
    from lockfile import LockFile, LockTimeout
except ImportError:
    click = None

logger = logging.getLogger('spoppy.main')


def get_version():
    return '2.3.0'


if click:
    @click.command()
    @click.argument('username', required=False)
    @click.argument('password', required=False)
    def main(username, password):
        from . import logging_utils
        logging_utils.configure_logging()
        from .navigation import Leifur
        from .config import get_config, set_config, get_config_from_user
        from .connectivity import check_internet_connection
        from .update_checker import check_for_updates

        lock = LockFile('/tmp/spoppy')

        try:
            try:
                # Try for 1s to acquire the lock
                lock.acquire(1)
            except LockTimeout:
                click.echo('Could not acquire lock, is spoppy running?')
                click.echo(
                    'If you\'re sure that spoppy is not running, '
                    'try removing the lock file %s' % lock.lock_file
                )
                click.echo(
                    'You can try removing the lock file by responding [rm]. '
                    'spoppy will exit on all other inputs'
                )
                try:
                    response = raw_input('')
                except NameError:
                    response = input('')
                if response == 'rm':
                    lock.break_lock()
                else:
                    raise TypeError('Could not get lock')
        except TypeError:
            pass
        else:
            check_internet_connection()
            # Check for updates
            check_for_updates(click, get_version(), lock)

            if username and password:
                set_config(username, password)
            else:
                username, password = get_config()
            if not (username and password):
                username, password = get_config_from_user()

            navigator = None
            try:
                navigator = Leifur(username, password)
                navigator.start()
            finally:
                if navigator:
                    navigator.shutdown()
                logger.debug('Finally, bye!')
        finally:
            if lock.i_am_locking():
                lock.release()
else:
    def main(*args, **kwargs):
        print('Something went horribly wrong, missing requirements...')
