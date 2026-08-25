"""Where the application's data files are, installed or packaged.

The built frontend and the example datasets sit beside the `app` package when
the project is installed, and inside a temporary extraction directory when
PyInstaller has frozen it into a single executable. Two callers need to know
that -- `main.py` for `static/` and `examples_store.py` for `examples/` -- and
resolving it here stops each of them from growing its own guess about where it
is running from.

Not in `core/`: this touches the filesystem and knows about a packaging tool,
neither of which the physics is allowed to (constitution I).
"""

from __future__ import annotations

import pathlib
import sys


def root() -> pathlib.Path:
    """The directory holding `static/` and `examples/`.

    Frozen, PyInstaller unpacks the bundle to a temporary directory and records
    it as `sys._MEIPASS`; the data files are laid out under it exactly as they
    are under `backend/`, so callers below this point need no second case.
    Otherwise it is `backend/`, one level above this package.
    """
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled is not None:
        return pathlib.Path(bundled)
    return pathlib.Path(__file__).resolve().parents[1]


def frozen() -> bool:
    """True when running from a PyInstaller build rather than from source."""
    return getattr(sys, "frozen", False)
