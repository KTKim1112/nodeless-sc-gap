"""Propagate stated measurement uncertainties through the whole chain.

Method and justification: specs/001-jc-to-gap/research.md R8.

Monte Carlo rather than a derivative because the output passes through a
numerical root solve and an iterative fit, so no closed-form partial derivative
exists (R8.1). Log-normal draws rather than Gaussian because the perturbed
quantities are strictly positive and are products of measured quantities
(R8.2). Two correlation modes because a stated relative uncertainty can mean a
calibration error shared by the dataset or point-to-point scatter, and the two
give materially different uncertainties on Delta(0) (R8.3).

The uncertainty produced here is not the same thing as the standard errors on
`FitResult`, and the two are not combined (R8.6).
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from .errors import CoreError, MonteCarloTooManyFailures
from .types import (
    AnalysisSettings,
    CoherenceSource,
    CorrelationMode,
    FloatArray,
    MeasurementDataset,
    ParameterDistribution,
    Severity,
    UncertaintyResult,
    UncertaintySettings,
    Warning_,
)

ProgressCallback = Callable[[float], None]

#: Below this fraction of surviving draws the sample is biased towards benign
#: inputs and the result would be misleadingly narrow, so nothing is reported.
MIN_VALID_FRACTION = 0.5
MIN_VALID_ABSOLUTE = 100


def lognormal_factors(
    rel_sigma: float, size: int | tuple[int, ...], rng: np.random.Generator
) -> FloatArray:
    """Multiplicative perturbations with mean 1 and relative sigma `rel_sigma`.

    Research R8.2, equations (7) and (8): for a target mean m and relative
    standard deviation cv,

        sigma = sqrt( ln(1 + cv^2) )        mu = ln(m) - sigma^2 / 2

    which reproduces both moments exactly. Here m = 1, so mu = -sigma^2/2.
    """
    if rel_sigma <= 0.0:
        return np.ones(size, dtype=float)
    sigma = np.sqrt(np.log1p(rel_sigma**2))
    return rng.lognormal(mean=-0.5 * sigma**2, sigma=sigma, size=size)


def _draw(
    rel_sigma: float,
    n_points: int,
    mode: CorrelationMode,
    rng: np.random.Generator,
) -> FloatArray:
    """One perturbation vector for a column of `n_points` values.

    SYSTEMATIC gives every point the same factor; INDEPENDENT gives each its
    own. That single choice is what decides whether the stated uncertainty can
    move Delta(0) at all (research R8.3).
    """
    if mode is CorrelationMode.SYSTEMATIC:
        return np.full(n_points, float(lognormal_factors(rel_sigma, 1, rng)[0]))
    return lognormal_factors(rel_sigma, n_points, rng)


def _distribution(samples: FloatArray, confidence: float) -> ParameterDistribution:
    """Mean, standard deviation and a central percentile interval.

    Percentiles rather than mean +/- z*sigma, because lambda ~ Jc^(-1/3) is
    non-linear and the resulting distribution is skewed; a symmetric interval
    would misplace both ends (research R8.5).
    """
    alpha = 0.5 * (1.0 - confidence) * 100.0
    return ParameterDistribution(
        mean=float(np.mean(samples)),
        std=float(np.std(samples, ddof=1)) if samples.size > 1 else 0.0,
        ci_low=float(np.percentile(samples, alpha)),
        ci_high=float(np.percentile(samples, 100.0 - alpha)),
    )


def propagate(
    dataset: MeasurementDataset,
    settings: AnalysisSettings,
    uncertainty: UncertaintySettings,
    progress: ProgressCallback | None = None,
) -> UncertaintyResult:
    """Re-run the entire analysis for every draw and summarise the spread."""
    # Imported here rather than at module scope to keep the dependency between
    # montecarlo and fitting one-directional and obvious.
    from .fitting import fit as run_fit
    from .lambda_solver import build_lambda_table

    rng = np.random.default_rng(uncertainty.seed)
    n = uncertainty.n_samples
    n_points = dataset.n_points
    mode = uncertainty.correlation_mode

    lambda0: list[float] = []
    delta0: list[float] = []
    tc: list[float] = []
    ratio: list[float] = []

    report_every = max(1, n // 100)

    for k in range(n):
        jc_k = dataset.jc * _draw(uncertainty.jc_rel_sigma, n_points, mode, rng)

        hc2_k = xi_k = None
        settings_k = settings
        if settings.coherence_source is CoherenceSource.FROM_HC2:
            hc2_k = dataset.hc2 * _draw(uncertainty.hc2_rel_sigma, n_points, mode, rng)
        elif settings.coherence_source is CoherenceSource.EXPLICIT_XI:
            xi_k = dataset.xi * _draw(uncertainty.xi_rel_sigma, n_points, mode, rng)
        else:
            # kappa is a single number the user supplied, so there is only ever
            # one factor to draw and the correlation mode does not apply to it.
            factor = float(lognormal_factors(uncertainty.kappa_rel_sigma, 1, rng)[0])
            settings_k = replace_kappa(settings, settings.kappa_fixed * factor)

        draw = MeasurementDataset(
            temperature_K=dataset.temperature_K, jc=jc_k, hc2=hc2_k, xi=xi_k
        )
        try:
            table = build_lambda_table(draw, settings_k)
            fit = run_fit(draw, table, settings_k)
        except CoreError:
            # Failed draws are discarded and counted. They are not missing at
            # random -- they are systematically the extreme ones -- which is why
            # the surviving fraction is checked below.
            continue

        lambda0.append(fit.lambda0.value)
        delta0.append(fit.delta0.value)
        tc.append(fit.tc.value)
        ratio.append(fit.coupling_ratio.value)

        if progress is not None and (k % report_every == 0):
            progress((k + 1) / n)

    if progress is not None:
        progress(1.0)

    n_valid = len(lambda0)
    required = max(MIN_VALID_ABSOLUTE, int(MIN_VALID_FRACTION * n))
    if n_valid < required:
        raise MonteCarloTooManyFailures(
            n_valid=n_valid, n_requested=n, n_required=required
        )

    warnings = [
        Warning_(
            code="CROSS_QUANTITY_CORRELATION_IGNORED",
            severity=Severity.INFO,
            params={"correlation_mode": mode.value},
        )
    ]
    if n_valid < n:
        warnings.append(Warning_(
            code="MC_SAMPLES_DISCARDED", severity=Severity.WARNING,
            params={"n_valid": n_valid, "n_requested": n}))

    c = uncertainty.confidence
    return UncertaintyResult(
        lambda0=_distribution(np.asarray(lambda0), c),
        delta0=_distribution(np.asarray(delta0), c),
        tc=_distribution(np.asarray(tc), c),
        coupling_ratio=_distribution(np.asarray(ratio), c),
        n_valid=n_valid,
        n_requested=n,
        settings=uncertainty,
        warnings=warnings,
    )


def replace_kappa(settings: AnalysisSettings, kappa: float) -> AnalysisSettings:
    """A copy of `settings` with a different fixed kappa.

    `AnalysisSettings` is frozen, which is what makes it safe to share across
    draws; this is the one field a draw needs to vary.
    """
    import dataclasses

    return dataclasses.replace(settings, kappa_fixed=kappa)
