import functools
import math
import struct

from Crypto.Hash import MD5
from Crypto.Cipher import AES, Blowfish
from binascii import a2b_hex, b2a_hex
import time
import os.path
import requests
from multiprocessing.pool import ThreadPool
import yaml
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)


def all_files_in(path, regex):
    for path in Path(path).rglob(regex):
        yield path


class RunStats:
    def __init__(self):
        self.mp3s_found = 0


class Track:
    def __init__(self, path):
        self.full_name = os.path.basename(path).replace('.mp3', '')
        self.artist, self.song = self.full_name.split(' - ')
        self.artist = self.artist.lower().split('feat.')[0]
        self.path = path
        self.abs_path = os.path.abspath(path)
        self.format = os.path.basename(os.path.dirname(path))


class DistributedDownloader:
    def __init__(self, deezer_api, doublenegative_api, workers=4):
        self.__pool = ThreadPool(4)
        self.deezer_api = deezer_api
        self.doublenegative_api = doublenegative_api

    def _get_track_id(self, track):
        response = requests.get(
            f'{self.deezer_api}/search',
            params={'q': f'{track.song} {track.artist}'},
        )
        response.raise_for_status()

        results = response.json()
        # todo: assume the first song is correct for now, but do some string comparison in the future
        return results['data'][0]['id']

    def _get_song(self, track_id):

        response = requests.get(
            f'{self.doublenegative_api}/deezer/track/{track_id}',
            params={'quality': 'FLAC'},
        )
        response.raise_for_status()

        return response.json()[0]

    def _threaded_download(self, track, destination):

        try:
            if not os.path.exists(destination):
                os.makedirs(destination)

            track_id = self._get_track_id(track)
            song = self._get_song(track_id)

            start = time.time()
            response = requests.get(url=song['STREAM']['sources'][0]['url'])

            flac_path = os.path.join(destination, f'{track.full_name}.flac')

            key = calcbfkey(int(track_id))

            with open(flac_path, 'wb') as f:
                writeid3v2(f, song)

                decryptfile(response.content, key, f)

                # writeid3v1_1(f, song)
        except Exception:
            logging.exception(f'failed to download {track.full_name} because:')
        else:
            logging.info(f'downloaded {track.full_name} to {destination} in {math.round(time.time() - start, 2)}s')
        finally:
            time.sleep(2)

    def download(self, track_list, destination):
        with self.__pool as p:
            logging.info(f'starting {self.__pool._processes}-worker pool to download track list to {destination}')
            p.map_async(functools.partial(self._threaded_download, destination=destination), track_list)
            p.close()
            p.join()

def writeid3v1_1(fo, song):
    # Bugfix changed song["SNG_TITLE... to song.get("SNG_TITLE... to avoid 'key-error' in case the key does not exist
    def song_get(song, key):
        try:
            return song.get(key).encode('utf-8')
        except Exception as e:
            return ""

    def album_get(key):
        global album_Data
        try:
            return album_Data.get(key).encode('utf-8')
        except Exception as e:
            return ""

    data = struct.pack("3s" "30s" "30s" "30s" "4s" "28sB" "B"  "B",
                       "TAG",  # header
                       song_get(song, "SNG_TITLE"),  # title
                       song_get(song, "ART_NAME"),  # artist
                       song_get(song, "ALB_TITLE"),  # album
                       album_get("PHYSICAL_RELEASE_DATE"),  # year
                       album_get("LABEL_NAME"), 0,  # comment

                       int(song_get(song, "TRACK_NUMBER") or 0),  # tracknum
                       255  # genre
                       )
    fo.write(data)

def decryptfile(fh, key, fo):
    """
    Decrypt data from file <fh>, and write to file <fo>.
    decrypt using blowfish with <key>.
    Only every third 2048 byte block is encrypted.
    """
    blockSize = 0x800  # 2048 byte
    i = 0

    while True:
        data = fh.read(blockSize)
        if not data:
            break

        isEncrypted = ((i % 3) == 0)
        isWholeBlock = len(data) == blockSize

        if isEncrypted and isWholeBlock:
            data = blowfishDecrypt(data, key)

        fo.write(data)
        i += 1

def blowfishDecrypt(data, key):
    """ CBC decrypt data with key """
    c = Blowfish.new(key,
                     Blowfish.MODE_CBC,
                     a2b_hex("0001020304050607")
                     )
    return c.decrypt(data)


def writeid3v2(fo, song):
    def make28bit(x):
        return (
                       (x << 3) & 0x7F000000) | (
                       (x << 2) & 0x7F0000) | (
                       (x << 1) & 0x7F00) | \
               (x & 0x7F)

    def maketag(tag, content):
        return struct.pack(">4sLH",
                           tag.encode("ascii"),
                           len(content),
                           0
                           ) + content

    def album_get(key):
        global album_Data
        try:
            return album_Data.get(key)  # .encode('utf-8')
        except Exception as e:
            return ""

    def song_get(song, key):
        try:
            return song[key]  # .encode('utf-8')
        except Exception as e:
            return ""

    def makeutf8(txt):
        return b"\x03" + txt.encode('utf-8')

    def makepic(data):
        # Picture type:
        # 0x00     Other
        # 0x01     32x32 pixels 'file icon' (PNG only)
        # 0x02     Other file icon
        # 0x03     Cover (front)
        # 0x04     Cover (back)
        # 0x05     Leaflet page
        # 0x06     Media (e.g. lable side of CD)
        # 0x07     Lead artist/lead performer/soloist
        # 0x08     Artist/performer
        # 0x09     Conductor
        # 0x0A     Band/Orchestra
        # 0x0B     Composer
        # 0x0C     Lyricist/text writer
        # 0x0D     Recording Location
        # 0x0E     During recording
        # 0x0F     During performance
        # 0x10     Movie/video screen capture
        # 0x11     A bright coloured fish
        # 0x12     Illustration
        # 0x13     Band/artist logotype
        # 0x14     Publisher/Studio logotype
        imgframe = ("\x00",  # text encoding
                    "image/jpeg", "\0",  # mime type
                    "\x03",  # picture type: 'Cover (front)'
                    ""[:64], "\0",  # description
                    data
                    )

        return b''.join(imgframe)

    # get Data as DDMM
    try:
        phyDate_YYYYMMDD = album_get("PHYSICAL_RELEASE_DATE").split('-')  # '2008-11-21'
        phyDate_DDMM = phyDate_YYYYMMDD[2] + phyDate_YYYYMMDD[1]
    except:
        phyDate_DDMM = ''

    # get size of first item in the list that is not 0
    try:
        FileSize = [
            song_get(song, i)
            for i in (
                'FILESIZE_AAC_64',
                'FILESIZE_MP3_320',
                'FILESIZE_MP3_256',
                'FILESIZE_MP3_64',
                'FILESIZE',
            ) if song_get(song, i)
        ][0]
    except:
        FileSize = 0

    try:
        track = "%02s" % song["TRACK_NUMBER"]
        track += "/%02s" % album_get("TRACKS")
    except:
        pass

    # http://id3.org/id3v2.3.0#Attached_picture
    id3 = [
        maketag("TRCK", makeutf8(track)),
        # The 'Track number/Position in set' frame is a numeric string containing the order number of the audio-file on its original recording. This may be extended with a "/" character and a numeric string containing the total numer of tracks/elements on the original recording. E.g. "4/9".
        maketag("TLEN", makeutf8(str(int(song["DURATION"]) * 1000))),
        # The 'Length' frame contains the length of the audiofile in milliseconds, represented as a numeric string.
        maketag("TORY", makeutf8(str(album_get("PHYSICAL_RELEASE_DATE")[:4]))),
        # The 'Original release year' frame is intended for the year when the original recording was released. if for example the music in the file should be a cover of a previously released song
        maketag("TYER", makeutf8(str(album_get("DIGITAL_RELEASE_DATE")[:4]))),
        # The 'Year' frame is a numeric string with a year of the recording. This frames is always four characters long (until the year 10000).
        maketag("TDAT", makeutf8(str(phyDate_DDMM))),
        # The 'Date' frame is a numeric string in the DDMM format containing the date for the recording. This field is always four characters long.
        maketag("TPUB", makeutf8(album_get("LABEL_NAME"))),
        # The 'Publisher' frame simply contains the name of the label or publisher.
        maketag("TSIZ", makeutf8(str(FileSize))),
        # The 'Size' frame contains the size of the audiofile in bytes, excluding the ID3v2 tag, represented as a numeric string.
        maketag("TFLT", makeutf8("MPG/3")),

    ]  # decimal, no term NUL
    id3.extend([
        maketag(ID_id3_frame, makeutf8(song_get(song, ID_song))) for (ID_id3_frame, ID_song) in \
        (
            ("TALB", "ALB_TITLE"),
            # The 'Album/Movie/Show title' frame is intended for the title of the recording(/source of sound) which the audio in the file is taken from.
            ("TPE1", "ART_NAME"),
            # The 'Lead artist(s)/Lead performer(s)/Soloist(s)/Performing group' is used for the main artist(s). They are seperated with the "/" character.
            ("TPE2", "ART_NAME"),
            # The 'Band/Orchestra/Accompaniment' frame is used for additional information about the performers in the recording.
            ("TPOS", "DISK_NUMBER"),
            # The 'Part of a set' frame is a numeric string that describes which part of a set the audio came from. This frame is used if the source described in the "TALB" frame is divided into several mediums, e.g. a double CD. The value may be extended with a "/" character and a numeric string containing the total number of parts in the set. E.g. "1/2".
            ("TIT2", "SNG_TITLE"),
            # The 'Title/Songname/Content description' frame is the actual name of the piece (e.g. "Adagio", "Hurricane Donna").
            ("TSRC", "ISRC"),
        # The 'ISRC' frame should contain the International Standard Recording Code (ISRC) (12 characters).
        )
    ])

    # try:
    # id3.append(
    # maketag( "APIC", makepic(
    # downloadpicture( song["ALB_PICTURE"] )
    # )
    # )
    # )
    # except Exception as e:
    # print "no pic", e

    id3data = b"".join(id3)
    # >	big-endian
    # s	char[]	bytes
    # H	unsigned short	integer	2
    # B	unsigned char	integer	1
    # L	unsigned long	integer	4

    hdr = struct.pack(">"
                      "3s" "H" "B" "L",
                      "ID3".encode("ascii"),
                      0x300,  # version
                      0x00,  # flags
                      make28bit(len(id3data)))

    fo.write(hdr)
    fo.write(id3data)



def md5hex(data):
    """ return hex string of md5 of the given string """
    h = MD5.new()
    h.update(data)
    return b2a_hex(h.digest())

def calcbfkey(songid):
    """ Calculate the Blowfish decrypt key for a given songid """
    h = md5hex("%d" % songid)
    key = "g4el58wc0zvf9na1"

    return "".join(
        chr(
            ord(h[i]) ^
            ord(h[i + 16]) ^
            ord(key[i])
        ) for i in range(16)
    )

class Doublenegative:
    def __init__(self, config):
        self.config = dict(config)
        self.mp3s = list()
        self.stats = RunStats()

    def run(self):
        for mp3_file in all_files_in(
                self.config['path']['mp3_library'],
                self.config['path']['mp3_regex']):
            self.mp3s.append(Track(mp3_file))
            logging.debug(f'found {mp3_file.name}')

        self.stats.mp3s_found = len(self.mp3s)
        logging.info(f'found a total of {self.stats.mp3s_found} tracks')

        downloader = DistributedDownloader(self.config['api']['deezer'], self.config['api']['doublenegative'])
        downloader.download(track_list=self.mp3s, destination=self.config['path']['flac_library'])


def app(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return Doublenegative(config)
