"""Build a validated `MeasurementDataset` from raw columns.

Kept apart from `types.py` so that a failure can name the offending row, which a
dataclass `__post_init__` is a poor place to do, and apart from `parsing.py`
because this is where units and physics meaning enter.
"""

from __future__ import annotations

import numpy as np

from .constants import KAPPA_MODEL_FLOOR, KAPPA_TYPE_II_BOUNDARY
from .errors import (
    KappaTooSmall,
    LengthMismatch,
    MissingColumn,
    NonPositiveValue,
    NotTypeII,
    TcFixedBelowData,
    TooFewPoints,
)
from .parsing import MIN_POINTS
from .types import AnalysisSettings, CoherenceSource, FloatArray, MeasurementDataset


def _check_positive(values: FloatArray, column: str) -> FloatArray:
    arr = np.atleast_1d(np.asarray(values, dtype=float))
    bad = ~np.isfinite(arr) | (arr <= 0.0)
    if np.any(bad):
        index = int(np.argmax(bad))
        raise NonPositiveValue(row=index + 1, column=column, value=float(arr[index]))
    return arr


def build_dataset(
    temperature_K,
    jc,
    hc2=None,
    xi=None,
) -> MeasurementDataset:
    """Validate and assemble. Inputs must already be in SI."""
    t = _check_positive(temperature_K, "temperature_K")
    j = _check_positive(jc, "jc")

    if t.size < MIN_POINTS:
        raise TooFewPoints(found=int(t.size), required=MIN_POINTS)
    if j.size != t.size:
        raise LengthMismatch(name="jc", expected=int(t.size), found=int(j.size))

    h = None
    if hc2 is not None:
        h = _check_positive(hc2, "hc2")
        if h.size != t.size:
            raise LengthMismatch(name="hc2", expected=int(t.size), found=int(h.size))

    x = None
    if xi is not None:
        x = _check_positive(xi, "xi")
        if x.size != t.size:
            raise LengthMismatch(name="xi", expected=int(t.size), found=int(x.size))

    return MeasurementDataset(temperature_K=t, jc=j, hc2=h, xi=x)


def check_settings(dataset: MeasurementDataset, settings: AnalysisSettings) -> None:
    """Cross-checks between the data and the chosen settings.

    Raised before any computation so that a misconfiguration is reported as
    such, rather than as a numerical failure further down.
    """
    source = settings.coherence_source
    if source is CoherenceSource.FROM_HC2 and dataset.hc2 is None:
        raise MissingColumn(coherence_source=source.value, missing="hc2")
    if source is CoherenceSource.EXPLICIT_XI and dataset.xi is None:
        raise MissingColumn(coherence_source=source.value, missing="xi")
    if source is CoherenceSource.FIXED_KAPPA:
        kappa = settings.kappa_fixed
        if kappa is None:
            raise MissingColumn(coherence_source=source.value, missing="kappa_fixed")
        if kappa <= KAPPA_MODEL_FLOOR:
            raise KappaTooSmall(kappa=float(kappa), floor=KAPPA_MODEL_FLOOR)
        if kappa <= KAPPA_TYPE_II_BOUNDARY:
            raise NotTypeII(kappa=float(kappa), boundary=KAPPA_TYPE_II_BOUNDARY)

    if settings.tc_fixed_K is not None:
        t_max = float(np.max(dataset.temperature_K))
        if settings.tc_fixed_K <= t_max:
            raise TcFixedBelowData(
                tc_fixed_K=float(settings.tc_fixed_K), t_max_K=t_max
            )
