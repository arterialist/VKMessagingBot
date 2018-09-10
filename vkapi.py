# -*- coding: utf-8 -*-
import json
from bs4 import BeautifulSoup
from time import sleep

import requests

import apiobjects
from sqliteutil import SQLUtil


class VkApiClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.names_cache = {}

    def build_url(self, method, args, need_auth):
        args_string = ''

        for key in args.keys():
            args_string += '{}={}&'.format(key, args.get(key))

        args_string = args_string[:-1]

        url = 'https://api.vk.com/method/{}?{}&'

        if need_auth:
            url += 'access_token={}&'.format(self.access_token)

        url += 'v=5.64'

        return url.format(method, args_string)

    @staticmethod
    def do_request(method, url, data=''):
        if method == 'post':
            response = requests.post(url, data)
        else:
            response = requests.get(url).text

        return response

    def link_to_name(self, link):
        cache_db = SQLUtil('name_cache.db', 'cache')
        user_id = link.split('id')[1]
        if cache_db.id_exists(user_id):
            return cache_db.get_name(user_id)

        if link.find('-') < 0:
            profile_page_response = requests.get(link).text
            profile_name = BeautifulSoup(profile_page_response, 'html.parser').find_all('h2')
            peer_name = profile_name[0].text
        else:
            group_id = link.split('/')[3][3:]
            print group_id
            args = {'group_id': group_id}
            response_raw = self.do_request('get', self.build_url('groups.getById', args, False))
            response_json = json.loads(response_raw)
            peer_name = response_json['response'][0]['name']

        print peer_name
        cache_db.save_id_to_cache(user_id, peer_name)

        return peer_name.encode('utf-8')

    def get_dialogs_offset(self, count):
        args = {'preview_length': 30}

        iterations = int(count) // 200 + 1
        dialogs_all = []

        for iteration in range(iterations):
            offset = 200 * iteration
            curr_count = 200 if iteration < iterations - 1 else int(count) - 200 * iteration
            args['count'] = curr_count
            args['offset'] = offset
            dialogs_json = self.do_request('get', self.build_url('messages.getDialogs', args, True))
            parsed = json.loads(dialogs_json)
            try:
                dialogs_raw = parsed['response']['items']
            except KeyError:
                dialogs_raw = json.loads('[]')
            dialogs_all.extend(dialogs_raw)

        return dialogs_all

    def get_dialogs(self, count, user_id):
        dialogs_raw = self.get_dialogs_offset(count)

        dialogs = []

        cache_db = SQLUtil('name_cache.db', 'cache')

        for dialog in dialogs_raw:
            dialog = apiobjects.get_message_from_json(dialog['message'], True, False)
            if dialog.get_sender_url().find(user_id) > 0:
                dialog.set_sender_name('Вами')
            else:
                dialog.set_sender_name(cache_db.get_name(dialog.get_sender_url().split('id')[1]))

            dialogs.append(dialog)

        return dialogs

    def get_dialog_messages_offset(self, user_id, peer_id, count):
        args = {'user_id': user_id, 'peer_id': peer_id, 'count': 10}

        iterations = int(count) // 200 + 1
        messages_all = []

        for iteration in range(iterations):
            offset = 200 * iteration
            curr_count = 200 if iteration < iterations - 1 else int(count) - 200 * iteration
            args['count'] = curr_count
            args['offset'] = offset
            messages_json = self.do_request('get', self.build_url('messages.getHistory', args, True))
            parsed = json.loads(messages_json)
            messages_raw = parsed['response']['items']
            messages_all.extend(messages_raw)
            sleep(1500)

        return messages_all

    def get_dialog_messages(self, user_id, peer_id, count):

        messages_raw = self.get_dialog_messages_offset(user_id, peer_id, count)
        messages = []

        cache_db = SQLUtil('name_cache.db', 'cache')

        for message in messages_raw:
            message = apiobjects.get_message_from_json(message, False, False)
            if message.get_sender_url().find(str(user_id)) > 0:
                message.set_sender_name('Вас')
            else:
                message.set_sender_name(cache_db.get_name(message.get_sender_url().split('id')[1]))

            if len(message.forwarded_messages) > 0:
                for fwd_msg in message.forwarded_messages:
                    if fwd_msg.get_sender_url().find(str(user_id)) > 0:
                        fwd_msg.set_sender_name('Вас')
                    else:
                        fwd_msg.set_sender_name(cache_db.get_name(fwd_msg.get_sender_url().split('id')[1]))

            messages.append(message)

        return messages

    def send_message(self, peer_id, peer_type, text):
        args = {'message': text}

        if peer_type == 'user':
            args['user_id'] = peer_id
        elif peer_type == 'chat':
            args['chat_id'] = peer_id.split('0')[-1]

        url = self.build_url('messages.send', args, True)
        self.do_request('get', url)

    def reply_to_message(self, peer_id, peer_type, message_id, text):
        args = {'message': text, 'forward_messages': message_id}

        if peer_type == 'user':
            args['user_id'] = peer_id
        elif peer_type == 'chat':
            args['chat_id'] = peer_id

        url = self.build_url('messages.send', args, True)
        self.do_request('get', url)
