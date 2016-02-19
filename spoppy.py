import logging

import click
from lockfile import LockFile, LockTimeout
# Ignore error, logging set up in logging utils
from spoppy import logging_utils
from spoppy.navigation import Leifur

logger = logging.getLogger('spoppy.main')


@click.command()
@click.argument('username', envvar='SPOPPY_USERNAME')
@click.argument('password', envvar='SPOPPY_PASSWORD')
def main(username, password):
    try:
        navigator = Leifur(username, password)
        navigator.start()
    finally:
        navigator.shutdown()
        logger.debug('Finally, bye!')


if __name__ == '__main__':
    lock = LockFile('/tmp/spoppy.lock')
    try:
        # Try for 5s to acquire the lock
        lock.acquire(5)
    except LockTimeout:
        click.echo('Could not acquire lock, is spoppy running?')
    else:
        try:
            main()
        except click.exceptions.MissingParameter:
            click.echo(
                'You must either set the SPOPPY_USERNAME and SPOPPY_PASSWORD '
                'environment variables or add username and password to your '
                'the script\'s parameters!'
            )
    finally:
        if lock.i_am_locking():
            lock.release()
