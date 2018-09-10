# -*- coding: utf-8 -*-

import json


def get_message_from_json(message_json, as_dialog, forwarded):
    msg_id = ''
    if not forwarded:
        msg_id = message_json['id']
    sender_url = "https://vk.com/id{}".format(str(message_json['user_id' if as_dialog or forwarded else 'from_id']))
    body = message_json['body'].encode('utf-8')

    attachments_raw = json.loads('[]')

    try:
        attachments_raw = message_json['attachments']
    except KeyError:
        pass

    if as_dialog:
        return Dialog(msg_id, sender_url, body, attachments_raw, message_json)
    else:
        return Message(msg_id, sender_url, body, attachments_raw, message_json, forwarded)


class Attachment:
    def __init__(self, a_type, url):
        self.a_type = a_type
        self.url = url

    def get_type(self):
        return self.a_type

    def get_url(self):
        return self.url


class Message:
    @staticmethod
    def get_attachment_url(attachment):
        url = ''
        attachment_type = attachment['type'].encode('utf-8')
        attachment_content = attachment[attachment_type]
        if attachment_type == 'video':
            url = 'https://vk.com/video{}_{}'.format(attachment_content['owner_id'], attachment_content['id'])
        elif attachment_type == 'photo':
            sizes = ['75', '130', '604', '807', '1280', '2560']
            for size in sizes:
                try:
                    url = attachment['photo']['photo_{}'.format(size).encode('utf-8')]
                except KeyError:
                    pass
        elif attachment_type == 'audio':
            url = attachment_content['url'].split('?')[0]
        elif attachment_type == 'doc':
            type_num = int(attachment_content['type'])

            if type_num is 4:
                url = attachment_content['preview']['photo']['sizes'][-1]['src']
            else:
                url = attachment_content['url'].split('?')[0]
                if type_num == 5:
                    try:
                        url = attachment_content['preview']['audio_msg']['link_ogg']
                    except KeyError:
                        url = attachment_content['url'].split('?')[0]
        elif attachment_type == 'sticker':
            url = attachment_content['photo_512']
        elif attachment_type == 'gift':
            url = attachment_content['thumb_256']

        return url

    @staticmethod
    def parse_peer_id(message_json):
        try:
            chat_id = message_json['chat_id']
            peer_id = '20000000{}'.format(chat_id)
        except KeyError:
            try:
                peer_id = message_json['from_id']
            except KeyError:
                peer_id = message_json['user_id']
        return peer_id

    def parse_attachments(self, attachments_json):
        attachments = []
        for item in attachments_json:
            attachments.append(Attachment(item['type'], self.get_attachment_url(item)))

        return attachments

    @staticmethod
    def parse_forwarded_messages(message_json):
        forwarded_messages = []

        try:
            fwd_messages_json = message_json['fwd_messages']
            for message in fwd_messages_json:
                forwarded_messages.append(get_message_from_json(message, False, True))

            return forwarded_messages
        except KeyError:
            return forwarded_messages

    def __init__(self, msg_id, sender_url, body, attachments_json, message_json, forwarded):
        self.message_id = msg_id
        self.sender_url = sender_url
        self.sender_name = ''
        self.body = body
        self.forwarded = forwarded
        self.peer_id = self.parse_peer_id(message_json)
        self.forwarded_messages = self.parse_forwarded_messages(message_json)
        self.attachments = self.parse_attachments(attachments_json)
        self.peer_type = 'chat' if str(self.peer_id).startswith('20000000') else 'user'

    def __str__(self):
        representation = 'Сообщение от *{}*\n  {}\n'.format(
            self.sender_url if not len(self.sender_name) else self.sender_name,
            self.body.replace('*', '\*').replace('_', '\_').replace('`', '\`'))

        forwarded_count = len(self.forwarded_messages)

        if forwarded_count:
            representation += 'Пересланн{} сообщени{}:\n'.format('ые' if forwarded_count > 1 else 'ое', 'я' if forwarded_count > 1 else 'е')

            for message in self.forwarded_messages:
                representation += str(message)

        attachments_count = len(self.attachments)
        if attachments_count:
            representation += '{} вложени{}:\n'.format(
                attachments_count, 'е' if attachments_count is 1 else 'я' if attachments_count in range(2, 5) else 'й')
            for attachment in self.attachments:
                representation += '{}: {}\n'.format(attachment.get_type(), attachment.get_url())

        return representation.decode('utf-8', 'ignore').encode('utf-8')

    def get_attachments(self):
        return self.attachments

    def get_sender_url(self):
        return self.sender_url

    def get_body(self):
        return self.body

    def get_id(self):
        return self.message_id

    def get_peer_id(self):
        return self.peer_id

    def get_peer_type(self):
        return self.peer_type

    def get_sender_name(self):
        return self.sender_name

    def set_sender_name(self, name):
        self.sender_name = name


# noinspection PyMethodMayBeStatic
class Dialog(Message):
    def __init__(self, msg_id, sender_url, body, attachments_json, message_json):
        Message.__init__(self, msg_id, sender_url, body, attachments_json, message_json, True)
        self.forwarded_messages = self.parse_forwarded_messages(message_json)

    def __str__(self):
        representation = 'ID диалога: `{}`\nДиалог с *{}*\nПоследнее сообщение:\n  {}\n'.format(self.peer_id, self.sender_url if not len(
            self.sender_name) else self.sender_name, self.body.replace('*', '\*').replace('_', '\_').replace('`', '\`'))

        forwarded_count = len(self.forwarded_messages)

        if forwarded_count:
            representation += 'Пересланн{} сообщени{}:'.format('ые' if forwarded_count > 1 else 'ое', 'я' if forwarded_count > 1 else 'е')
            for message in self.forwarded_messages:
                representation += '\n'
                representation += str(message)

            representation += '\n'

        attachments_count = len(self.attachments)
        if attachments_count:
            representation += '{} вложени{}:\n'.format(
                attachments_count, 'е' if attachments_count is 1 else 'я' if attachments_count in range(2, 5) else 'й')
            for attachment in self.attachments:
                representation += '{}: {}\n'.format(attachment.get_type(), attachment.get_url())

        return representation.decode('utf-8', 'ignore').encode('utf-8')
