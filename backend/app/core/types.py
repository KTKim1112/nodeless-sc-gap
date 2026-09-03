"""Domain types.

The definitive description of every type here is
specs/001-jc-to-gap/data-model.md. This module is the code that follows it.

Units: metres, joules, amperes per square metre, tesla, kelvin. A field whose
name ends in a unit suffix is the only exception and exists for display
(constitution V).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


# --- enumerations ------------------------------------------------------------

class JcUnit(str, Enum):
    A_PER_CM2 = "A_PER_CM2"
    A_PER_M2 = "A_PER_M2"


class XiUnit(str, Enum):
    M = "M"
    NM = "NM"
    UM = "UM"


class CoherenceSource(str, Enum):
    """How the coherence length is established at each temperature."""
    FROM_HC2 = "FROM_HC2"
    EXPLICIT_XI = "EXPLICIT_XI"
    FIXED_KAPPA = "FIXED_KAPPA"


class GapModel(str, Enum):
    CLEAN = "CLEAN"
    DIRTY = "DIRTY"


class FitRoute(str, Enum):
    """TWO_STEP fits lambda(T) obtained by inverting equation (1) point by
    point. DIRECT fits the measured Jc(T) in one pass. Research R6."""
    TWO_STEP = "TWO_STEP"
    DIRECT = "DIRECT"


class CorrelationMode(str, Enum):
    """Whether a stated input uncertainty is one calibration error shared by the
    whole dataset or scatter redrawn at every temperature. Research R8.3 shows
    the two give materially different uncertainties on Delta(0)."""
    SYSTEMATIC = "SYSTEMATIC"
    INDEPENDENT = "INDEPENDENT"


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class CouplingRegime(str, Enum):
    BELOW_BCS = "BELOW_BCS"
    WEAK_COUPLING_BCS = "WEAK_COUPLING_BCS"
    MODERATELY_STRONG = "MODERATELY_STRONG"
    STRONG_COUPLING = "STRONG_COUPLING"


class JobState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


# --- input -------------------------------------------------------------------

@dataclass(frozen=True)
class MeasurementDataset:
    """Measured data, already converted to SI.

    Validation of positivity, length agreement, and point count belongs to the
    boundary that builds this (see `validation.build_dataset`), not here, so
    that a failure can name the offending row.
    """

    temperature_K: FloatArray
    jc: FloatArray
    hc2: FloatArray | None = None
    xi: FloatArray | None = None

    @property
    def n_points(self) -> int:
        return int(self.temperature_K.size)


@dataclass(frozen=True)
class AnalysisSettings:
    coherence_source: CoherenceSource
    kappa_fixed: float | None = None
    gap_model: GapModel = GapModel.CLEAN
    fit_route: FitRoute = FitRoute.TWO_STEP
    tc_fixed_K: float | None = None
    film_thickness_m: float | None = None
    root_xtol: float = 1e-15
    root_rtol: float = 1e-12


@dataclass(frozen=True)
class UncertaintySettings:
    """Relative sigmas are fractions, not percentages. The percentage form is a
    display concern and is converted at the API boundary."""

    jc_rel_sigma: float = 0.0
    hc2_rel_sigma: float = 0.0
    xi_rel_sigma: float = 0.0
    kappa_rel_sigma: float = 0.0
    correlation_mode: CorrelationMode = CorrelationMode.SYSTEMATIC
    n_samples: int = 5000
    confidence: float = 0.6827
    seed: int = 12345

    @property
    def any_uncertainty(self) -> bool:
        return max(self.jc_rel_sigma, self.hc2_rel_sigma,
                   self.xi_rel_sigma, self.kappa_rel_sigma) > 0.0


# --- per-temperature results -------------------------------------------------

@dataclass(frozen=True)
class LambdaTable:
    """Parallel arrays, in the caller's original order."""

    temperature_K: FloatArray
    jc: FloatArray
    xi: FloatArray
    lambda_: FloatArray
    kappa: FloatArray


# --- fit results -------------------------------------------------------------

@dataclass(frozen=True)
class FittedParameter:
    value: float
    stderr: float | None = None
    fixed: bool = False


@dataclass(frozen=True)
class FitResult:
    gap_model: GapModel
    fit_route: FitRoute
    lambda0: FittedParameter          # m
    delta0: FittedParameter           # J
    tc: FittedParameter               # K
    coupling_ratio: FittedParameter   # dimensionless
    chi2_reduced: float
    residuals: FloatArray
    #: lambda0^2 / lambda_data^2 at each measured point, in input order. What
    #: the data look like on a superfluid-density plot. It needs lambda0, so
    #: only the fit can produce it.
    rho_s_measured: FloatArray
    #: Equation (1) at the fitted parameters, at each measured temperature, in
    #: input order (A/m^2). One value per measurement, so that it exports beside
    #: the measured column; `SuperfluidCurve.jc` is the same model drawn as a
    #: curve, and passes through these points by construction (FR-026a).
    jc_model: FloatArray
    n_points: int
    n_free_parameters: int
    converged: bool
    n_function_evaluations: int


@dataclass(frozen=True)
class SuperfluidCurve:
    """A dense model curve for plotting, distinct from residuals at the data."""

    temperature_K: FloatArray
    rho_s: FloatArray
    lambda_: FloatArray
    #: Equation (1) along the same grid (A/m^2). NaN wherever the coherence
    #: length is not available without an added assumption, which under
    #: FROM_HC2 and EXPLICIT_XI is everywhere outside the span of the
    #: measurements (FR-026a). Under FIXED_KAPPA the whole grid is populated,
    #: because there xi follows the fit.
    jc: FloatArray


# --- diagnostics -------------------------------------------------------------

@dataclass(frozen=True)
class Warning_:
    """Named with a trailing underscore to avoid shadowing the builtin.

    Carries a code and structured params, never a display sentence
    (constitution IV).
    """

    code: str
    severity: Severity
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DiagnosticReport:
    chi2_reduced: float
    coupling_ratio: float
    coupling_regime: CouplingRegime
    bcs_ratio_reference: float
    t_min_over_tc: float
    kappa_min: float
    kappa_max: float
    warnings: list[Warning_]
    chi2_clean: float | None = None
    chi2_dirty: float | None = None
    #: None when the data do not separate the two models by enough to say
    #: (research R10). That is the common case at realistic scatter, not a
    #: failure.
    preferred_model: GapModel | None = None
    #: Akaike separation of the two gap models, research R10 equation (16).
    delta_aic: float | None = None
    #: Akaike weight, equation (17): the relative support for whichever model
    #: fits better, whether or not it cleared the threshold to be declared.
    preferred_model_weight: float | None = None


# --- uncertainty results -----------------------------------------------------

@dataclass(frozen=True)
class ParameterDistribution:
    mean: float
    std: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class UncertaintyResult:
    lambda0: ParameterDistribution     # m
    delta0: ParameterDistribution      # J
    tc: ParameterDistribution          # K
    coupling_ratio: ParameterDistribution
    n_valid: int
    n_requested: int
    settings: UncertaintySettings
    warnings: list[Warning_] = field(default_factory=list)


# --- the whole thing ---------------------------------------------------------

@dataclass(frozen=True)
class AnalysisResult:
    dataset: MeasurementDataset
    settings: AnalysisSettings
    lambda_table: LambdaTable
    fit: FitResult
    curve: SuperfluidCurve
    diagnostics: DiagnosticReport
    uncertainty: UncertaintyResult | None = None
