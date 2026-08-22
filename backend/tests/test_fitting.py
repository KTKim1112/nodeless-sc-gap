"""The round trip. Constitution II calls this the primary correctness gate.

Synthetic Jc(T) is generated from known (lambda0, Delta0, Tc, kappa); the fit
must give them back. A wrong factor, a wrong sign, or a wrong unit anywhere in
the chain -- equation (1), the gap interpolation, the superfluid density, the
residual, the parameter packing -- shows up here and essentially nowhere else,
because every one of those mistakes still produces a plausible number.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core import fitting
from app.core import lambda_solver as ls
from app.core.constants import BCS_ALPHA, BCS_RATIO, KB, MEV_TO_J
from app.core.errors import TcFixedBelowData
from app.core.gap_models import coupling_ratio
from app.core.types import AnalysisSettings, CoherenceSource, FitRoute, GapModel
from app.core.validation import build_dataset

from .conftest import TRUE_DELTA0, TRUE_LAMBDA0, TRUE_TC, synthesise

TOLERANCE = 0.01  # 1 %, the requirement in research R9


def _fit_both_routes(model: GapModel):
    data = synthesise(model)
    dataset = build_dataset(data["temperature_K"], data["jc"], xi=data["xi"])
    settings = AnalysisSettings(
        coherence_source=CoherenceSource.EXPLICIT_XI, gap_model=model
    )
    table = ls.build_lambda_table(dataset, settings)
    return (fitting.fit_route_a(table, settings),
            fitting.fit_route_b(dataset, settings))


@pytest.mark.parametrize("model", [GapModel.CLEAN, GapModel.DIRTY])
def test_round_trip_route_a(model):
    fit, _ = _fit_both_routes(model)
    assert fit.converged
    assert fit.fit_route is FitRoute.TWO_STEP
    assert fit.lambda0.value == pytest.approx(TRUE_LAMBDA0, rel=TOLERANCE)
    assert fit.delta0.value == pytest.approx(TRUE_DELTA0, rel=TOLERANCE)
    assert fit.tc.value == pytest.approx(TRUE_TC, rel=TOLERANCE)


@pytest.mark.parametrize("model", [GapModel.CLEAN, GapModel.DIRTY])
def test_round_trip_route_b(model):
    _, fit = _fit_both_routes(model)
    assert fit.converged
    assert fit.fit_route is FitRoute.DIRECT
    assert fit.lambda0.value == pytest.approx(TRUE_LAMBDA0, rel=TOLERANCE)
    assert fit.delta0.value == pytest.approx(TRUE_DELTA0, rel=TOLERANCE)
    assert fit.tc.value == pytest.approx(TRUE_TC, rel=TOLERANCE)


@pytest.mark.parametrize("model", [GapModel.CLEAN, GapModel.DIRTY])
def test_the_two_routes_agree(model):
    """AS-5. The two residual functions share no code, so agreement is
    evidence rather than tautology."""
    a, b = _fit_both_routes(model)
    assert a.lambda0.value == pytest.approx(b.lambda0.value, rel=1e-6)
    assert a.delta0.value == pytest.approx(b.delta0.value, rel=1e-6)
    assert a.tc.value == pytest.approx(b.tc.value, rel=1e-6)


def test_round_trip_through_every_coherence_mode(
    dataset_xi, dataset_hc2, dataset_kappa,
    settings_xi, settings_hc2, settings_kappa,
):
    """FR-006: three ways of establishing xi, one answer."""
    cases = [(dataset_xi, settings_xi), (dataset_hc2, settings_hc2),
             (dataset_kappa, settings_kappa)]
    for dataset, settings in cases:
        table = ls.build_lambda_table(dataset, settings)
        for fit in (fitting.fit_route_a(table, settings),
                    fitting.fit_route_b(dataset, settings)):
            assert fit.lambda0.value == pytest.approx(TRUE_LAMBDA0, rel=TOLERANCE)
            assert fit.delta0.value == pytest.approx(TRUE_DELTA0, rel=TOLERANCE)
            assert fit.tc.value == pytest.approx(TRUE_TC, rel=TOLERANCE)


def test_weak_coupling_ratio_is_exactly_the_bcs_value():
    assert coupling_ratio(BCS_ALPHA * KB * TRUE_TC, TRUE_TC) == pytest.approx(
        BCS_RATIO, rel=1e-12
    )


def test_coupling_ratio_matches_its_own_parameters():
    fit, _ = _fit_both_routes(GapModel.CLEAN)
    assert fit.coupling_ratio.value == pytest.approx(
        2.0 * fit.delta0.value / (KB * fit.tc.value), rel=1e-12
    )


# --- fixing Tc ---------------------------------------------------------------

def test_tc_can_be_held_fixed(dataset_xi):
    """FR-013."""
    settings = AnalysisSettings(
        coherence_source=CoherenceSource.EXPLICIT_XI, tc_fixed_K=TRUE_TC
    )
    table = ls.build_lambda_table(dataset_xi, settings)
    fit = fitting.fit_route_a(table, settings)
    assert fit.tc.fixed
    assert fit.tc.value == TRUE_TC
    assert fit.tc.stderr is None
    assert fit.n_free_parameters == 2
    assert fit.lambda0.value == pytest.approx(TRUE_LAMBDA0, rel=TOLERANCE)
    assert fit.delta0.value == pytest.approx(TRUE_DELTA0, rel=TOLERANCE)


def test_tc_fixed_below_the_data_is_refused(dataset_xi):
    settings = AnalysisSettings(
        coherence_source=CoherenceSource.EXPLICIT_XI, tc_fixed_K=5.0
    )
    table = ls.build_lambda_table(dataset_xi, settings)
    with pytest.raises(TcFixedBelowData) as excinfo:
        fitting.fit_route_a(table, settings)
    assert excinfo.value.params["tc_fixed_K"] == 5.0
    assert excinfo.value.params["t_max_K"] == pytest.approx(9.0)


# --- the wrong model still returns a number ----------------------------------

def test_wrong_model_biases_the_gap_but_only_chi2_shows_it():
    """The reason FR-020 exists.

    Fitting clean-limit data with the dirty-limit expression returns a
    perfectly believable Delta(0). It is wrong by about 20 %, and nothing in
    the parameter values reveals that. Only the goodness of fit does, and it
    does so by many orders of magnitude.
    """
    data = synthesise(GapModel.CLEAN)
    dataset = build_dataset(data["temperature_K"], data["jc"], xi=data["xi"])
    settings = AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)
    table = ls.build_lambda_table(dataset, settings)

    right = fitting.fit_route_a(table, settings, gap_model=GapModel.CLEAN)
    wrong = fitting.fit_route_a(table, settings, gap_model=GapModel.DIRTY)

    assert right.delta0.value == pytest.approx(TRUE_DELTA0, rel=TOLERANCE)
    assert abs(wrong.delta0.value - TRUE_DELTA0) / TRUE_DELTA0 > 0.15
    assert 0.5 < wrong.delta0.value / MEV_TO_J < 3.0   # still entirely plausible
    assert wrong.chi2_reduced > 1e6 * max(right.chi2_reduced, 1e-30)


# --- standard errors ---------------------------------------------------------

def test_standard_errors_appear_when_the_data_scatter():
    rng = np.random.default_rng(7)
    data = synthesise(GapModel.CLEAN)
    noisy = data["jc"] * rng.lognormal(0.0, 0.03, data["jc"].size)
    dataset = build_dataset(data["temperature_K"], noisy, xi=data["xi"])
    settings = AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)
    fit = fitting.fit_route_a(ls.build_lambda_table(dataset, settings), settings)

    for parameter in (fit.lambda0, fit.delta0, fit.tc, fit.coupling_ratio):
        assert parameter.stderr is not None
        assert parameter.stderr > 0.0
    # The true values must sit within a few standard errors of the fit.
    assert abs(fit.delta0.value - TRUE_DELTA0) < 4.0 * fit.delta0.stderr
    assert abs(fit.lambda0.value - TRUE_LAMBDA0) < 4.0 * fit.lambda0.stderr


def test_reported_standard_errors_survive_a_parametric_bootstrap():
    """Are the standard errors honest?

    The Jacobian covariance is a linearised estimate, so it is worth checking
    against the thing it claims to predict. Perturb Jc, refit many times, and
    compare the actual spread of each parameter with the standard error the fit
    reported. Research R6 records the measurement that led to the logarithmic
    residual; this keeps the property from regressing.

    The tolerance is wide because the bootstrap spread is itself an estimate:
    with 120 replicas its own relative error is 1/sqrt(2*119) = 6.5 %.
    """
    data = synthesise(GapModel.CLEAN)
    settings = AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)
    rng = np.random.default_rng(2024)

    values = {"lambda0": [], "delta0": [], "tc": []}
    reported = {"lambda0": [], "delta0": [], "tc": []}
    for _ in range(120):
        noisy = data["jc"] * rng.lognormal(0.0, 0.05, data["jc"].size)
        dataset = build_dataset(data["temperature_K"], noisy, xi=data["xi"])
        fit = fitting.fit_route_a(ls.build_lambda_table(dataset, settings), settings)
        for name, parameter in (("lambda0", fit.lambda0), ("delta0", fit.delta0),
                                ("tc", fit.tc)):
            values[name].append(parameter.value)
            reported[name].append(parameter.stderr)

    for name in values:
        spread = float(np.std(values[name], ddof=1))
        median_stderr = float(np.median(reported[name]))
        ratio = spread / median_stderr
        assert 0.75 < ratio < 1.35, (
            f"{name}: bootstrap spread {spread:.3e} against reported "
            f"{median_stderr:.3e}, ratio {ratio:.2f}"
        )


def test_the_gap_is_better_determined_than_the_coupling_ratio():
    """A consequence of how the parameters correlate, worth pinning down.

    The fit variables are ln(lambda0), alpha = Delta0/(kB Tc), and Tc. A larger
    fitted Tc has to be paired with a smaller alpha to keep the same Delta(T),
    so the two are strongly anticorrelated -- about -0.89 for this dataset. In
    Delta0 = alpha kB Tc that anticorrelation enters the variance with a
    negative cross term, which makes Delta0 better determined than alpha, and
    therefore better determined than the coupling ratio 2*alpha.

    Dropping the covariance term from the propagation would silently reverse
    this, so it is asserted rather than assumed.
    """
    rng = np.random.default_rng(11)
    data = synthesise(GapModel.CLEAN)
    noisy = data["jc"] * rng.lognormal(0.0, 0.05, data["jc"].size)
    dataset = build_dataset(data["temperature_K"], noisy, xi=data["xi"])
    settings = AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)
    fit = fitting.fit_route_a(ls.build_lambda_table(dataset, settings), settings)

    relative_delta = fit.delta0.stderr / fit.delta0.value
    relative_ratio = fit.coupling_ratio.stderr / fit.coupling_ratio.value
    assert relative_delta < relative_ratio


def test_residual_count_matches_the_data():
    fit, _ = _fit_both_routes(GapModel.CLEAN)
    assert fit.residuals.size == fit.n_points == 20
