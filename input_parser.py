import pymorphy2 as pmp
import re

mra = pmp.MorphAnalyzer()


class Word:

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

    def word_collision(self, other):
        score = 0
        other = self.__class__(other)
        for i in self.data:
            for j in other.data:
                if i.normal_form == j.normal_form:
                    score += (i.score * j.score) * (1 - score)
        return score

    def sentence_collision(self, sentence):
        sentence = Sentence(sentence)
        score = 0
        collision = self.word_collision
        for i in sentence:
            c = collision(self.__class__(i))
            score += c * (1 - score)
        return score

    @property
    def agreement(self):
        ac = ['да', 'можно', 'разрешю', 'соглашаюсь', 'возможно', 'конечно', 'вероятно', 'даю', 'хочу',
              'хорошо', 'надо', 'очень', 'сильно', 'ладно', 'желаю', 'ок', 'окей', 'согласие', 'положительный']
        return self.sentence_collision(ac)

    @property
    def disagreement(self):
        ac = ['нет', 'не', 'ни', 'плохо', 'исключаю', 'стоп', 'отменяю', 'несогласие', 'отрицательный', 'ничто',
              'ничего']
        return self.sentence_collision(ac)


class Sentence:

    def __init__(self, data):
        if isinstance(data, str):
            self.data = [Word(e) for e in re.sub(r'[^\w\s]+', ' ', data).split() if e]
        else:
            self.data = [Word(e) for e in data if e]

    def __bool__(self):
        return bool(self.data)

    def __getitem__(self, ind):
        return self.data[ind]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return ' '.join(e[0].normal_form for e in self.data if e)

    def get_word(self, word):
        res = []
        for i in self.data:
            if i.word_collision(word):
                res.append(i)
        return res

    def word_collision(self, other):
        return Word(other).sentence_collision(self)

    def sentence_collision(self, sentence):
        sentence = self.__class__(sentence)
        score = 0
        for wa in self:
            for wb in sentence:
                score += wa.word_collision(wb) * (1 - score)
        return score

    def filter(self, words):
        return Sentence(e for e in self.data if not e.sentence_collision(words))

    def find(self, words):
        return Sentence(e for e in self.data if e.sentence_collision(words))

    @property
    def agreement(self):
        score = 0
        dscore = 0
        na = 0
        nd = 1
        for w in self:
            a = w.agreement
            da = w.disagreement
            if a:
                score += a * (1 - score)
                na += 1
            if da:
                dscore += da * (1 - dscore)
                nd += 1
        return score * na / (na + nd), dscore * nd / (na + nd)


# def sentence_collision(a, b):
#     if isinstance(a, str):
#         a = re.sub(r'[^\w\s]+', ' ', a).split()
#     if isinstance(b, str):
#         b = re.sub(r'[^\w\s]+', ' ', b).split()
#     score = 0
#     for wa in a:
#         wa = Word(wa)
#         for wb in b:
#             score += wa.word_collision(wb) * (1 - score)
#     return score
#
#
# def sentence_agreement(sentence):
#     if isinstance(sentence, str):
#         sentence = re.sub(r'[^\w\s]+', ' ', sentence).split()
#     score = 0
#     dscore = 0
#     na = 0
#     nd = 1
#     for i in sentence:
#         wv = Word(i)
#         a = wv.agreement
#         da = wv.disagreement
#         if a:
#             score += a * (1 - score)
#             na += 1
#         if da:
#             dscore += da * (1 - dscore)
#             nd += 1
#     return score * na / (na + nd), dscore * nd / (na + nd)


if __name__ == '__main__':
    print(Word('стали').word_collision(Word('сталь')))
    print(Word('ласка').word_collision(Word('ласка')))
    print(Word('замок').word_collision(Word('замок')))
    print(Word('мой').word_collision(Word('мой')))
    print(Word('да').word_collision('да'))
    print()
    print(Word('да').sentence_collision(
        'в этом слове есть согласие, да ведь? не очень сильно, но да, есть и несогласие'))
    print(Word('нет').sentence_collision(
        'в этом слове есть согласие, да ведь? не очень сильно, но да, есть и несогласие'))
    print(Word('да').agreement)
    print(Word('нет').disagreement)
    print()
    print(Sentence('в этом слове есть согласие, да ведь? не очень сильно, но да, есть и несогласие').agreement)
