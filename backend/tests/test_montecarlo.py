"""Uncertainty propagation. Research R8, FR-015 to FR-018, FR-029.

Sample counts here are kept small so the suite stays fast. Where a statistical
quantity is asserted, the tolerance is derived from equation (14),
sigma(std)/std = 1/sqrt(2(M-1)), rather than guessed.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core import lambda_solver as ls
from app.core import pipeline
from app.core.errors import MonteCarloTooManyFailures
from app.core.montecarlo import lognormal_factors, propagate
from app.core.types import (
    AnalysisSettings,
    CoherenceSource,
    CorrelationMode,
    UncertaintySettings,
)
from app.core.validation import build_dataset

from .conftest import TRUE_KAPPA, synthesise


def _fixed_kappa_case():
    data = synthesise()
    dataset = build_dataset(data["temperature_K"], data["jc"])
    settings = AnalysisSettings(
        coherence_source=CoherenceSource.FIXED_KAPPA, kappa_fixed=TRUE_KAPPA
    )
    return dataset, settings


# --- the sampling distribution -----------------------------------------------

@pytest.mark.parametrize("cv", [0.01, 0.05, 0.2, 0.5])
def test_lognormal_draws_reproduce_the_requested_moments(cv):
    """Research R8.2, equations (7) and (8). If these are wrong, every error
    bar in the application is wrong by the same factor."""
    rng = np.random.default_rng(0)
    draws = lognormal_factors(cv, 400_000, rng)
    assert np.mean(draws) == pytest.approx(1.0, abs=4e-3)
    assert np.std(draws, ddof=1) == pytest.approx(cv, rel=0.02)
    assert np.all(draws > 0.0)      # the reason for log-normal over Gaussian


def test_zero_sigma_gives_no_perturbation():
    rng = np.random.default_rng(0)
    assert np.all(lognormal_factors(0.0, 10, rng) == 1.0)


# --- reproducibility ---------------------------------------------------------

def test_same_seed_gives_identical_output():
    """Constitution VII. An error bar that moves between runs cannot be cited."""
    dataset, settings = _fixed_kappa_case()
    unc = UncertaintySettings(jc_rel_sigma=0.05, n_samples=150, seed=42)
    a = propagate(dataset, settings, unc)
    b = propagate(dataset, settings, unc)
    for name in ("lambda0", "delta0", "tc", "coupling_ratio"):
        first, second = getattr(a, name), getattr(b, name)
        assert first == second


def test_a_different_seed_gives_a_different_sample():
    """Asserted on lambda0, not Delta0: under SYSTEMATIC with a fixed kappa,
    Delta0 is exactly invariant and would be identical for every seed. That is
    the R8.3 result, not a failure of randomness."""
    dataset, settings = _fixed_kappa_case()
    make = lambda seed: propagate(  # noqa: E731
        dataset, settings,
        UncertaintySettings(jc_rel_sigma=0.05, n_samples=150, seed=seed),
    )
    assert make(42).lambda0.mean != make(43).lambda0.mean


def test_settings_are_echoed_back():
    dataset, settings = _fixed_kappa_case()
    unc = UncertaintySettings(
        jc_rel_sigma=0.05, n_samples=150, seed=7,
        correlation_mode=CorrelationMode.INDEPENDENT,
    )
    result = propagate(dataset, settings, unc)
    assert result.settings == unc
    assert result.n_requested == 150
    assert result.n_valid <= 150
    assert any(w.code == "CROSS_QUANTITY_CORRELATION_IGNORED" for w in result.warnings)


# --- the correlation mode consequence ----------------------------------------

def test_systematic_jc_error_moves_lambda_but_not_the_gap():
    """Research R8.3, and the reason FR-029 exists.

    Under a fixed kappa, lambda(T) = C Jc(T)^(-1/3). Scaling every Jc by one
    common factor scales every lambda by the same factor, so the normalised
    superfluid density lambda0^2/lambda(T)^2 is untouched and the parameters
    that depend only on its shape -- Delta0 and Tc -- cannot move at all.

    Reporting a geometry calibration error as an uncertainty on Delta(0) would
    simply be wrong, and this is the mechanism that prevents it.
    """
    dataset, settings = _fixed_kappa_case()
    result = propagate(
        dataset, settings,
        UncertaintySettings(jc_rel_sigma=0.05, n_samples=200, seed=1,
                            correlation_mode=CorrelationMode.SYSTEMATIC),
    )
    assert result.delta0.std / result.delta0.mean < 1e-12
    assert result.tc.std / result.tc.mean < 1e-12
    assert result.lambda0.std / result.lambda0.mean > 1e-2


def test_independent_jc_error_moves_all_three():
    dataset, settings = _fixed_kappa_case()
    result = propagate(
        dataset, settings,
        UncertaintySettings(jc_rel_sigma=0.05, n_samples=200, seed=1,
                            correlation_mode=CorrelationMode.INDEPENDENT),
    )
    assert result.delta0.std / result.delta0.mean > 1e-3
    assert result.tc.std / result.tc.mean > 1e-3
    assert result.lambda0.std / result.lambda0.mean > 1e-3


def test_systematic_lambda_spread_matches_the_closed_form():
    """Under a fixed kappa, equation (6) gives lambda ~ Jc^(-1/3) exactly, so
    the perturbation is a log-normal raised to the power -1/3 and its relative
    spread is available in closed form. Research R8.4, equation (12)."""
    dataset, settings = _fixed_kappa_case()
    cv = 0.05
    n = 3000
    result = propagate(
        dataset, settings,
        UncertaintySettings(jc_rel_sigma=cv, n_samples=n, seed=5,
                            correlation_mode=CorrelationMode.SYSTEMATIC),
    )
    sigma_ln = np.sqrt(np.log1p(cv**2))
    predicted = np.sqrt(np.expm1((sigma_ln / 3.0) ** 2))
    observed = result.lambda0.std / result.lambda0.mean
    tolerance = 5.0 / np.sqrt(2.0 * (n - 1))          # 5 sigma of equation (14)
    assert observed == pytest.approx(predicted, rel=tolerance)


def test_independent_gap_uncertainty_falls_as_one_over_root_n():
    """Research R8.3: point-to-point scatter averages down with more points,
    which is precisely what a common calibration error does not do."""
    settings = AnalysisSettings(
        coherence_source=CoherenceSource.FIXED_KAPPA, kappa_fixed=TRUE_KAPPA
    )
    scaled = []
    for n_points in (10, 40):
        data = synthesise(n_points=n_points)
        dataset = build_dataset(data["temperature_K"], data["jc"])
        result = propagate(
            dataset, settings,
            UncertaintySettings(jc_rel_sigma=0.05, n_samples=300, seed=3,
                                correlation_mode=CorrelationMode.INDEPENDENT),
        )
        scaled.append(result.delta0.std / result.delta0.mean * np.sqrt(n_points))
    assert scaled[1] == pytest.approx(scaled[0], rel=0.35)


def test_the_analytic_sensitivity_of_lambda_to_jc_and_hc2():
    """Research R8.4, equations (9) and (11).

    With kappa = 40 the closed form predicts a 1.815 % spread in lambda from
    5 % on Jc and 3 % on Hc2, of which the Hc2 term contributes only 0.13 %.
    This is the concrete number behind the claim in R11 that the upper critical
    field barely matters to the extracted penetration depth.
    """
    data = synthesise()
    jc0 = float(data["jc"][0])
    hc2_0 = float(data["hc2"][0])
    rng = np.random.default_rng(1)
    n = 4000

    samples = np.empty(n)
    for i in range(n):
        jc = jc0 * float(lognormal_factors(0.05, 1, rng)[0])
        xi = ls.xi_from_hc2(hc2_0 * float(lognormal_factors(0.03, 1, rng)[0]))[0]
        samples[i] = ls.solve_lambda(jc, float(xi))

    observed = samples.std(ddof=1) / samples.mean()
    length = np.log(TRUE_KAPPA) + 0.5
    predicted = np.hypot(
        (length / (3.0 * length - 1.0)) * 0.05,          # equation (9)
        (1.0 / (2.0 * (3.0 * length - 1.0))) * 0.03,     # equation (11)
    )
    assert predicted == pytest.approx(0.01815, rel=1e-3)
    assert observed == pytest.approx(predicted, rel=5.0 / np.sqrt(2.0 * (n - 1)))


# --- intervals and failure ---------------------------------------------------

def test_wider_input_uncertainty_gives_a_wider_interval():
    dataset, settings = _fixed_kappa_case()
    widths = []
    for cv in (0.02, 0.10):
        result = propagate(
            dataset, settings,
            UncertaintySettings(jc_rel_sigma=cv, n_samples=300, seed=9),
        )
        widths.append(result.lambda0.ci_high - result.lambda0.ci_low)
    assert widths[1] > 3.0 * widths[0]


def test_interval_brackets_the_mean_and_widens_with_confidence():
    dataset, settings = _fixed_kappa_case()
    narrow = propagate(dataset, settings, UncertaintySettings(
        jc_rel_sigma=0.05, n_samples=600, seed=4, confidence=0.6827))
    wide = propagate(dataset, settings, UncertaintySettings(
        jc_rel_sigma=0.05, n_samples=600, seed=4, confidence=0.95))
    assert narrow.lambda0.ci_low < narrow.lambda0.mean < narrow.lambda0.ci_high
    assert wide.lambda0.ci_low < narrow.lambda0.ci_low
    assert wide.lambda0.ci_high > narrow.lambda0.ci_high


def test_too_many_failed_draws_is_reported_rather_than_papered_over():
    """Failed draws are systematically the extreme ones, so a surviving
    minority would give a misleadingly narrow interval."""
    data = synthesise()
    # An xi far too large for these Jc: most draws land above the ceiling of
    # equation (1) and have no admissible root.
    dataset = build_dataset(data["temperature_K"], data["jc"], xi=data["xi"] * 60.0)
    settings = AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)
    with pytest.raises(MonteCarloTooManyFailures) as excinfo:
        propagate(dataset, settings,
                  UncertaintySettings(jc_rel_sigma=0.3, n_samples=200, seed=2))
    params = excinfo.value.params
    assert params["n_requested"] == 200
    assert params["n_valid"] < params["n_required"]


def test_progress_is_reported_and_reaches_one():
    """FR-018."""
    dataset, settings = _fixed_kappa_case()
    seen: list[float] = []
    propagate(dataset, settings,
              UncertaintySettings(jc_rel_sigma=0.05, n_samples=200, seed=1),
              progress=seen.append)
    assert seen
    assert seen == sorted(seen)
    assert 0.0 < seen[0] <= 1.0
    assert seen[-1] == 1.0


# --- and through the pipeline ------------------------------------------------

def test_pipeline_skips_the_computation_when_no_uncertainty_was_stated():
    dataset, settings = _fixed_kappa_case()
    assert pipeline.run_analysis(dataset, settings).uncertainty is None
    assert pipeline.run_analysis(
        dataset, settings, UncertaintySettings(n_samples=100)
    ).uncertainty is None


def test_pipeline_attaches_the_uncertainty_when_it_was():
    dataset, settings = _fixed_kappa_case()
    result = pipeline.run_analysis(
        dataset, settings,
        UncertaintySettings(jc_rel_sigma=0.05, n_samples=150, seed=1),
    )
    assert result.uncertainty is not None
    # FR-030: the fit standard errors are still there, separately.
    assert result.fit.lambda0.stderr is not None or result.fit.chi2_reduced < 1e-20
