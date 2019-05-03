from flask import jsonify
from settings import logging, dump_json


class DictHandler:

    def __init__(self, data=None):
        if data is not None:
            self.data = data
        elif not hasattr(self, 'data'):
            self.data = {}

    def __getitem__(self, item):
        return self.data[item]

    def get(self, item, default=None):
        return self.data.get(item, default)

    def __setitem__(self, item, val):
        self.data[item] = val

    def __delitem__(self, key):
        del self.data[key]

    @property
    def dict(self):
        return self.data


class Storage(DictHandler):
    storage = {}

    def __new__(cls, data):
        user_id = data['session']['user_id']
        if user_id in cls.storage:
            obj = cls.storage[user_id]
            return obj
        else:
            new = super().__new__(cls)
            cls.storage[user_id] = new
            new.__first_init(data)
            return new

    def __first_init(self, req):
        logging.info('NEW STORAGE INSTANCE ' + str(req['session']['user_id']))
        self.request = None
        self.response = None
        self.data = {
            'id': req['session']['user_id'],
            'buttons': [],
            'state': 0,
            'delay': 0
        }

    def __init__(self, req):
        super().__init__()

    @classmethod
    def remove(cls, uid):
        del cls.storage[uid]

    @property
    def id(self):
        return self.get('id', 0)

    @id.setter
    def id(self, n):
        oid = self.id
        if n != oid:
            if oid not in self.storage:
                self['id'] = n
                self.storage[n] = self
                del self.storage[n]

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
            logging.info('STATE SWITCHED ' + str(st))
            self['delay'] = 0
            self['state'] = st

    @property
    def delay(self):
        return self.get('delay', 0)

    @delay.setter
    def delay(self, d):
        self['delay'] = d

    def delay_up(self):
        self['delay'] += 1
        logging.info('DELAY UP: ' + str(self.delay))

    def add_button(self, text, one_time=True, url=None, payload=None):
        pass


class Request(DictHandler):

    def __init__(self, data):
        super().__init__(data)
        logging.info('INPUT ' + dump_json(self.data))
        self.storage = Storage(data)
        self.storage.request = self

    @property
    def id(self):
        return self.storage.id

    @id.setter
    def id(self, n):
        self.storage.id = n

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

    @property
    def tokens(self):
        # CHECK DIALOGS PROTOCOL
        # MAY NOT EXIST
        return self['request']['nlu']['tokens']

    def entity(self, t=None):
        res = []
        if not t:
            return self['request']['nlu']['entities']
        for i in self['request']['nlu']['entities']:
            if i['type'].lower().split('.')[-1] == t.lower():
                res.append(i)
        return res

    def geo_entity(self):
        geos = self.entity(t='geo')
        res = []
        for geo in geos:
            loc = []
            for lv in ['country', 'city', 'street', 'house_number', 'airport']:
                if lv in geo:
                    loc.append(geo[lv])
            if loc:
                res.append(','.join(loc))
        return res


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
        data = jsonify(self.data)
        if self.end:
            self.storage.remove(self.storage.id)
        return data

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
