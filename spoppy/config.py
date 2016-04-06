import getpass
import os

from appdirs import user_cache_dir

try:
    # python2.7
    input = raw_input
except NameError:
    pass

CONFIG_FILE_NAME = os.path.join(
    user_cache_dir(appname='spoppy'), '.creds'
)


def get_config():
    if os.path.exists(CONFIG_FILE_NAME):
        with open(CONFIG_FILE_NAME, 'r') as f:
            return [
                line.strip() for line in f.readlines()
            ][:2]
    return None, None


def set_config(username, password):
    with open(CONFIG_FILE_NAME, 'w') as f:
        f.write(username)
        f.write('\n')
        f.write(password)


def get_config_from_user():
    username, password = (
        input('Username: '),
        getpass.getpass('Password: ')
    )
    set_config(username, password)
    return username, password


def clear_config():
    os.remove(CONFIG_FILE_NAME)
