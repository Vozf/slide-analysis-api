import os
from collections import (
    namedtuple,
    OrderedDict,
)
from threading import Lock

from openslide import OpenSlide
from openslide.deepzoom import DeepZoomGenerator

from slide_analysis_api.constants import (
    SLIDE_CACHE_SIZE,
    SLIDE_DIR,
)

SlideObject = namedtuple('SlideObject', ['openslide', 'deepzoom', 'path'])


class _SlideCache:
    def __init__(self, cache_size):
        self.cache_size = cache_size
        self._lock = Lock()
        self._cache = OrderedDict()

    def get(self, path):
        with self._lock:
            if path in self._cache:
                # Move to end of LRU
                slide_object = self._cache.pop(path)
                self._cache[path] = slide_object
                return slide_object

        openslide = OpenSlide(path)
        deepzoom = DeepZoomGenerator(openslide)
        slide_object = SlideObject(openslide=openslide, deepzoom=deepzoom, path=path)

        with self._lock:
            if path not in self._cache:
                if len(self._cache) == self.cache_size:
                    self._cache.popitem(last=False)
                self._cache[path] = slide_object
        return slide_object


cache = _SlideCache(SLIDE_CACHE_SIZE)


def _get_slide(path):
    path = os.path.abspath(os.path.join(SLIDE_DIR, path))
    if not path.startswith(SLIDE_DIR):
        # Directory traversal
        raise Exception()
    if not os.path.exists(path):
        raise Exception()
    slide = cache.get(path)
    return slide
