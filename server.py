import logging

from flask import Flask, request
from dialog_json_handler import Storage, Request, Response

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

storage = {}


@app.route('/post', methods=['POST'])
def request_handler():
    data = request.json

    response = dialog(data)

    return response.send()


def dialog(data):
    storage = Storage(data)
    req = Request(data)
    resp = Response(data)

    if req.new:
        pass

    return resp


if __name__ == '__main__':
    app.run()
