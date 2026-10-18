"""shairport-sync metadata pipe tests"""

import asyncio
import base64
import logging
import os
import stat

import pytest

from media_center_kb.airplay_metadata import (
    CMOD,
    READ_LIMIT,
    SSNC,
    airplay_metadata_loop,
    parse_item,
)


def item(item_type: bytes, code: bytes, data: bytes = b"") -> bytes:
    """metadata item as shairport-sync writes it to the pipe"""
    out = (
        f"<item><type>{item_type.hex()}</type><code>{code.hex()}</code>"
        f"<length>{len(data)}</length>"
    ).encode()
    if data:
        out += b'\n<data encoding="base64">\n' + base64.b64encode(data) + b"</data>"
    return out + b"</item>\n"


def test_parse_item():
    """items are parsed, malformed ones rejected"""
    assert parse_item(item(b"ssnc", b"cmod", b"AppleTV11,1")) == (
        SSNC,
        CMOD,
        b"AppleTV11,1",
    )
    assert parse_item(item(b"ssnc", b"abeg")) == (
        SSNC,
        int.from_bytes(b"abeg", "big"),
        b"",
    )
    # leftovers of a previous item before the last one
    assert parse_item(
        b"QUJD</data></item>\n" + item(b"ssnc", b"cmod", b"iPhone14,5")
    ) == (
        SSNC,
        CMOD,
        b"iPhone14,5",
    )
    assert parse_item(b"garbage</item>") is None
    assert (
        parse_item(
            b"<item><type>73736e63</type><code>636d6f64</code><length>3</length>\n"
            b'<data encoding="base64">\n!!!</data></item>'
        )
        is None
    )


def test_airplay_metadata_loop(tmp_path, caplog):
    """client models are read from the pipe, other items and garbage are skipped"""
    caplog.set_level(logging.DEBUG, logger="meta")
    path = str(tmp_path / "shairport-sync-metadata")
    models = []

    def on_client_model(model: str):
        models.append(model)
        if model == "fail":
            raise RuntimeError("serial")

    def write(data: bytes):
        with open(path, "wb") as pipe:
            pipe.write(data)

    async def run():
        task = asyncio.create_task(airplay_metadata_loop(path, on_client_model))
        while not os.path.exists(path):
            await asyncio.sleep(0.01)
        assert stat.S_ISFIFO(os.stat(path).st_mode)
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o666

        await asyncio.to_thread(
            write,
            item(b"ssnc", b"abeg")
            + item(b"ssnc", b"cmod", b"fail")
            + item(b"core", b"asar", b"Artist")
            + b"garbage</item>"
            + item(b"ssnc", b"PICT", b"x" * READ_LIMIT * 2)
            + item(b"ssnc", b"cmod", b"AppleTV11,1"),
        )
        # writer closed and reopened, e.g. shairport-sync restart
        await asyncio.to_thread(write, item(b"ssnc", b"cmod", b"iPhone14,5"))

        while len(models) < 3:
            await asyncio.sleep(0.01)
        task.cancel()
        await task

    asyncio.run(asyncio.wait_for(run(), 5))
    assert models == ["fail", "AppleTV11,1", "iPhone14,5"]
    messages = [record.getMessage() for record in caplog.records]
    assert "metadata: skipped oversized item" in messages
    assert "metadata: core asar, 6 bytes" in messages
    # only the garbage, not the oversized item tail
    assert len([m for m in messages if m.startswith("metadata: malformed")]) == 1


@pytest.mark.parametrize("make_path", ["dir", "missing_parent"])
def test_airplay_metadata_bad_path(tmp_path, make_path):
    """a bad pipe path disables the reader instead of failing"""
    if make_path == "dir":
        path = str(tmp_path)
    else:
        path = str(tmp_path / "missing" / "pipe")
    asyncio.run(asyncio.wait_for(airplay_metadata_loop(path, print), 5))
