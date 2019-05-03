from flask import jsonify
from settings import logging, dump_json


class DictHandler:

    def __init__(self, data=None):
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def get(self, item, default=None):
        return self.data.get(item, default)

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
            obj = cls.storage[user_id]
            obj.pre_step()
            return obj
        else:
            new = super().__new__(cls)
            cls.storage[user_id] = new
            new.id = user_id
            logging.info('NEW STORAGE INSTANCE ' + str(user_id))
            new.pre_step()
            return new

    def __init__(self, req):
        super().__init__()
        self.request = None
        self.response = None
        self.data = {
            'id': 0,
            'buttons': [],
            'state': 0,
            'delay': 0
        }

    @property
    def id(self):
        return self.get('id', 0)

    @id.setter
    def id(self, n):
        self['id'] = n

    def pre_step(self):
        pass

    def post_step(self):
        pass

    @property
    def state(self):
        return self['state']

    @state.setter
    def state(self, st):
        if self.state != st:
            self['delay'] = 0
        self['state'] = st

    @property
    def delay(self):
        return self.get('delay', 0)

    @delay.setter
    def delay(self, d):
        self['delay'] = 0

    def delay_up(self):
        self['delay'] += 1

    def add_button(self, text, one_time=True, url=None, payload=None):
        pass


class Request(DictHandler):

    def __init__(self, data):
        super().__init__(data)
        logging.info('INPUT ' + dump_json(self.data))
        self.storage = Storage(data)
        self.storage.request = self

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
    def delay(self):
        return self.storage.delay

    @delay.setter
    def delay(self, d):
        self.storage.delay = d

    def delay_up(self):
        self.storage.delay_up()

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
        self.storage.response = self
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

    def send(self):
        self.storage.post_step()
        logging.info('SENDING ' + dump_json(self.data))
        return jsonify(self.data)

    @property
    def text(self):
        return self['response'].get('text', '')

    @text.setter
    def text(self, text):
        self['response']['text'] = text

    def msg(self, text):
        old = self['response'].get('text', '')
        self['response']['text'] = old + ('\n' if old else '') + text

    @property
    def buttons(self):
        return self['response']['buttons']

    def add_button(self, text, url=None, payload=None):
        d = {'text': text}
        if url is not None:
            d['url'] = str(url)
        if payload is not None:
            d['payload'] = str(payload)
        self['response']['buttons'] += d
