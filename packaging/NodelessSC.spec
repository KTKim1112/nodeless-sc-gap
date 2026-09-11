# PyInstaller build of the standalone Windows executable.
#
# Run it through `packaging/build.ps1` rather than directly: the build needs
# `backend/static/` to exist, and that is produced by the frontend build, not
# by anything here.
#
# The recipient has no Python, no Node, and no administrator rights. What comes
# out of this is one file they can double-click.

import os
import pathlib

from PyInstaller.utils.hooks import collect_submodules

ROOT = pathlib.Path(SPECPATH).resolve().parent
BACKEND = ROOT / "backend"

# One file or one folder. Measured on this machine: one file takes 19.4 s to
# start, because the bootloader unpacks 54 MB into a temporary directory on
# every launch and shows nothing while it does. One folder starts in about two
# seconds. `build.ps1 -OneDir` sets this.
ONEDIR = bool(os.environ.get("NSC_ONEDIR"))

# The frontend and the example datasets are read from disk at runtime through
# `app.resources.root()`, which returns PyInstaller's extraction directory when
# frozen. Laying them out here exactly as they sit under `backend/` is what
# makes that one function enough for both cases.
# Only `static/` now. The shipped example datasets used to be the second entry
# and FR-028 was withdrawn, so the executable carries no data of any kind.
datas = [
    (str(BACKEND / "static"), "static"),
]

# uvicorn resolves its loop, HTTP parser, websocket and lifespan
# implementations by importing them from strings at startup, so a static
# analysis of the imports cannot see them. Collecting the whole package is
# blunter than listing eight modules and stays correct when uvicorn adds a
# ninth.
hiddenimports = collect_submodules("uvicorn")

a = Analysis(
    # entry.py, not app/desktop.py. PyInstaller runs its entry point as
    # `__main__`, where a relative import has no parent package -- and it fails
    # the same way during analysis, so everything past that import goes
    # unbundled. See the note in entry.py.
    [str(ROOT / "packaging" / "entry.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Excluded because nothing in the application imports them, and together
    # they are most of the weight. pandas is a test-only dependency; the rest
    # arrive through scipy and matplotlib-adjacent packages and are never
    # reached from the analysis chain.
    excludes=[
        "pandas",
        "matplotlib",
        "tkinter",
        "IPython",
        "pytest",
        "PyInstaller",
        "notebook",
        "jupyter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# In one-folder mode the binaries and data files sit beside the executable and
# are collected below; in one-file mode they are embedded in it.
_payload = [] if ONEDIR else [a.binaries, a.datas]

exe = EXE(
    pyz,
    a.scripts,
    *_payload,
    [],
    exclude_binaries=ONEDIR,
    name="NodelessSC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX is off deliberately. It shrinks the file by a useful fraction and is
    # also one of the strongest signals antivirus heuristics use, and this file
    # has to arrive by email or a shared drive on somebody else's machine.
    upx=False,
    # A console window, because it is the only stop button the recipient has:
    # closing it ends the program. Without it a forgotten server would run
    # until the next reboot with nothing on screen to say so.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if ONEDIR:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="NodelessSC",
    )
