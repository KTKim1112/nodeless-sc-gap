# Data Model

**Feature:** 001-jc-to-gap

Domain types owned by `backend/app/core/`. They are plain dataclasses and enums
with no dependency on any web framework (constitution I). The API layer defines
its own request and response schemas and converts to and from these; the two are
deliberately not the same objects, so that changing the wire format cannot force
a change in the physics.

All lengths are metres, all energies joules, all current densities A/m^2, all
fields tesla, all temperatures kelvin (constitution V). Fields whose name ends
in a unit suffix are the only exceptions and exist for display.

---

## Enumerations

```
JcUnit          A_PER_CM2 | A_PER_M2
XiUnit          M | NM | UM
CoherenceSource FROM_HC2 | EXPLICIT_XI | FIXED_KAPPA
GapModel        CLEAN | DIRTY
FitRoute        TWO_STEP | DIRECT
CorrelationMode SYSTEMATIC | INDEPENDENT
Severity        INFO | WARNING | ERROR
JobState        PENDING | RUNNING | SUCCEEDED | FAILED
```

---

## `MeasurementDataset`

The measured data after parsing and unit conversion. Immutable.

| Field | Type | Unit | Notes |
| --- | --- | --- | --- |
| `temperature_K` | `float[]` | K | strictly positive, length `n >= 4` |
| `jc` | `float[]` | A/m^2 | strictly positive, length `n` |
| `hc2` | `float[] \| None` | T | present iff source is `FROM_HC2` |
| `xi` | `float[] \| None` | m | present iff source is `EXPLICIT_XI` |

**Invariants.** All present arrays have equal length. No NaN, no infinity, no
non-positive entry. Temperatures need not be sorted; the core sorts internally
and reports results in the caller's original order.

**Rationale for `n >= 4`.** Three free parameters are fitted; fewer than four
points cannot produce a meaningful residual degree of freedom.

---

## `AnalysisSettings`

Everything the user chose. Carried alongside every result so that a result is
always self-describing (constitution VI).

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `coherence_source` | `CoherenceSource` | — | selects which of `hc2`, `xi`, `kappa_fixed` is used |
| `kappa_fixed` | `float \| None` | `None` | required iff source is `FIXED_KAPPA`; must exceed `exp(-0.5)` |
| `gap_model` | `GapModel` | `CLEAN` | |
| `fit_route` | `FitRoute` | `TWO_STEP` | |
| `tc_fixed_K` | `float \| None` | `None` | when set, `Tc` is held and not fitted; must exceed `max(temperature_K)` |
| `film_thickness_m` | `float \| None` | `None` | diagnostics only, never enters the physics |
| `root_xtol` | `float` | `1e-15` | absolute tolerance of the root finder, in metres |
| `root_rtol` | `float` | `1e-12` | relative tolerance of the root finder |

**The two root tolerances are not exposed over the wire.** They are termination
conditions of the Brent solver, and the numerical error they control is many
orders of magnitude below any experimental uncertainty; tightening them cannot
improve a result and loosening them can only break one. Putting them in the
request would have made every client send two numbers it has no basis for
choosing. They stay here, in the core, with their defaults.

---

## `UncertaintySettings`

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `jc_rel_sigma` | `float` | `0.0` | relative 1-sigma, as a fraction not a percentage |
| `hc2_rel_sigma` | `float` | `0.0` | used iff source is `FROM_HC2` |
| `xi_rel_sigma` | `float` | `0.0` | used iff source is `EXPLICIT_XI` |
| `kappa_rel_sigma` | `float` | `0.0` | used iff source is `FIXED_KAPPA` |
| `correlation_mode` | `CorrelationMode` | `SYSTEMATIC` | see below |
| `n_samples` | `int` | `5000` | at least 100 |
| `confidence` | `float` | `0.6827` | strictly between 0 and 1 |
| `seed` | `int` | `12345` | reported back with the result |

Stored as fractions rather than percentages so that no conversion exists inside
the core. The percentage form is a display concern of the frontend.

**`correlation_mode`** decides whether one perturbation is shared by every
temperature point (`SYSTEMATIC`) or drawn independently at each one
(`INDEPENDENT`). Research R8.3 shows the two give materially different answers:
a common multiplicative error in `Jc` moves `lambda(0)` but leaves `Delta(0)`
and `Tc` essentially untouched, whereas point-to-point scatter propagates into
all three and averages down as `1/sqrt(n)`.

The default is `SYSTEMATIC` because the dominant real uncertainty in a
transport `Jc` is geometric — bridge width and film thickness — and a geometric
error is the same at every temperature by construction. Choosing `INDEPENDENT`
by default would report a `Delta(0)` uncertainty that the stated input error
does not actually imply.

---

## `LambdaTable`

Result of the per-temperature inversion. Arrays are parallel and in the caller's
original order.

| Field | Type | Unit |
| --- | --- | --- |
| `temperature_K` | `float[]` | K |
| `jc` | `float[]` | A/m^2 |
| `xi` | `float[]` | m |
| `lambda_` | `float[]` | m |
| `kappa` | `float[]` | — |

`lambda_` carries a trailing underscore because `lambda` is a reserved word in
Python. This is the one naming compromise in the project and is deliberate:
renaming it to something like `pen_depth` would make the code stop resembling
the equations it implements.

---

## `FittedParameter`

| Field | Type | Notes |
| --- | --- | --- |
| `value` | `float` | SI |
| `stderr` | `float \| None` | `None` when the covariance matrix is singular |
| `fixed` | `bool` | true when held rather than fitted |

---

## `FitResult`

| Field | Type | Unit | Notes |
| --- | --- | --- | --- |
| `gap_model` | `GapModel` | — | which model produced this |
| `fit_route` | `FitRoute` | — | |
| `lambda0` | `FittedParameter` | m | |
| `delta0` | `FittedParameter` | J | |
| `tc` | `FittedParameter` | K | |
| `coupling_ratio` | `FittedParameter` | — | `2*delta0/(KB*tc)`, derived |
| `chi2_reduced` | `float` | — | |
| `residuals` | `float[]` | — | one per data point, in input order |
| `rho_s_measured` | `float[]` | — | `lambda0^2 / lambda_data^2` at each measured point, in input order |
| `n_points` | `int` | — | |
| `n_free_parameters` | `int` | — | |
| `converged` | `bool` | — | false means the result must not be displayed as a fit (FR-014) |
| `n_function_evaluations` | `int` | — | |

`residuals` are differences of natural logarithms in both routes: of `lambda`
for `TWO_STEP`, of `Jc` for `DIRECT` (research R6). They are therefore
fractional deviations to first order, and comparable in magnitude between the
two routes, though not the same quantity. The route field is what tells a
reader which it is.

`rho_s_measured` is what the measured points look like on a superfluid-density
plot, and it lives here rather than being computed by whoever draws the plot
because it needs `lambda0`, which only the fit knows. Keeping the definition
`rho_s = lambda0^2 / lambda^2` in one place is the same reason every other
formula is in the core.

---

## `SuperfluidCurve`

A densely sampled model curve for plotting, distinct from the residuals at the
measured points.

| Field | Type | Unit |
| --- | --- | --- |
| `temperature_K` | `float[]` | K |
| `rho_s` | `float[]` | — |
| `lambda_` | `float[]` | m |

Sampled on a uniform grid from the lowest measured temperature to the fitted
`Tc`, 200 points by default.

---

## `Warning_`

The unit of everything the system needs to tell the user about assumptions.
Never contains a display sentence (constitution IV).

| Field | Type | Notes |
| --- | --- | --- |
| `code` | `str` | stable identifier, see the catalogue below |
| `severity` | `Severity` | |
| `params` | `dict[str, float \| str]` | values the frontend interpolates into its sentence |

### Warning code catalogue

| Code | Severity | `params` |
| --- | --- | --- |
| `SELF_FIELD_TRANSPORT_REQUIRED` | INFO | — (always emitted, FR-024) |
| `CROSS_QUANTITY_CORRELATION_IGNORED` | INFO | `correlation_mode` (emitted with every uncertainty result; correlation *within* a quantity is modelled by the mode, correlation *between* `Jc` and `Hc2`/`xi`/`kappa` is not) |
| `ISOTROPIC_GL_ASSUMED` | INFO | — (emitted when source is `FROM_HC2`) |
| `KAPPA_NEAR_TYPE_I_BOUNDARY` | WARNING | `kappa_min`, `temperature_K` |
| `LOW_T_COVERAGE_WEAK` | WARNING | `t_min_over_tc` |
| `LOW_T_COVERAGE_INSUFFICIENT` | WARNING | `t_min_over_tc` |
| `THIN_FILM_ASSUMPTION_STRAINED` | WARNING | `thickness_m`, `lambda0_m` |
| `MODELS_INDISTINGUISHABLE` | INFO | `chi2_clean`, `chi2_dirty` |
| `STDERR_UNAVAILABLE` | WARNING | `parameter` |
| `MC_SAMPLES_DISCARDED` | WARNING | `n_valid`, `n_requested` |

---

## `DiagnosticReport`

| Field | Type | Notes |
| --- | --- | --- |
| `chi2_reduced` | `float` | of the selected model |
| `chi2_clean` | `float \| None` | both are computed for FR-020 |
| `chi2_dirty` | `float \| None` | |
| `preferred_model` | `GapModel \| None` | `None` when indistinguishable |
| `coupling_ratio` | `float` | |
| `coupling_regime` | `str` | one of `BELOW_BCS`, `WEAK_COUPLING_BCS`, `MODERATELY_STRONG`, `STRONG_COUPLING` (research R10) |
| `bcs_ratio_reference` | `float` | `3.52775`, so the frontend never hard-codes it |
| `t_min_over_tc` | `float` | |
| `kappa_min` | `float` | |
| `kappa_max` | `float` | |
| `warnings` | `Warning_[]` | |

---

## `ParameterDistribution`

One fitted parameter after uncertainty propagation.

| Field | Type |
| --- | --- |
| `mean` | `float` |
| `std` | `float` |
| `ci_low` | `float` |
| `ci_high` | `float` |

---

## `UncertaintyResult`

| Field | Type | Notes |
| --- | --- | --- |
| `lambda0` | `ParameterDistribution` | m |
| `delta0` | `ParameterDistribution` | J |
| `tc` | `ParameterDistribution` | K |
| `coupling_ratio` | `ParameterDistribution` | — |
| `n_valid` | `int` | draws that survived |
| `n_requested` | `int` | |
| `settings` | `UncertaintySettings` | echoed back verbatim, including the seed and the correlation mode (constitution VII) |

The standard errors already present in `FitResult` are **not** replaced by these
distributions and **not** added to them. They measure different things and are
reported side by side; research R8.6 explains why combining them is the user's
judgement to make, not the tool's.

---

## `AnalysisResult`

What a complete analysis returns. This is the single object the API serialises.

| Field | Type |
| --- | --- |
| `dataset` | `MeasurementDataset` |
| `settings` | `AnalysisSettings` |
| `lambda_table` | `LambdaTable` |
| `fit` | `FitResult` |
| `curve` | `SuperfluidCurve` |
| `diagnostics` | `DiagnosticReport` |
| `uncertainty` | `UncertaintyResult \| None` |

---

## `Job`

State of a long-running uncertainty computation (FR-018). Held in process
memory; not persisted, because the application is single-user and single-machine
by QA-005.

| Field | Type | Notes |
| --- | --- | --- |
| `job_id` | `str` | opaque |
| `state` | `JobState` | |
| `progress` | `float` | 0.0 to 1.0 |
| `result` | `UncertaintyResult \| None` | present iff `SUCCEEDED` |
| `error` | `ErrorPayload \| None` | present iff `FAILED` |

---

## `ErrorPayload`

The only failure shape the API ever returns (constitution IV).

| Field | Type |
| --- | --- |
| `code` | `str` |
| `params` | `dict[str, float \| str \| int]` |

### Error code catalogue

| Code | Raised when | `params` |
| --- | --- | --- |
| `EMPTY_INPUT` | no data rows found | — |
| `COLUMN_COUNT_MISMATCH` | fewer columns than the chosen mode needs | `expected`, `found` |
| `NOT_A_NUMBER` | a cell cannot be parsed | `row`, `column`, `value` |
| `NON_POSITIVE_VALUE` | a strictly positive quantity is zero or negative | `row`, `column`, `value` |
| `TOO_FEW_POINTS` | fewer than four rows | `found`, `required` |
| `UNKNOWN_UNIT` | unrecognised unit string | `unit` |
| `KAPPA_TOO_SMALL` | `kappa <= exp(-0.5)`, model undefined | `kappa` |
| `NOT_TYPE_II` | `kappa <= 1/sqrt(2)` | `kappa` |
| `NO_ROOT_TYPE_II` | `Jc` reaches the ceiling (1a) of equation (1), i.e. the data imply `kappa <= 1` for this `xi` | `temperature_K`, `jc`, `xi`, `jc_max` |
| `ROOT_BRACKETING_FAILED` | upper bracket could not be expanded far enough | `temperature_K` |
| `TC_FIXED_BELOW_DATA` | a fixed `Tc` is not above every measured temperature | `tc_fixed_K`, `t_max_K` |
| `FIT_DID_NOT_CONVERGE` | the optimiser terminated without convergence | `route`, `model`, `status` |
| `MC_TOO_MANY_FAILURES` | fewer than `max(100, N/2)` draws survived | `n_valid`, `n_requested` |
| `JOB_NOT_FOUND` | unknown job identifier | `job_id` |

Codes are additive: a new one may be introduced, but an existing code must not
change meaning, because the frontend maps codes to Korean sentences by exact
match.
