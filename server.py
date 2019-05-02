import json

from flask import Flask, request
from settings import logging
from dialog_json_handler import Storage, Request, Response

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.errorhandler(404)
def error_404(*args):
    logging.error('404')
    logging.error(request.url)
    logging.error(str(dict(request.headers)))
    logging.error(json.dumps(request.json, ensure_ascii=False))


@app.route('/post', methods=['POST'])
def request_handler():
    data = request.json

    response = dialog(data)
    rs = response.send()
    logging.warning(str(rs))
    logging.warning(str(rs.json))
    return rs


def dialog(data):
    storage = Storage(data)
    req = Request(data)
    resp = Response(data)

    if req.new:
        resp.msg('Хотите сыграть? Отлично, обожаю эту игру!\nИз какого города начнём?')

    return resp
