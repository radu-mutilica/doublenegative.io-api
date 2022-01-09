import os
import shutil

import yaml
import pytest
import doublenegative
from random import choice
from pathlib import Path
from string import ascii_uppercase

TEST_CONFIG_PATH = Path.cwd() / 'data' / 'test_config.yaml'
NUM_GENRES = 3
NUM_MP3S = 5


def random_str(length=5):
    return ''.join(choice(ascii_uppercase) for i in range(length))


@pytest.fixture(scope='function')
def app():
    """Simple fixture which yields an app runner function for testing"""
    yield doublenegative.app(config_path=TEST_CONFIG_PATH)


@pytest.fixture(scope='class')
def fake_mp3s():
    """Generate a bunch of random genre directories and fill them with some fake mp3 files"""
    with open(TEST_CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)

    fake_mp3s = list()
    genre_paths = list()

    for i in range(NUM_GENRES):
        genre_path = os.path.join(config['path']['mp3_library'], random_str())

        os.makedirs(genre_path)
        genre_paths.append(genre_path)

        for j in range(NUM_MP3S):
            mp3_name = '{} - {}'.format(random_str(), random_str())
            mp3_path = os.path.join(genre_path, '.'.join((mp3_name, 'mp3')))

            with open(mp3_path, 'w') as f:
                f.write(random_str())

            fake_mp3s.append(mp3_path)

    yield fake_mp3s

    for genre_path in genre_paths:
        shutil.rmtree(genre_path)
