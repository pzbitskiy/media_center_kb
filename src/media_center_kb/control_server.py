"""
Local control socket used by shairport-sync session hooks.

Line protocol, one command per connection:
    airplay_on
    airplay_off
    airplay_volume <dB>
Reply is "ok" or "error <reason>".
"""

import asyncio
import logging
import os
from typing import Callable, Dict

logger = logging.getLogger("ctl")

# command name -> number of float arguments
ALLOWED_CMDS = {
    "airplay_on": 0,
    "airplay_off": 0,
    "airplay_volume": 1,
}

READ_TIMEOUT = 5


def handle_line(line: str, handlers: Dict[str, Callable]) -> str:
    """Parse and run a single command, return the reply"""
    parts = line.split()
    if not parts:
        return "error empty command"
    cmd, args = parts[0], parts[1:]
    nargs = ALLOWED_CMDS.get(cmd)
    if nargs is None or cmd not in handlers:
        return f"error unknown command: {cmd}"
    if len(args) != nargs:
        return f"error {cmd} expects {nargs} argument(s)"
    try:
        values = [float(arg) for arg in args]
    except ValueError:
        return f"error bad argument: {' '.join(args)}"

    logger.info("control: %s", line)
    try:
        handlers[cmd](*values)
    except Exception as ex:  # pylint: disable=broad-exception-caught
        logger.error("control %s failed: %s", cmd, ex)
        return f"error {ex}"
    return "ok"


async def control_server_loop(path: str, handlers: Dict[str, Callable]):
    """Serve control commands on a unix socket"""

    async def on_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            data = await asyncio.wait_for(reader.readline(), READ_TIMEOUT)
            reply = handle_line(data.decode(errors="replace").strip(), handlers)
            writer.write(reply.encode() + b"\n")
            await writer.drain()
        except (asyncio.TimeoutError, ConnectionError) as ex:
            logger.debug("control client error: %s", ex)
        finally:
            writer.close()

    try:
        if os.path.exists(path):
            os.unlink(path)
        server = await asyncio.start_unix_server(on_client, path=path)
        os.chmod(path, 0o660)
    except OSError as ex:
        # keep the keyboard and HA working without the control socket
        logger.error("control socket %s disabled: %s", path, ex)
        return
    logger.info("control socket listening on %s", path)
    try:
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        logger.info("cancelled control_server_loop")
    finally:
        if os.path.exists(path):
            os.unlink(path)
