import logging

logger = logging.getLogger(__name__)


class SpotipyWrapper(object):
    def __init__(self, navigator, client):
        self.client = client
        self.navigator = navigator

    def is_authenticated(self):
        return bool(self.client._auth)

    def __getattr__(self, func_name):
        def wrapped(*args, **kwargs):
            try:
                return getattr(self.client, func_name)(*args, **kwargs)
            except Exception as e:
                if getattr(e, 'http_status', None) == 401:
                    logger.debug(
                        'Access token for spotipy expired, '
                        'or unknown auth error'
                    )
                    # This will update the auth token in our current client
                    self.navigator.refresh_spotipy_client_and_token()
                    return getattr(self.client, func_name)(*args, **kwargs)
                raise e
        return wrapped
