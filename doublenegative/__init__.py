import logging
import time
import yaml

from doublenegative.downloader import DistributedDownloader
from doublenegative.helpers import all_files_in
from doublenegative.models import Track


def app(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return Doublenegative(config)


class Doublenegative:
    def __init__(self, config):
        self.config = dict(config)
        self.mp3s = list()

    def run(self):
        for mp3_file in all_files_in(
                self.config['path']['mp3_library'],
                self.config['path']['mp3_regex']):

            try:
                track = Track(mp3_file)
                self.mp3s.append(track)
                logging.info(f'found {track.name} ({track.genre})')
            except ValueError:
                logging.error(f'could not parse track "{mp3_file}"')

        logging.info(f'found a total of {len(self.mp3s)} tracks')

        distributed_downloader = DistributedDownloader(
            deezer_api=self.config['api']['deezer'],
            doublenegative_api=self.config['api']['doublenegative'],
            workers=int(self.config['threading']['workers']),
            sleep_interval=int(self.config['threading']['sleep_interval'])
        )
        results = distributed_downloader.download(track_list=self.mp3s, destination=self.config['path']['flac_library'])
        self.report(results)

    def report(self, results):
        """Write a failure report to see what tracks we missed"""
        success = 0
        failure_report_path = self.config['path']['failure_report'].format(time.time_ns())
        for result in results:
            if result.outcome:
                success += 1
            else:
                with open(failure_report_path, 'a') as f:
                    f.write(
                        f'track_name="{result.track.name}",genre="{result.track.genre}";'
                        f'search_query="{result.track.search_query}"\n')

        logging.info(f'total downloaded {success}')
        logging.info(f'total failures {len(self.mp3s) - success}')
        logging.info(f'failures written to "{failure_report_path}"')
