import pymorphy2 as pmp
import re

mra = pmp.MorphAnalyzer()


class WordVars:

    def __init__(self, word, *tags, score_thr=0, single=False, **ntags):
        self.source = word.lower()
        res = mra.parse(self.source)
        for i in res.copy():
            if i.score < score_thr:
                res.remove(i)
                continue
            if not (set(tags) in i.tag):
                res.remove(i)
                continue
            for k, v in ntags.items():
                if getattr(i.tag, k, None) != v:
                    res.remove(i)
                    continue
        self.data = res if not single else [max(res, key=lambda e: e.score)]

    def __bool__(self):
        return bool(self.data)

    def __getitem__(self, item):
        return self.data[item]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return str(self.data)

    def collision(self, other):
        score = 0
        for i in self.data:
            for j in other.data:
                if i.normal_form == j.normal_form:
                    score += (i.score * j.score) ** .5
        return score / (len(self) + len(other))


def word_collision(a, b):
    if isinstance(a, str):
        a = WordVars(a)
    if isinstance(b, str):
        b = WordVars(b)
    return a.collision(b)


def word_sentence_collision(w, s):
    if isinstance(w, str):
        w = WordVars(w)
    s = re.sub(r'[^\w\s]+', ' ', s)
    score = 0
    for i in s.split():
        c = w.collision(WordVars(i))
        if c > 0:
            score += c * (1 - score)
    return score


print(WordVars('стали').collision(WordVars('сталь')))
print(WordVars('ласка').collision(WordVars('ласка')))
print(WordVars('замок').collision(WordVars('замок')))
print(WordVars('мой').collision(WordVars('мой')))
