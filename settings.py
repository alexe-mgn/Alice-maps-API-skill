import logging
import json


def dump_json(dct):
    return json.dumps(dct, ensure_ascii=False)


FORMATTER = logging.Formatter('%(asctime)s %(name)s:%(levelname)s - %(message)s')

logging.basicConfig()
logger = logging.getLogger()
logger.handlers.clear()
logger.setLevel(logging.DEBUG)

last_handler = logging.FileHandler('last_log.log', mode='w')
last_handler.setFormatter(FORMATTER)
logger.addHandler(last_handler)

file_handler = logging.FileHandler('local_log.log', mode='a')
file_handler.setFormatter(FORMATTER)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(FORMATTER)
logger.addHandler(stream_handler)

logging.info('LOGGING SET UP')
