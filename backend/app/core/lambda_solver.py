"""Invert the Talantsev-Tallon self-field relation for the penetration depth.

Equations are numbered as in specs/001-jc-to-gap/research.md.

    Jc(T) = PHI0 / (4 pi MU0 lambda^3) * ( ln(lambda/xi) + 0.5 )        ... (1)
    xi(T) = sqrt( PHI0 / (2 pi Bc2(T)) )                                ... (2)
    lambda(T) = [ PHI0 (ln kappa + 0.5) / (4 pi MU0 Jc) ]^(1/3)         ... (6)

`lambda` appears both algebraically and inside the logarithm, so (1) has no
closed-form inverse and is solved numerically -- except under a fixed kappa,
where (6) is explicit.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

from .constants import KAPPA_MODEL_FLOOR, MU0, PHI0
from .errors import (
    KappaTooSmall,
    MissingColumn,
    NoRootTypeII,
    RootBracketingFailed,
)
from .types import (
    AnalysisSettings,
    CoherenceSource,
    FloatArray,
    LambdaTable,
    MeasurementDataset,
)

#: The recurring prefactor of equation (1), PHI0 / (4 pi MU0), in SI.
_A = PHI0 / (4.0 * math.pi * MU0)


def xi_from_hc2(hc2_T) -> FloatArray:
    """Equation (2). `hc2_T` is a value in tesla, used numerically as Bc2.

    Always returns at least a one-dimensional array, so that callers working
    over a temperature column never have to special-case a single point.
    """
    b = np.atleast_1d(np.asarray(hc2_T, dtype=float))
    return np.sqrt(PHI0 / (2.0 * np.pi * b))


def jc_model(lambda_, xi):
    """Equation (1): the critical current density the model predicts."""
    lam = np.asarray(lambda_, dtype=float)
    x = np.asarray(xi, dtype=float)
    return _A / lam**3 * (np.log(lam / x) + 0.5)


def jc_max_for(xi: float) -> float:
    """The supremum of equation (1) on the branch lambda > xi.

    On that branch the model is monotonically decreasing: differentiating gives
    d/dlambda [ lambda^-3 (ln(lambda/xi) + 0.5) ] = lambda^-4 [1 - 3L] with
    L = ln(lambda/xi) + 0.5, and L >= 0.5 for lambda >= xi, so the bracket is
    at most -0.5 and never changes sign. The supremum is therefore the limit at
    lambda -> xi, where L -> 0.5.

    A measured Jc above this value has no admissible solution, which is a
    statement about the data rather than about the solver.
    """
    return _A * 0.5 / xi**3


def solve_lambda(
    jc: float,
    xi: float,
    root_xtol: float = 1e-15,
    root_rtol: float = 1e-12,
    temperature_K: float | None = None,
) -> float:
    """Solve equation (1) for lambda on the strong type-II branch lambda > xi.

    The branch is chosen deliberately: it is the physically relevant one for the
    materials this analysis applies to, and the model is monotonic there, so the
    root is unique and a bracketed solver cannot land on the wrong one.
    """
    ceiling = jc_max_for(xi)
    if jc >= ceiling:
        raise NoRootTypeII(
            temperature_K=temperature_K, jc=jc, xi=xi, jc_max=ceiling
        )

    lo = xi * (1.0 + 1e-10)
    hi = max(10.0 * xi, 1e-7)
    for _ in range(60):
        if jc_model(hi, xi) - jc < 0.0:
            break
        hi *= 10.0
    else:
        raise RootBracketingFailed(temperature_K=temperature_K)

    return float(
        brentq(
            lambda lam: jc_model(lam, xi) - jc,
            lo,
            hi,
            xtol=root_xtol,
            rtol=root_rtol,
            maxiter=300,
        )
    )


def lambda_from_fixed_kappa(jc, kappa: float) -> FloatArray:
    """Equation (6). Explicit, so no root finding is needed."""
    if kappa <= KAPPA_MODEL_FLOOR:
        raise KappaTooSmall(kappa=kappa, floor=KAPPA_MODEL_FLOOR)
    j = np.atleast_1d(np.asarray(jc, dtype=float))
    return np.cbrt(_A * (math.log(kappa) + 0.5) / j)


def interpolate_xi(
    temperature_K: FloatArray, xi: FloatArray, grid_K: FloatArray
) -> FloatArray:
    """The coherence length between the measured temperatures, for plotting.

    Equation (1) needs `xi` wherever the model curve is drawn, and outside a
    fixed kappa it is known only where a measurement supplied it. This fills the
    gaps, and returns NaN outside the span of the measurements rather than
    extrapolating: beyond the coldest and hottest measured point there is
    nothing to interpolate between, and section 9 of the specification declines
    to assume a temperature dependence for the upper critical field.

    The interpolation is in `PHI0 / (2 pi xi^2)`, which is `Bc2` under
    FROM_HC2 and the field an explicit `xi` corresponds to under EXPLICIT_XI --
    not in `xi` itself. Research R12 measures why: `xi` goes as `Bc2^(-1/2)`
    and turns sharply upward as `Bc2` falls towards zero, so interpolating it
    directly is thirty to a hundred times less accurate on the same points.
    PCHIP rather than a spline for the same reason recorded there: a spline is
    more accurate on noiseless data and worse on data with realistic scatter,
    where it invents oscillations the model does not have.

    Duplicate temperatures are averaged. Two measurements at one temperature is
    a repeat, not a discontinuity, and PCHIP requires a strictly increasing
    abscissa.
    """
    t = np.asarray(temperature_K, dtype=float)
    b = PHI0 / (2.0 * np.pi * np.asarray(xi, dtype=float) ** 2)

    order = np.argsort(t, kind="stable")
    t, b = t[order], b[order]
    unique_t, inverse = np.unique(t, return_inverse=True)
    if unique_t.size < 2:
        return np.full(np.shape(grid_K), np.nan, dtype=float)
    if unique_t.size != t.size:
        counts = np.bincount(inverse)
        b = np.bincount(inverse, weights=b) / counts

    grid = np.asarray(grid_K, dtype=float)
    b_grid = PchipInterpolator(unique_t, b, extrapolate=False)(grid)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.sqrt(PHI0 / (2.0 * np.pi * b_grid))


def resolve_xi(dataset: MeasurementDataset, settings: AnalysisSettings) -> FloatArray | None:
    """The coherence length at each temperature, or None under a fixed kappa.

    Under FIXED_KAPPA the coherence length is an *output* -- it follows from
    lambda -- so there is nothing to resolve up front.
    """
    source = settings.coherence_source
    if source is CoherenceSource.FROM_HC2:
        if dataset.hc2 is None:
            raise MissingColumn(coherence_source=source.value, missing="hc2")
        return xi_from_hc2(dataset.hc2)
    if source is CoherenceSource.EXPLICIT_XI:
        if dataset.xi is None:
            raise MissingColumn(coherence_source=source.value, missing="xi")
        return np.asarray(dataset.xi, dtype=float)
    return None


def build_lambda_table(
    dataset: MeasurementDataset, settings: AnalysisSettings
) -> LambdaTable:
    """Penetration depth at every measured temperature.

    All three coherence-length modes end here; they are branches of one function
    rather than three separate programs.
    """
    temperature = np.asarray(dataset.temperature_K, dtype=float)
    jc = np.asarray(dataset.jc, dtype=float)

    if settings.coherence_source is CoherenceSource.FIXED_KAPPA:
        kappa_value = float(settings.kappa_fixed)  # presence is validated upstream
        lam = lambda_from_fixed_kappa(jc, kappa_value)
        xi = lam / kappa_value
        kappa = np.full_like(lam, kappa_value)
    else:
        xi = resolve_xi(dataset, settings)
        assert xi is not None
        lam = np.array(
            [
                solve_lambda(j, x, settings.root_xtol, settings.root_rtol, temperature_K=t)
                for j, x, t in zip(jc, xi, temperature)
            ],
            dtype=float,
        )
        kappa = lam / xi

    return LambdaTable(
        temperature_K=temperature, jc=jc, xi=xi, lambda_=lam, kappa=kappa
    )
