import pytest
import doublenegative
import functools

TEST_CONFIG_PATH = 'test/data/test_config.ini'


@pytest.fixture(scope='function')
def app():
    """Simple fixture which yields an app runner function for testing"""
    yield functools.partial(doublenegative.run_app, config_path=TEST_CONFIG_PATH)
