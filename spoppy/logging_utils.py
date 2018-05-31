import logging
from logging.handlers import RotatingFileHandler
import os

from appdirs import user_cache_dir


def configure_logging():
    cache_dir = user_cache_dir(appname='spoppy')

    LOG_FILE_NAME = os.path.join(
        cache_dir, 'spoppy.log'
    )

    LOG_LEVEL = getattr(
        logging,
        os.getenv('SPOPPY_LOG_LEVEL', '').upper(),
        logging.INFO
    )

    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir)

    logger = logging.getLogger('spoppy')
    logger.setLevel(LOG_LEVEL)
    handler = RotatingFileHandler(
        LOG_FILE_NAME,
        maxBytes=1024 * 1024 * 10,
        backupCount=10,
    )
    handler.setLevel(LOG_LEVEL)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.debug('Spoppy logger set up')

    requests_log = logging.getLogger('urllib3')
    requests_log.setLevel(LOG_LEVEL)
    requests_log.propagate = True
    requests_log.addHandler(handler)
    logger.debug('urllib3 logger set up')
