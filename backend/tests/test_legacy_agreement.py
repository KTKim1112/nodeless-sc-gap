"""The rewrite must not have changed the physics.

`legacy/` holds the three command-line prototypes this project replaces. No code
was copied from them -- the new core has a different architecture entirely -- so
the only thing tying the two together is that they must produce the same
numbers. That is checked here, by running the legacy scripts as subprocesses on
a fixture and comparing their `lambda(T)` column against ours.

This is the one test that would catch the rewrite having quietly introduced a
different factor while remaining internally consistent, because every other
test in the suite checks the new code against itself or against theory.

The legacy scripts need pandas, which this project deliberately does not
depend on. When it is absent the comparison is skipped rather than failed:
missing a cross-check is not the same as failing one, and the skip message says
how to enable it.
"""

from __future__ import annotations

import csv
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
import pytest

from app.core import lambda_solver as ls
from app.core.types import AnalysisSettings, CoherenceSource
from app.core.validation import build_dataset

LEGACY = pathlib.Path(__file__).resolve().parents[2] / "legacy"

pandas_available = pytest.mark.skipif(
    __import__("importlib").util.find_spec("pandas") is None,
    reason="legacy scripts need pandas; run `pip install pandas` to enable this cross-check",
)

# A small hand-written table in the units the legacy scripts expect:
# T [K], Jc [A/cm^2], Hc2 [T], xi [nm].
FIXTURE = [
    (2.0, 6.50e6, 13.0, 5.03),
    (4.0, 5.20e6, 11.5, 5.35),
    (6.0, 3.40e6, 9.0, 6.05),
    (8.0, 1.30e6, 5.0, 8.12),
    (9.0, 5.00e5, 2.5, 11.49),
]

T = np.array([row[0] for row in FIXTURE])
JC_CM2 = np.array([row[1] for row in FIXTURE])
JC_SI = JC_CM2 * 1e4
HC2 = np.array([row[2] for row in FIXTURE])
XI_NM = np.array([row[3] for row in FIXTURE])
XI_SI = XI_NM * 1e-9
KAPPA = 40.0


def _run_legacy(script: str, columns, *args) -> np.ndarray:
    """Run one legacy script on the fixture and return its lambda column in metres."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        data_file = tmp_path / "data.txt"
        data_file.write_text(
            "\n".join(" ".join(f"{value:.10g}" for value in row) for row in columns),
            encoding="utf-8",
        )
        out_file = tmp_path / "out.csv"
        completed = subprocess.run(
            [sys.executable, str(LEGACY / script), str(data_file),
             "--output", str(out_file), *args],
            capture_output=True, text=True,
        )
        if completed.returncode != 0:
            pytest.fail(f"{script} failed:\n{completed.stdout}\n{completed.stderr}")
        with out_file.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    return np.array([float(row["lambda_m"]) for row in rows])


def _ours(dataset, settings) -> np.ndarray:
    return ls.build_lambda_table(dataset, settings).lambda_


@pandas_available
def test_agrees_with_the_hc2_script():
    theirs = _run_legacy(
        "lambda_from_T_Jc_Hc2.py",
        list(zip(T, JC_CM2, HC2)),
        "--jc-unit", "A/cm2",
    )
    ours = _ours(
        build_dataset(T, JC_SI, hc2=HC2),
        AnalysisSettings(coherence_source=CoherenceSource.FROM_HC2),
    )
    assert np.allclose(ours, theirs, rtol=1e-9, atol=0.0)


@pandas_available
def test_agrees_with_the_explicit_xi_script():
    theirs = _run_legacy(
        "lambda_from_T_Jc_xi.py",
        list(zip(T, JC_CM2, XI_NM)),
        "--jc-unit", "A/cm2", "--xi-unit", "nm",
    )
    ours = _ours(
        build_dataset(T, JC_SI, xi=XI_SI),
        AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI),
    )
    assert np.allclose(ours, theirs, rtol=1e-9, atol=0.0)


@pandas_available
def test_agrees_with_the_fixed_kappa_script():
    theirs = _run_legacy(
        "lambda_from_T_Jc_constant_kappa.py",
        list(zip(T, JC_CM2)),
        "--jc-unit", "A/cm2", "--kappa", str(KAPPA),
    )
    ours = _ours(
        build_dataset(T, JC_SI),
        AnalysisSettings(coherence_source=CoherenceSource.FIXED_KAPPA, kappa_fixed=KAPPA),
    )
    assert np.allclose(ours, theirs, rtol=1e-9, atol=0.0)


def test_the_legacy_scripts_are_still_present():
    """If they are ever deleted, the cross-check silently stops being run, so
    their absence is itself a failure rather than a skip."""
    for name in ("lambda_from_T_Jc_Hc2.py", "lambda_from_T_Jc_xi.py",
                 "lambda_from_T_Jc_constant_kappa.py"):
        assert (LEGACY / name).is_file(), f"legacy/{name} is missing"
