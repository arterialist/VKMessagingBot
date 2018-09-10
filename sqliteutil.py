# coding=utf-8


import sqlite3

charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ '


class SQLUtil:
    def __init__(self, database, table):
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()
        self.table = table

    @staticmethod
    def text_to_num(text):
        num = ''
        for symbol in text:
            num += str(charset.find(symbol))
            num += '_'

        return num[:-1]

    @staticmethod
    def num_to_text(num):
        text = ''

        for symbol in num.split('_'):
            text += charset[int(symbol)]

        return text

    def add_user(self, tg_user_id, user_id, access_token, tg_username):
        with self.connection:
            self.cursor.execute('INSERT INTO {} VALUES {}'.format(self.table, (tg_user_id, user_id, access_token, tg_username)))

    def edit_user(self, tg_user_id, user_id, access_token):
        with self.connection:
            self.cursor.execute(
                "UPDATE {} SET user_id = '{}', access_token = '{}' WHERE tg_user_id = {}".format(self.table, user_id, access_token, tg_user_id))

    def select_all(self):
        with self.connection:
            return self.cursor.execute('SELECT * FROM {}'.format(self.table)).fetchall()

    def select_single(self, tg_user_id):
        with self.connection:
            return self.cursor.execute('SELECT * FROM {} WHERE tg_user_id = {}'.format(self.table, tg_user_id)).fetchall()[0]

    def has_user(self, tg_user_id):
        all_users = self.select_all()

        for user in all_users:
            if user[0] == tg_user_id:
                return True

        return False

    def save_id_to_cache(self, user_id, name):
        count = len(self.select_all())
        print user_id
        with self.connection:
            encoded = name.encode('utf-8')
            self.cursor.execute('INSERT INTO {} VALUES {}'.format(self.table, (count + 1, user_id, self.text_to_num(encoded))))

    def id_exists(self, user_id):
        with self.connection:
            res = self.cursor.execute('SELECT * FROM {} WHERE link = {}'.format(self.table, user_id)).fetchall()
            return len(res) is not 0

    def get_name(self, link):
        if self.id_exists(link):
            with self.connection:
                name = self.cursor.execute('SELECT name FROM {} WHERE link = {}'.format(self.table, link)).fetchall()[0][0].encode('utf-8')
            return self.num_to_text(name)
        else:
            return ''
