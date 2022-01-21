import functools
import logging
import os.path
import socket
import time
import urllib.request
from multiprocessing.pool import ThreadPool

import requests

from doublenegative.encryption import decrypt_stream, calculate_blowfish_key
from doublenegative.helpers import timed
from doublenegative.models import DownloadResult, APIs




class DistributedDownloader:
    def __init__(self, deezer_api, doublenegative_api, workers, sleep_interval):
        self.__apis = APIs(deezer_api, doublenegative_api)
        self.__workers = workers
        self.__sleep_interval = sleep_interval

    @timed
    def download(self, track_list, destination):
        results = list()
        with ThreadPool(self.__workers) as p:
            logging.info(f'starting {self.__workers}-worker pool to download track list to {destination}')
            for result in p.imap_unordered(functools.partial(
                    _threaded_download,
                    destination=destination,
                    apis=self.__apis,
                    sleep_duration=self.__sleep_interval),
                    track_list):
                results.append(result)
        return results


def get_track_id(track, apis):
    response = requests.get(
        f'{apis.deezer}/search',
        params={'q': track.search_query},
    )
    response.raise_for_status()

    results = response.json()
    # todo: assume the first song is correct for now, but do some string comparison in the future
    return results['data'][0]['id']


def get_song(track_id, apis):
    response = requests.get(
        f'{apis.doublenegative}/deezer/track/{track_id}',
        params={'quality': 'FLAC'},
    )
    response.raise_for_status()

    return response.json()[0]


@timed
def _threaded_download(track, destination, apis, sleep_duration):
    try:
        outcome = False

        if not os.path.exists(destination):
            os.makedirs(destination)

        track_id = get_track_id(track, apis)
        song = get_song(track_id, apis)

        url = song['STREAM']['sources'][0]['url']
        song_stream = urllib.request.urlopen(url, timeout=10)
        key = calculate_blowfish_key(track_id)

        flac_path = os.path.join(destination, track.genre, f'{track.name}.flac')

        if not os.path.exists(os.path.dirname(flac_path)):
            os.makedirs(os.path.dirname(flac_path))

        with open(flac_path, 'wb') as f:
            decrypt_stream(song_stream, key, f)

        outcome = True
    except socket.timeout:
        logging.error(f'timed out while trying to open url "{url}" for "{track.name}"')
    except IndexError:
        logging.error(f'could not find the song "{track.name}" while searching for "{track.search_query}"')
    except Exception:
        logging.exception(f'failed to download "{track.name}" because:')
    finally:
        time.sleep(sleep_duration)

    return DownloadResult(track, outcome)


