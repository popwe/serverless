import logging
import os
import random
import re

import pyquery
import requests


class BaseClient:

    def __init__(self):
        self.base_url = None
        self.http = requests.session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36'
        }
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = {}
        self.username = None
        self.password = None
        self.default_username = None
        self.default_password = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def before_run(self):
        self.username = os.environ.get('USER_NAME', self.default_username)
        self.password = os.environ.get('PASSWORD', self.default_password)

    def run(self):
        pass

    def dz_user_info(self):
        info_url = '{}/home.php?mod=spacecp&ac=credit&op=base'.format(self.base_url)
        res = self.fetch(info_url)
        doc = pyquery.PyQuery(res.text)
        html = doc('.creditl').html()
        if html:
            html = html.replace('&#13;', '').strip()
            html = html.replace('<em>', '').replace('</em>', '').replace('(前往兌換商城)', '').strip()
            html = re.sub('<[^>]+>', '', html)
            html = re.sub('(\r?\n)', '', html).strip()
        return html

    def dz_views(self):
        uid_list = self.dz_get_users()
        if type(uid_list) != list or len(uid_list) <= 2:
            return None

        _uid = []
        for i in range(11):
            uid = random.choice(uid_list)
            _uid.append(uid)
            url = '%s/space-uid-%s.html' % (self.base_url, uid)
            self.fetch(url)
        return _uid

    def dz_get_users(self):
        user_url = '{}/home.php?gender=0&startage=&endage=&avatarstatus=1&username=&searchsubmit=true&op=sex&mod=spacecp&ac=search&type=base'.format(
            self.base_url)
        html = self.fetch(user_url).text
        doc = pyquery.PyQuery(html)

        message = doc('#messagetext').text()
        if message:
            raise Exception(message)

        elements = doc('ul.buddy li.bbda')
        user_id_list = []
        for element in elements.items():
            link = element('div.avt a').eq(0).attr('href')
            if not link:
                continue
            uid = re.search('uid[=-]([0-9]+)', link)
            if uid:
                user_id_list.append(uid.group(1))
        return user_id_list

    def dz_post(self, **kwargs):
        post_url = '{}/forum.php?mod=post&action=newthread&fid={}'
        fid = kwargs.get('fid', 7)
        form_name = kwargs.get('form_name', '#postform')
        post_url = post_url.format(self.base_url, fid)
        res = self.fetch(post_url)

        doc = pyquery.PyQuery(res.text)
        form = doc(form_name)
        input_list = form('input')

        params = {}
        for _input in input_list.items():
            params[_input.attr('name')] = _input.val()
        params['subject'] = '簽到賺積分'
        params['message'] = '簽到賺積分簽到賺積分簽到賺積分簽到賺積分簽到賺積分'
        action = '%s/%s%s' % (self.base_url, form.attr('action').strip('/'), '&inajax=1')
        res = self.fetch(action, params)
        if res.text.find('主題已發佈') != -1:
            return '{} publish done.'.format(params['subject'])

        message = _get_message(res.text)
        return '{} publish fail.\n{}'.format(params['subject'], message)

    def dz_login(self, max_retry=4):
        form = None
        for i in range(1, max_retry):
            res = self.fetch('{}/member.php?mod=logging&action=login'.format(self.base_url))
            doc = pyquery.PyQuery(res.text)
            form = doc('form[name="login"]')
            if form:
                break

            if not form and i >= max_retry:
                raise Exception('login parse form error', self.base_url)

        action = '%s/%s%s' % (self.base_url, form.attr('action').strip('/'), '&inajax=1')
        input_list = form('input')
        params = {}
        for _input in input_list.items():
            if _input.attr('name'):
                params[_input.attr('name')] = _input.val()
        params['username'] = self.username
        params['password'] = self.password
        params['cookietime'] = '2592000'
        params['loginfield'] = 'username'

        response = self.fetch(action, data=params, method='POST')
        html = response.text
        if html.find(self.username) == -1:
            logging.info('[{}]: login fail'.format(self.username))
            logging.info(_get_message(html))
            return False
        logging.info('[{}]: login success'.format(self.username))
        return True

    def fetch(self, url, data=None, method='GET', **kwargs):
        kwargs.setdefault('timeout', 10)
        kwargs.setdefault('headers', self.headers)

        if data:
            method = 'POST'

        response = self.http.request(method, url, data=data, **kwargs)
        if response.ok:
            return response
        raise Exception(url)

    def dz_sign(self, **kwargs):
        sign_url = '{}/plugin.php?id=dsu_paulsign:sign'.format(self.base_url)
        response = self.fetch(sign_url)
        form_name = kwargs.get('form_name', '#qiandao')
        doc = pyquery.PyQuery(response.text)
        form = doc(form_name)

        if not form:
            return response.text

        action = '%s/%s%s' % (self.base_url, form.attr('action').strip('/'), '&inajax=1')

        input_list = form('input')
        params = {}
        for _input in input_list.items():
            params[_input.attr('name')] = _input.val()
        params['todaysay'] = '哈哈哈'

        return self.fetch(action, params).text

    def dz_poke(self, **kwargs):
        uid_list = self.dz_get_users()
        if len(uid_list) <= 2:
            return 'find user fail. %s' % uid_list
        success_text = kwargs.get('success_text', '已發送')
        result = []
        for i in range(11):
            uid = random.choice(uid_list)
            poke_url = '{}/home.php?mod=spacecp&ac=poke&op=send&uid={}'.format(self.base_url, uid)
            res = self.fetch(poke_url)

            doc = pyquery.PyQuery(res.text)
            form = doc('#ct form')
            input_list = form('input')

            params = {}
            for _input in input_list.items():
                params[_input.attr('name')] = _input.val()
            params['iconid'] = '3'

            action = '%s&inajax=1' % poke_url
            res = self.fetch(action, params)
            html = res.text
            if html.find(success_text) != -1:
                result.append(f'{uid} poke done.')

        return result


def _get_message(html, default_message=None):
    message = re.search(r'<div class="alert_error">([^<]+)<', html)
    if message:
        return message.group(1)
    message = re.search(r'CDATA\[(.*?)<', html)
    if message:
        return message.group(1)

    if default_message:
        return default_message
    return html
