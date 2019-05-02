import json
import logging

from flask import jsonify


class DictHandler:

    def __init__(self, data=None):
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, item, val):
        self.data[item] = val

    @property
    def dict(self):
        return self.data


class Storage(DictHandler):
    storage = {}

    def __new__(cls, data):
        user_id = data['session']['user_id']
        if user_id in cls.storage:
            logging.info('CONTINUE with ' + str(user_id))
            return cls.storage[user_id]
        else:
            logging.info('NEW instance ' + str(user_id))
            new = super().__new__(cls)
            cls.storage[user_id] = new
            return new

    def __init__(self, data):
        super().__init__()
        self.data = {
            'buttons': [],
            'state': 'new'
        }

    @property
    def state(self):
        return self['state']

    @state.setter
    def state(self, text):
        self['state'] = text


class Request(DictHandler):

    def __init__(self, data):
        logging.debug('INPUT ' + json.dumps(self.data, ensure_ascii=False))
        super().__init__(data)
        self.storage = Storage(data)

    @property
    def new(self):
        return bool(self['session']['new'])

    @property
    def state(self):
        return self.storage.state

    @state.setter
    def state(self, val):
        self.storage.state = val

    @property
    def command(self):
        return self['request']['command']

    @property
    def text(self):
        return self['request']['original_utterance']


class Response(DictHandler):

    def __init__(self, data):
        super().__init__()
        self.storage = Storage(data)
        self.data = {
            'session': data['session'],
            'version': data['version'],
            'response': {
                'end_session': False,
                'buttons': self.storage['buttons']
            }
        }

    @property
    def end(self):
        return self['response']['end_session']

    @end.setter
    def end(self, end):
        self['response']['end_session'] = bool(end)

    @property
    def send(self):
        logging.debug('RESPONSE ' + json.dumps(self.data, ensure_ascii=False))
        return jsonify(self.data)

    @property
    def text(self):
        return self['response'].get('text', '')

    @text.setter
    def text(self, text):
        self['response']['text'] = text
