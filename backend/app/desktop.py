"""Entry point for the packaged desktop build.

Serves the application on the loopback interface and opens a browser at it.
Nothing else imports this: `main.py` does not know it exists, so the packaged
build, the container, and the development server all run the same `app` object
and can only differ in how they are started.

Deliberately not a second copy of the application. If a behaviour differs
between the executable and `uvicorn app.main:app`, that is a bug here.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from .main import app

HOST = "127.0.0.1"

#: How long to wait for the server before giving up on opening a browser. The
#: server itself keeps running; only the convenience of launching the page is
#: abandoned, and the console prints the address so it can be opened by hand.
BROWSER_TIMEOUT_S = 30.0


def _listening_socket() -> socket.socket:
    """A bound, listening socket on a port the operating system chose.

    Asking for port 0 rather than naming one. A fixed port is a guess about a
    machine that has never been seen, and 8000 in particular is already taken
    on a great many of them. Handing the bound socket to uvicorn rather than
    just its number closes the window in which something else could take the
    port between the two steps.

    Bound to the loopback address, so the server is unreachable from the
    network however the recipient's firewall is configured. The application is
    single-user by design and holds unpublished measurements (QA-006).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, 0))
    sock.listen()
    return sock


def _open_browser_when_ready(server: uvicorn.Server, url: str) -> None:
    """Open the page once the server answers, not before.

    Opening it immediately shows the recipient a connection error for the
    second or two that startup takes, which reads as a broken program.
    """
    deadline = time.monotonic() + BROWSER_TIMEOUT_S
    while time.monotonic() < deadline:
        if server.started:
            webbrowser.open(url)
            return
        time.sleep(0.1)


def main() -> int:
    sock = _listening_socket()
    port = sock.getsockname()[1]
    url = f"http://{HOST}:{port}/"

    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    threading.Thread(
        target=_open_browser_when_ready, args=(server, url), daemon=True
    ).start()

    # flush, because this is the only thing on screen until the browser opens
    # and Python buffers stdout whenever it is not a terminal -- which is how
    # the packaged build is launched from a shortcut, a scheduler, or a test.
    print("Nodeless SC gap extractor", flush=True)
    print(f"  {url}", flush=True)
    print("  Closing this window stops the program.", flush=True)
    print(flush=True)

    try:
        server.run(sockets=[sock])
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
