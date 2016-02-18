import logging
import traceback

import click
# Ignore error, logging set up in logging utils
from spoppy import logging_utils
from spoppy.navigation import Leifur

logger = logging.getLogger(__name__)


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
    main(auto_envvar_prefix='SPOPPY', standalone_mode=False)
