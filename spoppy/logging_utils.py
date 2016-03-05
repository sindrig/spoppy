import logging
import os

from appdirs import user_cache_dir

cache_dir = user_cache_dir(appname='spoppy')

LOG_FILE_NAME = os.path.join(
    cache_dir, 'spoppy.log'
)

if not os.path.isdir(cache_dir):
    os.makedirs(cache_dir)

logger = logging.getLogger('spoppy')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(LOG_FILE_NAME)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.debug('Logger set up')
