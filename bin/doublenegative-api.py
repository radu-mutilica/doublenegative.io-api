from doublenegative import app
import logging

logging.basicConfig(level=logging.INFO)

CONFIG_PATH = 'config.yaml'

if __name__ == '__main__':
    logging.info(f'starting up new run with config={CONFIG_PATH}')
    app(config_path=CONFIG_PATH).run()
