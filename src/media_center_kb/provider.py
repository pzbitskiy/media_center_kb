"""Info provider about relays and YSP"""

from ysp4000.ysp import Ysp4000

from .relays import Relays


class Provider:
    """Relays and YSP info provider"""

    def __init__(self, relays: Relays, ysp: Ysp4000):
        self._relays = relays
        self._ysp = ysp
