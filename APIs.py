import requests
import json
from io import BytesIO

from url_parsing import Parse, Str
from geometry import GeoRect

from settings import log_request


SEARCH_API_KEY = 'dda3ddba-c9ea-4ead-9010-f43fbc15c6e3'
SEARCH_API_URL = 'https://search-maps.yandex.ru/v1/?apikey={}&lang=ru_RU'.format(SEARCH_API_KEY)

RASP_API_KEY = '9456c68c-75f5-466c-aa34-b660e8ac146b'
RASP_API_URL = 'https://api.rasp.yandex.net/v3.0/{}/?apikey=%s' % (RASP_API_KEY,)

GEOCODE_API_URL = "https://geocode-maps.yandex.ru/1.x/?format=json"
STATIC_MAPS_API_URL = "https://static-maps.yandex.ru/1.x/?"
MAPS_URL = "https://yandex.ru/maps?"


class Toponym:

    def __init__(self, geo_obj_dict):
        if 'type' in geo_obj_dict and geo_obj_dict['type'] == 'Feature':
            self.feature = True
            self.data = dict(geo_obj_dict)
            self.biz = 'properties' in self.data and 'CompanyMetaData' in self.data['properties']
        else:
            self.feature = False
            self.data = dict(geo_obj_dict['GeoObject'])
            self.biz = False

    @property
    def pos(self):
        return Parse.pos(self.data['Point']['pos']) if not self.feature else self.data['geometry']['coordinates']

    @property
    def rect(self):
        if not self.feature:
            env = self.data['boundedBy']['Envelope']
            d = Parse.pos(env['lowerCorner'])
            u = Parse.pos(env['upperCorner'])
            return GeoRect(d[0], u[1], u[0] - d[0], u[1] - d[1])
        else:
            if 'boundedBy' in self.data['properties']:
                return GeoRect.bounding(self.data['properties']['boundedBy'])
            else:
                return GeoRect(*self.data['geometry']['coordinates'], 0, 0)

    @property
    def name(self):
        if not self.feature:
            return self.data['name']
        else:
            return self.data['properties']['name']

    @property
    def kind(self):
        if not self.feature:
            return self.data['metaDataProperty']['GeocoderMetaData']['kind']
        else:
            if self.biz:
                return 'biz'
            else:
                return self.data['properties']['GeocoderMetaData']['kind']

    @property
    def formatted_address(self):
        if not self.feature:
            return self['metaDataProperty']['GeocoderMetaData']['Address']['formatted']
        else:
            if not self.biz:
                return self.data['properties']['GeocoderMetaData']['text']
            else:
                return self.data['properties']['CompanyMetaData']['address']

    def __getitem__(self, key):
        return self.data[key]

    def __str__(self):
        return json.dumps(self.data, indent=2, ensure_ascii=False)

    def __len__(self):
        return 1

    @property
    def workhours(self):
        if self.biz:
            d = self.data['properties']['CompanyMetaData']
            if 'Hours' in d:
                return d['Hours']
        return None

    @property
    def phone_numbers(self):
        res = []
        if self.biz:
            for p in self.data['properties']['CompanyMetaData'].get('Phones', []):
                res.append(p['formatted'])
        return res


class MapsApi:
    pars = {
        'l': 'map',
    }

    def __init__(self, pos_mode='bbox', **kwargs):
        self.pars = self.overriden_pars(**kwargs)
        self.mode_init = False
        self.pars['bbox'] = None
        self.pars.pop('ll', None)
        self.pars.pop('spn', None)
        self.pos_mode = pos_mode
        if kwargs:
            if pos_mode == 'bbox' and 'bbox' in kwargs:
                self.mode_init = True
                self.pars['bbox'] = kwargs['bbox']
            elif pos_mode == 'spn':
                if 'll' in kwargs:
                    self.mode_init = True
                    self.pars['ll'] = kwargs['ll']
                if 'spn' in kwargs:
                    self.pars['spn'] = kwargs['spn']

    def overriden_pars(self, **kwargs):
        pars = self.pars.copy()
        for k, v in kwargs.items():
            pars[k] = v
        return pars

    def get_url(self, static=False, **kwargs):
        pars = self.overriden_pars(**kwargs)
        if not static:
            rect = pars.pop('bbox', None)
            if rect is not None:
                pars['ll'] = rect.center
                pars['spn'] = rect.size
            res = {}
            for k in ['ll', 'spn', 'z']:
                if k in pars:
                    res[k] = pars[k]
            for p in pars.get('pt', []):
                res['pt'] = res.get('pt', []) + [p[:1]]
            return MAPS_URL + Str.string_query(res)
        else:
            return STATIC_MAPS_API_URL + Str.string_query(pars)

    def get(self, surface=False, **kwargs):
        resp = requests.get(self.get_url(static=True, **kwargs))
        try:
            resp.raise_for_status()
        except Exception:
            log_request(resp)
            raise
        mf = BytesIO(resp.content)
        if surface:
            import pygame
            return pygame.image.load(mf, '_.png')
        else:
            return mf

    def show(self, **kwargs):
        import pygame
        pygame.display.set_mode((650, 400))
        image = self.get(surface=True, **kwargs)
        screen = pygame.display.set_mode(image.get_size())
        screen.blit(image, (0, 0))
        pygame.display.flip()
        while pygame.event.wait().type != pygame.QUIT:
            pass
        pygame.quit()

    def include_view(self, obj):
        if hasattr(obj, 'rect'):
            rect = obj.rect
        elif len(obj) == 4:
            rect = GeoRect(obj)
        elif len(obj) == 2:
            rect = GeoRect(*obj, 0, 0)
        else:
            return
        rect.inflate_ip(rect.w * .5, rect.h * .5)
        if self.mode_init:
            self.rect = self.bounding().union(rect)
        else:
            self.rect = rect
        # if mode == 'bbox':
        #     self.pars['bbox'] = n_rect
        # elif mode == 'spn':
        #     self.pars['spn'] = n_rect.size
        #     self.pars['ll'] = n_rect.center

    @property
    def pos_mode(self):
        keys = self.pars.keys()
        if 'bbox' in keys:
            return 'bbox'
        elif 'spn' in keys and 'll' in keys:
            return 'spn'

    @pos_mode.setter
    def pos_mode(self, key):
        old_mode = self.pos_mode
        if key != old_mode:
            if self.mode_init:
                old_rect = self.bounding()
                if key == 'bbox':
                    self.pars['bbox'] = old_rect
                    self.pars.pop('spn', None)
                    self.pars.pop('ll', None)
                elif key == 'spn':
                    self.pars['ll'] = old_rect.center
                    self.pars['spn'] = old_rect.size
                    self.pars.pop('bbox', None)
            else:
                if key == 'bbox':
                    self.pars['bbox'] = None
                    self.pars.pop('spn', None)
                    self.pars.pop('ll', None)
                elif key == 'spn':
                    self.pars['ll'] = None
                    self.pars.pop('bbox', None)

    @property
    def rect(self):
        if self.pos_mode == 'bbox':
            return self.pars['bbox']
        else:
            raise AttributeError(
                '.rect is a linked rectangle and not available if position mode != "bbox"\n'
                'You can use read-only .bounding() rectangle or change mode')

    @rect.setter
    def rect(self, rect):
        pos_mode = self.pos_mode
        rect = GeoRect(rect)
        if pos_mode == 'bbox':
            self.pars['bbox'] = rect
        elif pos_mode == 'spn':
            self.pars['ll'] = rect.center
            self.pars['spn'] = rect.size
        else:
            raise AttributeError(
                '.rect is a linked rectangle and not available if position mode != "bbox"\n'
                'You can use read-only .bounding() or change mode')
        self.mode_init = True

    @property
    def center(self):
        mode = self.pos_mode
        if self.mode_init:
            if mode == 'bbox':
                return self.pars['bbox'].center
            elif mode == 'spn':
                return self.pars['ll']
        else:
            return None

    @center.setter
    def center(self, pos):
        mode = self.pos_mode
        if mode == 'bbox':
            if self.mode_init:
                self.pars['bbox'].center = pos
            else:
                self.pars['bbox'] = GeoRect(*pos, 0, 0)
        elif mode == 'spn':
            self.pars['ll'] = list(pos)
            if not self.mode_init:
                self.pars['ll'] = [0, 0]
        self.mode_init = True

    @property
    def size(self):
        mode = self.pos_mode
        if mode == 'bbox':
            return self.pars['bbox'].size
        elif mode == 'spn':
            return list(self.pars['spn'])

    @size.setter
    def size(self, sz):
        mode = self.pos_mode
        if mode == 'bbox':
            rect = self.pars['bbox']
            c = rect.center
            rect.size = sz
            rect.center = c
        elif mode == 'spn':
            self.pars['spn'] = list(sz)

    def bounding(self):
        if self.mode_init:
            pm = self.pos_mode
            if pm == 'bbox':
                return self.pars['bbox'].copy()
            elif pm == 'spn':
                r = GeoRect()
                r.size = self.pars['spn']
                r.center = self.pars['ll']
                return r
        else:
            return None

    def add_marker(self, pos, style=None):
        style = [] if not style else str(style)
        self.pars['pt'] = self.pars.get('pt', []) + [
            [list(pos), style]
        ]

    def add_poly(self, curves=None, **kwargs):
        args = {k: v for k, v in kwargs.items() if k in ['c', 'f', 'w']}
        args['curves'] = [] if not curves else list(curves)
        self.pars['pl'] = self.pars.get('pl', []) + [
            args
        ]

    def add_curve(self, points, p_ind=None, **kwargs):
        if p_ind is not None:
            self.pars['pl'][p_ind]['curves'].append(points)
        else:
            self.add_poly(curves=[points], **kwargs)


class GeoApi:

    def __init__(self, geocode, **kwargs):
        kwargs['geocode'] = geocode
        for k, v in kwargs.items():
            if v is None:
                pass
            elif isinstance(v, str) or hasattr(v, '__int__'):
                pass
            elif hasattr(v, 'str_parameter'):
                kwargs[k] = str(v)
            else:
                kwargs[k] = Str.pos(v)
        resp = requests.get(GEOCODE_API_URL, params=kwargs)
        try:
            resp.raise_for_status()
        except Exception:
            log_request(resp)
            raise
        res = resp.json()
        self.data = res['response']['GeoObjectCollection']

    @property
    def rect(self):
        env = self.data['metaDataProperty']['GeocoderResponseMetaData']['boundedBy']['Envelope']
        d = Parse.pos(env['lowerCorner'])
        u = Parse.pos(env['upperCorner'])
        return GeoRect(d[0], u[1], u[0] - d[0], u[1] - d[1])

    def __len__(self):
        return int(self.data['metaDataProperty']['GeocoderResponseMetaData']['found'])

    def __getitem__(self, ind):
        if isinstance(ind, slice):
            return [Toponym(e) for e in self.data['featureMember'][ind]]
        return Toponym(self.data['featureMember'][ind])

    def __iter__(self):
        return iter(Toponym(e) for e in self.data['featureMember'])

    def __bool__(self):
        return len(self) > 0

    def __str__(self):
        return json.dumps(self.data, indent=2, ensure_ascii=False)


class SearchApi:
    def __init__(self, text, **kwargs):
        kwargs['text'] = text
        for k, v in kwargs.items():
            if v is None:
                pass
            elif isinstance(v, str) or hasattr(v, '__int__'):
                pass
            elif hasattr(v, 'str_parameter'):
                kwargs[k] = v.str_parameter()
            else:
                kwargs[k] = Str.pos(v)
        resp = requests.get(SEARCH_API_URL, params=kwargs)
        try:
            resp.raise_for_status()
        except Exception:
            log_request(resp)
            raise
        res = resp.json()
        if res.get('status', None) == 'error':
            raise ValueError(res)
        self.data = res

    @property
    def rect(self):
        bbox = self.data['properties']['ResponseMetaData']['SearchResponse']['boundedBy']
        return GeoRect.bounding(bbox)

    def __len__(self):
        return int(self.data['properties']['ResponseMetaData']['SearchResponse']['found'])

    def __getitem__(self, ind):
        if isinstance(ind, slice):
            return [Toponym(e) for e in self.data['features'][ind]]
        return Toponym(self.data['features'][ind])

    def __iter__(self):
        return iter(Toponym(e) for e in self.data['features'])

    def __bool__(self):
        return len(self) > 0

    def __str__(self):
        return json.dumps(self.data, indent=2, ensure_ascii=False)


class RaspApi:

    @staticmethod
    def nearest_stations(pos, dist=1):
        resp = requests.get(RASP_API_URL.format('nearest_stations'),
                            params=Str.string_query({
                                'lat': pos[0],
                                'lng': pos[1],
                                'distance': dist
                            }))
        try:
            resp.raise_for_status()
        except Exception:
            log_request(resp)
            raise
        return resp.json()

    @staticmethod
    def route(src, trg):
        resp = requests.get(RASP_API_URL.format('search'),
                            params={'from': str(src), 'to': str(trg)})
        try:
            resp.raise_for_status()
        except Exception:
            log_request(resp)
            raise
        return resp.json()
