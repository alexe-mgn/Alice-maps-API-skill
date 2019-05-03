from flask import Flask, request
from settings import logging, dump_json
from dialog_json_handler import Storage, Request, Response
from parser import sentence_agreement
from APIs import GeoHandler

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
    storage = Storage(data)
    user = Request(data)
    resp = Response(data)
    logging.info('CONTINUE ' + str(user.id))
    logging.info('STATE ' + str(user.state) + ' DELAY ' + str(user.delay))
    logging.info('STORAGE ' + dump_json(storage.data))
    storage.pre_step()

    if user.state == 0:
        # delay НЕ ПО НАЗНАЧЕНИЮ!
        if user.delay == 0:
            resp.msg('Приветствую! Не хотите поиграть в...\nПутешествие?')
            user.init_state(True)
        elif user.delay == 1:
            a, d = sentence_agreement(user.text)
            if a > d:
                user.state = 1
            elif d > a:
                resp.msg('Ну давайте, будет весело!')
                user.delay_up()
            else:
                resp.msg('Не томите меня ответом. Соглашайтесь!')
        else:
            a, d = sentence_agreement(user.text)
            if a > d:
                user.state = 1
            elif d > a:
                resp.msg('Как жаль, ну как хотите, до скорой встречи.')
                logging.info('FINISHING DIALOG')
                resp.end = True
            else:
                resp.msg('Что говорите? Согласны?')
            user.delay_up()

    if user.state == 1:
        if user.delay == 0:
            user.init_state()
            resp.msg('Прекрасно! Как вас зовут?')
        else:
            fios = user.entity(t='fio')
            if fios and 'first_name' in fios[0]['value']:
                logging.info('NAME RECOGNIZED ' + dump_json(fios))
                storage['name'] = fios[0]['value']['first_name']
                user.state = 2
            else:
                resp.msg('Простите, я не расслышала вашего имени. Повторите, пожалуйста.')
        user.delay_up()

    if user.state == 2:
        if user.delay == 0:
            user.init_state()
            resp.msg('Хотите узнать правила игры?')
        else:
            a, d = sentence_agreement(user.text)
            if a > d:
                resp.msg('Ну чтож\n\n'
                         'Вы начинаете своё путешествие почти из любой точки Земного шара, '
                         'а ваша цель - добраться до какого-нибудь другого места.\n'
                         'Для этого вы можете использовать большинство видов транспорта, либо идти пешком\n'
                         'В конце я подведу итоги ваших действий, например - затраченное время')
                user.state = 3
            elif d > a:
                resp.msg('Как скажете...')
                user.state = 3
            else:
                resp.msg('Я не очень поняла, что вы имеете ввиду.')
        user.delay_up()

    if user.state == 3:
        if user.delay == 0:
            user.init_state()
            resp.msg('Откуда начнём?')
        else:
            geo = user.geo_entity()
            if geo:
                res = GeoHandler(geocode=','.join(geo[0]))
                if not res:
                    resp.msg('Простите, я такого места не знаю, попробуйте ещё раз')
                else:
                    resp.msg('Вы это место иммели ввиду?')
        user.delay_up()

    storage.post_step()
    return resp
