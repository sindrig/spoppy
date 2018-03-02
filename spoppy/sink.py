import logging

import spotify

logger = logging.getLogger(__name__)


def get_wrapped_alsa_sink():
    from alsaaudio import ALSAAudioError

    class AlsaSink(spotify.AlsaSink):
        def _on_music_delivery(self, *args, **kwargs):
            try:
                return super(AlsaSink, self)._on_music_delivery(
                    *args,
                    **kwargs
                )
            except ALSAAudioError as e:
                logger.warn("ALSAAudioError", exc_info=True)
                self._device = None
                return super(AlsaSink, self)._on_music_delivery(
                    *args,
                    **kwargs
                )

    return AlsaSink
