"""The dense model curve, and the coherence length it needs to exist.

FR-026a. The critical current density is drawn as a curve like the two beside
it, which means equation (1) has to be evaluated between the measurements, and
that needs xi where nothing was measured. Research R12 settles how.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core import lambda_solver as ls
from app.core import pipeline
from app.core.constants import PHI0
from app.core.gap_models import lambda_of_T
from app.core.types import GapModel

from .conftest import TRUE_DELTA0, TRUE_KAPPA, TRUE_LAMBDA0, TRUE_TC


def _xi_of(bc2):
    return np.sqrt(PHI0 / (2.0 * np.pi * np.asarray(bc2, dtype=float)))


# --- the interpolation itself ------------------------------------------------

def test_interpolation_returns_the_data_at_the_data():
    """A curve that missed the points it was built from would be a new model.

    PCHIP is an interpolant, so its value at a node is that node, and the round
    trip through Bc2 and back is one square and one square root of the same
    number.
    """
    t = np.linspace(1.0, 9.0, 9)
    xi = _xi_of(10.0 * (1.0 - (t / TRUE_TC) ** 2))
    assert ls.interpolate_xi(t, xi, t) == pytest.approx(xi, rel=1e-15)


def test_interpolation_refuses_to_extrapolate():
    """Outside the measurements there are not two points to interpolate between.

    Specification section 9 declines to assume a temperature dependence for the
    upper critical field, and extrapolating one silently is how that assumption
    would get made without being stated.
    """
    t = np.linspace(2.0, 8.0, 7)
    xi = _xi_of(10.0 * (1.0 - (t / TRUE_TC) ** 2))
    grid = np.array([0.0, 1.999, 2.0, 5.0, 8.0, 8.001, 9.5])
    out = ls.interpolate_xi(t, xi, grid)

    assert np.isnan(out[[0, 1, 6]]).all()
    assert np.isfinite(out[[2, 3, 4]]).all()
    # 8.001 K is past the hottest measurement by a thousandth of a kelvin and is
    # refused as firmly as 9.5 K is. A tolerance here would be an extrapolation
    # with a small number attached to it.
    assert np.isnan(out[5])


def test_interpolation_is_exact_on_a_linear_upper_critical_field():
    """Bc2 linear in T is the one case with a right answer to check against.

    PCHIP reproduces a straight line exactly, so the only step left is the
    conversion to xi, which is not an approximation at all. Research R12
    measures the two curved cases, where there is no exact answer to assert.
    """
    t = np.linspace(1.0, 9.0, 9)
    dense = np.linspace(1.0, 9.0, 101)
    expected = _xi_of(10.0 * (1.0 - dense / TRUE_TC))
    got = ls.interpolate_xi(t, _xi_of(10.0 * (1.0 - t / TRUE_TC)), dense)
    assert got == pytest.approx(expected, rel=1e-12)


def test_interpolation_averages_a_repeated_temperature():
    """Two measurements at one temperature are a repeat, not a discontinuity.

    Left alone this is an error from the interpolator about a strictly
    increasing abscissa, which tells the user nothing about their data.
    """
    t = np.array([2.0, 4.0, 4.0, 6.0])
    bc2 = np.array([8.0, 5.0, 7.0, 3.0])
    out = ls.interpolate_xi(t, _xi_of(bc2), np.array([4.0]))
    assert out[0] == pytest.approx(_xi_of(6.0), rel=1e-12)


def test_interpolation_gives_up_rather_than_guessing_from_one_point():
    t = np.array([3.0, 3.0])
    out = ls.interpolate_xi(t, _xi_of(np.array([5.0, 5.0])), np.array([3.0, 4.0]))
    assert np.isnan(out).all()


# --- the curve the plot draws ------------------------------------------------

@pytest.mark.parametrize("source", ["hc2", "xi", "kappa"])
def test_curve_carries_a_jc_column_of_the_right_length(
    source, dataset_hc2, dataset_xi, dataset_kappa,
    settings_hc2, settings_xi, settings_kappa,
):
    pairs = {
        "hc2": (dataset_hc2, settings_hc2),
        "xi": (dataset_xi, settings_xi),
        "kappa": (dataset_kappa, settings_kappa),
    }
    curve = pipeline.run_analysis(*pairs[source]).curve
    assert curve.jc.shape == curve.temperature_K.shape
    assert np.any(np.isfinite(curve.jc))


def test_the_drawn_curve_is_the_same_model_as_the_reported_prediction(
    dataset_hc2, settings_hc2
):
    """The curve and the per-point prediction must not be two models.

    `FitResult.jc_model` is what the direct route's residual measures and what
    the results table exports; the curve is what the user looks at. If the two
    came from different expressions the figure and the file could disagree and
    nothing on the screen would show it. Evaluating the curve's own recipe at
    the measured temperatures has to give the reported column back.
    """
    result = pipeline.run_analysis(dataset_hc2, settings_hc2)
    fit, table = result.fit, result.lambda_table

    lam = lambda_of_T(table.temperature_K, fit.lambda0.value, fit.delta0.value,
                      fit.tc.value, fit.gap_model)
    xi = ls.interpolate_xi(table.temperature_K, table.xi, table.temperature_K)
    assert np.asarray(ls.jc_model(lam, xi)) == pytest.approx(fit.jc_model, rel=1e-12)


def test_the_curve_stops_where_the_measurements_do_outside_fixed_kappa(
    dataset_hc2, settings_hc2
):
    """FR-026a. Absolute zero is outside the data, and gets no value there.

    Asserted on the same curve that carries rho_s and lambda all the way from
    zero to Tc: the three columns share one grid, and this one alone has gaps,
    which is why the gaps are sent rather than a shorter array.
    """
    result = pipeline.run_analysis(dataset_hc2, settings_hc2)
    curve, table = result.curve, result.lambda_table
    known = np.isfinite(curve.jc)

    assert curve.temperature_K[0] == 0.0
    assert not known[0]
    assert np.isfinite(curve.rho_s[0]) and np.isfinite(curve.lambda_[0])
    assert curve.temperature_K[known].min() >= table.temperature_K.min()
    assert curve.temperature_K[known].max() <= table.temperature_K.max()


def test_the_curve_is_complete_under_a_fixed_kappa(dataset_kappa, settings_kappa):
    """There the coherence length follows the fit, so nothing is missing.

    The asymmetry with the test above is deliberate, and the plot is the one
    place it becomes visible: fixing kappa buys a model that can be drawn
    everywhere, by assuming the number it needed to draw it.
    """
    result = pipeline.run_analysis(dataset_kappa, settings_kappa)
    curve = result.curve

    assert np.all(np.isfinite(curve.jc))
    assert np.all(curve.jc > 0.0)
    # The model's own xi, not the table's: lambda(0)/kappa at absolute zero.
    lambda0 = result.fit.lambda0.value
    expected = np.asarray(ls.jc_model(lambda0, lambda0 / TRUE_KAPPA)).ravel()[0]
    assert curve.jc[0] == pytest.approx(expected, rel=1e-12)


def test_the_curve_recovers_the_data_it_was_generated_from(dataset_hc2, settings_hc2):
    """The whole chain, seen between the measurements rather than at them.

    Everywhere the curve has a value, it is compared against equation (1) at
    the parameters the data were generated from -- not against the data, which
    would only re-test the points the curve already passes through. What this
    catches that the per-point tests cannot is an interpolated coherence length
    that is wrong between the nodes while being right on them.
    """
    result = pipeline.run_analysis(dataset_hc2, settings_hc2)
    curve = result.curve
    known = np.isfinite(curve.jc)
    t = curve.temperature_K[known]

    truth = lambda_of_T(t, TRUE_LAMBDA0, TRUE_DELTA0, TRUE_TC, GapModel.CLEAN)
    expected = np.asarray(ls.jc_model(truth, truth / TRUE_KAPPA))
    assert curve.jc[known] == pytest.approx(expected, rel=5e-3)


def test_a_fixed_kappa_curve_reaches_far_below_the_measured_range(
    dataset_kappa, settings_kappa
):
    """Why the plot sets its own axis range instead of letting Plotly choose.

    Towards Tc the model Jc falls orders of magnitude past anything measured.
    Pinning the size of that fall records why the frontend bounds the axis by
    the measured values, so that a later change here cannot quietly make that
    code look unnecessary.
    """
    result = pipeline.run_analysis(dataset_kappa, settings_kappa)
    decades = np.log10(result.lambda_table.jc.min() / result.curve.jc.min())
    assert decades > 2.0
