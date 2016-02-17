import logging

logger = logging.getLogger('spoppy')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('spoppy.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.debug('Logger set up')
