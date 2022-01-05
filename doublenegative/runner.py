import configparser


class Doublenegative:
    def __init__(self, config):
        self.config = config

    def run(self):
        return True


def run_app(config_path):
    config = configparser.RawConfigParser()
    config.read(config_path)
    app = Doublenegative(config)
    return app.run()
