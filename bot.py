# -*- coding: utf-8 -*-

import re
from os import system

import telebot
from telebot import types

import config
import cryptoutil
import sqliteutil
import vkapi

bot = telebot.TeleBot(config.bot_token)

# ---- exchange
waiting_for_reply_text = False
waiting_for_send_text = False
waiting_for_key = False

reply_send_message_id = ''
reply_send_peer_type = ''
reply_send_peer_id = ''

exchange_key = ''
current_call = None


# ----

def validate_count(count, message):
    try:
        int(count)
        if '-' in count:
            bot.send_message(message.chat.id, 'Количество должно быть положительным!')
            return False

    except ValueError:
        bot.send_message(message.chat.id, 'Количество должно быть числом!')
        return False

    return True


def validate_key(key, encrypted_token, chat_id):
    if len(key) is not 16:
        bot.send_message(chat_id, 'Неверный ключ! Если Ты его забыл(а), то пройди процедуру аутентификации повторно -> /auth')
        return False

    cipher = cryptoutil.get_cipher(key)
    try:
        cryptoutil.decode_aes(cipher, encrypted_token).encode('utf-8')
    except UnicodeDecodeError:
        bot.send_message(chat_id, 'Неверный ключ! Если Ты его забыл(а), то пройди процедуру аутентификации повторно -> /auth')
        return False

    return True


def send_messages(chat_id, vk_api, user_id, peer_id, count):
    bot.send_message(chat_id, 'Получаю сообщения...')
    response = vk_api.get_dialog_messages(user_id, peer_id, count)
    if len(response) is 0:
        bot.send_message(chat_id, 'Сообщений нет!')
        return
    for vk_message in reversed(response):
        keyboard = types.InlineKeyboardMarkup()

        callback_data = 'reply_{}_{}_{}'.format(str(vk_message.get_id()), vk_message.get_peer_type(), str(vk_message.get_peer_id()))
        reply_button = types.InlineKeyboardButton(text='Ответить', callback_data=callback_data)

        has_name = len(vk_message.get_sender_name()) is 0
        if has_name:
            view_name_callback = 'link_{}_{}_{}_{}_{}'.format(str(vk_message.get_sender_url()), str(vk_message.get_peer_id()),
                                                              vk_message.get_peer_type(),
                                                              str(vk_message.get_id()), 'm')
            view_name_button = types.InlineKeyboardButton(text='Показать имя', callback_data=view_name_callback)
            keyboard.add(view_name_button, reply_button)
        else:
            keyboard.add(reply_button)

        bot.send_message(chat_id, str(vk_message), has_name, reply_markup=keyboard, parse_mode='Markdown')


def notify_all_users():
    db = sqliteutil.SQLUtil('vk_data.db', 'data')

    for user in db.select_all():
        try:
            bot.send_message(user[1],
                             'Update Text',
                             parse_mode='Markdown')
        except telebot.apihelper.ApiException:
            pass


@bot.message_handler(commands=['start'])
def handle_start(message):
    system('echo \'\' > reports_{}.txt'.format(message.chat.id))

    database = sqliteutil.SQLUtil('vk_data.db', 'data')
    if not database.has_user(message.chat.id):
        username = message.from_user.username
        if username is not None:
            username = username.encode('utf-8')
        else:
            username = ''
        name = message.from_user.first_name
        last_name = message.from_user.last_name
        database.add_user(message.chat.id, '', '', '@' + username if len(username) > 0 else '{} {}'.format(name, last_name))

    bot.send_message(message.chat.id,
                     'Привет! Я - бот, который поможет Тебе чатиться ВК не выходя из Телеграмма! Ты сможешь остаться в режиме невидимки, '
                     'используя меня. Для использования инструментов ВК мне нужно, чтобы Ты авторизовал(а) приложение ВК. Для этого нажми сюда -> '
                     '/auth')


@bot.message_handler(commands=['auth'])
def auth_user_in_vk(message):
    parts = message.text.split(' ')
    if len(parts) is 2:
        regex = r'https://oauth\.vk\.com/blank\.html\#access_token=([a-z0-9]{85})&expires_in=0&user_id=(\d{0,11})'
        result = re.search(regex, parts[1])

        if not result:
            bot.send_message(message.chat.id, 'Неправильная ссылка, удостоверься, что все сделано правильно.')
            return

        token = result.groups()[0].encode('utf-8')
        user_id = result.groups()[1].encode('utf-8')

        # noinspection PyShadowingNames
        secret = cryptoutil.generate_secret()
        global exchange_key
        exchange_key = secret
        cipher = cryptoutil.get_cipher(secret)
        bot.send_message(message.chat.id, secret)
        bot.send_message(message.chat.id,
                         'Это Твой ключ, которым зашифрованы данные, отправленные только что. Обязательно сохрани его, он необходим для выполнения '
                         'действий с ботом. Для подробностей о шифровании отправь мне команду /privacy')

        database = sqliteutil.SQLUtil('vk_data.db', 'data')
        database.edit_user(message.chat.id, user_id, cryptoutil.encode_aes(cipher, token))

        bot.send_message(message.chat.id, 'Спасибо! Теперь Ты можешь пользоваться всеми функциями бота! Нажми /help для списка всех команд.')
    else:
        bot.send_message(message.chat.id,
                         '*Внимание!* Так как Вконтакте не представляет удобной работы с API для приложений вроде этого, Тебе придется скопировать '
                         'ссылку в адресной строке браузера после авторизации и отправить ее мне вот так:\n\t /auth ссылка\n Без этого бот работать '
                         'не будет. ВКонтакте предупредит тебя, что это делать нежелательно, но другого способа нет.\n\nПожалуйста, перейди по этой '
                         'ссылке и нажми "Разрешить":\n https://oauth.vk.com/authorize?client\_id={0}&display=page&redirect\_uri=https://oauth'
                         '.vk.com&scope=offline,messages&response\_type=token&v=5.63'.format(config.client_id),
                         parse_mode='Markdown')


@bot.message_handler(commands=['privacy'])
def show_privacy_info(message):
    bot.send_message(message.chat.id, 'Итак, ты хотел(а) узнать побольше о шифровании в этом боте. Приступим!')
    bot.send_message(message.chat.id,
                     'Прежде всего, Ты хочешь, чтобы Твой аккаунт остался в безопасности. Я это понимаю. Именно поэтому возникает необходимость '
                     'шифровать данные Твоего аккаунта и давать только Тебе известный ключ для их расшифровки. С шифрованием об аккаунте можно не '
                     'беспокоиться, даже учитывая тот факт, что этот бот может получить только сообщения. Для достижения секретности используется '
                     'алгоритм AES (Advanced Encryption Standard), считающийся одним из самых лучших. Если не хочешь вдаваться в подробности, '
                     'то можешь не читать это сообщение дальше, а если все таки хочется узнать больше про AES, то вот тебе ссылка: '
                     'https://goo.gl/UqIcLg \nА теперь немного подробностей.\nВ качестве ключа используется 16-тизначная случайно сгенерированная '
                     'строка, состоящая из строчных и прописных букв английского алфавита, а так же цифр. Сразу же после отправки ссылки, '
                     'полученный токен шифруется и записывается в базу, а ключ пропадает в чертогах Твоего разума или на листочке. В дальнейшем при '
                     'каждом Твоем запросе нужно указать ключ для использования токена в запросе к API ВКонтакте. Вот и все. Надеюсь теперь Ты '
                     'будешь спать спокойнее.')


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id,
                     'Привет! Это бот для обмена сообщениями ВК через Телеграм!\n\nЧтобы получить список диалогов, введи \n    /dialogs n key\nгде '
                     'n - количество диалогов, key - ключ, полученный при аутентификации\n\nЧтобы получить сообщения из конкретного '
                     'диалога, введи\n    /last n from id key\nгде n - количество сообщений, id - идентификатор диалога, key - ключ, полученный при '
                     'аутентификации\n\nЧтобы отправить сообщение об ошибке или отзыв, введи\n    /report текст текст лалала\n\nЧтобы прочитать о '
                     'шифровании твоих данных, отправь /privacy\n\nТак же Ты можешь поддержать проект, введя /donate')


@bot.message_handler(commands=['report'])
def report_bug(message):
    parts = message.text.split(' ')

    if len(parts) is 1:
        bot.send_message(message.chat.id, 'Пожалуйста, отправь текст вместе с этой командой.')
    else:
        with open('reports_{}.txt'.format(message.chat.id), 'a') as reports_file:
            reports_file.write(message.text[7:].encode('utf-8') + '\n')
        bot.send_message(message.chat.id, 'Спасибо, отчет отправлен!')


@bot.message_handler(commands=['dialogs'])
def send_dialogs(message):
    database = sqliteutil.SQLUtil('vk_data.db', 'data')
    vk_data = database.select_single(message.chat.id)
    access_token_encrypted = vk_data[2].encode('utf-8')

    if len(access_token_encrypted) > 0:
        parts = message.text.split(' ')

        if len(parts) is not 3:
            bot.send_message(message.chat.id, 'Неправильный формат запроса. Смотри /help для инструкций.')
            return

        count = parts[1]
        key = parts[2]

        if not validate_key(key, access_token_encrypted, message.chat.id):
            return

        global exchange_key
        exchange_key = key

        if not validate_count(count, message):
            return

        cipher = cryptoutil.get_cipher(key)
        access_token = cryptoutil.decode_aes(cipher, access_token_encrypted)
        vk_api = vkapi.VkApiClient(access_token)

        bot.send_message(message.chat.id, 'Получаю диалоги...')
        response = vk_api.get_dialogs(count, str(vk_data[1]))

        for dialog in response:
            keyboard = types.InlineKeyboardMarkup()

            view_messages_callback = 'peer_{}'.format(str(dialog.peer_id))
            view_messages_button = types.InlineKeyboardButton(text='Просмотреть сообщения', callback_data=view_messages_callback)

            send_message_callback = 'send_{}_{}'.format(dialog.get_peer_type(), str(dialog.get_peer_id()))
            send_button = types.InlineKeyboardButton(text='Написать сообщение', callback_data=send_message_callback)

            has_name = len(dialog.get_sender_name()) is 0  # or not dialog.get_sender_url().endswith(str(vk_data[2]))
            if has_name:
                view_name_callback = 'link_{}_{}_{}_{}'.format(str(dialog.get_sender_url()), str(dialog.get_peer_id()), dialog.get_peer_type(), 'd')
                view_name_button = types.InlineKeyboardButton(text='Показать имя', callback_data=view_name_callback)

                keyboard.add(view_messages_button, view_name_button)
                keyboard.add(send_button)
            else:
                keyboard.add(view_messages_button, send_button)

            bot.send_message(message.chat.id, str(dialog), has_name, reply_markup=keyboard, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "Ты еще не авторизирован(а). Нажми /auth, чтобы это сделать.")


@bot.message_handler(commands=['last'])
def send_last_messages(message):
    database = sqliteutil.SQLUtil('vk_data.db', 'data')
    vk_data = database.select_single(message.chat.id)
    access_token_encrypted = vk_data[2].encode('utf-8')

    if len(access_token_encrypted) > 0:
        parts = message.text.split(' ')

        if len(parts) is not 5:
            bot.send_message(message.chat.id, 'Неправильный формат запроса. Смотри /help для инструкций.')
            return

        key = parts[4]

        if not validate_key(key, access_token_encrypted, message.chat.id):
            return

        global exchange_key
        exchange_key = key

        count = parts[1]
        if not validate_count(count, message):
            return

        cipher = cryptoutil.get_cipher(key)
        access_token = cryptoutil.decode_aes(cipher, access_token_encrypted)
        vk_api = vkapi.VkApiClient(access_token)
        peer_id = parts[3]

        try:
            int(parts[3])
        except ValueError:
            bot.send_message(message.chat.id, 'ID диалога должен быть числом!')
            return

        send_messages(message.chat.id, vk_api, vk_data[1], peer_id, count)
    else:
        bot.send_message(message.chat.id, "Ты еще не авторизирован(а). Нажми /auth, чтобы это сделать.")


@bot.callback_query_handler(func=lambda call: True)
def inline_callback(call):
    action = call.data.split('_')[0]

    global waiting_for_key, current_call
    if action != 'link':
        bot.send_message(call.message.chat.id, 'Отправь мне ключ, полученный после аутентификации. Для отмены нажми /cancel_key')
        waiting_for_key = True
        current_call = call
    else:
        current_call = call
        process_current_call()
    return


@bot.message_handler(commands=['cancel_reply', 'cancel_send', 'cancel_key'])
def cancel_action(message):
    global waiting_for_reply_text, waiting_for_send_text, waiting_for_key
    if waiting_for_reply_text:
        waiting_for_reply_text = False
        bot.send_message(message.chat.id, 'Отправка ответа успешно отменена!')
    elif waiting_for_send_text:
        waiting_for_send_text = False
        bot.send_message(message.chat.id, 'Отправка сообщения успешно отменена!')
    elif waiting_for_key:
        waiting_for_key = False
        bot.send_message(message.chat.id, 'Операция успешно отменена!')
    else:
        bot.send_message(message.chat.id, 'Нечего отменять!')


# noinspection PyUnboundLocalVariable
@bot.message_handler(content_types=['text'])
def handle_reply_to_vk_message(message):
    global waiting_for_reply_text, waiting_for_send_text, waiting_for_key

    if waiting_for_reply_text or waiting_for_send_text:
        database = sqliteutil.SQLUtil('vk_data.db', 'data')
        vk_data = database.select_single(message.chat.id)
        access_token_encrypted = vk_data[2]
        cipher = cryptoutil.get_cipher(exchange_key)
        access_token = cryptoutil.decode_aes(cipher, access_token_encrypted)
        vk_api = vkapi.VkApiClient(access_token)

    if waiting_for_reply_text:
        vk_api.reply_to_message(reply_send_peer_id, reply_send_peer_type, reply_send_message_id, message.text.encode('utf-8'))

        waiting_for_reply_text = False
        bot.send_message(message.chat.id, 'Ответ на сообщение отправлен!')
    elif waiting_for_send_text:
        vk_api.send_message(reply_send_peer_id, reply_send_peer_type, message.text.encode('utf-8'))

        waiting_for_send_text = False
        bot.send_message(message.chat.id, 'Сообщение отправлено!')
    elif waiting_for_key:
        database = sqliteutil.SQLUtil('vk_data.db', 'data')
        vk_data = database.select_single(message.chat.id)
        access_token_encrypted = vk_data[2]

        if not validate_key(message.text, access_token_encrypted, message.chat.id):
            return

        global exchange_key
        exchange_key = message.text

        waiting_for_key = False
        process_current_call()


def process_current_call():
    call = current_call
    parts = call.data.split('_')
    call_action = parts[0]
    if call_action == 'peer':
        peer_id = parts[1]

        database = sqliteutil.SQLUtil('vk_data.db', 'data')
        vk_data = database.select_single(call.message.chat.id)
        access_token_encrypted = vk_data[2].encode('utf-8')

        global exchange_key

        cipher = cryptoutil.get_cipher(exchange_key)
        access_token = cryptoutil.decode_aes(cipher, access_token_encrypted)

        vk_api = vkapi.VkApiClient(access_token)

        send_messages(call.message.chat.id, vk_api, vk_data[1], peer_id, 15)
    elif call_action == 'link':
        link = parts[1].encode('utf-8')

        vk_api = vkapi.VkApiClient('')
        name = vk_api.link_to_name(link)

        prev_text = call.message.text.encode('utf-8')

        if len(parts) in [5, 6]:
            keyboard = types.InlineKeyboardMarkup()

            if parts[4] == 'd':
                view_messages_callback = 'peer_' + parts[2]
                view_messages_button = types.InlineKeyboardButton(text='Просмотреть сообщения', callback_data=view_messages_callback)

                send_message_callback = 'send_{}_{}'.format(parts[3], parts[2])
                send_button = types.InlineKeyboardButton(text='Написать сообщение', callback_data=send_message_callback)

                keyboard.add(view_messages_button, send_button)
            elif parts[5] == 'm':
                callback_data = 'reply_{}_{}_{}'.format(parts[4], parts[3], parts[2])
                reply_button = types.InlineKeyboardButton(text='Ответить', callback_data=callback_data)

                keyboard.add(reply_button)

            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=prev_text.replace(link, name),
                                  reply_markup=keyboard)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=prev_text.replace(link, name))
    elif call_action == 'reply':
        global reply_send_message_id, reply_send_peer_type, reply_send_peer_id, waiting_for_reply_text
        reply_send_message_id = parts[1]
        reply_send_peer_type = parts[2]
        reply_send_peer_id = parts[3]

        bot.send_message(chat_id=call.message.chat.id, text='Теперь отправь мне текст ответа. Для отмены отправь /cancel_reply')
        waiting_for_reply_text = True
    elif call_action == 'send':
        global reply_send_peer_type, reply_send_peer_id, waiting_for_send_text
        reply_send_peer_type = parts[1]
        reply_send_peer_id = parts[2]

        bot.send_message(chat_id=call.message.chat.id, text='Теперь отправь мне текст сообщения. Для отмены отправь /cancel_send')
        waiting_for_send_text = True


if __name__ == '__main__':
    bot.polling(none_stop=True)
