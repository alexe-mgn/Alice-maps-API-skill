from flask import Flask, request
from settings import logging, dump_json
from dialog_json_handler import Storage, Response, Button, Card
from parser import WordVars, Sentence
from APIs import GeoApi, MapsApi, SearchApi
from dialogs_API import DialogsApi

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
    if data['session']['new']:
        Storage.remove(data['session']['user_id'])
    user = Storage(data)
    resp = Response(data)
    logging.info('CONTINUE ' + str(user.id))
    logging.info('INPUT ' + dump_json(user.request))
    logging.info('STATE ' + str(user.state) + ' ' + str(user.state_init) + ' DELAY ' + str(user.delay))
    logging.info('TYPE ' + str(user.type))

    user.pre_step()

    if user.type == 'SimpleUtterance':
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
                resp.msg('Что вы хотите узнать, %s? Я могу:\n'
                         '- Найти определённое место по названию\n'
                         '"найди|где ... [В радиусе ... (в км)]"\n'
                         % (user['name'],))
            else:
                text = Sentence(user.text)

                if text.sentence_collision(['где', 'найти']):
                    api_res = None
                    geo = user.geo_entity()
                    try:
                        if geo:
                            api_res = GeoApi(geo[0])
                        else:
                            api_res = SearchApi(str(text.filter(['где', 'найти', 'близкий', 'радиус'])))
                    except Exception:
                        pass
                    if api_res:
                        user['context'] = 'search'
                        resp.msg('Мне удалось найти несколько вариантов.')
                        mp = MapsApi()
                        for n, i in enumerate(api_res):
                            resp.msg('{} - {}'.format(n, i.formatted_address))
                            mp.include_view(i.rect)

                        btn = Button(user, None, 'Показать карту', url=mp.get_url(static=False))
                        try:
                            mid = DialogsApi.upload_image_url(mp.get_url(static=True))
                            if mid:
                                user.set_image('temp', mid)
                            else:
                                raise Exception
                            card = Card(user, user.text, mid)
                            card['button'] = btn.send()
                            user.add_card(card)
                        except Exception:
                            user.add_button(btn)
                    else:
                        resp.msg('Простите, не могу понять, о чём вы говорите.')
                else:
                    resp.msg('Простите, не понимаю вашу просьбу')

            user.delay_up()

    elif user.type == 'ButtonPressed':
        resp.text = 'Выполняю'

    user.post_step()
    return resp
