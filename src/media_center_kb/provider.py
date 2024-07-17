"""Info provider about relays and YSP"""

from ysp4000 import YSP4000

from .relays import Relays


class Provider:
    """Relays and YSP info provider"""

    def __init__(self, relays: Relays, ysp: YSP4000):
        self._relays = relays
        self._ysp = ysp
