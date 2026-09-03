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
from .lambda_solver import build_lambda_table, interpolate_xi, jc_model
from .montecarlo import ProgressCallback, propagate
from .types import (
    AnalysisResult,
    AnalysisSettings,
    CoherenceSource,
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


def build_curve(
    fit: FitResult, table: LambdaTable, settings: AnalysisSettings
) -> SuperfluidCurve:
    """A dense model curve from absolute zero up towards Tc.

    Starting at zero rather than at the coldest measurement (FR-026), so that
    the intercept the analysis reports is on the plot instead of being inferred
    from where the data happen to stop. Both gap models are total at T = 0 --
    delta_of_T returns Delta(0), _reduced_gap returns d = inf, and both
    superfluid densities return exactly 1 -- so lambda at the first sample is
    bit-for-bit the fitted lambda(0) rather than an extrapolation towards it.

    Stopping just short of Tc rather than at it, because rho_s -> 0 there and
    lambda diverges; a plot and an exported table both need a finite last point.

    The critical current density is on the same grid, and is the same model as
    `FitResult.jc_model` rather than a second expression of it: both are
    equation (1) at the fitted parameters, and the only difference is where
    they are sampled. Its coherence length comes from the fit under a fixed
    kappa and from the measurements otherwise, which is why it is NaN outside
    their span there -- `interpolate_xi` says why (FR-026a, research R12).
    """
    t = np.linspace(0.0, fit.tc.value * 0.999, CURVE_POINTS)
    r = rho_s(t, fit.delta0.value, fit.tc.value, fit.gap_model)
    lam = lambda_of_T(t, fit.lambda0.value, fit.delta0.value, fit.tc.value, fit.gap_model)

    if settings.coherence_source is CoherenceSource.FIXED_KAPPA:
        xi = lam / float(settings.kappa_fixed)
    else:
        xi = interpolate_xi(table.temperature_K, table.xi, t)
    with np.errstate(divide="ignore", invalid="ignore"):
        jc = np.asarray(jc_model(lam, xi), dtype=float)

    return SuperfluidCurve(temperature_K=t, rho_s=r, lambda_=lam, jc=jc)


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
    curve = build_curve(fit, table, settings)

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
