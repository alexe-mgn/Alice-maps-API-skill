import math

SEARCH_API_KEY = 'dda3ddba-c9ea-4ead-9010-f43fbc15c6e3'
CODER_URL = "http://geocode-maps.yandex.ru/1.x/?format=json"
MAP_URL = "http://static-maps.yandex.ru/1.x/"
SEARCH_URL = 'https://search-maps.yandex.ru/v1/?apikey={}&lang=ru_RU'.format(SEARCH_API_KEY)


# noinspection PyAttributeOutsideInit
class GeoRect:
    EARTH_RADIUS = 6371
    EARTH_ORTHODROME_PERIMETER = EARTH_RADIUS * 2 * math.pi

    def __init__(self, x=None, y=0., w=0., h=0.):
        if hasattr(x, '__getitem__'):
            for n in range(4):
                self[n] = x[n]
        else:
            if x is None:
                x = 0
            self._x = x
            self._y = y
            self._w = w
            self._h = h

    def move_ip(self, x, y):
        self._x += x
        self._y += y

    def move(self, x, y):
        new = self.copy()
        new.move_ip(x, y)
        return new

    def inflate_ip(self, w, h):
        center = self.center
        self._w += w
        self._h += h
        self.center = center

    def inflate(self, w, h):
        new = self.copy()
        new.inflate_ip(w, h)

    def clamp_ip(self, rect):
        if self.x < rect[0]:
            self.x = rect[0]
        elif self.right > rect[0] + rect[2]:
            self.right = rect[0] + rect[2]
        if self.right > rect[0] + rect[2]:
            self.centerx = rect[0] + rect[2] / 2

        if self.y > rect[1]:
            self.y = rect[1]
        elif self.bottom < rect[1] - rect[3]:
            self.bottom = rect[1] - rect[3]
        if self.bottom < rect[1] - rect[3]:
            self.centery = rect[1] - rect[3] / 2

    def clamp(self, rect):
        new = self.copy()
        new.clamp_ip(rect)
        return new

    def clip_ip(self, rect):
        if not (self.x <= rect[0] + rect[2] and self.right >= rect[0]):
            return self.__class__(0, 0, 0, 0)
        if not (self.y <= rect[1] + rect[3] and self.bottom >= rect[1]):
            return self.__class__(0, 0, 0, 0)

        if self.x < rect[0]:
            self._x = rect[0]
        if self.right > rect[0] + rect[2]:
            self.right = rect[0] + rect[2]

        if self.y > rect[1]:
            self._y = rect[1]
        if self.bottom < rect[1] - rect[3]:
            self.bottom = rect[1] - rect[3]

    def clip(self, rect):
        new = self.copy()
        new.clip_ip(rect)

    def fit_ip(self, rect):
        ks = [rect[2] / self._w, rect[3] / self._h]
        k = min(ks)
        self._w, self._h = self._w * k, self._h * k
        self.center = (rect[0] + rect[2] / 2, rect[1] - rect[3] / 2)

    def fit(self, rect):
        new = self.copy()
        new.fit(rect)
        return new

    def union_ip(self, rect):
        lt = min(self._x, rect[0])
        t = max(self._y, rect[1])
        self._x, self._y = lt, t

        r = max(self._x + self._w, rect[0] + (rect[2] if len(rect) > 2 else 0))
        b = min(self._y - self._h, rect[1] - (rect[3] if len(rect) > 3 else 0))
        self._w, self._h = r - lt, t - b

    def union(self, rect):
        new = self.__class__()
        lt = min(self._x, rect[0])
        t = max(self._y, rect[1])
        new._x, new._y = lt, t

        r = max(self._x + self._w, rect[0] + (rect[2] if len(rect) > 2 else 0))
        b = min(self._y - self._h, rect[1] - (rect[3] if len(rect) > 3 else 0))
        new._w, new._h = r - lt, t - b

        return new

    def unionall_ip(self, rects):
        seq = tuple(rects) + (self,)
        lt = min(map(lambda e: e[0], seq))
        t = max(map(lambda e: e[1], seq))
        r = max(map(lambda e: e[0] + (e[2] if len(e) > 2 else 0), seq))
        b = min(map(lambda e: e[1] - (e[3] if len(e) > 3 else 0), seq))
        self._x, self._y = lt, t
        self._w, self._h = r - lt, t - b

    def unionall(self, rects):
        new = self.__class__()
        seq = tuple(rects) + (self,)
        lt = min(map(lambda e: e[0], seq))
        t = max(map(lambda e: e[1], seq))
        r = max(map(lambda e: e[0] + (e[2] if len(e) > 2 else 0), seq))
        b = min(map(lambda e: e[1] - (e[3] if len(e) > 3 else 0), seq))
        new._x, new._y = lt, t
        new._w, new._h = r - lt, t - b
        return new

    def contains(self, rect):
        return rect[0] >= self.x and \
               rect[0] + rect[2] <= self.right and \
               rect[1] <= self.y and \
               rect[1] - rect[3] >= self.bottom

    def collidepoint(self, x, y):
        return self.x <= x <= self.right and \
               self.bottom <= y <= self.y

    def colliderect(self, rect):
        return rect[0] - self._w <= self._x <= rect[0] + rect[2] and rect[1] + self._h <= self._y <= rect[1] - rect[3]

    @classmethod
    def bounding(cls, points):
        new = cls()
        lt = min(map(lambda e: e[0], points))
        r = max(map(lambda e: e[0], points))
        t = max(map(lambda e: e[1], points))
        b = min(map(lambda e: e[1], points))
        new._x, new._y = lt, t
        new._w, new._h = r - lt, t - b
        return new

    @classmethod
    def pts_angular_orthodromic(cls, a, b):
        ala1, ala2 = math.radians(90 - a[1]), math.radians(90 - b[1])
        dif_lo = math.radians(b[0] - a[0])
        return math.degrees(
            math.acos(
                math.cos(ala1) * math.cos(ala2) + math.sin(ala1) * math.sin(ala2) * math.cos(dif_lo)
            ))

    @classmethod
    def pts_orthodromic(cls, a, b):
        return cls.pts_angular_orthodromic(a, b) / 360 * cls.EARTH_ORTHODROME_PERIMETER

    @property
    def angular_orthodromic(self):
        return self.pts_angular_orthodromic(self.topleft, self.bottomright)

    @property
    def orthodromic(self):
        return self.pts_orthodromic(self.topleft, self.bottomright) / 360 * self.EARTH_ORTHODROME_PERIMETER

    def make_int(self):
        for n in range(4):
            self[n] = int(self[n])

    def int(self):
        new = self.copy()
        new.make_int()

    def round(self, digs):
        for n in range(4):
            self[n] = round(self[n], digs)

    def copy(self):
        return self.__class__(self._x, self._y, self._w, self._h)

    def __getitem__(self, ind):
        return [self._x, self._y, self._w, self._h][ind]

    def __setitem__(self, ind, val):
        setattr(self, ['_x', '_y', '_w', '_h'][ind], val)

    def __iter__(self):
        return iter((self._x, self._y, self._w, self._h))

    def __len__(self):
        return 4

    def __str__(self):
        self.str_parameter()

    def str_parameter(self):
        return '%s,%s~%s,%s' % (self.left, self.bottom, self.right, self.top)

    def curve(self):
        return [self.bottomleft, self.topleft, self.topright, self.bottomright, self.bottomleft]

    def __repr__(self):
        return '%s(%s, %s, %s, %s)' % (self.__class__.__name__, self._x, self._y, self._w, self._h)

    @property
    def size(self):
        return [self._w, self._h]

    @size.setter
    def size(self, size):
        self._w, self._h = size[0], size[1]

    def get_w(self):
        return self._w

    def set_w(self, w):
        self._w = w

    w = property(get_w, set_w)
    width = property(get_w, set_w)

    def get_h(self):
        return self._h

    def set_h(self, h):
        self._h = h

    h = property(get_h, set_h)
    height = property(get_h, set_h)

    @property
    def topleft(self):
        return [self._x, self._y]

    @topleft.setter
    def topleft(self, pos):
        self._x, self._y = pos[0], pos[1]

    @property
    def bottomleft(self):
        return [self._x, self._y - self._h]

    @bottomleft.setter
    def bottomleft(self, pos):
        self._x, self._y = pos[0], pos[1] + self._h

    def get_x(self):
        return self._x

    def set_x(self, x):
        self._x = x

    x = property(get_x, set_x)
    left = property(get_x, set_x)

    def get_y(self):
        return self._y

    def set_y(self, y):
        self._y = y

    y = property(get_y, set_y)
    top = property(get_y, set_y)

    @property
    def right(self):
        return self._x + self._w

    @right.setter
    def right(self, x):
        self._x = x - self._w

    @property
    def bottom(self):
        return self._y - self._h

    @bottom.setter
    def bottom(self, y):
        self._y = y + self._h

    @property
    def bottomright(self):
        return [self._x + self._w, self._y - self._h]

    @bottomright.setter
    def bottomright(self, pos):
        self._x, self._y = pos[0] - self._w, pos[1] + self._h

    @property
    def topright(self):
        return [self._x + self._w, self.y]

    @topright.setter
    def topright(self, pos):
        self._x, self._y = pos[0] - self._w, pos[1]

    @property
    def center(self):
        return [self._x + self._w / 2, self._y - self._h / 2]

    @center.setter
    def center(self, pos):
        self._x, self._y = pos[0] - self._w / 2, pos[1] + self._h / 2

    @property
    def centerx(self):
        return self._x + self._w / 2

    @centerx.setter
    def centerx(self, x):
        self._x = x - self._w / 2

    @property
    def centery(self):
        return self._y - self._h / 2

    @centery.setter
    def centery(self, y):
        self._y = y + self._h / 2

    def centered(self, pos):
        new = self.copy()
        new.center = pos
        return new
