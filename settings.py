import logging
import json

FORMATTER = logging.Formatter('%(asctime)s %(name)s:%(levelname)s - %(message)s')

logging.basicConfig()
logger = logging.getLogger()
logger.handlers.clear()
logger.setLevel(logging.DEBUG)

last_handler = logging.FileHandler('last_log.log', mode='w')
last_handler.setFormatter(FORMATTER)
logger.addHandler(last_handler)

# file_handler = logging.FileHandler('local_log.log', mode='a')
# file_handler.setFormatter(FORMATTER)
# logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(FORMATTER)
logger.addHandler(stream_handler)


class LogEncoder(json.JSONEncoder):
    def encode(self, o):
        try:
            return super().encode(o)
        except TypeError:
            return super().encode(str(o))


def log_object(dct):
    return str(dct)[:15000]


def log_request(response):
    logging.info(
        'RESPONSE STATUS ' + str(response.status_code) + ' GOT ' + str(response.content.decode('utf-8'))[:15000])


logging.info('LOGGING SET UP')

if __name__ == '__main__':
    def f():
        return None

    logging.info(log_object({'functions': {'a': lambda: None, 'b': lambda: None, 'c': [f, 'слова, функции', {'functions': {'a': lambda: None, 'b': lambda: None, 'c': [f, 'слова, функции', {'functions': {'a': lambda: None, 'b': lambda: None, 'c': [f, 'слова, функции', {'functions': {'a': lambda: None, 'b': lambda: None, 'c': [f, 'слова, функции']}}]}}]}}]}}))
