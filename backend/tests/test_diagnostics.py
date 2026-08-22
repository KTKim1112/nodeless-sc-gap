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
