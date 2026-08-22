# Implementation Plan

**Feature:** 001-jc-to-gap
**Spec:** `spec.md` | **Physics:** `research.md` | **Types:** `data-model.md`
**Constitution:** `../../.specify/memory/constitution.md` v1.0.0

---

## 1. Technical context

| Aspect | Decision |
| --- | --- |
| Backend language | Python 3.11+ (3.12 present on the development machine) |
| Backend framework | FastAPI |
| Validation / serialisation | Pydantic v2 |
| Numerics | NumPy, SciPy |
| Backend tests | pytest |
| Frontend | React 18 + TypeScript, built with Vite |
| Plotting | Plotly.js via `react-plotly.js` |
| Frontend-backend types | generated from the OpenAPI document, not hand-written |
| Packaging | one Docker image, multi-stage (Node build, Python runtime) |
| Local orchestration | Docker Compose for development |
| Persistence | none; all state is in the browser or in process memory |
| Target scale | one user, one machine, datasets of a few hundred points |

## 2. Architecture

Four layers, each allowed to depend only on the one below it.

    frontend/            React. Korean UI text. Talks HTTP only.
        |
    backend/app/api      FastAPI routes. HTTP <-> Pydantic.
        |
    backend/app/schemas  Pydantic models. Wire format. Unit conversion boundary.
        |
    backend/app/core     Pure physics. NumPy in, NumPy out. No framework.

The rule that makes this worth having is that the arrows never reverse.
`core/` cannot import from `schemas/`; `schemas/` cannot import from `api/`.
This is enforced by a test, not by discipline (see section 6).

### Why the schema layer is separate from the core

Pydantic models describe what arrives over the network: units the user chose,
percentages, optional fields, strings. Core dataclasses describe physics: SI
only, no optionality that the physics does not have. Keeping them separate means
the unit conversion and the "which of `hc2`/`xi`/`kappa` is present" branching
happen in exactly one place, at the boundary, and the core never has to ask.

### Request lifecycle for `POST /api/analyze`

1. FastAPI validates the JSON against `AnalyzeRequest` (Pydantic). Malformed
   input never reaches our code.
2. `schemas.to_domain()` converts units to SI and builds `MeasurementDataset`,
   `AnalysisSettings`.
3. `core.pipeline.run_analysis()` performs the whole chain and returns
   `AnalysisResult`. It raises `CoreError` subclasses carrying an error code.
4. `schemas.from_domain()` converts back, adding display-unit fields (`nm`,
   `meV`) alongside the SI values.
5. An exception handler turns any `CoreError` into `{"code", "params"}` with an
   appropriate HTTP status.

## 3. Project structure

```
backend/
  app/
    main.py                 app creation, exception handlers, static mount
    api/
      __init__.py
      routes.py             all endpoints
      deps.py               shared dependencies (job store)
    schemas.py              Pydantic request/response models + conversion
    jobs.py                 in-memory job store, background execution
    core/
      __init__.py
      constants.py          PHI0, MU0, KB, MEV_TO_J, BCS_ALPHA, BCS_RATIO
      types.py              enums and dataclasses from data-model.md
      errors.py             CoreError hierarchy, code constants
      units.py              unit conversion helpers
      parsing.py            text -> numeric table
      lambda_solver.py      equation (1): xi_from_hc2, solve_lambda, lambda_table
      gap_models.py         Delta(T), rho_s clean and dirty  [research R3-R5]
      fitting.py            route A and route B least squares [research R6]
      montecarlo.py         log-normal propagation            [research R8]
      diagnostics.py        thresholds and warnings           [research R10]
      pipeline.py           orchestrates the above into AnalysisResult
  examples/
    nbti_like.txt           example with Hc2 column
    mgb2_like.txt           example with fixed kappa
  tests/
    test_core_purity.py     constitution I enforcement
    test_units.py
    test_parsing.py
    test_lambda_solver.py
    test_gap_models.py      limits, monotonicity        [research R9]
    test_fitting.py         round trip                  [research R9]
    test_montecarlo.py      reproducibility from seed
    test_diagnostics.py     threshold boundaries
    test_legacy_agreement.py
    test_api.py
  pyproject.toml
  Dockerfile

frontend/
  src/
    main.tsx
    App.tsx
    api/client.ts           fetch wrappers
    api/generated.ts        generated from openapi.json - do not edit
    errorMessages.ts        error and warning code -> Korean sentence
    format.ts               SI -> display units and significant figures
    components/
      DataInput.tsx         upload, paste, example picker
      ColumnPreview.tsx     FR-003
      SettingsPanel.tsx     units, coherence source, model, route, Tc
      UncertaintyPanel.tsx  input sigmas, samples, confidence, seed
      LambdaTable.tsx
      FitSummary.tsx
      DiagnosticsPanel.tsx
      Charts.tsx            lambda(T), rho_s(T), residuals
      JobProgress.tsx       FR-018
  index.html
  package.json
  vite.config.ts
  tsconfig.json
  Dockerfile

Dockerfile                  production image (multi-stage)
docker-compose.yml          development
```

## 4. Dependency justification (constitution IX)

Every runtime dependency needs a reason here.

| Dependency | Why it is not avoidable |
| --- | --- |
| FastAPI | The chosen interface is HTTP. Its automatic OpenAPI output is what makes the frontend types generated rather than hand-written, which removes an entire class of mistake. |
| Pydantic | Comes with FastAPI. Validating the request shape declaratively is strictly less code than validating it by hand. |
| NumPy | Array arithmetic across temperature points. |
| SciPy | `brentq` for equation (1) and `least_squares` for the fit. Reimplementing either would be worse. The clean-limit integral uses a fixed Gauss-Legendre rule built from NumPy, not SciPy quadrature — see section 5. |
| React + Vite | Chosen by the project owner in preference to a lighter option. |
| TypeScript | Pays for itself here specifically: the API shape is generated, so a backend change surfaces as a compile error rather than as a blank screen at runtime. |
| Plotly.js | Interactive plots plus a built-in PNG export button, which satisfies half of FR-027 with no code. |

**Deliberately not taken.** Matplotlib on the backend (Plotly's export covers
FR-027). A database (nothing is persisted). Celery or Redis for background jobs
(a thread and a dictionary suffice at this scale, see section 5). Any
internationalisation framework (constitution VIII). Pandas — the parsing this
project needs is a few dozen lines of NumPy, and the dependency is large.

## 5. Notable design decisions

### Long-running uncertainty computation

Monte Carlo with several thousand draws re-runs the whole fit each time and
takes tens of seconds to minutes. Doing that inside the request would block the
connection and give the user nothing to look at, violating FR-018.

`POST /api/uncertainty` therefore starts a `threading.Thread`, registers a
`Job` in a module-level dictionary, and returns a `job_id` immediately.
`GET /api/jobs/{job_id}` returns state and progress. The frontend polls at
roughly 1 Hz.

A thread rather than a process because the work is inside NumPy and SciPy, which
release the GIL; a dictionary rather than a queue system because the application
is single-user, single-container, and loses nothing by forgetting jobs on
restart. If either assumption ever changes, this is the one component to
replace, and it is isolated in `jobs.py` for that reason.

### Evaluating the clean-limit integral

`rho_s_clean` reduces to a single-argument integral in `d = Delta(T)/(2 kB T)`
(research R4). A fit evaluates it of order `n_points x n_iterations` times, and
a Monte Carlo run multiplies that by the number of draws.

Caching was the first idea and was discarded: during a fit the parameters move
every iteration, so `d` is a different float every time and the hit rate is
near zero. The chosen approach is a fixed-node panelled Gauss-Legendre rule,
evaluated for all temperature points in one array operation. Measured against
adaptive quadrature it is 250 times faster at the same accuracy, and it is
deterministic, which the reproducibility requirement needs. Research R4 records
the measurements.

### Serving the frontend from the backend

The production image serves the built static files from the same FastAPI
application that serves the API. One port, one container, no CORS configuration
in production. In development the Vite dev server proxies `/api` to the backend
so that hot reload still works.

### Display units live in the response, not in the frontend

The response carries both `lambda0_m` and `lambda0_nm`, both `delta0_J` and
`delta0_meV`. The conversion factor is a physical constant and belongs next to
the physics, not duplicated in TypeScript where it could drift.

## 6. Constitution check

| Principle | How it is satisfied | Verified by |
| --- | --- | --- |
| I. Core is framework-agnostic | `core/` imports only stdlib, NumPy, SciPy | `test_core_purity.py` scans every module's imports |
| II. No physics without a test | Every `core` function computing a physical quantity has a limit or round-trip test | `research.md` R9 table is the checklist; `tests/` implements it |
| III. Spec precedes implementation | `spec.md` written and reviewed before `tasks.md`; `spec.md` names no technology | manual review of `spec.md` |
| IV. Codes not prose | `ErrorPayload` and `Warning_` carry `code` + `params`; `errorMessages.ts` holds every Korean sentence | `test_api.py` asserts no non-ASCII in any error response |
| V. SI internally | Conversion confined to `core/units.py`, called from `schemas.py` only | `test_units.py`; naming convention reviewed |
| VI. Assumptions travel with results | `AnalysisResult.diagnostics.warnings` always contains at least `SELF_FIELD_TRANSPORT_REQUIRED` | `test_diagnostics.py` |
| VII. Reproducible randomness | `UncertaintySettings.seed` required, echoed in the result | `test_montecarlo.py` runs twice and compares |
| VIII. English code, Korean UI | enforced by review; no Korean literal in `backend/` | `test_api.py` ASCII assertion |
| IX. Simplicity | dependency table in section 4; no database, no task queue, no i18n library | this document |

**Deviations:** none.

## 7. Risks

| Risk | Mitigation |
| --- | --- |
| The clean-limit integral is subtly wrong and produces a plausible gap | The dimensionless reduction in research R4 has two exact analytic limits (`d=0` gives 1, `d>=30` gives 0) that are tested directly, plus a round-trip test through synthetic data |
| Route A and route B disagree | They are tested against the *same* synthetic dataset with known parameters; disagreement fails the build rather than being discovered later |
| The fit finds a local minimum | Bounded trust-region optimisation with physically motivated initial guesses (research R6); `converged` is reported and an unconverged fit is refused (FR-014) |
| Node.js and Docker are not installed yet | Phases 1 and 2 need neither; installation can happen in parallel |
| A future contributor inlines physics into a route for convenience | `test_core_purity.py` fails the build |

## 8. Phasing

| Phase | Delivers | Gate |
| --- | --- | --- |
| 0 | SDD documents, repository skeleton, `legacy/` archived | documents reviewed |
| 1 | `core/` complete with tests | `pytest` green, round-trip within 1 % |
| 2 | API layer, OpenAPI document | every endpoint exercised through `/docs` |
| 3 | Frontend base flow: input, table, fit summary | example dataset analysed in the browser |
| 4 | Charts, export, built-in examples | FR-025 to FR-028 met |
| 5 | Uncertainty jobs and progress | FR-015 to FR-018 met |
| 6 | Diagnostics panel | FR-019 to FR-024 met |
| 7 | Docker image, README | `docker compose up` reproduces phase 6 |

Detailed tasks are in `tasks.md`.
