"""HTTP endpoints.

Every function here is thin on purpose: validate, convert, call the core,
convert back. Anything longer than a few lines belongs in `core/` where it can
be tested without a server (plan.md section 2).

The contract these implement is specs/001-jc-to-gap/contracts/openapi.yaml.
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Response, status

from .. import examples_store, schemas
from ..core import pipeline
from ..core.parsing import parse_table
from ..jobs import store as job_store

router = APIRouter(prefix="/api", tags=["analysis"])


# --- data entry --------------------------------------------------------------

@router.post("/parse", response_model=schemas.ParseResponse, tags=["data"])
def parse(request: schemas.ParseRequest) -> schemas.ParseResponse:
    """Interpret text as a numeric table and report how it was read.

    Performs no physics. Separate from the analysis so that a misread file is
    caught before any computation and before any unit is chosen (FR-003).
    """
    return schemas.ParseResponse.of(parse_table(request.text, request.comment_prefix))


@router.get("/examples", response_model=list[schemas.ExampleSummary], tags=["data"])
def list_examples() -> list[dict]:
    """The built-in example datasets (FR-028)."""
    return examples_store.summaries()


@router.get("/examples/{name}", response_model=schemas.Example, tags=["data"])
def get_example(name: str) -> dict:
    return examples_store.load(name)


# --- analysis ----------------------------------------------------------------

@router.post("/lambda", response_model=schemas.LambdaResponse)
def lambda_table(request: schemas.LambdaRequest) -> schemas.LambdaResponse:
    """Per-temperature inversion only, without a gap fit (FR-006, FR-007).

    Useful when the data are too sparse to fit a gap, or when the user only
    wants to look at lambda(T) and kappa(T).
    """
    table = pipeline.run_lambda_table(
        request.dataset.to_domain(), request.settings.to_domain()
    )
    return schemas.LambdaResponse.of(table)


@router.post("/analyze", response_model=schemas.AnalyzeResponse)
def analyze(request: schemas.AnalyzeRequest) -> schemas.AnalyzeResponse:
    """The full chain from Jc to the gap.

    Uncertainty propagation is not done here: it is slow, and FR-018 requires
    the page to stay usable while it runs. See POST /api/uncertainty.
    """
    result = pipeline.run_analysis(
        request.dataset.to_domain(), request.settings.to_domain()
    )
    return schemas.AnalyzeResponse.of(result, request.settings)


# --- uncertainty -------------------------------------------------------------

@router.post(
    "/uncertainty",
    response_model=schemas.JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["uncertainty"],
)
def start_uncertainty(request: schemas.UncertaintyRequest) -> schemas.JobAccepted:
    """Start a Monte Carlo run in the background and return its identifier.

    The dataset and settings are validated here, synchronously, so that a
    misconfiguration is refused immediately rather than after minutes of
    computation.
    """
    dataset = request.dataset.to_domain()
    settings = request.settings.to_domain()
    pipeline.run_lambda_table(dataset, settings)      # fail fast on bad input

    job_id = job_store.submit(dataset, settings, request.uncertainty.to_domain())
    return schemas.JobAccepted(job_id=job_id)


@router.get("/jobs/{job_id}", response_model=schemas.JobStatus, tags=["uncertainty"])
def job_status(job_id: str) -> schemas.JobStatus:
    job = job_store.get(job_id)
    return schemas.JobStatus(
        job_id=job.job_id,
        state=job.state,
        progress=job.progress,
        result=(
            None if job.result is None
            else schemas.UncertaintyResultOut.of(job.result)
        ),
        error=None if job.error is None else schemas.ErrorPayload(**job.error),
    )


# --- export ------------------------------------------------------------------

#: Column headers for the exported table. Each carries its unit, because a
#: number without one is not a result (QA-004). Defined here rather than in the
#: frontend so that units and names exist in exactly one place.
_CSV_COLUMNS = [
    ("T_K", "temperature_K"),
    ("Jc_A_per_m2", "jc_A_per_m2"),
    ("xi_nm", "xi_nm"),
    ("lambda_nm", "lambda_nm"),
    ("kappa", "kappa"),
]


@router.post("/export/csv", tags=["export"])
def export_csv(result: schemas.AnalyzeResponse) -> Response:
    """Render a completed analysis as a spreadsheet-readable table (FR-027).

    The fitted parameters and the assumptions in play go in a comment block
    above the table, so that the file is self-describing once it has been
    detached from the screen that produced it (constitution VI).
    """
    buffer = io.StringIO()
    fit, diagnostics = result.fit, result.diagnostics

    def comment(line: str = "") -> None:
        buffer.write(f"# {line}\n" if line else "#\n")

    comment("Nodeless SC gap extraction")
    comment()
    comment(f"gap model            : {fit.gap_model.value}")
    comment(f"extraction route     : {fit.fit_route.value}")
    comment(f"lambda(0) [nm]       : {_pm(fit.lambda0_nm)}")
    comment(f"Delta(0) [meV]       : {_pm(fit.delta0_meV)}")
    comment(f"Tc [K]               : {_pm(fit.tc_K)}"
            + ("  (held fixed)" if fit.tc_K.fixed else ""))
    comment(f"2 Delta(0) / kB Tc   : {_pm(fit.coupling_ratio)}"
            f"   BCS weak coupling {diagnostics.bcs_ratio_reference}")
    comment(f"coupling regime      : {diagnostics.coupling_regime.value}")
    comment(f"reduced chi-squared  : {fit.chi2_reduced:.6g}")
    if diagnostics.chi2_clean is not None and diagnostics.chi2_dirty is not None:
        preferred = (diagnostics.preferred_model.value
                     if diagnostics.preferred_model else "not distinguishable")
        comment(f"clean vs dirty       : chi2 {diagnostics.chi2_clean:.6g} vs "
                f"{diagnostics.chi2_dirty:.6g}, Delta_AIC "
                f"{diagnostics.delta_aic:.3g} -> {preferred}")

    if result.uncertainty is not None:
        unc = result.uncertainty
        comment()
        comment(f"Monte Carlo, {unc.n_valid}/{unc.n_requested} draws, seed "
                f"{unc.settings.seed}, {unc.settings.correlation_mode.value}, "
                f"{unc.settings.confidence_percent} % interval")
        comment(f"lambda(0) [nm]       : {_interval(unc.lambda0_nm)}")
        comment(f"Delta(0) [meV]       : {_interval(unc.delta0_meV)}")
        comment(f"Tc [K]               : {_interval(unc.tc_K)}")

    comment()
    for warning in diagnostics.warnings:
        comment(f"{warning.severity.value}: {warning.code} {warning.params or ''}".rstrip())
    comment()

    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([header for header, _ in _CSV_COLUMNS])
    table = result.lambda_table
    columns = [getattr(table, attribute) for _, attribute in _CSV_COLUMNS]
    for row in zip(*columns):
        writer.writerow([f"{value:.10g}" for value in row])

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="nodeless_sc_result.csv"'},
    )


def _pm(parameter: schemas.FittedParameter) -> str:
    if parameter.stderr is None:
        return f"{parameter.value:.6g}"
    return f"{parameter.value:.6g} +/- {parameter.stderr:.3g}"


def _interval(dist: schemas.ParameterDistribution) -> str:
    return (f"{dist.mean:.6g} +/- {dist.std:.3g}"
            f"   [{dist.ci_low:.6g}, {dist.ci_high:.6g}]")
