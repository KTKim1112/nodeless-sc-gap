"""Entry script for the frozen build.

PyInstaller runs its entry point as `__main__`, which has no parent package, so
`app/desktop.py` cannot be pointed at directly: its `from .main import app`
raises `ImportError` before anything else happens. Worse, it does so at analysis
time as well, and PyInstaller then bundles nothing that lies beyond that import
-- the first build produced an 11 MB executable with neither numpy nor scipy in
it, which is what gave the mistake away.

This file exists to turn that relative import into an absolute one. It holds no
logic, so that the executable and `python -m app.desktop` cannot diverge.
"""

import sys

from app.desktop import main

if __name__ == "__main__":
    sys.exit(main())
