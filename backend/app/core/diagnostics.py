"""Judgements about whether a result can be trusted.

Every threshold here is stated in specs/001-jc-to-gap/research.md R10 rather
than invented in code, so that the numbers can be argued about in review.

The output is a list of `Warning_` objects carrying codes and parameters, never
sentences (constitution IV). Constitution VI is the reason this module exists at
all: equation (1) returns a number for input that violates every one of its
assumptions, and the user cannot see that from the number.
"""

from __future__ import annotations

import math

import numpy as np

from .constants import (
    BCS_RATIO,
    KAPPA_STRONG_TYPE_II,
    KAPPA_TYPE_II_BOUNDARY,
)
from .fitting import parameters_at_limit
from .types import (
    AnalysisSettings,
    CoherenceSource,
    CouplingRegime,
    DiagnosticReport,
    FitResult,
    GapModel,
    LambdaTable,
    Severity,
    Warning_,
)

#: Reduced temperature of the coldest measured point, above which Delta(0) is
#: increasingly an extrapolation rather than a measurement (research R10).
LOW_T_WEAK = 0.3
LOW_T_INSUFFICIENT = 0.5

#: A preferred gap model is declared only when the Akaike information criterion
#: separates the two by at least this much -- the conventional point at which the
#: weaker model has essentially no support (research R10, equation 16).
#:
#: A fixed ratio of reduced chi-squared was used first and replaced on
#: measurement: a ratio ignores how much data produced it, so collecting more
#: points did not improve the verdict and above 2 % scatter actually degraded it.
DELTA_AIC_THRESHOLD = 10.0

#: The thin-film relation of research R1 was derived for a conductor whose
#: transverse dimension is not large compared with lambda.
THIN_FILM_THICKNESS_FACTOR = 2.0

#: Coupling regime boundaries on 2 Delta(0) / (kB Tc).
_REGIME_EDGES = ((3.3, CouplingRegime.BELOW_BCS),
                 (3.8, CouplingRegime.WEAK_COUPLING_BCS),
                 (5.0, CouplingRegime.MODERATELY_STRONG))

#: The largest standard error on the coupling ratio at which a regime can still
#: be named: half the width of the narrowest band above, 3.3 to 3.8. Wider than
#: that and the one-sigma interval does not fit inside any band (FR-023a).
#:
#: Derived from the bands rather than tuned, and then measured: over 1200 fits
#: it flags 91 % of those whose ratio is more than 10 % wrong, and fires on none
#: of the 120 fits whose data reach 0.9 Tc (research R10).
RATIO_SIGMA_LIMIT = 0.25

#: The fraction of Tc the data must reach for the gap to be determined, however
#: small the reported uncertainty. Added because the rule above has a blind spot
#: exactly where a user following the obvious advice would land: with Tc held
#: fixed and data stopping at 0.2 Tc, the linearised error bar came out small
#: and the ratio came out 19 % low and was labelled below-BCS.
#:
#: Not circular when Tc is fixed, since it is then the user's number; and when
#: Tc is free and resting on its ceiling this is exactly 1/3, so it fires there
#: too. Measured: for fixed-Tc fits it raises the share of bad fits caught from
#: 80 % to 99.5 %, and it adds no firing at all on data reaching 0.6 Tc or more.
#: 0.35 and 0.40 score identically; 0.50 doubles the firing on sound data
#: (research R10).
RATIO_REACH_MIN = 0.40


def compare_models(
    chi2_clean: float | None, chi2_dirty: float | None, n_points: int
) -> tuple[GapModel | None, float | None, float | None]:
    """Decide whether the data prefer one gap model. Research R10, FR-020.

    Returns (preferred model or None, Delta_AIC, Akaike weight). The model is
    None when the evidence does not clear the threshold, which is the honest
    answer far more often than one might hope: with a few per cent of scatter on
    `Jc` the two models are simply not separable.
    """
    if chi2_clean is None or chi2_dirty is None:
        return None, None, None

    lo = min(chi2_clean, chi2_dirty)
    hi = max(chi2_clean, chi2_dirty)
    if lo <= 0.0 or hi <= 0.0:
        # A perfect fit to synthetic data. The comparison is meaningless rather
        # than infinitely decisive, so it is declined.
        return None, None, None

    # Equation (16). Both models have the same number of free parameters, so the
    # penalty terms of the AIC cancel and only the likelihood ratio survives.
    delta_aic = float(n_points * math.log(hi / lo))
    weight = 1.0 / (1.0 + math.exp(-0.5 * delta_aic))          # equation (17)

    if delta_aic < DELTA_AIC_THRESHOLD:
        return None, delta_aic, weight
    preferred = GapModel.CLEAN if chi2_clean < chi2_dirty else GapModel.DIRTY
    return preferred, delta_aic, weight


def classify_coupling(ratio: float) -> CouplingRegime:
    for edge, regime in _REGIME_EDGES:
        if ratio < edge:
            return regime
    return CouplingRegime.STRONG_COUPLING


def build_report(
    table: LambdaTable,
    fit: FitResult,
    settings: AnalysisSettings,
    chi2_clean: float | None = None,
    chi2_dirty: float | None = None,
) -> DiagnosticReport:
    warnings: list[Warning_] = []

    # Unconditional. The analysis is only meaningful for self-field transport
    # data from a weak-link-free sample, and nothing in the numbers can reveal
    # a violation, so it is stated every time (FR-024).
    warnings.append(Warning_(code="SELF_FIELD_TRANSPORT_REQUIRED", severity=Severity.INFO))

    if settings.coherence_source is CoherenceSource.FROM_HC2:
        warnings.append(Warning_(code="ISOTROPIC_GL_ASSUMED", severity=Severity.INFO))

    # --- Ginzburg-Landau parameter ---
    kappa_min = float(np.min(table.kappa))
    kappa_max = float(np.max(table.kappa))
    if kappa_min <= KAPPA_TYPE_II_BOUNDARY:
        # Not a warning but an error; raised upstream. Kept here as a guard so
        # a future caller that skips validation still surfaces it.
        warnings.append(Warning_(
            code="KAPPA_NEAR_TYPE_I_BOUNDARY", severity=Severity.ERROR,
            params={"kappa_min": kappa_min,
                    "temperature_K": float(table.temperature_K[int(np.argmin(table.kappa))]),
                    "boundary": KAPPA_TYPE_II_BOUNDARY}))
    elif kappa_min < KAPPA_STRONG_TYPE_II:
        warnings.append(Warning_(
            code="KAPPA_NEAR_TYPE_I_BOUNDARY", severity=Severity.WARNING,
            params={"kappa_min": kappa_min,
                    "temperature_K": float(table.temperature_K[int(np.argmin(table.kappa))]),
                    "threshold": KAPPA_STRONG_TYPE_II}))

    # --- low-temperature coverage ---
    t_min_over_tc = float(np.min(table.temperature_K) / fit.tc.value)
    if t_min_over_tc > LOW_T_INSUFFICIENT:
        warnings.append(Warning_(
            code="LOW_T_COVERAGE_INSUFFICIENT", severity=Severity.WARNING,
            params={"t_min_over_tc": t_min_over_tc, "threshold": LOW_T_INSUFFICIENT}))
    elif t_min_over_tc > LOW_T_WEAK:
        warnings.append(Warning_(
            code="LOW_T_COVERAGE_WEAK", severity=Severity.WARNING,
            params={"t_min_over_tc": t_min_over_tc, "threshold": LOW_T_WEAK}))

    # --- thin-film regime ---
    if settings.film_thickness_m is not None:
        limit = THIN_FILM_THICKNESS_FACTOR * fit.lambda0.value
        if settings.film_thickness_m > limit:
            warnings.append(Warning_(
                code="THIN_FILM_ASSUMPTION_STRAINED", severity=Severity.WARNING,
                params={"thickness_m": float(settings.film_thickness_m),
                        "lambda0_m": float(fit.lambda0.value),
                        "limit_m": float(limit)}))

    # --- clean versus dirty ---
    preferred, delta_aic, weight = compare_models(
        chi2_clean, chi2_dirty, fit.n_points
    )
    if delta_aic is not None and preferred is None:
        warnings.append(Warning_(
            code="MODELS_INDISTINGUISHABLE", severity=Severity.INFO,
            params={"chi2_clean": float(chi2_clean), "chi2_dirty": float(chi2_dirty),
                    "delta_aic": delta_aic, "threshold": DELTA_AIC_THRESHOLD}))

    # --- missing standard errors ---
    for name, parameter in (("lambda0", fit.lambda0), ("delta0", fit.delta0),
                            ("tc", fit.tc), ("coupling_ratio", fit.coupling_ratio)):
        if parameter.stderr is None and not parameter.fixed:
            warnings.append(Warning_(
                code="STDERR_UNAVAILABLE", severity=Severity.WARNING,
                params={"parameter": name}))

    # --- is the coupling ratio determined at all? (FR-023a) ---
    #
    # After the low-temperature check, which asks the opposite question. Data
    # that stop below about a third of Tc carry almost no information about the
    # gap; the fit still returns one, and without this the regime below would be
    # named from it. lambda0 is unaffected and nothing here touches it.
    t_max = float(np.max(table.temperature_K))
    at_limit = parameters_at_limit(fit, t_max)
    ratio_sigma = fit.coupling_ratio.stderr
    reach = t_max / fit.tc.value
    too_uncertain = ratio_sigma is None or ratio_sigma > RATIO_SIGMA_LIMIT
    too_short = reach < RATIO_REACH_MIN
    ratio_determined = not (at_limit or too_uncertain or too_short)
    if not ratio_determined:
        # Every reason is reported rather than the first one found. They call
        # for different things -- a parameter on a bound says the fit was
        # stopped, a short reach says measure nearer Tc -- and more than one
        # usually holds.
        warnings.append(Warning_(
            code="COUPLING_RATIO_NOT_DETERMINED", severity=Severity.WARNING,
            params={"coupling_ratio": float(fit.coupling_ratio.value),
                    "coupling_ratio_stderr": (None if ratio_sigma is None
                                              else float(ratio_sigma)),
                    "sigma_limit": RATIO_SIGMA_LIMIT,
                    "too_uncertain": too_uncertain,
                    "reach": reach,
                    "reach_min": RATIO_REACH_MIN,
                    "too_short": too_short,
                    "at_limit": at_limit,
                    "t_max_K": t_max,
                    "tc_K": float(fit.tc.value),
                    "tc_fixed": bool(fit.tc.fixed)}))

    return DiagnosticReport(
        chi2_reduced=fit.chi2_reduced,
        coupling_ratio=fit.coupling_ratio.value,
        coupling_regime=(classify_coupling(fit.coupling_ratio.value)
                         if ratio_determined else CouplingRegime.UNDETERMINED),
        bcs_ratio_reference=BCS_RATIO,
        t_min_over_tc=t_min_over_tc,
        kappa_min=kappa_min,
        kappa_max=kappa_max,
        warnings=warnings,
        chi2_clean=chi2_clean,
        chi2_dirty=chi2_dirty,
        preferred_model=preferred,
        delta_aic=delta_aic,
        preferred_model_weight=weight,
    )
