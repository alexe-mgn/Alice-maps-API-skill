import requests
from settings import logging, dump_json

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
        return [[e['id'], e['origUrl']] for e in
                requests.get(DIALOGS_API_SKILL_URL,
                             headers={
                                 'Authorization': 'OAuth {}'.format(OAuth)
                             }).json()['images']]

    @staticmethod
    def upload_image_source(source):
        logging.info('UPLOADING IMAGE')
        resp = requests.post(DIALOGS_API_SKILL_URL, files={'file': source},
                             headers={
                                 'Authorization': 'OAuth {}'.format(OAuth),
                                 'Content-Type': 'multipart/form-data'
                             }).json()
        logging.info('GOT ' + dump_json(resp))
        if 'image' in resp:
            return resp['image']['id'], resp['image']['origUrl']
        return False

    @staticmethod
    def upload_image_url(url):
        logging.info('UPLOADING IMAGE FROM ' + url)
        resp = requests.post(DIALOGS_API_SKILL_URL, data={"url": url},
                             headers={
                                 'Authorization': 'OAuth {}'.format(OAuth),
                                 'Content-Type': 'application/json'
                             }).json()
        logging.info('GOT ' + dump_json(resp))
        if 'image' in resp:
            return resp['image']['id'], resp['image']['origUrl']
        return False
