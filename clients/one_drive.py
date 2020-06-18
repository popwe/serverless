import json
import os
import time
from pathlib import Path

import requests

from clients.base import BaseClient


class OneDrive(BaseClient):

    def __init__(self):
        super(OneDrive, self).__init__()
        self._api_base_url = 'https://graph.microsoft.com/v1.0/'
        self.response_error = 'error.message'
        self.token = None

    def before_run(self):
        self.token = self.get_ms_token()

    def run(self):
        name = int(time.time())
        new_file = Path(f'/tmp/{name}.txt')
        new_file.write_text(f'{name}')
        self.upload(new_file)
        new_file.unlink()
        data = self.list()
        print(json.dumps(data, indent=4))

    def upload(self, src: Path, **kwargs):
        user_name = os.environ.get('user_name') or kwargs.get('user_name')
        drive = f'/users/{user_name}/drive/root'
        return self.api(f'{drive}:/{src.name}:/content', method='PUT', data=src.read_bytes())

    def get_ms_token(self, **kwargs):
        tenant_id = os.environ.get('tenant_id') or kwargs.get('tenant_id')
        url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        scope = 'https://graph.microsoft.com/.default'
        post_data = {
            'grant_type': 'client_credentials',
            'client_id': os.environ.get('client_id') or kwargs.get('client_id'),
            'client_secret': os.environ.get('client_secret') or kwargs.get('client_secret'),
            'scope': scope
        }
        result = self.fetch(url, data=post_data).json()
        return result['access_token']

    def list(self, **kwargs):
        api_params = {'select': 'id, name, createdDateTime', 'top': 10, 'orderby': 'name desc'}
        user_name = os.environ.get('user_name') or kwargs.get('user_name')
        return self.api(f'/users/{user_name}/drive/root/children', api_params)

    def api(self, api_sub_url, params=None, data=None, method=None, **kwargs):
        self.http.headers['Authorization'] = "Bearer {}".format(self.token)

        if api_sub_url.find('http') == -1:
            url = '{}/{}'.format(self._api_base_url.strip('/'), api_sub_url.strip('/'))
        else:
            url = api_sub_url
        return self.fetch(url, data=data, method=method, params=params, **kwargs).json()

    def fetch(self, url, data=None, method=None, json=None, **kwargs):
        kwargs.setdefault('timeout', 10)
        if (data or json) and method is None:
            method = 'POST'

        if method is None:
            method = 'GET'
        response = self.http.request(method, url, data=data, json=json, **kwargs)
        if response.ok:
            return response
        raise Exception(self._format_error_message(response))

    def _format_error_message(self, response: requests.Response):
        try:
            fields = self.response_error.split('.')
            data = response.json()
            message = None
            for field in fields:
                data = data.get(field)
                if type(data) == str:
                    message = data
            if not message:
                message = str(data)
            return response.request.url, response.status_code, message
        except Exception as e:
            return response.request.url, response.cookies, response.text


def script_main():
    one = OneDrive()
    one.before_run()
    return one.run()


def main_handler(event, context):
    return script_main()


if __name__ == '__main__':
    print(script_main())
