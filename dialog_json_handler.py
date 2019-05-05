from flask import jsonify
from settings import logging, log_object
from dialogs_API import DialogsApi


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


class Button(DictHandler):

    def __init__(self, storage, bid, text, attach=True, url=None, life=1, payload=None):
        super().__init__()
        self.storage = storage
        self.id = bid
        self.life = life
        self.attach = attach
        self.visible = True
        self.data = {
            'title': text,
            'payload': {} if not payload else payload,
            'hide': not attach
        }
        if url:
            self.data['url'] = url

    @property
    def alive(self):
        return self.life != 0

    def send(self):
        self.life -= 1
        if self.attach:
            self.visible = False
        return self.data

    def on_death(self):
        pass


class Card(DictHandler):

    def __init__(self, storage, text, image, life=1):
        super().__init__()
        self.storage = storage
        self.life = life
        self.visible = True
        self.data = {
            'title': text,
            'type': 'BigImage',
            'image_id': image
        }

    @property
    def alive(self):
        return self.life != 0

    def send(self):
        self.life -= 1
        self.visible = False
        return self.data

    def on_death(self):
        pass


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
        self.request = {}
        self.response = None
        self._state = 0
        self._state_init = False
        self._delay = 0
        self._id = req['session']['user_id']
        self.buttons = []
        self.cards = []
        self.images = {}
        self.data = {
            'position': None,
            'next': [],
            'back': []
        }

    def __init__(self, req):
        super().__init__()
        self.request = req

    def next(self):
        nxt = self['next'].pop(-1)
        if hasattr(nxt, '__call__'):
            return nxt()
        else:
            return nxt

    def back(self):
        bck = self['back'].pop(-1)
        if hasattr(bck, '__call__'):
            return bck()
        else:
            return bck

    @classmethod
    def remove(cls, uid):
        if uid in cls.storage:
            logging.info('REMOVING ' + str(uid))
            del cls.storage[uid]

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, n):
        oid = self._id
        if n != oid:
            if oid not in self.storage:
                self._id = n
                self.storage[n] = self
                del self.storage[n]

    def pre_step(self):
        pass

    def post_step(self):
        bts = []
        for i in self.buttons.copy():
            if i.alive:
                v = i.visible
                d = i.send()
                if v:
                    bts.append(d)
            else:
                i.on_death()
                self.buttons.remove(i)
        self.response['response']['buttons'] = bts

        card = None
        for i in self.cards.copy():
            if i.alive:
                v = i.visible
                d = i.send()
                if v:
                    card = d
            else:
                i.on_death()
                self.cards.remove(i)
        if card:
            self.response['response']['card'] = card

    @property
    def type(self):
        # ButtonPressed, SimpleUtterance
        return self.request['request']['type']

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, st):
        if st is not None:
            if self._state != st:
                logging.info('STATE SWITCHED ' + str(st))
                self._delay = 0
                self._state = st
            self._state_init = False

    @property
    def state_init(self):
        return self._state_init

    def init_state(self, delay_up=False):
        self._state_init = True
        if delay_up:
            self.delay_up()

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, d):
        self._delay = d

    def delay_up(self):
        if self.state_init:
            self._delay += 1
            logging.info('DELAY UP: ' + str(self._delay))
        else:
            logging.info('STATE WAS NOT INIT, leaving delay at ' + str(self._delay))

    def get_button(self, bid):
        for i in self.buttons:
            if i.id == bid:
                return i

    def add_button(self, button):
        self.buttons.append(button)

    def add_card(self, card):
        logging.info('Adding card ' + log_object(card.data))
        self.cards.append(card)

    def remove_button(self, bid):
        for i in self.buttons.copy():
            if i.id == bid:
                self.buttons.remove(i)

    def upload_image(self, key, url):
        try:
            mid = DialogsApi.upload_image_url(url)
            if mid:
                self.set_image(key, mid)
                return mid
        except Exception:
            pass

    def set_image(self, key, mid):
        logging.info('SETTING IMAGE ' + str(key) + ' TO ' + str(mid))
        if mid:
            if key in self.images:
                DialogsApi.remove_image(self.images[key])
            self.images[key] = mid
            logging.info('NEW IMAGES ' + log_object(self.images))

    def get_image(self, key):
        logging.info('FROM IMAGES ' + log_object(self.images))
        for k, v in self.images.items():
            if k == key:
                logging.info('WITH KEY ' + str(key) + ' GOT ' + str(v))
                return v
        logging.info('WITH KEY ' + str(key) + ' GOT NONE')
        return None

    # REQUEST

    @property
    def command(self):
        return self.request['request'].get('command', None)

    @property
    def text(self):
        return self.request['request'].get('original_utterance', None)

    @text.setter
    def text(self, text):
        self.request['request']['original_utterance'] = text

    @property
    def payload(self):
        return self.request['request']['payload']

    @property
    def tokens(self):
        # CHECK DIALOGS PROTOCOL
        # MAY NOT EXIST
        return self.request['request']['nlu']['tokens']

    def entity(self, t=None):
        res = []
        if not t:
            return self.request['request']['nlu']['entities']
        for i in self.request['request']['nlu']['entities']:
            if i['type'].lower().split('.')[-1] == t.lower():
                res.append(i)
        return res

    def geo_entity(self):
        geos = self.entity(t='geo')
        res = []
        for geo in geos:
            loc = []
            for lv in ['country', 'city', 'street', 'house_number', 'airport']:
                if lv in geo['value']:
                    loc.append(geo['value'][lv])
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
                'buttons': []
            }
        }

    @property
    def end(self):
        return self['response']['end_session']

    @end.setter
    def end(self, end):
        self['response']['end_session'] = bool(end)

    def send(self):
        logging.info('SENDING ' + log_object(self.data))
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
