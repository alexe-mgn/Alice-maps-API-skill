from flask import Flask, request

from settings import logging, dump_json
from dialog_json_handler import Storage, Response, Button, Card

from input_parser import Sentence
from APIs import GeoApi, MapsApi, SearchApi

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.errorhandler(404)
def error_404(*args):
    logging.error('404')
    logging.error(request.url)
    logging.error(str(dict(request.headers)))
    logging.error(dump_json(request.json))


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
    logging.info('INPUT ' + dump_json(user.request))
    logging.info('STATE ' + str(user.state) + ' ' + str(user.state_init) + ' DELAY ' + str(user.delay))
    logging.info('TYPE ' + str(user.type))
    logging.info('STORAGE ' + str(id(user)) + ' ' + dump_json(user.data))

    user.pre_step()
    result = handle_state(user, resp)
    user.post_step()
    return result


def handle_state(user, resp):
    if user.type == 'SimpleUtterance':
        sent = Sentence(user.text)
        key_loc = sent.filter(
            ['где', 'найти', 'близкий', 'радиус', 'от', 'до', 'наиболее', 'более', 'нахожусь', 'поблизости'])
        ag, dg = sent.agreement
        if user.state == 0:
            if user.delay == 0:
                user.init_state()
                resp.msg('Приветствую! Меня зовут Алиса, а как ваше имя?')
            else:
                fios = user.entity(t='fio')
                if fios and 'first_name' in fios[0]['value']:
                    logging.info('NAME RECOGNIZED ' + dump_json(fios))
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
                resp.msg('Что вы хотите узнать, %s? Я могу:\n\n'
                         '- Найти определённое место по названию\n'
                         '"найди|где ... [В радиусе ... (в км)]"\n'
                         'Дополнительно:\n'
                         '"Я нахожусь ..." - для улучшения поиска'
                         % (user['name'],))
            else:
                if sent.sentence_collision(['близкий', 'поблизости']) and not user['position']:
                    user['next'].append(user.state)
                    user.state = -1
                    resp.msg('{}?'.format(sent.find(['близкий', 'поблизости'])[0][0].word))
                elif sent.word_collision('нахожусь'):
                    user['next'].append(user.state)
                    user.state = -1
                    user.init_state(True)
                elif sent.sentence_collision(['где', 'найти']):
                    api_res = None
                    geo = user.geo_entity()
                    try:
                        if geo:
                            logging.info('RECOGNIZED GEO ' + dump_json(geo))
                            api_res = GeoApi(geo[0], ll=user['position'])
                        else:
                            logging.info('SEARCHING BY WORDS ' + str(key_loc))
                            api_res = SearchApi(str(key_loc), ll=user['position'])
                    except Exception:
                        pass
                    if api_res:
                        logging.info('RECOGNIZED {} GEO '.format(len(api_res)) + dump_json(api_res.data))
                        user['context'] = 'search'
                        resp.msg('Вот что мне удалось найти:\n')
                        mp = MapsApi()
                        for n, i in enumerate(api_res, 1):
                            resp.msg('{} - {}'.format(n, i.formatted_address))
                            mp.include_view(i.rect)
                            mp.add_marker(i.pos, 'pm2rdm' + str(n))

                        btn = Button(user, None, 'Показать карту', payload={
                            'action': 'map',
                            'url': mp.get_url(False),
                            'image_url': mp.get_url(True)
                        })
                        user.add_button(btn)
                    else:
                        resp.msg('Простите, не могу понять, о чём вы говорите. Попробуйте ещё раз')
                else:
                    resp.msg('Простите, не понимаю вашу просьбу')
            user.delay_up()

        if user.state == -1:
            if user.delay == 0:
                user.init_state()
                resp.msg('Где вы находитесь?')
            else:
                geo = user.geo_entity()
                api_res = None
                if geo:
                    logging.info('RECOGNIZED GEO ' + dump_json(geo))
                    api_res = GeoApi(geo[0])
                if api_res:
                    loc = api_res[0]

                    def callback():
                        user['position'] = loc.pos
                        return -1

                    user['next'].append(callback)
                    mp = MapsApi(bbox=loc.rect)
                    mp.add_marker(loc.pos, 'pm2al')
                    user.add_button(Button(user, None, 'Показать карту', payload={
                        'url': mp.get_url(False),
                        'image_url': mp.get_url(True),
                        'action': 'map'
                    }))
                    user['back'].append(-1)
                    user.state = -2
                else:
                    resp.msg('Простите, не понимаю о чём вы говорите')
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
                btn = Button(user, None, 'Показать на Яндекс.Картах', url=pl['url'])
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
