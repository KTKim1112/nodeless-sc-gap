"""Single-band nodeless gap models and the normalised superfluid density.

Equations are numbered as in specs/001-jc-to-gap/research.md R3 to R5.

    Delta(T) = Delta(0) tanh{ 1.82 [ 1.018 (Tc/T - 1) ]^0.51 }     T < Tc
    rho_s    = 1 - INT[0..inf] sech^2( sqrt(u^2 + d^2) ) du         clean  ... (3)
    rho_s    = ( Delta(T)/Delta(0) ) tanh(d)                        dirty  ... (4)

with the single dimensionless argument

    d = Delta(T) / (2 kB T)

`rho_s` is lambda^2(0)/lambda^2(T), so it runs from 1 at T = 0 to 0 at Tc.
"""

from __future__ import annotations

import numpy as np

from .constants import KB
from .types import FloatArray, GapModel

# --- the clean-limit quadrature rule -----------------------------------------
#
# Fixed-node Gauss-Legendre over four graded panels. Research R4 records the
# measurements behind these numbers: 80 nodes reach 4.4e-16 against adaptive
# quadrature, which is the floating-point floor, while being 250 times faster.
# Panelling is what buys the accuracy -- sech^2 has poles at u = i pi/2, so a
# single long panel converges slowly no matter how many nodes it is given.
#
# The rule is fixed rather than adaptive so that the result is bit-identical on
# every run, which the reproducibility requirement of constitution VII needs.

_PANEL_EDGES = (0.0, 2.0, 6.0, 14.0, 30.0)
_NODES_PER_PANEL = 20

#: Beyond this the integrand is below sech^2(30) = 3.5e-26 everywhere and the
#: whole integral is below 1e-24, which is not representable beside a result of
#: order 1. Also the short-circuit threshold on d itself.
_U_MAX = 30.0


def _build_rule() -> tuple[FloatArray, FloatArray]:
    x, w = np.polynomial.legendre.leggauss(_NODES_PER_PANEL)
    nodes, weights = [], []
    for a, b in zip(_PANEL_EDGES[:-1], _PANEL_EDGES[1:]):
        nodes.append(0.5 * (b - a) * x + 0.5 * (b + a))
        weights.append(0.5 * (b - a) * w)
    return np.concatenate(nodes), np.concatenate(weights)


_NODES, _WEIGHTS = _build_rule()
_NODES_SQ = _NODES**2


def clean_integral(d) -> FloatArray:
    """The integral of equation (3), evaluated for every element of `d` at once.

    Vectorising over temperature points rather than looping is what makes a
    Monte Carlo run take minutes instead of hours.
    """
    d_arr = np.atleast_1d(np.asarray(d, dtype=float))
    out = np.zeros_like(d_arr)

    # For d >= 30 the integrand is below 3.5e-26 everywhere; the integral is
    # zero to double precision and rho_s is exactly 1.
    active = d_arr < _U_MAX
    if np.any(active):
        arg = np.sqrt(_NODES_SQ[None, :] + d_arr[active][:, None] ** 2)
        out[active] = (1.0 / np.cosh(arg) ** 2) @ _WEIGHTS
    return out


# --- gap and superfluid density ----------------------------------------------

def delta_of_T(temperature_K, delta0: float, tc: float) -> FloatArray:
    """BCS interpolation formula, research R3. Zero at and above Tc."""
    t = np.atleast_1d(np.asarray(temperature_K, dtype=float))
    out = np.zeros_like(t)
    below = (t > 0.0) & (t < tc)
    if np.any(below):
        ratio = tc / t[below] - 1.0
        out[below] = delta0 * np.tanh(1.82 * (1.018 * ratio) ** 0.51)
    # T <= 0 is not physical input, but the limit of the formula there is
    # Delta(0), and returning that keeps the function total.
    out[t <= 0.0] = delta0
    return out


def _reduced_gap(temperature_K, delta0: float, tc: float) -> tuple[FloatArray, FloatArray]:
    """Return (Delta(T), d) with d = Delta(T) / (2 kB T), guarding T = 0."""
    t = np.atleast_1d(np.asarray(temperature_K, dtype=float))
    delta = delta_of_T(t, delta0, tc)
    d = np.full_like(t, np.inf)
    positive = t > 0.0
    d[positive] = delta[positive] / (2.0 * KB * t[positive])
    return delta, d


def rho_s_clean(temperature_K, delta0: float, tc: float) -> FloatArray:
    """Normalised superfluid density in the clean limit, equation (3)."""
    _, d = _reduced_gap(temperature_K, delta0, tc)
    finite = np.isfinite(d)
    out = np.ones_like(d)
    if np.any(finite):
        out[finite] = 1.0 - clean_integral(d[finite])
    return out


def rho_s_dirty(temperature_K, delta0: float, tc: float) -> FloatArray:
    """Normalised superfluid density in the dirty limit, equation (4)."""
    delta, d = _reduced_gap(temperature_K, delta0, tc)
    out = np.ones_like(d)
    finite = np.isfinite(d)
    if np.any(finite):
        out[finite] = (delta[finite] / delta0) * np.tanh(d[finite])
    return out


def rho_s(temperature_K, delta0: float, tc: float, model: GapModel) -> FloatArray:
    """Dispatch on the chosen model."""
    if model is GapModel.CLEAN:
        return rho_s_clean(temperature_K, delta0, tc)
    if model is GapModel.DIRTY:
        return rho_s_dirty(temperature_K, delta0, tc)
    raise ValueError(f"unhandled gap model: {model!r}")


def lambda_of_T(temperature_K, lambda0: float, delta0: float, tc: float,
                model: GapModel) -> FloatArray:
    """Equation (5): lambda(T) = lambda0 / sqrt(rho_s(T)).

    Diverges as rho_s -> 0 at Tc, which is physically correct; callers that
    sample near Tc must expect large values rather than treat them as an error.
    """
    r = rho_s(temperature_K, delta0, tc, model)
    with np.errstate(divide="ignore", invalid="ignore"):
        return lambda0 / np.sqrt(r)


def coupling_ratio(delta0: float, tc: float) -> float:
    """2 Delta(0) / (kB Tc). The weak-coupling BCS value is 3.52775."""
    return 2.0 * delta0 / (KB * tc)
