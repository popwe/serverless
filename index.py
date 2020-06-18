import argparse
import inspect
import logging
import os
from importlib import import_module

from clients.base import BaseClient

DEFAULT_FORMATTER = '%(asctime)s[%(filename)s:%(lineno)d][%(levelname)s]:%(message)s'
logging.basicConfig(format=DEFAULT_FORMATTER, level=logging.INFO)


def script_main(params):
    client = params.get('client')
    m = import_module('.'.join(['clients', client]))
    if not m:
        logging.info('No client %s was found' % client)
        return

    try:
        for name, obj in inspect.getmembers(m):
            if inspect.isclass(obj) and issubclass(obj, BaseClient) and name != 'BaseClient':
                instance = obj()
                instance.config = params
                instance.before_run()
                instance.run()
                break
    except Exception as e:
        logging.exception(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('client', nargs='?', default='one_drive')
    parser.add_argument('a', nargs='?')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    params = vars(args)
    if params.get('client') is None:
        print('Please select a client.')
        return
    print(os.environ)

    return script_main(params)


if __name__ == '__main__':
    main()
