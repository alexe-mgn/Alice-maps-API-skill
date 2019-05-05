from flask import Flask, request

from settings import logging, log_object
from dialog_json_handler import Storage, Response, Button, Card

from input_parser import Sentence
from APIs import GeoApi, MapsApi, SearchApi

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

hint = 'Что вы хотите узнать, %s? Я могу:\n\n' \
       '- Найти определённое место по названию\n' \
       '(можете указать искать "место" или "объект"/"организацию")\n' \
       '"найди|где ["место" / "объект"] ..."\n' \
       'Про любой из найденных результатов я могу рассказать подробнее\n' \
       '"... подробнее | вариант | расскажи ... <номер>"\n' \
       'Например\n\n' \
       'Дополнительно:\n' \
       '"Я нахожусь ..." - для улучшения поиска\n' \
       '"Что ты умеешь|можешь..."'


@app.errorhandler(404)
def error_404(*args):
    logging.error('404')
    logging.error(request.url)
    logging.error(str(dict(request.headers)))
    logging.error(log_object(request.json))


@app.route('/post', methods=['POST'])
def request_handler():
    data = request.json
    resp = dialog(data)
    return resp.send()


def dialog(data):
    logging.info('-----------DIALOG-----------')
    if data['session']['new']:
        Storage.remove(data['session']['user_id'])
    user = Storage(data)
    resp = Response(data)
    logging.info('CONTINUE ' + str(user.id))
    logging.info('INPUT ' + log_object(user.request))
    logging.info('STATE ' + str(user.state) + ' ' + str(user.state_init) + ' DELAY ' + str(user.delay))
    logging.info('TYPE ' + str(user.type))
    logging.info('STORAGE ' + str(id(user)) + ' ' + log_object(user.data))

    user.pre_step()
    result = handle_state(user, resp)
    user.post_step()
    return result


def handle_state(user, resp):
    if user.type == 'SimpleUtterance':
        sent = Sentence(user.text)
        key_loc = sent.filter(
            ['где', 'найти', 'близкий', 'радиус', 'от', 'до', 'наиболее', 'более', 'нахожусь', 'поблизости', 'рядом',
             'искать'])
        ag, dg = sent.agreement

        if user.state == 0:
            if user.delay == 0:
                user.init_state()
                resp.msg('Приветствую! Меня зовут Алиса, а как ваше имя?')
            else:
                fios = user.entity(t='fio')
                if fios and 'first_name' in fios[0]['value']:
                    logging.info('NAME RECOGNIZED ' + log_object(fios))
                    name = fios[0]['value']['first_name']
                    user['name'] = name[0].upper() + name[1:]
                    resp.msg('Очень приятно.')
                    user.state = 1
                else:
                    resp.msg('Простите, я не расслышала вашего имени. Повторите, пожалуйста.')
            user.delay_up()

        if user.state == 1:
            if user.delay == 0:
                user.init_state()
                if not user.get('context', None):
                    resp.msg(hint % (user['name'],))
            else:
                if sent.sentence_collision(['близкий', 'поблизости', 'рядом']) and not user['position']:
                    def callback(user=user, request=user.request):
                        user.state = 1
                        user.init_state(True)
                        user.request = request
                        logging.info('continue after position recognition ' + log_object(
                            {'text': user.text, 'pos': user['position'], 'state': (user.state, user.delay)}
                        ))

                    user['next'].append(callback)
                    user.state = -1
                    resp.msg('{}?'.format(sent.find(['близкий', 'поблизости', 'рядом'])[0][0].word))

                elif sent.word_collision('нахожусь'):
                    user['next'].append(user.state)
                    user.state = -1
                    user.init_state(True)

                elif sent.sentence_collision(['где', 'найти', 'искать']):
                    api_res = None
                    geo = user.geo_entity()
                    try:
                        if (geo or sent.word_collision('место')) and \
                                not sent.sentence_collision(['объект', 'организация']):
                            logging.info('RECOGNIZED GEO ' + log_object(geo))
                            api_res = GeoApi(geo[0], ll=user['position'])
                        else:
                            logging.info('SEARCHING BY WORDS ' + str(key_loc))
                            api_res = SearchApi(str(key_loc), ll=user['position'])
                    except Exception:
                        pass
                    if api_res:
                        logging.info('RECOGNIZED {} GEO '.format(len(api_res)) + log_object(api_res.data))
                        user['context'] = 'search'
                        user['variants'] = []
                        resp.msg('Вот что мне удалось найти:\n')
                        mp = MapsApi()
                        for n, i in enumerate(api_res, 1):
                            resp.msg('{} - {}\n\t{}'.format(n, i.name, i.formatted_address))
                            user['variants'].append(i)
                            mp.include_view(i.rect)
                            mp.add_marker(i.pos, 'pm2rdm' + str(n))
                        ym = mp.get_url(False)
                        if user['position']:
                            mp.add_marker(user['position'], 'pm2al')
                        btn = Button(user, 'map', 'Показать карту', life=-1, payload={
                            'action': 'map',
                            'url': ym,
                            'image_url': mp.get_url(True)
                        })
                        user.add_button(btn)
                    else:
                        resp.msg('Простите, не могу понять, о каком месте вы говорите. Попробуйте ещё раз')

                elif sent.sentence_collision(['умеешь', 'можешь']):
                    resp.msg(hint % (user['name'],))

                elif user.get('variants', None) and sent.sentence_collision(['вариант', 'подробный', 'расскажи']):
                    if user.entity(t='number'):
                        vn = int(user.entity(t='number')[0]['value'])
                        if 1 <= vn <= len(user['variants']):
                            user['vn'] = vn - 1
                            user['back'].append(1)
                            user.state = 2
                        else:
                            resp.msg('Я что-то не помню варианта под таким номером.')
                    else:
                        resp.msg('Я могу рассказать вам поподробнее про любой из вариантов.\n'
                                 'Сначала выберите вариант, а потом скажите, какую информацию хотите узнать,\n'
                                 'Либо сразу задайте вопрос про такой-то вариант')

                else:
                    for i in user.buttons[::-1]:
                        if sent.sentence_collision(i['title']):
                            user.type = 'ButtonPressed'
                            user.payload = i['payload']
                            return handle_state(user, resp)
                    resp.msg('Простите, не понимаю вашу просьбу')
            user.delay_up()

        if user.state == 2:
            user['context'] = 'variant'
            v = user['variants'][user['vn']]
            user.delay_up()
            if sent.word_collision('карта'):
                mp = MapsApi(bbox=v.rect)
                mp.add_marker(v.pos, 'pm2bll')
                ym = mp.get_url(False)
                if user['position']:
                    mp.add_marker(user['position'], 'pm2al')
                    mp.include_view(user['position'])

                mid = user.upload_image('map', mp.get_url(True))
                resp.msg('Показать карту не удалось')
                btn = Button(user, 'map_url', 'Показать на Яндекс.Картах', url=ym)
                if mid:
                    card = Card(user, 'Показать на Яндекс.Картах', mid)
                    card['button'] = btn.send()
                    user.add_card(card)
                else:
                    user.add_button(btn)
            elif sent.sentence_collision(['имя', 'название', 'что', 'тип']):
                resp.msg(v.name)
            elif sent.sentence_collision(['адрес', 'находиться']):
                resp.msg('Полный адрес:\n' + v.formatted_address)
            elif sent.sentence_collision(['время', 'когда', 'часы', 'сейчас', 'работает']):
                wh = v.workhours
                if wh:
                    resp.msg(wh['text'])
                    resp.msg(wh['State']['text'])
                    resp.msg('Сейчас {}'.format('открыто' if wh['State']['is_open_now'] == '1' else 'закрыто'))
                else:
                    resp.msg('Данных о времени работы нет')
            elif sent.sentence_collision(['телефон', 'сотовый', 'номер']):
                t = v.phone_numbers
                if t:
                    resp.msg('Известные номера для этого объекта:')
                    resp.msg('\n'.join(t))
                else:
                    resp.msg('Нет информации о номере телефона')
            elif dg > .2:
                resp.msg('Как скажете')
            else:
                resp.msg('Что вы хотите узнать?')
                for i in ['Время работы', 'телефон', 'адрес', 'покажи на карте']:
                    user.add_button(Button(user, None, i, attach=False))
                return resp
            user.state = user.back()
            return handle_state(user, resp)

        if user.state == -1:
            if user.delay == 0:
                user.init_state()
                resp.msg('Где вы находитесь?')
            else:
                geo = user.geo_entity()
                api_res = None
                if geo:
                    logging.info('RECOGNIZED GEO ' + log_object(geo))
                    api_res = GeoApi(geo[0])
                if api_res:
                    loc = api_res[0]
                    mp = MapsApi(bbox=loc.rect)
                    mp.add_marker(loc.pos, 'pm2al')
                    user.add_button(Button(user, None, 'Показать карту', payload={
                        'url': mp.get_url(False),
                        'image_url': mp.get_url(True),
                        'action': 'map'
                    }))
                    user['back'].append(-1)

                    def callback(user=user, pos=loc.pos):
                        logging.info('CALLBACK setting position')
                        user['position'] = list(pos)
                        return user.next()

                    user['next'].append(callback)
                    user.state = -2
                else:
                    resp.msg('Где вы находитесь?')
                    resp.msg('Простите, не могу понять где это')
            user.delay_up()

        if user.state == -2:
            if user.delay == 0:
                user.init_state()
                resp.msg('Это здесь?')
            else:
                if ag > dg:
                    resp.msg('Понятно')
                    user.state = user.next()
                    return handle_state(user, resp)
                elif dg > ag:
                    resp.msg('Как скажете')
                    user.state = user.back()
                    return handle_state(user, resp)
                else:
                    resp.msg('Не могу понять вашего ответа')
            user.delay_up()

    elif user.type == 'ButtonPressed':
        if user.payload:
            pl = user.payload
            action = pl.get('action')
            if action == 'map':
                resp.text = 'Показать карту не удалось'
                btn = Button(user, 'map_url', 'Показать на Яндекс.Картах', url=pl['url'])
                img = user.upload_image('map', pl['image_url'])
                if img:
                    card = Card(user, '', img)
                    card['button'] = btn.send()
                    card['title'] = btn['title']
                    user.add_card(card)
                else:
                    user.add_button(btn)
        else:
            resp.text = 'Выполняю'

    return resp
