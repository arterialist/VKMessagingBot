from Crypto.Cipher import AES
import base64
from random import randint

# the block size for the cipher object; must be 16 per FIPS-197
BLOCK_SIZE = 16

# the character used for padding--with a block cipher such as AES, the value
# you encrypt must be a multiple of BLOCK_SIZE in length.  This character is
# used to ensure that your value is always a multiple of BLOCK_SIZE
PADDING = '{'


def get_cipher(secret):
    return AES.new(secret)


# to sufficiently pad the text to be encrypted
def pad(string):
    s = string + (BLOCK_SIZE - len(string) % BLOCK_SIZE) * PADDING
    return s


def encode_aes(cipher, message):
    return base64.b64encode(cipher.encrypt(pad(message)))


def decode_aes(cipher, string):
    return cipher.decrypt(base64.b64decode(string)).rstrip(PADDING)


def generate_secret():
    charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

    secret = ''

    for index in range(16):
        secret += charset[randint(0, len(charset)-1)]

    return secret
