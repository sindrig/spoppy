import click

from spoppy.navigation import Leifur

import logging
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
def main(username, password):
    navigator = Leifur(username, password)
    try:
        navigator.start()
    finally:
        navigator.shutdown()
        logger.debug('Bye')


if __name__ == '__main__':
    # click.clear()
    try:
        main(auto_envvar_prefix='SPOPPY')
    finally:
        pass  # click.clear()
