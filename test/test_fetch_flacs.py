import pytest


def test_sanity(app):
    assert app.run()


@pytest.mark.usefixtures('fake_mp3s')
class TestDiscovery:

    def test_find_mp3s(self, app, fake_mp3s):
        app.run()
        assert len(app.mp3s) == len(fake_mp3s)
