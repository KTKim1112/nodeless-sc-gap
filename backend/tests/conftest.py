"""Shared fixtures.

The synthetic dataset defined here is the backbone of the whole suite: data
generated from parameters we know, so that "did the code recover them?" has an
exact answer. Constitution II.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core import gap_models as gm
from app.core import lambda_solver as ls
from app.core.constants import MEV_TO_J, PHI0
from app.core.types import (
    AnalysisSettings,
    CoherenceSource,
    GapModel,
    MeasurementDataset,
)
from app.core.validation import build_dataset

# --- ground truth ------------------------------------------------------------
# Roughly a clean low-Tc film: lambda(0) = 200 nm, Delta(0) = 1.5 meV,
# Tc = 10 K, kappa = 40. The coupling ratio is then 3.481, just inside the
# weak-coupling BCS band.
TRUE_LAMBDA0 = 200e-9
TRUE_DELTA0 = 1.5 * MEV_TO_J
TRUE_TC = 10.0
TRUE_KAPPA = 40.0


def synthesise(
    model: GapModel = GapModel.CLEAN,
    n_points: int = 20,
    t_min: float = 0.5,
    t_max: float = 9.0,
) -> dict:
    """Build Jc(T) from the known parameters, exactly as the model would.

    Returns every intermediate quantity so a test can assert against whichever
    stage it is exercising.
    """
    t = np.linspace(t_min, t_max, n_points)
    lam = gm.lambda_of_T(t, TRUE_LAMBDA0, TRUE_DELTA0, TRUE_TC, model)
    xi = lam / TRUE_KAPPA
    jc = np.asarray(ls.jc_model(lam, xi), dtype=float)
    hc2 = PHI0 / (2.0 * np.pi * xi**2)
    return {"temperature_K": t, "lambda_": lam, "xi": xi, "jc": jc, "hc2": hc2}


@pytest.fixture
def clean_data() -> dict:
    return synthesise(GapModel.CLEAN)


@pytest.fixture
def dirty_data() -> dict:
    return synthesise(GapModel.DIRTY)


@pytest.fixture
def dataset_xi(clean_data) -> MeasurementDataset:
    return build_dataset(clean_data["temperature_K"], clean_data["jc"], xi=clean_data["xi"])


@pytest.fixture
def dataset_hc2(clean_data) -> MeasurementDataset:
    return build_dataset(clean_data["temperature_K"], clean_data["jc"], hc2=clean_data["hc2"])


@pytest.fixture
def dataset_kappa(clean_data) -> MeasurementDataset:
    return build_dataset(clean_data["temperature_K"], clean_data["jc"])


@pytest.fixture
def settings_xi() -> AnalysisSettings:
    return AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)


@pytest.fixture
def settings_hc2() -> AnalysisSettings:
    return AnalysisSettings(coherence_source=CoherenceSource.FROM_HC2)


@pytest.fixture
def settings_kappa() -> AnalysisSettings:
    return AnalysisSettings(
        coherence_source=CoherenceSource.FIXED_KAPPA, kappa_fixed=TRUE_KAPPA
    )
