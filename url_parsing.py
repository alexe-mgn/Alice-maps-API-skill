class Str:

    @staticmethod
    def pos(pos, rev=False):
        return ','.join(str(e) for e in pos[::int(not rev) * 2 - 1])

    @staticmethod
    def points(points, rev=False):
        return ','.join((Str.pos(e, rev) for e in points))

    @staticmethod
    def marks(points, style=None, color=None, size=None, content=None, rev=False):
        pts = []
        for n, e in enumerate(points):
            v = []
            for sk in [style, color, size, content]:
                if sk:
                    if not isinstance(sk, str) and hasattr(sk, '__getitem__'):
                        if 0 <= n < len(sk):
                            v.append(str(sk[n]))
                        else:
                            continue
                    else:
                        v.append(str(sk))
            pts.append(','.join([Str.pos(e, rev)] + [''.join(v)]))
        return '~'.join(pts)

    @staticmethod
    def curve(points, color=None, fill=None, width=None, rev=False):
        q = []
        if color is not None:
            q.append('c:%s' % (str(color),))
        if fill is not None:
            q.append('f:%s' % (str(fill),))
        if width is not None:
            q.append('w:%s' % (str(width),))
        return ','.join(q + [Str.points(points, rev)])

    @staticmethod
    def parameter(k, v):
        pass

    @staticmethod
    def query(dct):
        res = dct.copy()
        for k, v in dct.items():
            if v is None:
                pass
            elif k == 'pt':
                res[k] = '~'.join(
                    [(
                            Str.pos(m[0]) + ((',' + m[1]) if len(m) > 1 and m[1] else '')
                    ) for m in v]
                )
            elif k == 'pl':
                polys = []
                for poly in v:
                    str_args = ','.join(
                        '{k}:{v}'.format(k=pk, v=pv)
                        for pk, pv in poly.items()
                        if pk in ['c', 'f', 'w']
                    )
                    curves = []
                    for curve in poly['curves']:
                        if hasattr(curve, 'curve'):
                            pts = curve.curve()
                        else:
                            pts = list(curve)
                        curves.append(','.join(Str.pos(p) for p in pts))
                    str_curves = ';'.join(curves)
                    str_poly = ''.join(
                        ((str_args + ',') if str_args else '',
                         str_curves)
                    )
                    polys.append(str_poly)
                res[k] = '~'.join(polys)
            elif isinstance(v, str) or hasattr(v, '__int__'):
                res[k] = str(v)
            elif hasattr(v, 'str_parameter'):
                res[k] = v.str_parameter()
            elif len(v) == 2 and hasattr(v[0], '__int__'):
                res[k] = Str.pos(v)
            elif hasattr(v, '__getitem__'):
                pass
            else:
                res[k] = str(v)
        return res

    @classmethod
    def string_query(cls, pars):
        return '&'.join(['{}={}'.format(k, v) for k, v in cls.query(pars).items()])


class Parse:

    @staticmethod
    def pos(pos, rev=False):
        return [float(e) for e in pos.split(' ')[::int(not rev) * 2 - 1]]
