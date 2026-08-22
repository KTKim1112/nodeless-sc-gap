"""Wire format, and the boundary where units enter and leave.

Pydantic models describing what arrives over HTTP and what goes back. They are
deliberately not the same objects as the dataclasses in `core.types`:

  - These carry the units the user chose, percentages, optional fields, and
    strings. Core types are SI only, with no optionality the physics does not
    have (constitution V).
  - Keeping them apart means the conversion and the "which of hc2 / xi / kappa
    is present" branching happen in exactly one place, here, and the physics
    never has to ask.
  - Changing the wire format then cannot force a change in the physics.

The definitive description of the wire format is
specs/001-jc-to-gap/contracts/openapi.yaml. This module is the code that
follows it, and tests/test_api.py checks that the two have not drifted apart.
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from .core import types as t
from .core import units as u
from .core.parsing import ParsedTable
from .core.validation import build_dataset


def _list(values) -> list[float]:
    """NumPy array to a JSON-serialisable list."""
    return [float(x) for x in np.asarray(values, dtype=float).ravel()]


class Model(BaseModel):
    """Base: reject unknown fields rather than silently ignoring them.

    A misspelled field name is far more often a mistake than an intention, and
    a silently ignored `gap_modle` would produce a plausible wrong answer.
    """

    model_config = ConfigDict(extra="forbid")


# --- errors and warnings -----------------------------------------------------

class ErrorPayload(Model):
    """The only failure shape the API returns (constitution IV)."""

    code: str = Field(description="Stable identifier from the data-model.md catalogue")
    params: dict[str, Any] = Field(default_factory=dict)


class WarningOut(Model):
    code: str
    severity: t.Severity
    params: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def of(cls, warning: t.Warning_) -> "WarningOut":
        return cls(code=warning.code, severity=warning.severity, params=warning.params)


# --- input -------------------------------------------------------------------

class ParseRequest(Model):
    text: str = Field(description="File contents or pasted text")
    comment_prefix: str = "#"


class ParseResponse(Model):
    n_rows: int
    n_columns: int
    header_detected: bool
    column_names: list[str]
    preview: list[list[float]] = Field(description="First rows, for the user to confirm")
    values: list[list[float]] = Field(description="The full table, in the file's own units")

    @classmethod
    def of(cls, table: ParsedTable, preview_rows: int = 5) -> "ParseResponse":
        rows = [[float(x) for x in row] for row in table.values]
        return cls(
            n_rows=table.n_rows,
            n_columns=table.n_columns,
            header_detected=table.header_detected,
            column_names=table.column_names,
            preview=rows[:preview_rows],
            values=rows,
        )


class Dataset(Model):
    """Measured columns, together with the units they are expressed in."""

    temperature_K: list[float] = Field(min_length=4)
    jc: list[float] = Field(min_length=4)
    jc_unit: t.JcUnit = t.JcUnit.A_PER_CM2
    hc2_T: list[float] | None = Field(
        default=None, description="Required when coherence_source is FROM_HC2"
    )
    xi: list[float] | None = Field(
        default=None, description="Required when coherence_source is EXPLICIT_XI"
    )
    xi_unit: t.XiUnit = t.XiUnit.NM

    def to_domain(self) -> t.MeasurementDataset:
        return build_dataset(
            temperature_K=self.temperature_K,
            jc=u.jc_to_si(self.jc, self.jc_unit),
            hc2=self.hc2_T,
            xi=u.xi_to_si(self.xi, self.xi_unit) if self.xi is not None else None,
        )


class Settings(Model):
    coherence_source: t.CoherenceSource
    kappa_fixed: float | None = Field(
        default=None, description="Required when coherence_source is FIXED_KAPPA"
    )
    gap_model: t.GapModel = t.GapModel.CLEAN
    fit_route: t.FitRoute = t.FitRoute.TWO_STEP
    tc_fixed_K: float | None = Field(
        default=None, description="When present, Tc is held rather than fitted"
    )
    film_thickness_nm: float | None = Field(
        default=None, description="Diagnostics only; never enters the physics"
    )
    root_xtol: float = 1e-15
    root_rtol: float = 1e-12

    def to_domain(self) -> t.AnalysisSettings:
        return t.AnalysisSettings(
            coherence_source=self.coherence_source,
            kappa_fixed=self.kappa_fixed,
            gap_model=self.gap_model,
            fit_route=self.fit_route,
            tc_fixed_K=self.tc_fixed_K,
            film_thickness_m=(
                u.nm_to_m(self.film_thickness_nm)
                if self.film_thickness_nm is not None else None
            ),
            root_xtol=self.root_xtol,
            root_rtol=self.root_rtol,
        )


class UncertaintySettingsIn(Model):
    """Percentages here, fractions in the core.

    The percentage is what an experimentalist writes down; the fraction is what
    the arithmetic wants. The conversion belongs at this boundary and nowhere
    else.
    """

    jc_error_percent: float = Field(default=0.0, ge=0.0)
    hc2_error_percent: float = Field(default=0.0, ge=0.0)
    xi_error_percent: float = Field(default=0.0, ge=0.0)
    kappa_error_percent: float = Field(default=0.0, ge=0.0)
    correlation_mode: t.CorrelationMode = t.CorrelationMode.SYSTEMATIC
    n_samples: int = Field(default=5000, ge=100, le=200_000)
    confidence_percent: float = Field(default=68.27, gt=0.0, lt=100.0)
    seed: int = 12345

    def to_domain(self) -> t.UncertaintySettings:
        return t.UncertaintySettings(
            jc_rel_sigma=self.jc_error_percent / 100.0,
            hc2_rel_sigma=self.hc2_error_percent / 100.0,
            xi_rel_sigma=self.xi_error_percent / 100.0,
            kappa_rel_sigma=self.kappa_error_percent / 100.0,
            correlation_mode=self.correlation_mode,
            n_samples=self.n_samples,
            confidence=self.confidence_percent / 100.0,
            seed=self.seed,
        )

    @classmethod
    def of(cls, settings: t.UncertaintySettings) -> "UncertaintySettingsIn":
        return cls(
            jc_error_percent=settings.jc_rel_sigma * 100.0,
            hc2_error_percent=settings.hc2_rel_sigma * 100.0,
            xi_error_percent=settings.xi_rel_sigma * 100.0,
            kappa_error_percent=settings.kappa_rel_sigma * 100.0,
            correlation_mode=settings.correlation_mode,
            n_samples=settings.n_samples,
            confidence_percent=settings.confidence * 100.0,
            seed=settings.seed,
        )


class LambdaRequest(Model):
    dataset: Dataset
    settings: Settings


class AnalyzeRequest(LambdaRequest):
    pass


class UncertaintyRequest(Model):
    dataset: Dataset
    settings: Settings
    uncertainty: UncertaintySettingsIn


# --- output ------------------------------------------------------------------

class LambdaResponse(Model):
    """SI is always present; the nm columns are additions for display."""

    temperature_K: list[float]
    jc_A_per_m2: list[float]
    xi_m: list[float]
    xi_nm: list[float]
    lambda_m: list[float]
    lambda_nm: list[float]
    kappa: list[float]
    warnings: list[WarningOut] = Field(default_factory=list)

    @classmethod
    def of(cls, table: t.LambdaTable,
           warnings: list[t.Warning_] | None = None) -> "LambdaResponse":
        return cls(
            temperature_K=_list(table.temperature_K),
            jc_A_per_m2=_list(table.jc),
            xi_m=_list(table.xi),
            xi_nm=_list(u.m_to_nm(table.xi)),
            lambda_m=_list(table.lambda_),
            lambda_nm=_list(u.m_to_nm(table.lambda_)),
            kappa=_list(table.kappa),
            warnings=[WarningOut.of(w) for w in (warnings or [])],
        )


class FittedParameter(Model):
    value: float
    stderr: float | None = Field(
        default=None, description="null when the covariance matrix is singular"
    )
    fixed: bool = False

    @classmethod
    def of(cls, parameter: t.FittedParameter, scale: float = 1.0) -> "FittedParameter":
        return cls(
            value=parameter.value * scale,
            stderr=None if parameter.stderr is None else parameter.stderr * scale,
            fixed=parameter.fixed,
        )


class FitResultOut(Model):
    gap_model: t.GapModel
    fit_route: t.FitRoute
    converged: bool = Field(
        description="When false the frontend must not present this as a result"
    )
    lambda0_m: FittedParameter
    lambda0_nm: FittedParameter
    delta0_J: FittedParameter
    delta0_meV: FittedParameter
    tc_K: FittedParameter
    coupling_ratio: FittedParameter
    chi2_reduced: float
    residuals: list[float]
    n_points: int
    n_free_parameters: int
    n_function_evaluations: int

    @classmethod
    def of(cls, fit: t.FitResult) -> "FitResultOut":
        from .core.constants import MEV_TO_J

        return cls(
            gap_model=fit.gap_model,
            fit_route=fit.fit_route,
            converged=fit.converged,
            lambda0_m=FittedParameter.of(fit.lambda0),
            lambda0_nm=FittedParameter.of(fit.lambda0, 1e9),
            delta0_J=FittedParameter.of(fit.delta0),
            delta0_meV=FittedParameter.of(fit.delta0, 1.0 / MEV_TO_J),
            tc_K=FittedParameter.of(fit.tc),
            coupling_ratio=FittedParameter.of(fit.coupling_ratio),
            chi2_reduced=fit.chi2_reduced,
            residuals=_list(fit.residuals),
            n_points=fit.n_points,
            n_free_parameters=fit.n_free_parameters,
            n_function_evaluations=fit.n_function_evaluations,
        )


class SuperfluidCurveOut(Model):
    temperature_K: list[float]
    rho_s: list[float]
    lambda_nm: list[float]

    @classmethod
    def of(cls, curve: t.SuperfluidCurve) -> "SuperfluidCurveOut":
        return cls(
            temperature_K=_list(curve.temperature_K),
            rho_s=_list(curve.rho_s),
            lambda_nm=_list(u.m_to_nm(curve.lambda_)),
        )


class DiagnosticReportOut(Model):
    chi2_reduced: float
    chi2_clean: float | None = None
    chi2_dirty: float | None = None
    preferred_model: t.GapModel | None = None
    delta_aic: float | None = None
    preferred_model_weight: float | None = None
    coupling_ratio: float
    coupling_regime: t.CouplingRegime
    bcs_ratio_reference: float = Field(
        description="Supplied so the frontend never hard-codes a physical constant"
    )
    t_min_over_tc: float
    kappa_min: float
    kappa_max: float
    warnings: list[WarningOut]

    @classmethod
    def of(cls, report: t.DiagnosticReport) -> "DiagnosticReportOut":
        return cls(
            chi2_reduced=report.chi2_reduced,
            chi2_clean=report.chi2_clean,
            chi2_dirty=report.chi2_dirty,
            preferred_model=report.preferred_model,
            delta_aic=report.delta_aic,
            preferred_model_weight=report.preferred_model_weight,
            coupling_ratio=report.coupling_ratio,
            coupling_regime=report.coupling_regime,
            bcs_ratio_reference=report.bcs_ratio_reference,
            t_min_over_tc=report.t_min_over_tc,
            kappa_min=report.kappa_min,
            kappa_max=report.kappa_max,
            warnings=[WarningOut.of(w) for w in report.warnings],
        )


class ParameterDistribution(Model):
    mean: float
    std: float
    ci_low: float
    ci_high: float

    @classmethod
    def of(cls, dist: t.ParameterDistribution, scale: float = 1.0) -> "ParameterDistribution":
        return cls(
            mean=dist.mean * scale,
            std=dist.std * scale,
            ci_low=dist.ci_low * scale,
            ci_high=dist.ci_high * scale,
        )


class UncertaintyResultOut(Model):
    lambda0_nm: ParameterDistribution
    delta0_meV: ParameterDistribution
    tc_K: ParameterDistribution
    coupling_ratio: ParameterDistribution
    n_valid: int
    n_requested: int
    settings: UncertaintySettingsIn = Field(
        description="Echoed verbatim including the seed, so the result is reproducible"
    )
    warnings: list[WarningOut] = Field(default_factory=list)

    @classmethod
    def of(cls, result: t.UncertaintyResult) -> "UncertaintyResultOut":
        from .core.constants import MEV_TO_J

        return cls(
            lambda0_nm=ParameterDistribution.of(result.lambda0, 1e9),
            delta0_meV=ParameterDistribution.of(result.delta0, 1.0 / MEV_TO_J),
            tc_K=ParameterDistribution.of(result.tc),
            coupling_ratio=ParameterDistribution.of(result.coupling_ratio),
            n_valid=result.n_valid,
            n_requested=result.n_requested,
            settings=UncertaintySettingsIn.of(result.settings),
            warnings=[WarningOut.of(w) for w in result.warnings],
        )


class AnalyzeResponse(Model):
    lambda_table: LambdaResponse
    fit: FitResultOut
    curve: SuperfluidCurveOut
    diagnostics: DiagnosticReportOut
    settings: Settings
    uncertainty: UncertaintyResultOut | None = None

    @classmethod
    def of(cls, result: t.AnalysisResult, settings: Settings) -> "AnalyzeResponse":
        return cls(
            lambda_table=LambdaResponse.of(result.lambda_table),
            fit=FitResultOut.of(result.fit),
            curve=SuperfluidCurveOut.of(result.curve),
            diagnostics=DiagnosticReportOut.of(result.diagnostics),
            settings=settings,
            uncertainty=(
                None if result.uncertainty is None
                else UncertaintyResultOut.of(result.uncertainty)
            ),
        )


# --- examples ----------------------------------------------------------------

class ExampleSummary(Model):
    name: str
    title: str
    coherence_source: t.CoherenceSource
    n_points: int
    expects_model_preference: bool = Field(
        description=(
            "Whether this example's data are clean enough to separate the "
            "clean and dirty limits. One shipped example is and one is not."
        )
    )


class Example(ExampleSummary):
    text: str = Field(description="Raw file contents, to be sent to /api/parse unchanged")
    suggested_settings: Settings


# --- jobs --------------------------------------------------------------------

class JobAccepted(Model):
    job_id: str


class JobStatus(Model):
    job_id: str
    state: t.JobState
    progress: float = Field(ge=0.0, le=1.0)
    result: UncertaintyResultOut | None = None
    error: ErrorPayload | None = None


class Health(Model):
    status: Literal["ok"] = "ok"
    version: str
