import requests
from settings import logging, log_request

SKILL_ID = '18bd15c0-0056-4265-8e24-f8245b56530c'
OAuth = 'AQAAAAAOlI_mAAT7o4LNuuJYEUh7rJFD90giiuw'
DIALOGS_API_URL = 'https://dialogs.yandex.net/api/v1/'
DIALOGS_API_SKILL_URL = DIALOGS_API_URL + 'skills/{}/images/'.format(SKILL_ID)


class DialogsApi:

    @staticmethod
    def get_storage_status():
        resp = requests.get(DIALOGS_API_URL + 'status',
                            headers={
                                'Authorization': 'OAuth {}'.format(OAuth)
                            }).json()['images']['quota']
        return resp['used'], resp['total']

    @staticmethod
    def get_images():
        resp = [e['id'] for e in
                requests.get(DIALOGS_API_SKILL_URL,
                             headers={
                                 'Authorization': 'OAuth {}'.format(OAuth)
                             }).json()['images']]
        return resp

    @staticmethod
    def remove_image(mid):
        logging.info('REMOVING IMAGE ' + str(mid))
        resp = requests.delete(DIALOGS_API_SKILL_URL + str(mid).strip('/'),
                               headers={
                                   'Authorization': 'OAuth {}'.format(OAuth)
                               })
        log_request(resp)
        resp = resp.json()
        return 'result' in resp and resp['result'] == 'ok'

    @classmethod
    def remove_all_images(cls):
        logging.info('REMOVING IMAGES')
        r = True
        for i in cls.get_images():
            if not cls.remove_image(i):
                r = False
        return r

    @staticmethod
    def upload_image_source(source):
        logging.info('UPLOADING IMAGE')
        resp = requests.post(DIALOGS_API_SKILL_URL, files={'file': source},
                             headers={
                                 'Authorization': 'OAuth {}'.format(OAuth),
                             })
        log_request(resp)
        resp = resp.json()
        if 'image' in resp:
            return resp['image']['id']
        return False

    @staticmethod
    def upload_image_url(url):
        logging.info('UPLOADING IMAGE FROM ' + url)
        resp = requests.post(DIALOGS_API_SKILL_URL, json={'url': url},
                             headers={
                                 'Authorization': 'OAuth {}'.format(OAuth),
                             })
        logging.info('request finished, got ' + resp.content.decode('utf-8'))
        log_request(resp)
        resp = resp.json()
        if 'image' in resp:
            return resp['image']['id']
        return False
