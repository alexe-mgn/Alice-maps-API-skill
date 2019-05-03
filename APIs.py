import requests
import json
from io import BytesIO

# import pygame

from parsing import Parse, Str
from geometry import GeoRect


SEARCH_API_KEY = 'dda3ddba-c9ea-4ead-9010-f43fbc15c6e3'
SEARCH_API_URL = 'https://search-maps.yandex.ru/v1/?apikey={}&lang=ru_RU'.format(SEARCH_API_KEY)

GEOCODE_API_URL = "http://geocode-maps.yandex.ru/1.x/?format=json"
STATIC_MAPS_API_URL = "http://static-maps.yandex.ru/1.x/"


class Toponym:

    def __init__(self, geo_obj_dict):
        if 'type' in geo_obj_dict and geo_obj_dict['type'] == 'FeatureCollection':
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
            if not self.biz:
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


class StaticMapsHandler:
    pars = {
        'l': 'map',
    }

    def __init__(self, pos_mode='bbox'):
        self.pars = self.pars.copy()
        self.pars['bbox'] = None
        self.mode_init = False
        self.pos_mode = pos_mode

    def overriden_pars(self, **kwargs):
        pars = self.pars.copy()
        for k, v in kwargs.items():
            pars[k] = v
        return pars

    def get_rect(self, rect, **kwargs):
        """Fetch image from API"""
        pars = self.overriden_pars(**kwargs)
        pars['bbox'] = GeoRect(rect)
        dct = Str.query(pars)
        resp = requests.get(STATIC_MAPS_API_URL, params='&'.join(['{}={}'.format(k, v) for k, v in dct.items()]))
        try:
            resp.raise_for_status()
        except Exception:
            print(resp.content)
            raise
        mf = BytesIO(resp.content)
        return mf

    def get(self, surface=True, **kwargs):
        pars = self.overriden_pars(**kwargs)
        dct = Str.query(pars)
        resp = requests.get(STATIC_MAPS_API_URL, params='&'.join(['{}={}'.format(k, v) for k, v in dct.items()]))
        try:
            resp.raise_for_status()
        except Exception:
            print(resp.content)
            raise
        mf = BytesIO(resp.content)
        return mf

    # def show(self, **kwargs):
    #     image = self.get(**kwargs)
    #     screen = pygame.display.set_mode(image.get_size())
    #     screen.blit(image, (0, 0))
    #     pygame.display.flip()
    #     while pygame.event.wait().type != pygame.QUIT:
    #         pass

    def include_view(self, obj):
        if hasattr(obj, 'rect'):
            rect = obj.rect
        elif len(obj) == 4:
            rect = GeoRect(obj)
        elif len(obj) == 2:
            rect = GeoRect(*obj, 0, 0)
        else:
            return
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
            self.add_poly(curves=[list(points)], **kwargs)


class GeoHandler:

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, str) or hasattr(v, '__int__'):
                pass
            elif hasattr(v, 'str_parameter'):
                kwargs[k] = str(v)
            else:
                kwargs[k] = Str.pos(v)
        resp = requests.get(GEOCODE_API_URL, params=kwargs)
        try:
            resp.raise_for_status()
        except Exception:
            print(resp.content)
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


class SearchHandler:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, str) or hasattr(v, '__int__'):
                pass
            elif hasattr(v, 'str_parameter'):
                kwargs[k] = v.str_parameter()
            else:
                kwargs[k] = Str.pos(v)
        resp = requests.get(SEARCH_API_URL, params=kwargs)
        print(kwargs)
        try:
            resp.raise_for_status()
        except Exception:
            print(resp.content)
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
