import logging

LOGGER_NAME = 'main_logger'

logger = logging.getLogger(LOGGER_NAME)

fileHandler = logging.FileHandler('local_log.log', mode='w')
logger.addHandler(fileHandler)

streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)

logger.setLevel(logging.DEBUG)

logging.debug('STARTING LOGGING')
logging.info('STARTING LOGGING INFO')
