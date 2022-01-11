import functools
import logging
import math
import os.path
import time
import urllib.request
from multiprocessing.pool import ThreadPool
from pathlib import Path

import requests
import yaml

from doublenegative.encryption import decrypt_stream, calculate_blowfish_key

logging.basicConfig(level=logging.INFO)


def all_files_in(path, regex):
    for path in Path(path).rglob(regex):
        yield path


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
        self._pool = ThreadPool(workers)
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
            song_stream = urllib.request.urlopen(song['STREAM']['sources'][0]['url'])
            key = calculate_blowfish_key(track_id)

            flac_path = os.path.join(destination, f'{track.full_name}.flac')
            with open(flac_path, 'wb') as f:
                decrypt_stream(song_stream, key, f)

            elapsed = time.time() - start
        except IndexError:
            logging.error(f'could not find the song "{track.full_name}" while searching for it')
        except Exception:
            logging.exception(f'failed to download "{track.full_name}" because:')
        else:
            logging.info(f'downloaded "{track.full_name}" to "{flac_path}" in {elapsed:.2f}s')
        finally:
            time.sleep(1)

    def download(self, track_list, destination):
        with self._pool as p:
            logging.info(f'starting {self._pool._processes}-worker pool to download track list to {destination}')
            p.map_async(functools.partial(self._threaded_download, destination=destination), track_list)
            p.close()
            p.join()


class Doublenegative:
    def __init__(self, config):
        self.config = dict(config)
        self.mp3s = list()

    def run(self):
        for mp3_file in all_files_in(
                self.config['path']['mp3_library'],
                self.config['path']['mp3_regex']):
            self.mp3s.append(Track(mp3_file))
            logging.debug(f'found {mp3_file.name}')

        logging.info(f'found a total of {len(self.mp3s)} tracks')

        downloader = DistributedDownloader(self.config['api']['deezer'], self.config['api']['doublenegative'])
        downloader.download(track_list=self.mp3s[2:20], destination=self.config['path']['flac_library'])


def app(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return Doublenegative(config)
