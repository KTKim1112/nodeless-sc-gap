"""Diagnostics. Research R10, FR-019 to FR-024.

Each threshold is checked just inside and just outside its boundary, because a
threshold that fires at the wrong place is worse than none: it teaches the user
to ignore the warnings.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core import lambda_solver as ls
from app.core import pipeline
from app.core.constants import BCS_RATIO, KB
from app.core.diagnostics import (
    LOW_T_INSUFFICIENT,
    LOW_T_WEAK,
    build_report,
    classify_coupling,
)
from app.core.types import (
    AnalysisSettings,
    CoherenceSource,
    CouplingRegime,
    GapModel,
    Severity,
)
from app.core.validation import build_dataset

from .conftest import TRUE_LAMBDA0, TRUE_TC, synthesise


def _codes(report) -> set[str]:
    return {w.code for w in report.warnings}


def _analyse(**settings_kwargs):
    data = synthesise(GapModel.CLEAN, **{
        k: v for k, v in settings_kwargs.pop("synth", {}).items()
    })
    dataset = build_dataset(data["temperature_K"], data["jc"], xi=data["xi"])
    settings = AnalysisSettings(
        coherence_source=CoherenceSource.EXPLICIT_XI, **settings_kwargs
    )
    return pipeline.run_analysis(dataset, settings)


# --- coupling regime ---------------------------------------------------------

@pytest.mark.parametrize("ratio,expected", [
    (3.29, CouplingRegime.BELOW_BCS),
    (3.30, CouplingRegime.WEAK_COUPLING_BCS),
    (BCS_RATIO, CouplingRegime.WEAK_COUPLING_BCS),
    (3.79, CouplingRegime.WEAK_COUPLING_BCS),
    (3.80, CouplingRegime.MODERATELY_STRONG),
    (4.99, CouplingRegime.MODERATELY_STRONG),
    (5.00, CouplingRegime.STRONG_COUPLING),
    (9.00, CouplingRegime.STRONG_COUPLING),
])
def test_coupling_regime_boundaries(ratio, expected):
    assert classify_coupling(ratio) is expected


def test_bcs_reference_is_supplied_so_the_frontend_never_hard_codes_it():
    result = _analyse()
    assert result.diagnostics.bcs_ratio_reference == BCS_RATIO


# --- unconditional statements ------------------------------------------------

def test_self_field_requirement_is_always_stated():
    """FR-024. Nothing in the numbers can reveal that the input was not
    self-field transport data, so it is said every time."""
    result = _analyse()
    assert "SELF_FIELD_TRANSPORT_REQUIRED" in _codes(result.diagnostics)


def test_isotropic_assumption_is_stated_only_when_hc2_is_used(
    dataset_hc2, settings_hc2, dataset_xi, settings_xi
):
    from_hc2 = pipeline.run_analysis(dataset_hc2, settings_hc2)
    from_xi = pipeline.run_analysis(dataset_xi, settings_xi)
    assert "ISOTROPIC_GL_ASSUMED" in _codes(from_hc2.diagnostics)
    assert "ISOTROPIC_GL_ASSUMED" not in _codes(from_xi.diagnostics)


# --- low-temperature coverage ------------------------------------------------

def test_ample_low_temperature_data_raises_no_warning():
    result = _analyse()
    assert result.diagnostics.t_min_over_tc < LOW_T_WEAK
    assert "LOW_T_COVERAGE_WEAK" not in _codes(result.diagnostics)
    assert "LOW_T_COVERAGE_INSUFFICIENT" not in _codes(result.diagnostics)


def test_thin_low_temperature_coverage_warns():
    """AS-8: the fit still runs, but Delta(0) is weakly constrained."""
    data = synthesise(GapModel.CLEAN, t_min=3.5, t_max=9.0)   # t_min/Tc = 0.35
    dataset = build_dataset(data["temperature_K"], data["jc"], xi=data["xi"])
    result = pipeline.run_analysis(
        dataset, AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)
    )
    assert LOW_T_WEAK < result.diagnostics.t_min_over_tc <= LOW_T_INSUFFICIENT
    assert "LOW_T_COVERAGE_WEAK" in _codes(result.diagnostics)
    assert result.fit.converged


def test_absent_low_temperature_coverage_warns_more_strongly():
    data = synthesise(GapModel.CLEAN, t_min=6.0, t_max=9.5)   # t_min/Tc = 0.60
    dataset = build_dataset(data["temperature_K"], data["jc"], xi=data["xi"])
    result = pipeline.run_analysis(
        dataset, AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)
    )
    assert result.diagnostics.t_min_over_tc > LOW_T_INSUFFICIENT
    assert "LOW_T_COVERAGE_INSUFFICIENT" in _codes(result.diagnostics)
    assert "LOW_T_COVERAGE_WEAK" not in _codes(result.diagnostics)


# --- whether the coupling ratio is determined at all (FR-023a) ---------------
#
# The other end of the temperature range from the tests above. Research R10
# measures the failure: data stopping below about a third of Tc still produce a
# gap, typically wrong by a factor of three, and the regime was named from it.

def _low_temperature_only(frac: float, *, tc_fixed: float | None = None,
                          scatter: float = 0.01, seed: int = 1):
    """Jc(T) measured only up to `frac * Tc`, as from a liquid-helium dip.

    With scatter, because that is the realistic case and because noiseless
    data hide the failure: with no scatter the residual variance is zero, the
    standard errors come out zero, and every fit looks perfectly determined.
    """
    t = np.linspace(0.05 * TRUE_TC, frac * TRUE_TC, 20)
    data = synthesise(GapModel.CLEAN, n_points=20, t_min=t[0], t_max=t[-1])
    jc = data["jc"] * np.random.default_rng(seed).lognormal(0.0, scatter, t.size)
    dataset = build_dataset(data["temperature_K"], jc, xi=data["xi"])
    return pipeline.run_analysis(dataset, AnalysisSettings(
        coherence_source=CoherenceSource.EXPLICIT_XI, tc_fixed_K=tc_fixed))


def test_data_that_stop_low_do_not_determine_the_coupling_ratio():
    result = _low_temperature_only(0.2)
    d = result.diagnostics
    assert "COUPLING_RATIO_NOT_DETERMINED" in _codes(d)
    # FR-023a: no regime is named. Before this, it was named from the central
    # value alone and a BCS superconductor came out strongly coupled.
    assert d.coupling_regime is CouplingRegime.UNDETERMINED
    # And the fit is not refused: lambda(0) is set by the coldest points and
    # stays right, which is worth keeping.
    assert result.fit.lambda0.value == pytest.approx(TRUE_LAMBDA0, rel=0.01)


def test_fixing_tc_does_not_rescue_the_gap():
    """The obvious remedy, pinned as not working so that no one advises it.

    Research R10: with Tc held at the true value, data to 0.2 Tc still give a
    coupling ratio wrong by about a factor of three. What is missing is the
    curvature of rho_s(T), which lives above a third of Tc; knowing where the
    curve ends does not supply its shape.
    """
    result = _low_temperature_only(0.2, tc_fixed=TRUE_TC)
    assert result.fit.tc.fixed
    assert "COUPLING_RATIO_NOT_DETERMINED" in _codes(result.diagnostics)
    assert result.diagnostics.coupling_regime is CouplingRegime.UNDETERMINED


def test_data_that_reach_near_tc_determine_it():
    result = _low_temperature_only(0.9)
    assert "COUPLING_RATIO_NOT_DETERMINED" not in _codes(result.diagnostics)
    assert result.diagnostics.coupling_regime is CouplingRegime.WEAK_COUPLING_BCS


def test_the_ratio_threshold_is_where_the_bands_say(dataset_xi, settings_xi):
    """Checked just inside and just outside, as every threshold here is.

    The limit is half the width of the narrowest regime band. The fit itself is
    good; only the reported uncertainty is changed, so what is exercised is the
    rule and nothing else.
    """
    import dataclasses

    from app.core.diagnostics import RATIO_SIGMA_LIMIT
    from app.core.fitting import fit_route_a
    from app.core.types import FittedParameter

    table = ls.build_lambda_table(dataset_xi, settings_xi)
    fit = fit_route_a(table, settings_xi)

    def with_sigma(sigma):
        return dataclasses.replace(fit, coupling_ratio=FittedParameter(
            value=fit.coupling_ratio.value, stderr=sigma))

    inside = build_report(table, with_sigma(RATIO_SIGMA_LIMIT * 0.99), settings_xi)
    outside = build_report(table, with_sigma(RATIO_SIGMA_LIMIT * 1.01), settings_xi)
    missing = build_report(table, with_sigma(None), settings_xi)

    assert "COUPLING_RATIO_NOT_DETERMINED" not in _codes(inside)
    assert inside.coupling_regime is CouplingRegime.WEAK_COUPLING_BCS
    for report in (outside, missing):
        assert "COUPLING_RATIO_NOT_DETERMINED" in _codes(report)
        assert report.coupling_regime is CouplingRegime.UNDETERMINED


def test_the_reach_threshold_catches_what_the_error_bar_misses(dataset_xi, settings_xi):
    """Just inside and just outside the reach limit, with a tiny error bar.

    This is the blind spot the reach rule exists for: the linearised
    uncertainty can come out small while the data stop far below Tc, and then
    only how far the data reach can say that the ratio is not determined. The
    error bar is held small throughout so that reach is the only thing varied.
    """
    import dataclasses

    from app.core.diagnostics import RATIO_REACH_MIN
    from app.core.fitting import fit_route_a
    from app.core.types import FittedParameter

    table = ls.build_lambda_table(dataset_xi, settings_xi)
    fit = fit_route_a(table, settings_xi)
    t_max = float(np.max(table.temperature_K))

    def reaching(reach):
        tc = t_max / reach
        return dataclasses.replace(
            fit,
            tc=FittedParameter(value=tc, stderr=None, fixed=True),
            delta0=FittedParameter(value=1.764 * KB * tc, stderr=1e-25),
            coupling_ratio=FittedParameter(value=3.528, stderr=0.01))

    inside = build_report(table, reaching(RATIO_REACH_MIN * 1.01), settings_xi)
    outside = build_report(table, reaching(RATIO_REACH_MIN * 0.99), settings_xi)

    assert "COUPLING_RATIO_NOT_DETERMINED" not in _codes(inside)
    assert "COUPLING_RATIO_NOT_DETERMINED" in _codes(outside)
    warning = next(w for w in outside.warnings if w.code == "COUPLING_RATIO_NOT_DETERMINED")
    assert warning.params["too_short"] is True
    assert warning.params["too_uncertain"] is False
    assert warning.params["at_limit"] == []


def test_a_parameter_on_a_bound_is_named(dataset_xi, settings_xi):
    """A value resting on a limit of the fit is the bound's, not the data's.

    The warning names which parameter, because the remedy differs: Tc on its
    ceiling says the data stop far below Tc, alpha on its ceiling says the
    fitter found no gap it could distinguish from an arbitrarily large one.
    """
    import dataclasses

    from app.core.fitting import _ALPHA_BOUNDS, _TC_UPPER_FACTOR, parameters_at_limit
    from app.core.fitting import fit_route_a
    from app.core.types import FittedParameter

    table = ls.build_lambda_table(dataset_xi, settings_xi)
    fit = fit_route_a(table, settings_xi)
    t_max = float(np.max(table.temperature_K))
    assert parameters_at_limit(fit, t_max) == []

    capped_tc = _TC_UPPER_FACTOR * t_max
    on_tc = dataclasses.replace(
        fit,
        tc=FittedParameter(value=capped_tc, stderr=1.0),
        delta0=FittedParameter(value=1.764 * KB * capped_tc, stderr=1e-23))
    assert parameters_at_limit(on_tc, t_max) == ["tc"]

    on_alpha = dataclasses.replace(
        fit, delta0=FittedParameter(value=_ALPHA_BOUNDS[1] * KB * fit.tc.value,
                                    stderr=1e-23))
    assert parameters_at_limit(on_alpha, t_max) == ["alpha"]

    report = build_report(table, on_alpha, settings_xi)
    warning = next(w for w in report.warnings if w.code == "COUPLING_RATIO_NOT_DETERMINED")
    assert warning.params["at_limit"] == ["alpha"]


def test_a_fixed_tc_is_never_reported_as_resting_on_a_bound(dataset_xi):
    """Held fixed, Tc is the user's number and was never searched for."""
    import dataclasses

    from app.core.fitting import _TC_UPPER_FACTOR, fit_route_a, parameters_at_limit
    from app.core.types import FittedParameter

    settings = AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI,
                                tc_fixed_K=TRUE_TC)
    table = ls.build_lambda_table(dataset_xi, settings)
    fit = fit_route_a(table, settings)
    t_max = float(np.max(table.temperature_K))
    coincident = dataclasses.replace(fit, tc=FittedParameter(
        value=_TC_UPPER_FACTOR * t_max, stderr=None, fixed=True))
    assert "tc" not in parameters_at_limit(coincident, t_max)


# --- thin-film regime --------------------------------------------------------

def test_no_thin_film_warning_without_a_thickness():
    assert "THIN_FILM_ASSUMPTION_STRAINED" not in _codes(_analyse().diagnostics)


def test_thickness_within_the_regime_is_accepted():
    result = _analyse(film_thickness_m=1.5 * TRUE_LAMBDA0)
    assert "THIN_FILM_ASSUMPTION_STRAINED" not in _codes(result.diagnostics)


def test_thickness_beyond_twice_lambda_warns():
    result = _analyse(film_thickness_m=10.0 * TRUE_LAMBDA0)
    codes = _codes(result.diagnostics)
    assert "THIN_FILM_ASSUMPTION_STRAINED" in codes
    warning = next(w for w in result.diagnostics.warnings
                   if w.code == "THIN_FILM_ASSUMPTION_STRAINED")
    assert warning.severity is Severity.WARNING
    assert set(warning.params) == {"thickness_m", "lambda0_m", "limit_m"}


# --- Ginzburg-Landau parameter -----------------------------------------------

def test_strong_type_ii_data_raises_no_kappa_warning():
    result = _analyse()
    assert result.diagnostics.kappa_min == pytest.approx(40.0, rel=1e-6)
    assert "KAPPA_NEAR_TYPE_I_BOUNDARY" not in _codes(result.diagnostics)


def test_kappa_near_the_boundary_warns():
    """A fixed kappa of 2 is a legitimate type-II value, but the large-kappa
    form of Hc1 inside equation (1) is a poor approximation there."""
    data = synthesise(GapModel.CLEAN)
    dataset = build_dataset(data["temperature_K"], data["jc"])
    result = pipeline.run_analysis(
        dataset,
        AnalysisSettings(coherence_source=CoherenceSource.FIXED_KAPPA, kappa_fixed=2.0),
    )
    assert "KAPPA_NEAR_TYPE_I_BOUNDARY" in _codes(result.diagnostics)


# --- clean versus dirty ------------------------------------------------------

def test_both_models_are_fitted_and_the_right_one_preferred():
    """FR-020."""
    result = _analyse()
    d = result.diagnostics
    assert d.chi2_clean is not None and d.chi2_dirty is not None
    assert d.preferred_model is GapModel.CLEAN
    assert d.chi2_clean < d.chi2_dirty


def test_dirty_data_prefers_the_dirty_model():
    data = synthesise(GapModel.DIRTY)
    dataset = build_dataset(data["temperature_K"], data["jc"], xi=data["xi"])
    result = pipeline.run_analysis(
        dataset,
        AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI,
                         gap_model=GapModel.DIRTY),
    )
    assert result.diagnostics.preferred_model is GapModel.DIRTY


def test_models_are_declared_indistinguishable_when_they_are():
    """When neither fit is meaningfully better, saying so is the honest
    answer, and is what MODELS_INDISTINGUISHABLE exists for."""
    from app.core.diagnostics import build_report

    data = synthesise(GapModel.CLEAN)
    dataset = build_dataset(data["temperature_K"], data["jc"], xi=data["xi"])
    settings = AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)
    table = ls.build_lambda_table(dataset, settings)
    from app.core.fitting import fit_route_a

    fit = fit_route_a(table, settings)
    report = build_report(table, fit, settings, chi2_clean=1.0, chi2_dirty=1.05)
    assert report.preferred_model is None
    assert "MODELS_INDISTINGUISHABLE" in _codes(report)

    decisive = build_report(table, fit, settings, chi2_clean=1.0, chi2_dirty=10.0)
    assert decisive.preferred_model is GapModel.CLEAN
    assert "MODELS_INDISTINGUISHABLE" not in _codes(decisive)


# --- shape of the report -----------------------------------------------------

def test_report_carries_the_numbers_behind_every_judgement():
    result = _analyse()
    d = result.diagnostics
    assert d.kappa_min <= d.kappa_max
    assert 0.0 < d.t_min_over_tc < 1.0
    assert d.chi2_reduced >= 0.0
    assert d.coupling_ratio == pytest.approx(
        2.0 * result.fit.delta0.value / (KB * result.fit.tc.value)
    )
    for warning in d.warnings:
        assert isinstance(warning.code, str) and warning.code.isupper()
        assert warning.code.isascii()          # constitution IV
        assert isinstance(warning.params, dict)
