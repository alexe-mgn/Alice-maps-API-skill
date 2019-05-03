import pymorphy2 as pmp
import re

mra = pmp.MorphAnalyzer()


class WordVars:

    def __init__(self, word, *tags, score_thr=0, single=False, **ntags):
        if isinstance(word, self.__class__):
            res = word.data
        elif isinstance(word, str):
            res = mra.parse(word)
        else:
            res = list(word)
        for i in res.copy():
            tag = i.tag
            if i.score < score_thr:
                res.remove(i)
                continue
            if not (set(tags) in tag):
                res.remove(i)
                continue
            for k, v in ntags.items():
                if getattr(tag, k, None) != v:
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
        other = WordVars(other)
        for i in self.data:
            for j in other.data:
                if i.normal_form == j.normal_form and i.tag.POS == j.tag.POS:
                    score += (i.score * j.score) * (1 - score)
        return score

    def sentence_collision(self, sentence):
        if isinstance(sentence, str):
            sentence = re.sub(r'[^\w\s]+', ' ', sentence).split()
        score = 0
        collision = self.collision
        for i in sentence:
            c = collision(WordVars(i))
            score += c * (1 - score)
        return score

    def agreement(self):
        ac = ['да', 'можно', 'разрешать', 'соглашаться', 'возможно', 'конечно', 'вероятно', 'давать', 'хотеть',
              'хорошо', 'надо', 'очень', 'сильно', 'ладно', 'желать']
        return self.sentence_collision(ac)

    def disagreement(self):
        ac = ['нет', 'не', 'ни', 'плохо', 'исключить', 'стоп', 'отменить']
        return self.sentence_collision(ac)


def sentence_agreement(sentence):
    if isinstance(sentence, str):
        sentence = re.sub(r'[^\w\s]+', ' ', sentence).split()
    score = 0
    dscore = 0
    na = 0
    nd = 1
    for i in sentence:
        wv = WordVars(i)
        a = wv.agreement()
        da = wv.disagreement()
        if a:
            score += a * (1 - score)
            na += 1
        if da:
            dscore += da * (1 - dscore)
            nd += 1
    return score * na / (na + nd), dscore * nd / (na + nd)


if __name__ == '__main__':
    print(WordVars('стали').collision(WordVars('сталь')))
    print(WordVars('ласка').collision(WordVars('ласка')))
    print(WordVars('замок').collision(WordVars('замок')))
    print(WordVars('мой').collision(WordVars('мой')))
    print(WordVars('да').collision('да'))
    print()
    print(WordVars('да').sentence_collision(
        'в этом слове есть согласие, да ведь? не очень сильно, но да, есть и несогласие'))
    print(WordVars('нет').sentence_collision(
        'в этом слове есть согласие, да ведь? не очень сильно, но да, есть и несогласие'))
    print(WordVars('да').agreement())
    print(WordVars('нет').disagreement())
    print()
    print(sentence_agreement('в этом слове есть согласие, да ведь? не очень сильно, но да, есть и несогласие'))
