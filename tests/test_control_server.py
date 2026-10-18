"""Control socket tests"""

import asyncio
import os
import stat

from media_center_kb.control_server import control_server_loop, handle_line


def test_handle_line():
    """commands are checked against the allow-list and parsed"""
    calls = []
    handlers = {
        "airplay_on": lambda: calls.append("on"),
        "airplay_volume": calls.append,
        "shutdown": lambda: calls.append("shutdown"),
    }

    assert handle_line("airplay_on", handlers) == "ok"
    assert handle_line("airplay_volume -12.5", handlers) == "ok"
    assert calls == ["on", -12.5]

    assert handle_line("", handlers).startswith("error")
    assert handle_line("shutdown", handlers).startswith("error")
    assert handle_line("airplay_off", handlers).startswith("error")
    assert handle_line("airplay_on 1", handlers).startswith("error")
    assert handle_line("airplay_volume", handlers).startswith("error")
    assert handle_line("airplay_volume loud", handlers).startswith("error")
    assert calls == ["on", -12.5]

    def fail():
        raise RuntimeError("serial")

    assert handle_line("airplay_on", {"airplay_on": fail}) == "error serial"


def test_control_server(tmp_path):
    """commands sent over the socket reach the handlers"""
    path = str(tmp_path / "ctl.sock")
    calls = []
    handlers = {
        "airplay_on": lambda: calls.append("on"),
        "airplay_off": lambda: calls.append("off"),
    }

    async def send(line: str) -> str:
        reader, writer = await asyncio.open_unix_connection(path)
        writer.write(line.encode() + b"\n")
        await writer.drain()
        reply = await reader.readline()
        writer.close()
        return reply.decode().strip()

    async def run():
        task = asyncio.create_task(control_server_loop(path, handlers))
        while not os.path.exists(path):
            await asyncio.sleep(0.01)
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o660

        replies = [
            await send("airplay_on"),
            await send("bogus"),
            await send("airplay_off"),
        ]

        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        return replies

    replies = asyncio.run(run())
    assert replies[0] == "ok"
    assert replies[1].startswith("error")
    assert replies[2] == "ok"
    assert calls == ["on", "off"]
    assert not os.path.exists(path)


def test_control_server_bad_path(tmp_path):
    """failing to create the socket does not stop the app"""
    path = str(tmp_path / "missing" / "ctl.sock")
    asyncio.run(control_server_loop(path, {}))
    assert not os.path.exists(path)
