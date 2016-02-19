import logging
import traceback

import click
# Ignore error, logging set up in logging utils
from spoppy import logging_utils
from spoppy.navigation import Leifur

logger = logging.getLogger('spoppy.main')


@click.command()
@click.argument('username', envvar='SPOPPY_USERNAME')
@click.argument('password', envvar='SPOPPY_PASSWORD')
@click.option('--debug', default=False)
def main(username, password, debug):
    navigator = Leifur(username, password)
    if debug:
        try:
            navigator.start()
        except Exception:
            traceback.print_exc()
            logger.error(traceback.format_exc())
        finally:
            navigator.shutdown()
            logger.debug('Finally, bye!')
    else:
        try:
            navigator.start()
        finally:
            navigator.shutdown()
            logger.debug('Finally, bye!')


if __name__ == '__main__':
    try:
        main()
    except click.exceptions.MissingParameter:
        click.echo(
            'You must either set the SPOPPY_USERNAME and SPOPPY_PASSWORD '
            'environment variables or add username and password to your '
            'the script\'s parameters!'
        )
