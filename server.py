from flask import Flask, request
from settings import logging, dump_json
from dialog_json_handler import Storage, Request, Response

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
    logging.info('CONTINUE ' + str(user_id))
    logging.info('STATE ' + str(obj.state) + ' DELAY ' + str(obj.delay))
    logging.info('STORAGE ' + dump_json(obj.data))

    if user.state == 0:
        if user.delay == 0:
            resp.msg('Приветствую! Не хотите поиграть в...\nПутешествие?')
            user.delay_up()
        elif user.delay < 2:
            if True:
                resp.msg('Прекрасно! Как вас зовут?')
                user.state = 1
            else:
                resp.msg('Ну давайте, будет весело!')
                user.delay_up()
        else:
            resp.end = True

    return resp
