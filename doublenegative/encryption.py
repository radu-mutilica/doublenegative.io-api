from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import Blowfish
from Crypto.Hash import MD5


def md5hex(data):
    """Generate MD5 of a given string"""
    h = MD5.new()
    h.update(str(data).encode('utf-8'))
    return b2a_hex(h.digest())


def decrypt_stream(song_stream, key, f):
    """Decrypt data from the song stream, and write if to the file."""
    block_size = 0x800  # 2048 bytes
    i = 0

    while True:
        data = song_stream.read(block_size)
        if not data:
            break

        # Only every third 2048 byte block is encrypted
        is_encrypted = ((i % 3) == 0)
        is_full_block = len(data) == block_size

        if is_encrypted and is_full_block:
            data = blowfish_decrypt(data, key)

        f.write(data)
        i += 1


def blowfish_decrypt(data, key):
    """CBC decrypt data with key"""
    c = Blowfish.new(
        key.encode('utf-8'),
        Blowfish.MODE_CBC,
        a2b_hex("0001020304050607")
    )
    return c.decrypt(data)


def calculate_blowfish_key(song_id):
    """Calculate the Blowfish decrypt key for a given song_id """
    h = md5hex(song_id).decode("utf-8")
    key = "g4el58wc0zvf9na1"  # Not sure why this is what it is

    return "".join(
        chr(
            ord(h[i]) ^
            ord(h[i + 16]) ^
            ord(key[i])
        ) for i in range(16)
    )
