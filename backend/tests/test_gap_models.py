"""Gap and superfluid density. Research R3, R4, R5, R9.

These check against limits that are known analytically, which is the only way
to catch a superfluid density that is wrong but plausible -- the kind of error
that produces a believable gap and ends up in a paper.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core import gap_models as gm
from app.core.constants import BCS_ALPHA, BCS_RATIO, KB, MEV_TO_J
from app.core.types import GapModel

TC = 10.0
DELTA0 = 1.5 * MEV_TO_J
MODELS = [GapModel.CLEAN, GapModel.DIRTY]


# --- Delta(T) ----------------------------------------------------------------

def test_gap_equals_delta0_at_zero_and_vanishes_at_tc():
    assert gm.delta_of_T(0.0, DELTA0, TC)[0] == pytest.approx(DELTA0)
    assert gm.delta_of_T(TC, DELTA0, TC)[0] == 0.0
    assert gm.delta_of_T(TC * 1.5, DELTA0, TC)[0] == 0.0


def test_gap_is_monotonic_below_tc():
    """Non-increasing everywhere, and strictly decreasing wherever the change
    is representable. Below about T/Tc = 0.07 the interpolation formula has
    already saturated to Delta(0) to within one ulp, so consecutive values are
    bit-identical there; that is the floating-point floor, not a defect."""
    t = np.linspace(0.05, TC * 0.999, 500)
    values = gm.delta_of_T(t, DELTA0, TC)
    assert np.all(np.diff(values) <= 0.0)
    assert np.all(np.diff(gm.delta_of_T(np.linspace(0.1 * TC, 0.999 * TC, 300),
                                        DELTA0, TC)) < 0.0)


def test_interpolation_residual_at_low_temperature():
    """Research R3 records this as 2.6e-5 at T/Tc = 0.1. It is harmless for
    fitting but it is what makes the two models cross at low T, so it is pinned
    here rather than left to be rediscovered."""
    ratio = gm.delta_of_T(0.1 * TC, DELTA0, TC)[0] / DELTA0
    assert 1.0 - ratio == pytest.approx(2.6e-5, rel=0.1)


# --- the clean-limit integral ------------------------------------------------

def test_clean_integral_is_one_at_d_zero():
    """Analytic: INT[0..inf] sech^2(u) du = [tanh u] = 1. This single number
    fixes the normalisation of the whole clean-limit expression."""
    assert gm.clean_integral(0.0)[0] == pytest.approx(1.0, abs=1e-12)


def test_clean_integral_short_circuits_above_thirty():
    assert gm.clean_integral(30.0)[0] == 0.0
    assert gm.clean_integral(1e6)[0] == 0.0


def test_clean_integral_is_positive_and_decreasing():
    d = np.linspace(0.0, 20.0, 400)
    values = gm.clean_integral(d)
    assert np.all(values >= 0.0)
    assert np.all(np.diff(values) < 0.0)


# --- rho_s limits ------------------------------------------------------------

@pytest.mark.parametrize("model", MODELS)
def test_rho_s_is_one_at_zero_temperature(model):
    assert gm.rho_s(1e-9, DELTA0, TC, model)[0] == pytest.approx(1.0, abs=1e-12)
    assert gm.rho_s(0.0, DELTA0, TC, model)[0] == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("model", MODELS)
def test_rho_s_vanishes_at_tc(model):
    assert gm.rho_s(TC, DELTA0, TC, model)[0] == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("model", MODELS)
def test_rho_s_is_non_increasing(model):
    """Non-increasing rather than strictly decreasing: at low temperature the
    d >= 30 short circuit makes rho_s exactly 1 over a range of T, and the
    difference from 1 there is below 1e-24, which double precision cannot
    represent. Flat is the correct answer, not a defect."""
    t = np.linspace(0.01, TC * 0.9999, 600)
    values = gm.rho_s(t, DELTA0, TC, model)
    assert np.all(np.diff(values) <= 0.0)
    assert np.all((values >= 0.0) & (values <= 1.0))


@pytest.mark.parametrize("model", MODELS)
def test_rho_s_is_strictly_decreasing_where_it_matters(model):
    t = np.linspace(0.2 * TC, 0.99 * TC, 300)
    assert np.all(np.diff(gm.rho_s(t, DELTA0, TC, model)) < 0.0)


# --- the two models are distinguishable --------------------------------------

def test_dirty_lies_above_clean_across_the_useful_range():
    """Research R5: the separation is what FR-020 relies on."""
    t = np.linspace(0.4 * TC, 0.95 * TC, 60)
    separation = gm.rho_s_dirty(t, DELTA0, TC) - gm.rho_s_clean(t, DELTA0, TC)
    assert np.min(separation) >= 0.028
    assert np.max(separation) == pytest.approx(0.097, abs=0.005)


def test_the_ordering_reverses_at_low_temperature_and_that_is_expected():
    """Research R5 warns against asserting the ordering below T/Tc ~ 0.25.
    Pinning the reversal here documents it as understood rather than unnoticed,
    and would catch anyone 'fixing' it."""
    t = np.array([0.1, 0.2]) * TC
    separation = gm.rho_s_dirty(t, DELTA0, TC) - gm.rho_s_clean(t, DELTA0, TC)
    assert np.all(separation < 0.0)
    assert np.all(np.abs(separation) < 1e-3)


# --- derived quantities ------------------------------------------------------

def test_weak_coupling_bcs_ratio():
    assert gm.coupling_ratio(BCS_ALPHA * KB * TC, TC) == pytest.approx(BCS_RATIO, rel=1e-12)


def test_lambda_of_T_matches_rho_s():
    t = np.linspace(1.0, 9.0, 15)
    lam = gm.lambda_of_T(t, 200e-9, DELTA0, TC, GapModel.CLEAN)
    rho = gm.rho_s(t, DELTA0, TC, GapModel.CLEAN)
    assert np.allclose(lam, 200e-9 / np.sqrt(rho), rtol=1e-14)
    assert lam[0] < lam[-1]     # lambda grows towards Tc
