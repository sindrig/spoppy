import logging
import traceback

import click
from spoppy.navigation import Leifur

logger = logging.getLogger('spoppy')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('spoppy.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.debug('Logger set up')


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
            logging.shutdown()
    else:
        try:
            navigator.start()
        finally:
            navigator.shutdown()
            logger.debug('Finally, bye!')
            logging.shutdown()


if __name__ == '__main__':
    main(auto_envvar_prefix='SPOPPY', standalone_mode=False)
