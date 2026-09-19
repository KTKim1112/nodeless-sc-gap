"""Fit the superfluid density to a single-band nodeless gap model.

Two routes, both minimising a sum of squares over (lambda0, Delta0, Tc), and
both described in specs/001-jc-to-gap/research.md R6.

    Route A, TWO_STEP: invert equation (1) at every temperature first, then fit
        r_i = ln( lambda_model(T_i) ) - ln( lambda_data(T_i) )

    Route B, DIRECT: fit the measured Jc themselves in one pass
        r_i = ln( Jc_data(T_i) ) - ln( Jc_model(T_i) )

Both residuals are logarithmic, for the same reason: a multiplicative error in
Jc produces a constant fractional error, so logarithmic residuals have constant
scatter and the covariance formula below is entitled to assume they do. Research
R6 records the bootstrap that established this for route A.

Route B never inverts equation (1), so it cannot fail for want of an admissible
root, and it does not accumulate the error of the intermediate inversion.
Route A is faster and lets the user look at lambda(T) directly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from .constants import BCS_ALPHA, KB
from .errors import FitDidNotConverge, TcFixedBelowData
from .gap_models import coupling_ratio, lambda_of_T
from .lambda_solver import jc_model, solve_lambda
from .types import (
    AnalysisSettings,
    CoherenceSource,
    FitResult,
    FitRoute,
    FittedParameter,
    FloatArray,
    GapModel,
    LambdaTable,
    MeasurementDataset,
)

#: Bounds on lambda0 in metres. Generous: real values run from tens of
#: nanometres to a few micrometres, and a fit that wants to leave this range is
#: telling us something is wrong rather than needing more room.
_LAMBDA0_BOUNDS = (1e-9, 1e-4)

#: Delta0 as a multiple of kB * Tc. The weak-coupling BCS value is 1.7639, and
#: even extreme strong-coupling materials stay well inside this.
_ALPHA_BOUNDS = (0.2, 6.0)

#: Tc must exceed every measured temperature, since rho_s vanishes at Tc.
_TC_UPPER_FACTOR = 3.0
_TC_LOWER_MARGIN = 1.0001


@dataclass(frozen=True)
class _Problem:
    """Everything a residual function needs, assembled once."""

    temperature_K: FloatArray
    gap_model: GapModel
    tc_fixed_K: float | None
    # route A fits this
    lambda_data: FloatArray | None = None
    # route B fits this
    jc_data: FloatArray | None = None
    #: How equation (1) gets its coherence length. Route B needs these to form
    #: its residual; route A supplies them too, because the reported jc_model
    #: is wanted whichever route produced the parameters, and one expression
    #: for both is what keeps the two consistent.
    xi: FloatArray | None = None
    kappa_fixed: float | None = None
    #: The measured lambda(T), for reporting rho_s_measured. Route A fits it, so
    #: this is the same array there. Route B does not, and gets it from the
    #: caller, which has already built the table.
    lambda_reference: FloatArray | None = None

    @property
    def n_free(self) -> int:
        return 2 if self.tc_fixed_K is not None else 3


# --- parameter packing -------------------------------------------------------
#
# The optimiser works on a scaled vector rather than on raw SI values, because
# lambda0 ~ 2e-7 and Delta0 ~ 2e-22 differ by fifteen orders of magnitude and a
# trust region cannot be sized sensibly for both at once.
#
#   p[0] = ln(lambda0 / metre)
#   p[1] = Delta0 / (kB * Tc)     the conventional alpha
#   p[2] = Tc / K                 present only when Tc is free

def _unpack(p: np.ndarray, problem: _Problem) -> tuple[float, float, float]:
    lambda0 = math.exp(p[0])
    tc = problem.tc_fixed_K if problem.tc_fixed_K is not None else float(p[2])
    delta0 = p[1] * KB * tc
    return lambda0, delta0, tc


def _pack(lambda0: float, alpha: float, tc: float, problem: _Problem) -> np.ndarray:
    if problem.tc_fixed_K is not None:
        return np.array([math.log(lambda0), alpha], dtype=float)
    return np.array([math.log(lambda0), alpha, tc], dtype=float)


def _bounds(problem: _Problem, t_max: float) -> tuple[np.ndarray, np.ndarray]:
    lo = [math.log(_LAMBDA0_BOUNDS[0]), _ALPHA_BOUNDS[0]]
    hi = [math.log(_LAMBDA0_BOUNDS[1]), _ALPHA_BOUNDS[1]]
    if problem.tc_fixed_K is None:
        lo.append(t_max * _TC_LOWER_MARGIN)
        hi.append(t_max * _TC_UPPER_FACTOR)
    return np.array(lo, dtype=float), np.array(hi, dtype=float)


# --- residuals ---------------------------------------------------------------

def _predicted_jc(
    lambda0: float, delta0: float, tc: float, problem: _Problem
) -> FloatArray:
    """Equation (1) at the given parameters, on the measured temperatures.

    The coherence length is the model's own under a fixed kappa, where the fit
    determines it, and the supplied one otherwise, where it is data. Route B's
    residual and the reported jc_model both come through here, so they cannot
    drift apart (FR-026a, data-model.md `FitResult`).
    """
    lam = lambda_of_T(problem.temperature_K, lambda0, delta0, tc, problem.gap_model)
    xi = lam / problem.kappa_fixed if problem.kappa_fixed is not None else problem.xi
    with np.errstate(divide="ignore", invalid="ignore"):
        return jc_model(lam, xi)


def _residuals(p: np.ndarray, problem: _Problem) -> FloatArray:
    lambda0, delta0, tc = _unpack(p, problem)
    t = problem.temperature_K

    if problem.lambda_data is not None:
        # Route A, equation (7a). The logarithm is what makes the reported
        # standard errors honest: under a multiplicative error in Jc the
        # fractional error in lambda is the same at every temperature, so these
        # residuals are homoscedastic, which is what the covariance formula in
        # _covariance assumes. A superfluid-density residual is not, and
        # research R6 records the bootstrap showing it overstates the
        # uncertainty on Tc by a factor of two.
        model = lambda_of_T(t, lambda0, delta0, tc, problem.gap_model)
        with np.errstate(divide="ignore", invalid="ignore"):
            predicted = np.where(np.isfinite(model) & (model > 0.0), model, 1e300)
        return np.log(predicted) - np.log(problem.lambda_data)

    # Route B. The logarithm is essential: Jc spans orders of magnitude across
    # the temperature range, and a linear residual would let the coldest point
    # decide the fit on its own.
    predicted = _predicted_jc(lambda0, delta0, tc, problem)
    # Near Tc the model Jc collapses towards zero; guard the logarithm so the
    # optimiser sees a large finite penalty instead of a NaN it cannot use.
    predicted = np.where(np.isfinite(predicted) & (predicted > 0.0), predicted, 1e-300)
    return np.log(problem.jc_data) - np.log(predicted)


# --- uncertainty of the fitted parameters ------------------------------------

def _covariance(result, n_points: int, n_free: int) -> np.ndarray | None:
    """Parameter covariance from the Jacobian at the solution, research R6.

    Returns None when J^T J is singular, which is reported as an unavailable
    standard error rather than silently as zero.
    """
    dof = n_points - n_free
    if dof <= 0:
        return None
    jac = result.jac
    try:
        # Pseudo-inverse via SVD is stable where a direct inverse is not.
        _, s, vt = np.linalg.svd(jac, full_matrices=False)
        if s[0] <= 0 or s[-1] / s[0] < 1e-12:
            return None
        inv_jtj = (vt.T / s**2) @ vt
    except np.linalg.LinAlgError:
        return None
    residual_variance = 2.0 * result.cost / dof
    return residual_variance * inv_jtj


def _assemble(
    result,
    problem: _Problem,
    route: FitRoute,
) -> FitResult:
    lambda0, delta0, tc = _unpack(result.x, problem)
    n_points = int(result.fun.size)
    n_free = problem.n_free
    cov = _covariance(result, n_points, n_free)

    # The optimiser's variables are ln(lambda0), alpha and Tc; the reported
    # quantities are lambda0, Delta0 and Tc. Propagate through that change of
    # variables to first order.
    #   d(lambda0)/d(p0) = lambda0
    #   Delta0 = alpha * kB * Tc, so d(Delta0)/d(alpha) = kB*Tc
    #                              and d(Delta0)/d(Tc)  = alpha*kB
    alpha = result.x[1]
    se_lambda0 = se_delta0 = se_tc = None
    if cov is not None:
        var_ln_l, var_alpha = cov[0, 0], cov[1, 1]
        se_lambda0 = float(lambda0 * math.sqrt(max(var_ln_l, 0.0)))
        if problem.tc_fixed_K is not None:
            se_delta0 = float(KB * tc * math.sqrt(max(var_alpha, 0.0)))
        else:
            var_tc = cov[2, 2]
            cov_at = cov[1, 2]
            se_tc = float(math.sqrt(max(var_tc, 0.0)))
            var_delta0 = ((KB * tc) ** 2 * var_alpha
                          + (alpha * KB) ** 2 * var_tc
                          + 2.0 * (KB * tc) * (alpha * KB) * cov_at)
            se_delta0 = float(math.sqrt(max(var_delta0, 0.0)))

    # coupling_ratio = 2 alpha, exactly, so its uncertainty is that of alpha
    # alone and does not need the Tc term at all.
    ratio = coupling_ratio(delta0, tc)
    se_ratio = (float(2.0 * math.sqrt(max(cov[1, 1], 0.0))) if cov is not None else None)

    dof = max(n_points - n_free, 1)
    chi2_reduced = float(2.0 * result.cost / dof)

    reference = problem.lambda_reference
    if reference is None:
        reference = problem.lambda_data
    rho_s_measured = (
        np.asarray((lambda0 / reference) ** 2, dtype=float)
        if reference is not None
        else np.empty(0, dtype=float)
    )

    # Unguarded, unlike the copy inside the residual: that one substitutes a
    # finite penalty so the optimiser has something to work with, and this one
    # is reported, so a value the model cannot produce must not be disguised
    # as one it can.
    predicted_jc = np.asarray(
        _predicted_jc(lambda0, delta0, tc, problem), dtype=float
    )

    return FitResult(
        gap_model=problem.gap_model,
        fit_route=route,
        lambda0=FittedParameter(value=float(lambda0), stderr=se_lambda0),
        delta0=FittedParameter(value=float(delta0), stderr=se_delta0),
        tc=FittedParameter(
            value=float(tc),
            stderr=se_tc,
            fixed=problem.tc_fixed_K is not None,
        ),
        coupling_ratio=FittedParameter(value=float(ratio), stderr=se_ratio),
        chi2_reduced=chi2_reduced,
        residuals=np.asarray(result.fun, dtype=float),
        rho_s_measured=rho_s_measured,
        jc_model=predicted_jc,
        n_points=n_points,
        n_free_parameters=n_free,
        converged=bool(result.success),
        n_function_evaluations=int(result.nfev),
    )


# --- initial guesses ---------------------------------------------------------

def _initial_lambda0(problem: _Problem, tc_guess: float) -> float:
    """A starting value for lambda0 = lambda(T -> 0).

    The coldest measured point is already close to that limit for typical data,
    so it is used directly rather than extrapolated. The fit corrects it.
    """
    coldest = int(np.argmin(problem.temperature_K))
    if problem.lambda_data is not None:
        return float(problem.lambda_data[coldest])
    xi_cold = (problem.xi[coldest] if problem.xi is not None else None)
    if xi_cold is None:
        # Fixed kappa: equation (6) is explicit.
        from .lambda_solver import lambda_from_fixed_kappa
        return float(lambda_from_fixed_kappa(
            problem.jc_data[coldest], problem.kappa_fixed)[0])
    return solve_lambda(float(problem.jc_data[coldest]), float(xi_cold))


def _solve(problem: _Problem, route: FitRoute) -> FitResult:
    t_max = float(np.max(problem.temperature_K))
    if problem.tc_fixed_K is not None and problem.tc_fixed_K <= t_max:
        raise TcFixedBelowData(tc_fixed_K=problem.tc_fixed_K, t_max_K=t_max)

    tc_guess = problem.tc_fixed_K if problem.tc_fixed_K is not None else 1.05 * t_max
    p0 = _pack(_initial_lambda0(problem, tc_guess), BCS_ALPHA, tc_guess, problem)
    lo, hi = _bounds(problem, t_max)
    p0 = np.clip(p0, lo + 1e-12, hi - 1e-12)

    result = least_squares(
        _residuals, p0, args=(problem,), bounds=(lo, hi),
        method="trf", xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=4000,
    )
    fit = _assemble(result, problem, route)
    if not fit.converged:
        raise FitDidNotConverge(
            route=route.value, model=problem.gap_model.value, status=int(result.status)
        )
    return fit


# --- whether a result is the data's or the bounds' ---------------------------

#: How close to a bound counts as resting on it. The optimiser lands on an
#: active bound to within about 1e-10; this is loose enough to catch that and
#: far too tight for a genuine value to be mistaken for it (research R10).
_AT_LIMIT_RTOL = 1e-4


def parameters_at_limit(fit: FitResult, t_max_K: float) -> list[str]:
    """Which fitted parameters are resting on a bound rather than on the data.

    A parameter there is a statement about where the search was allowed to go,
    not about the sample, and the covariance formula in `_covariance` does not
    describe it -- that formula has no term for the constraint. Research R10
    measures how often this happens and finds the reported uncertainty is
    enormous in every such case; this exists so that it can be *said*, rather
    than left for the reader to infer from an error bar of 19 000 %.

    Here, rather than in diagnostics, because this module owns the bounds and
    a second copy of them elsewhere is how the two would drift apart. `t_max_K`
    is needed because the `Tc` bounds are relative to it.
    """
    out: list[str] = []
    alpha = fit.delta0.value / (KB * fit.tc.value)
    if any(math.isclose(alpha, b, rel_tol=_AT_LIMIT_RTOL) for b in _ALPHA_BOUNDS):
        out.append("alpha")
    if not fit.tc.fixed:
        tc_bounds = (t_max_K * _TC_LOWER_MARGIN, t_max_K * _TC_UPPER_FACTOR)
        if any(math.isclose(fit.tc.value, b, rel_tol=_AT_LIMIT_RTOL) for b in tc_bounds):
            out.append("tc")
    if any(math.isclose(fit.lambda0.value, b, rel_tol=_AT_LIMIT_RTOL)
           for b in _LAMBDA0_BOUNDS):
        out.append("lambda0")
    return out


# --- public entry points -----------------------------------------------------

def _model_xi_inputs(
    settings: AnalysisSettings, table_xi: FloatArray
) -> tuple[FloatArray | None, float | None]:
    """What equation (1) should use for the coherence length, and from where.

    Under a fixed kappa the table's `xi` is `lambda_data / kappa`, which is a
    property of the measurement rather than of the model; the model's own is
    `lambda_model / kappa`, so the parameter is passed instead of the column.
    """
    if settings.coherence_source is CoherenceSource.FIXED_KAPPA:
        return None, settings.kappa_fixed
    return table_xi, None


def fit_route_a(
    table: LambdaTable, settings: AnalysisSettings, gap_model: GapModel | None = None
) -> FitResult:
    """Fit lambda(T) that has already been extracted point by point."""
    xi, kappa_fixed = _model_xi_inputs(settings, table.xi)
    problem = _Problem(
        temperature_K=table.temperature_K,
        gap_model=gap_model or settings.gap_model,
        tc_fixed_K=settings.tc_fixed_K,
        lambda_data=table.lambda_,
        # Not fitted here -- route A's residual is in lambda. Carried so that
        # the reported jc_model exists for this route too.
        xi=xi,
        kappa_fixed=kappa_fixed,
        lambda_reference=table.lambda_,
    )
    return _solve(problem, FitRoute.TWO_STEP)


def fit_route_b(
    dataset: MeasurementDataset,
    settings: AnalysisSettings,
    gap_model: GapModel | None = None,
    lambda_reference: FloatArray | None = None,
) -> FitResult:
    """Fit the measured Jc(T) directly, without inverting equation (1)."""
    from .lambda_solver import resolve_xi

    fixed_kappa = (
        settings.kappa_fixed
        if settings.coherence_source is CoherenceSource.FIXED_KAPPA
        else None
    )
    problem = _Problem(
        temperature_K=np.asarray(dataset.temperature_K, dtype=float),
        gap_model=gap_model or settings.gap_model,
        tc_fixed_K=settings.tc_fixed_K,
        jc_data=np.asarray(dataset.jc, dtype=float),
        xi=resolve_xi(dataset, settings),
        kappa_fixed=fixed_kappa,
        lambda_reference=lambda_reference,
    )
    return _solve(problem, FitRoute.DIRECT)


def fit(
    dataset: MeasurementDataset,
    table: LambdaTable,
    settings: AnalysisSettings,
    gap_model: GapModel | None = None,
) -> FitResult:
    """Dispatch on the configured route."""
    if settings.fit_route is FitRoute.TWO_STEP:
        return fit_route_a(table, settings, gap_model)
    return fit_route_b(dataset, settings, gap_model, lambda_reference=table.lambda_)
