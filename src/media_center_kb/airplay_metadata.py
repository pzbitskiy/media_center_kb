"""
shairport-sync metadata pipe reader, reports the AirPlay client model.

Items look like:
    <item><type>73736e63</type><code>636d6f64</code><length>11</length>
    <data encoding="base64">
    QXBwbGVUVjExLDE=</data></item>
type and code are 4-character codes in hex ('ssnc', 'cmod'), data is base64.
"""

import asyncio
import base64
import binascii
import logging
import os
import re
import stat
from typing import Callable, Optional, Tuple

logger = logging.getLogger("meta")

SSNC = int.from_bytes(b"ssnc", "big")
# client model, e.g. "AppleTV11,1", "iPhone14,5", sent on every stream setup
CMOD = int.from_bytes(b"cmod", "big")

ITEM_START = b"<item>"
ITEM_END = b"</item>"
ITEM_RE = re.compile(
    rb"<type>([0-9a-f]+)</type><code>([0-9a-f]+)</code><length>(\d+)</length>"
    rb'(?:\s*<data encoding="base64">([^<]*)</data>)?'
)

# items larger than that (cover art) are skipped
READ_LIMIT = 64 * 1024


def parse_item(item: bytes) -> Optional[Tuple[int, int, bytes]]:
    """Parse the last item in the chunk, return (type, code, data) or None if malformed"""
    match = ITEM_RE.search(item, max(item.rfind(ITEM_START), 0))
    if match is None:
        return None
    type_hex, code_hex, _, data = match.groups()
    try:
        payload = (
            base64.b64decode(b"".join(data.split()), validate=True) if data else b""
        )
    except binascii.Error:
        return None
    return int(type_hex, 16), int(code_hex, 16), payload


def fourcc(value: int) -> str:
    """4-character code as text, e.g. 'cmod'"""
    return value.to_bytes(4, "big").decode(errors="replace")


def handle_item(item: bytes, on_client_model: Callable[[str], None]):
    """Call on_client_model for a client model item"""
    parsed = parse_item(item)
    if parsed is None:
        logger.debug("metadata: malformed item %r", item[:200])
        return
    item_type, code, data = parsed
    logger.debug(
        "metadata: %s %s, %d bytes", fourcc(item_type), fourcc(code), len(data)
    )
    if item_type != SSNC or code != CMOD:
        return

    model = data.decode(errors="replace")
    logger.info("metadata: client model %s", model)
    try:
        on_client_model(model)
    except Exception as ex:  # pylint: disable=broad-exception-caught
        logger.error("metadata: client model %s failed: %s", model, ex)


def open_pipe(path: str) -> int:
    """Open the metadata pipe, create it if shairport-sync has not yet"""
    if not os.path.exists(path):
        os.mkfifo(path)
        # shairport-sync creates it world-writable too, chmod is not affected by umask
        os.chmod(path, 0o666)
    if not stat.S_ISFIFO(os.stat(path).st_mode):
        raise OSError(f"not a fifo: {path}")
    # read-write: the pipe stays open when shairport-sync restarts, no EOF
    return os.open(path, os.O_RDWR | os.O_NONBLOCK)


async def airplay_metadata_loop(path: str, on_client_model: Callable[[str], None]):
    """Read shairport-sync metadata pipe and report client models"""
    loop = asyncio.get_running_loop()
    try:
        pipe = os.fdopen(open_pipe(path), "rb", buffering=0)
        reader = asyncio.StreamReader(limit=READ_LIMIT)
        transport, _ = await loop.connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(reader), pipe
        )
    except OSError as ex:
        # keep the keyboard, HA and the control socket working without the metadata
        logger.error("metadata pipe %s disabled: %s", path, ex)
        return
    logger.info("metadata pipe reading %s", path)

    try:
        oversized = False
        while True:
            try:
                item = await reader.readuntil(ITEM_END)
            except asyncio.LimitOverrunError as ex:
                # skip the oversized item (e.g. a picture) up to its end
                await reader.readexactly(ex.consumed)
                oversized = True
                continue
            if oversized:
                oversized = False
                logger.debug("metadata: skipped oversized item")
                continue
            handle_item(item, on_client_model)
    except asyncio.CancelledError:
        logger.info("cancelled airplay_metadata_loop")
    except asyncio.IncompleteReadError:
        logger.error("metadata pipe %s closed", path)
    finally:
        transport.close()
