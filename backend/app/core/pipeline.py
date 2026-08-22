"""Compose the physics into one analysis.

This is the only entry point the API layer needs. Everything above it is
transport and serialisation; everything below it is physics.
"""

from __future__ import annotations

import numpy as np

from .diagnostics import build_report
from .errors import CoreError
from .fitting import fit as run_fit
from .gap_models import lambda_of_T, rho_s
from .lambda_solver import build_lambda_table
from .montecarlo import ProgressCallback, propagate
from .types import (
    AnalysisResult,
    AnalysisSettings,
    FitResult,
    GapModel,
    LambdaTable,
    MeasurementDataset,
    SuperfluidCurve,
    UncertaintySettings,
)
from .validation import check_settings

#: Points on the plotted model curve. Enough to look smooth, few enough to send.
CURVE_POINTS = 200


def run_lambda_table(
    dataset: MeasurementDataset, settings: AnalysisSettings
) -> LambdaTable:
    """The per-temperature inversion on its own, without a gap fit.

    Useful when the data are too sparse to fit, or when the user only wants to
    look at lambda(T) and kappa(T).
    """
    check_settings(dataset, settings)
    return build_lambda_table(dataset, settings)


def build_curve(fit: FitResult, t_min: float) -> SuperfluidCurve:
    """A dense model curve from the coldest measured point up towards Tc.

    Stopping just short of Tc rather than at it, because rho_s -> 0 there and
    lambda diverges; a plot needs a finite last point.
    """
    t = np.linspace(t_min, fit.tc.value * 0.999, CURVE_POINTS)
    r = rho_s(t, fit.delta0.value, fit.tc.value, fit.gap_model)
    lam = lambda_of_T(t, fit.lambda0.value, fit.delta0.value, fit.tc.value, fit.gap_model)
    return SuperfluidCurve(temperature_K=t, rho_s=r, lambda_=lam)


def _chi2_both_models(
    dataset: MeasurementDataset, table: LambdaTable, settings: AnalysisSettings
) -> tuple[float | None, float | None]:
    """Fit with each gap model so the two can be compared (FR-020).

    A model that fails to converge contributes None rather than aborting the
    analysis: the user asked for one model, and the comparison is advisory.
    """
    out: dict[GapModel, float | None] = {}
    for model in (GapModel.CLEAN, GapModel.DIRTY):
        try:
            out[model] = run_fit(dataset, table, settings, gap_model=model).chi2_reduced
        except CoreError:
            out[model] = None
    return out[GapModel.CLEAN], out[GapModel.DIRTY]


def run_analysis(
    dataset: MeasurementDataset,
    settings: AnalysisSettings,
    uncertainty: UncertaintySettings | None = None,
    progress: ProgressCallback | None = None,
) -> AnalysisResult:
    """The whole chain: Jc -> lambda(T) -> superfluid density -> Delta(0)."""
    check_settings(dataset, settings)

    table = build_lambda_table(dataset, settings)
    fit = run_fit(dataset, table, settings)
    chi2_clean, chi2_dirty = _chi2_both_models(dataset, table, settings)
    report = build_report(table, fit, settings, chi2_clean, chi2_dirty)
    curve = build_curve(fit, float(np.min(table.temperature_K)))

    result_uncertainty = None
    if uncertainty is not None and uncertainty.any_uncertainty:
        result_uncertainty = propagate(dataset, settings, uncertainty, progress)

    return AnalysisResult(
        dataset=dataset,
        settings=settings,
        lambda_table=table,
        fit=fit,
        curve=curve,
        diagnostics=report,
        uncertainty=result_uncertainty,
    )
