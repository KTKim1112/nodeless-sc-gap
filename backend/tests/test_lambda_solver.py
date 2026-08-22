"""Inverting equation (1). Research R1, R7, R9."""

from __future__ import annotations

import numpy as np
import pytest

from app.core import lambda_solver as ls
from app.core.constants import PHI0
from app.core.errors import KappaTooSmall, NoRootTypeII
from app.core.types import CoherenceSource

from .conftest import TRUE_KAPPA, TRUE_LAMBDA0


def test_xi_from_hc2_matches_the_gl_relation():
    xi = 5e-9
    bc2 = PHI0 / (2.0 * np.pi * xi**2)
    assert ls.xi_from_hc2(bc2)[0] == pytest.approx(xi, rel=1e-14)


def test_solving_then_substituting_back_reproduces_jc():
    """The tightest available check on the solver: it is its own inverse."""
    xi = TRUE_LAMBDA0 / TRUE_KAPPA
    jc = float(ls.jc_model(TRUE_LAMBDA0, xi))
    lam = ls.solve_lambda(jc, xi)
    assert lam == pytest.approx(TRUE_LAMBDA0, rel=1e-9)
    assert float(ls.jc_model(lam, xi)) == pytest.approx(jc, rel=1e-9)


@pytest.mark.parametrize("kappa", [1.05, 5.0, 40.0, 200.0])
def test_fixed_kappa_explicit_form_agrees_with_the_root_finder(kappa):
    """Equation (6) and equation (1) must describe the same physics.

    They are different code paths -- one algebraic, one iterative -- so this
    catches a mistake in either.
    """
    xi = TRUE_LAMBDA0 / kappa
    jc = float(ls.jc_model(TRUE_LAMBDA0, xi))
    explicit = ls.lambda_from_fixed_kappa(jc, kappa)[0]
    numerical = ls.solve_lambda(jc, xi)
    assert explicit == pytest.approx(numerical, rel=1e-9)


def test_model_is_monotonic_on_the_chosen_branch():
    """Research R1: on lambda > xi the derivative is lambda^-4 (1 - 3L) with
    L >= 0.5, so it never changes sign and the root is unique."""
    xi = 5e-9
    lam = np.geomspace(xi * 1.000001, xi * 1e4, 2000)
    jc = ls.jc_model(lam, xi)
    assert np.all(np.diff(jc) < 0.0)


def test_jc_above_the_ceiling_has_no_admissible_solution():
    xi = 5e-9
    ceiling = ls.jc_max_for(xi)
    with pytest.raises(NoRootTypeII) as excinfo:
        ls.solve_lambda(ceiling * 1.001, xi, temperature_K=4.2)
    params = excinfo.value.params
    assert params["temperature_K"] == 4.2
    assert params["jc_max"] == pytest.approx(ceiling)


def test_just_below_the_ceiling_still_solves():
    xi = 5e-9
    lam = ls.solve_lambda(ls.jc_max_for(xi) * 0.999, xi)
    assert lam > xi


def test_the_ceiling_is_exactly_kappa_equals_one():
    """Research R1, equation (1a).

    The largest Jc the lambda > xi branch can account for is the limit as
    lambda -> xi, which is the case kappa = 1. So inverting equation (1) can
    only ever return kappa > 1, and a Jc at the ceiling is the data telling us
    kappa <= 1 rather than the solver failing.
    """
    xi = 5e-9
    jc_at_kappa_one = float(ls.jc_model(xi, xi))       # lambda == xi
    assert jc_at_kappa_one == pytest.approx(ls.jc_max_for(xi), rel=1e-14)
    with pytest.raises(NoRootTypeII):
        ls.solve_lambda(jc_at_kappa_one, xi)

    # Just inside the branch, kappa comes out just above 1.
    lam = ls.solve_lambda(jc_at_kappa_one * 0.99, xi)
    assert 1.0 < lam / xi < 1.1


def test_fixed_kappa_reaches_below_one_where_the_root_finder_cannot():
    """The asymmetry documented in research R1.

    Equation (6) is explicit and searches no branch, so under a fixed kappa the
    region exp(-0.5) < kappa < 1 is available. That region is unreachable when
    inverting for kappa, and the difference is deliberate.
    """
    lam = ls.lambda_from_fixed_kappa(1e10, 0.8)[0]
    assert lam > 0.0


def test_kappa_below_the_model_floor_is_refused():
    # ln(kappa) + 0.5 <= 0 makes equation (1) return a negative Jc.
    with pytest.raises(KappaTooSmall):
        ls.lambda_from_fixed_kappa(1e6, 0.5)


def test_table_agrees_across_all_three_coherence_modes(
    clean_data, dataset_xi, dataset_hc2, dataset_kappa,
    settings_xi, settings_hc2, settings_kappa,
):
    """The three modes are different routes to the same lambda(T) when the
    inputs describe the same sample. If they disagree, one branch is wrong."""
    a = ls.build_lambda_table(dataset_xi, settings_xi)
    b = ls.build_lambda_table(dataset_hc2, settings_hc2)
    c = ls.build_lambda_table(dataset_kappa, settings_kappa)
    truth = clean_data["lambda_"]
    for table in (a, b, c):
        assert np.allclose(table.lambda_, truth, rtol=1e-9)
        assert np.allclose(table.kappa, TRUE_KAPPA, rtol=1e-9)
        assert np.allclose(table.xi, clean_data["xi"], rtol=1e-9)


def test_fixed_kappa_mode_reports_the_implied_xi(dataset_kappa, settings_kappa):
    """AS-3: under a fixed kappa the coherence length is an output."""
    table = ls.build_lambda_table(dataset_kappa, settings_kappa)
    assert np.allclose(table.xi, table.lambda_ / TRUE_KAPPA)


def test_results_keep_the_caller_s_row_order(clean_data):
    """Temperatures need not be sorted, and the answer must not depend on it."""
    from app.core.validation import build_dataset

    order = np.array([7, 0, 15, 3, 11, 1, 19, 5, 9, 13, 2, 17, 4, 8, 6, 10, 12, 14, 16, 18])
    ds = build_dataset(
        clean_data["temperature_K"][order],
        clean_data["jc"][order],
        xi=clean_data["xi"][order],
    )
    from app.core.types import AnalysisSettings

    table = ls.build_lambda_table(
        ds, AnalysisSettings(coherence_source=CoherenceSource.EXPLICIT_XI)
    )
    assert np.allclose(table.lambda_, clean_data["lambda_"][order], rtol=1e-9)
