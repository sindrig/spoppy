import logging
import requests
import subprocess

try:
    import click
    from lockfile import LockFile, LockTimeout
except ImportError:
    click = None

logger = logging.getLogger('spoppy.main')


def get_version():
    return '1.7.5'


def check_for_updates(lock):
    info = requests.get(
        "https://pypi.python.org/pypi/spoppy/json").json()["info"]

    pypi_version = info["version"].split('.')

    version = get_version().split('.')

    for sub in version:
        if sub < pypi_version[version.index(sub)]:
            click.echo("\033[1m\033[94mA new version of spoppy is "
                       "available!\033[0m")
            click.echo("\033[1m\033[96m Installed: {} \033[92m"
                       "PyPi: {}\033[0m".format('.'.join(version),
                                                '.'.join(pypi_version)))
            click.echo("\033[94m You can install it yourself or "
                       "automatically download it. Automatically "
                       "install it?\033[0m")
            try:
                response = raw_input(
                    '[Y(Automatically) / n(Manually)] ').lower()
            except NameError:
                response = input(
                    '[Y(Automatically) / n(Manually)] ').lower()

            # Only do anything if they say yes
            if response == "y":
                try:
                    subprocess.check_call(
                        ["sudo", "pip", "install", "spoppy", "--upgrade"])
                    click.echo(
                        "\033[1m\033[92mspoppy updated sucessfully!\033[0m")

                    click.echo("Please restart spoppy!")
                    lock.release()
                    raise SystemExit

                except subprocess.CalledProcessError:
                    # Pip failed to automatically update
                    click.echo(
                        "\033[1m\033[91mAutomatic updating failed!\033[0m")
                    click.echo(
                        "You will have to manually update spoppy")

                    # Pause execution so the user sees the error
                    try:
                        raw_input()
                    except NameError:
                        input()

if click:
    @click.command()
    @click.argument('username', required=False)
    @click.argument('password', required=False)
    def main(username, password):
        # Ignore error, logging set up in logging utils
        from . import logging_utils
        from .navigation import Leifur
        from .config import get_config, set_config, get_config_from_user
        from .connectivity import check_internet_connection

        lock = LockFile('/tmp/spoppy')
        check_internet_connection()

        # Check for updates
        check_for_updates(lock)

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
