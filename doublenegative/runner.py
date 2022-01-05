import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def all_files_in(path, regex):
    for path in Path(path).rglob(regex):
        yield path


class RunStats:
    def __init__(self):
        self.mp3s_found = 0


class Doublenegative:
    def __init__(self, config):
        self.config = dict(config)
        self.mp3s = list()
        self.stats = RunStats()

    def run(self):
        for mp3_file in all_files_in(
                self.config['path']['mp3_library'],
                self.config['path']['mp3_regex']):
            self.mp3s.append(mp3_file)
            logger.debug(f'found {mp3_file.name}')

        self.stats.mp3s_found = len(self.mp3s)
        logger.info(f'found a total of {self.stats.mp3s_found} files')

        return True


def app(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return Doublenegative(config)
