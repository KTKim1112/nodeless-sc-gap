"""Where the application looks for its data files.

The frozen branch is the one nothing else covers. Every other test runs from
source, and the packaged build is exercised only by starting the executable by
hand -- which is exactly the arrangement that lets a path bug ship. These two
tests pin both branches so that a change to `resources.root()` has to be
deliberate.
"""

from __future__ import annotations

import pathlib
import sys

from app import resources


def test_from_source_the_root_is_the_backend_directory():
    root = resources.root()
    assert root == pathlib.Path(__file__).resolve().parents[1]
    # The two callers must actually find something there, or the constant is
    # right and useless.
    assert (root / "examples" / "manifest.json").is_file()
    assert not resources.frozen()


def test_frozen_the_root_is_the_extraction_directory(tmp_path, monkeypatch):
    """PyInstaller unpacks the bundle and records where, as `sys._MEIPASS`.

    Set rather than mocked away: the attribute does not exist off a frozen
    build, so `raising=False` is what makes this a test of the branch rather
    than of monkeypatch.
    """
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert resources.root() == tmp_path
    assert resources.frozen()
