"""Where the application's data files are, installed or packaged.

The built frontend sits beside the `app` package when the project is installed,
and inside a temporary extraction directory when PyInstaller has frozen it into
a single executable. `main.py` needs to know that in order to find `static/`,
and resolving it here rather than there keeps the packaging knowledge in one
place.

There used to be a second caller, for the shipped example datasets. FR-028 was
withdrawn and they are gone, so this now serves one directory -- kept as its
own module anyway, because the frozen branch is the one nothing else covers and
it has its own test.

Not in `core/`: this touches the filesystem and knows about a packaging tool,
neither of which the physics is allowed to (constitution I).
"""

from __future__ import annotations

import pathlib
import sys


def root() -> pathlib.Path:
    """The directory holding `static/`.

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
