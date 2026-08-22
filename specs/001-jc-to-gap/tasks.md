# Tasks

**Feature:** 001-jc-to-gap
**Reads:** `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`

Each task is small enough to finish and verify in one sitting. `[P]` marks tasks
that touch disjoint files and could be done in any order relative to each other.
A phase is complete only when its gate passes.

Legend: `T###` task id, `->` depends on.

---

## Phase 0 — Documents and skeleton

| Id | Task | Status |
| --- | --- | --- |
| T001 | Initialise the repository, add `.gitignore` | done |
| T002 | Move the prototype scripts and their READMEs to `legacy/`, add `legacy/README.md` explaining their status | done |
| T003 | Write `.specify/memory/constitution.md` | done |
| T004 | Write `spec.md` | done |
| T005 | Write `research.md` | done |
| T006 | Write `data-model.md` | done |
| T007 | Write `plan.md` including the constitution check | done |
| T008 | Write `contracts/openapi.yaml` | done |
| T009 | Write `quickstart.md` | done |
| T010 | Write this file | done |

**Gate:** the documents are internally consistent — every FR in `spec.md` is
reachable from a task below, every equation used below is fixed in `research.md`,
every type below appears in `data-model.md`.

---

## Phase 1 — Physics core

No web framework anywhere in this phase. Verified by `pytest` alone.

| Id | Task | Depends on |
| --- | --- | --- |
| T101 | [done] `backend/pyproject.toml`: package metadata, runtime deps (numpy, scipy, fastapi, pydantic, uvicorn), dev deps (pytest) | — |
| T102 | [done] `core/constants.py` from research R0 | T101 |
| T103 | [done] `core/types.py`: every enum and dataclass in `data-model.md` | T101 |
| T104 | [done] `core/units.py`: `jc_to_si`, `xi_to_si`, `j_to_meV`, `m_to_nm` and inverses; unknown unit raises `UnknownUnitError` | T102, T103 |
| T105 | [done] `core/errors.py`: `CoreError` base carrying `code` and `params`, one subclass per code in the `data-model.md` catalogue. It lives in `core/` and the API layer imports it, not the reverse — the dependency arrow of `plan.md` section 2 must not be bent for this | T103 |
| T106 | [done] `core/parsing.py`: text to float matrix; separators, header detection, comment lines, per-cell error reporting with row and column | T105 |
| T107 | [done] `core/lambda_solver.py`: `xi_from_hc2`, `jc_model`, `solve_lambda` (bracket on `lambda > xi`, expand upper bound, `brentq`), `lambda_from_fixed_kappa` (explicit form, research R7), `build_lambda_table` dispatching on `CoherenceSource` | T102, T105 |
| T108 | [done] `core/gap_models.py`: `delta_of_T` (research R3), `rho_s_clean` via the dimensionless integral (research R4) with the `d >= 30` short circuit and caching, `rho_s_dirty` (research R5), `rho_s` dispatching on `GapModel` | T102 |
| T109 | [done] `core/fitting.py`: `fit_route_a`, `fit_route_b`, shared initial guesses and bounds (research R6), covariance from the Jacobian, `converged` flag, derived coupling ratio with propagated error | T107, T108 |
| T110 | [done] `core/diagnostics.py`: every threshold in research R10, emitting `Warning_` objects; `SELF_FIELD_TRANSPORT_REQUIRED` always present | T107, T109 |
| T111 | [done] `core/montecarlo.py`: log-normal sampling via research R8.2 equations (7) and (8); `SYSTEMATIC` and `INDEPENDENT` correlation modes (R8.3); full-chain re-run per draw; discard-and-count with the `M < max(100, N/2)` bound; percentile intervals; progress callback; seeded RNG | T109 |
| T112 | [done] `core/pipeline.py`: `run_lambda_table`, `run_analysis` composing T107 to T110 into `AnalysisResult`, plus the dense `SuperfluidCurve` | T107-T110 |
| T113 [P] | [done] `tests/test_core_purity.py`: walk `core/`, parse each module's imports, fail on any framework import | T112 |
| T114 [P] | [done] `tests/test_units.py`: round trips, unknown unit raises | T104 |
| T115 [P] | [done] `tests/test_parsing.py`: all four separators, header present and absent, comment lines, non-numeric cell reports the right row and column, fewer than four rows rejected | T106 |
| T116 [P] | [done] `tests/test_lambda_solver.py`: substituting the solved `lambda` back into equation (1) reproduces `Jc` to 1e-9; fixed-kappa explicit form agrees with the root finder; `NO_ROOT_TYPE_II` raised when `Jc` is impossibly large | T107 |
| T117 [P] | [done] `tests/test_gap_models.py`: `rho_s(0)=1` and `rho_s(Tc)=0` for both models; monotonic decreasing; clean-limit integral equals 1 at `d=0`; `Delta(T)` limits; dirty exceeds clean by at least 0.028 over `0.4 <= T/Tc <= 0.95`. Do **not** assert that ordering below `T/Tc = 0.25` — research R5 explains why it reverses there | T108 |
| T118 | [done] `tests/test_fitting.py`: **the round trip.** Generate synthetic `Jc(T)` from `lambda0=200 nm`, `Delta0=1.5 meV`, `Tc=10 K`, `kappa=40`; recover all three to within 1 % by route A and by route B; assert the two routes agree; assert `2 Delta0/(kB Tc) = 3.52775` when `Delta0 = 1.763875 kB Tc` | T109 |
| T119 [P] | [done] `tests/test_diagnostics.py`: each threshold in research R10 checked just inside and just outside its boundary | T110 |
| T120 [P] | [done] `tests/test_montecarlo.py`: same seed gives identical output; a wider input sigma gives a wider interval; too many failures raises `MC_TOO_MANY_FAILURES`; log-normal draws reproduce the requested mean and relative sigma | T111 |
| T120a [P] | [done] `tests/test_montecarlo.py`: **analytic cross-check.** With `kappa = 40`, 5 % on `Jc` and 3 % on `Hc2`, the Monte Carlo relative sigma of `lambda` must match the closed form of research R8.4, `1.815 %`, to within the estimator precision of equation (14) | T111 |
| T120b [P] | [done] `tests/test_montecarlo.py`: **the correlation-mode consequence.** In `SYSTEMATIC` mode with fixed `kappa`, a `Jc` uncertainty must leave `Delta0` and `Tc` unchanged to machine precision while moving `lambda0`; in `INDEPENDENT` mode it must move all three (research R8.3) | T111 |
| T121 | [done] `tests/test_legacy_agreement.py`: run each `legacy/` script on a fixture and assert the new core reproduces its `lambda(T)` to 1e-9 relative | T107 |
| T122 [P] | [done] `backend/examples/nbti_like.txt` and `nb3sn_like.txt`, generated from known parameters so the expected answer is known. One carries 0.2 % scatter so the clean/dirty comparison is decisive, the other a realistic 3 % so it honestly reports `MODELS_INDISTINGUISHABLE` (research R10) | T112 |

**Gate:** `pytest -v` green, T118 in particular. **Met**: 139 tests pass. The
round trip recovers `lambda0`, `Delta0` and `Tc` to better than 1e-9
relative by both routes and in all three coherence modes.

Added beyond the original list, each because a measurement showed it was needed:

| Id | Task | Why |
| --- | --- | --- |
| T123 | `core/validation.py`: `build_dataset` and `check_settings` | positivity and settings checks need to name the offending row, which a frozen dataclass is a poor place to do |
| T124 | `tests/test_examples.py`: run the shipped examples end to end from raw text | nothing else exercised parsing, units, inversion, fit and diagnostics together |
| T125 | `examples/generate.py` | the examples must be reproducible from stated parameters, not hand-edited |

---

## Phase 2 — API layer

| Id | Task | Depends on |
| --- | --- | --- |
| T201 | [done] `app/schemas.py`: Pydantic models for every schema in `contracts/openapi.yaml`, plus `to_domain` and `from_domain` conversion including display units | T103, T104 |
| T202 | [done] `app/main.py`: application factory, `CoreError` exception handler producing `{"code","params"}` and mapping each code to an HTTP status (the mapping lives here, never in `core/`), `/api/health` | T105, T201 |
| T203 | [done] `app/api/routes.py`: `POST /api/parse`, `POST /api/lambda`, `POST /api/analyze` | T112, T201 |
| T204 | [done] `app/jobs.py`: in-memory job store, thread runner, progress updates | T111 |
| T205 | [done] `app/api/routes.py`: `POST /api/uncertainty`, `GET /api/jobs/{job_id}` | T204 |
| T206 | [done] `app/api/routes.py`: `GET /api/examples`, `GET /api/examples/{name}` | T122 |
| T207 | [done] `app/api/routes.py`: `POST /api/export/csv`, column names carrying units | T203 |
| T208 | [done] `tests/test_api.py`: happy path per endpoint; error codes returned with the right HTTP status; **no non-ASCII in any response body**; the generated `/openapi.json` contains every path and required property in the contract | T203-T207 |

**Gate:** every endpoint exercised through `http://localhost:8000/docs`, and
`test_api.py` green. **Met**: 166 tests pass, nine endpoints live.

Added while implementing:

| Id | Task | Why |
| --- | --- | --- |
| T209 | `app/examples_store.py` | reading the example files is I/O, which `core/` is forbidden to do and routes should not be doing either |
| T210 | `tests/test_api.py` checks the generated `/openapi.json` against `contracts/openapi.yaml` | the contract was written before the code, so drift between them has to be a build failure rather than something noticed later |
| T211 | `tests/test_api.py` asserts no response body contains non-ASCII | constitution IV and VIII: Korean leaking into the backend is invisible by eye and breaks the separation that keeps errors testable |

---

## Phase 3 — Frontend base flow

| Id | Task | Depends on |
| --- | --- | --- |
| T301 | [done] Scaffold Vite + React + TypeScript in `frontend/`, `npm run gen:api` script, dev proxy for `/api` | T202 |
| T302 | [done] `src/api/generated.ts` produced from the running backend; `src/api/client.ts` typed fetch wrappers that surface `ErrorPayload` | T301 |
| T303 | [done] `src/errorMessages.ts`: Korean sentence for every error and warning code in `data-model.md`, with parameter interpolation and a visible fallback for an unknown code | T302 |
| T304 | [done] `src/format.ts`: significant figures, `value +/- stderr` rendering, unit suffixes | — |
| T305 | [done] `DataInput.tsx`: file upload, paste area, example picker | T302 |
| T306 | [done] `ColumnPreview.tsx`: shows the parse result for confirmation (FR-003) | T305 |
| T307 | [done] `SettingsPanel.tsx`: units, coherence source with conditional `kappa`/`Hc2`/`xi` fields, gap model, route, optional fixed `Tc`, optional thickness | T302 |
| T308 | [done] `LambdaTable.tsx` and `FitSummary.tsx`; `FitSummary` refuses to display an unconverged fit (FR-014) | T302, T304 |
| T309 | [done] `App.tsx`: wire the flow, loading and error states | T305-T308 |

**Gate:** quickstart steps 1, 2, 3 and 8 pass in the browser. **Met**: the page
loads, an example runs end to end through the dev proxy, and the production
build is served by FastAPI on one port.

Notes from implementing:

| Id | Task | Why |
| --- | --- | --- |
| T310 | `frontend/.nvmrc` pinning Node 24.19.0 | the toolchain is managed by nvm, so the version belongs in the repository rather than in someone's memory |
| T311 | `root_xtol` / `root_rtol` removed from the wire model | the generated types made them REQUIRED fields, which would have obliged every client to send two Brent termination conditions it has no basis for choosing. Found by the type checker on the first build |
| T312 | TypeScript pinned to 5.x | `openapi-typescript` 7 requires it, and generated API types are the whole reason TypeScript is here, so the generator wins |

---

## Phase 4 — Charts, export, examples

| Id | Task | Depends on |
| --- | --- | --- |
| T401 | [done] `Charts.tsx`: `lambda(T)` and `rho_s(T)`, measured points plus fitted curve, Plotly PNG export enabled | T309 |
| T402 | [done] Residual plot (supports FR-019) | T401 |
| T403 | [done] CSV download button calling `POST /api/export/csv` | T309 |
| T404 | [done] Example picker wired to `GET /api/examples` | T305 |

**Gate:** quickstart steps 4, 5, 9. **Met**, and the walkthrough is now executed by `npm run test:e2e`.

---

## Phase 5 — Uncertainty

| Id | Task | Depends on |
| --- | --- | --- |
| T501 | [done] `UncertaintyPanel.tsx`: input sigmas as percentages, correlation mode with `SYSTEMATIC` preselected and an explanation of the choice (FR-029), sample count, confidence, seed | T307 |
| T502 | [done] `JobProgress.tsx`: start the job, poll at 1 Hz, show progress, allow the rest of the page to be used | T501, T205 |
| T503 | [done] Show intervals alongside the fitted parameters, keeping the fit standard errors visible and separate (FR-030); display the seed and the correlation mode that produced them | T502 |

**Gate:** quickstart step 6. **Met**: the run is a background job with a progress bar, the page stays usable, and the propagated interval is shown beside the fit standard error rather than merged with it.

---

## Phase 6 — Diagnostics

| Id | Task | Depends on |
| --- | --- | --- |
| T601 | [done] `DiagnosticsPanel.tsx`: chi-squared, clean versus dirty comparison, coupling regime against the BCS reference | T309 |
| T602 | [done] Warning list rendered through `errorMessages.ts`, grouped by severity, always showing the unconditional notices | T303, T601 |
| T603 | [done] Film thickness input feeding the thin-film check | T307, T601 |

**Gate:** quickstart step 7. **Met**.

---

## Phase 7 — Containerisation

| Id | Task | Depends on |
| --- | --- | --- |
| T701 | [done] `frontend/Dockerfile` build stage producing static assets | phase 6 |
| T702 | [done] Root `Dockerfile`: multi-stage, Node build then Python runtime, non-root user, `HEALTHCHECK` against `/api/health` | T701 |
| T703 | [done] Serve the built assets from FastAPI, with SPA fallback routing | T702 |
| T704 | [done] `docker-compose.yml` for development | T702 |
| T705 | [done] Root `README.md`: what it is, how to run, how to verify, pointer to `specs/` | T704 |

**Gate:** quickstart step 10 plus the whole walkthrough repeated against
`docker compose up --build`. **Partly met, and honestly so.**

Docker Desktop is not installed on the development machine and installing it
needs administrator rights, so the image has never been built. Everything that
can be checked without a daemon has been:

- stage 1's exact command, `npx vite build --outDir ... --emptyOutDir`, runs
  and produces the asset bundle;
- the dependency layer installs from `pyproject.toml` alone, which is what
  makes the stub-package trick in the Dockerfile work and keeps the dependency
  list in one place;
- the resulting `/app` layout -- `app/`, `examples/`, `static/` and
  nothing else -- was reproduced with a non-editable install into a clean
  virtual environment, and the image's `CMD` was run against it: the page is
  served with the asset hash stage 1 produced, `/api/*` answers, `/docs`
  answers, an unknown path falls back to the page, the `HEALTHCHECK` command
  exits 0, and a full analysis returns the expected numbers;
- `backend/tests/` is absent from the layout, as `.dockerignore` intends.

What remains unverified is the daemon's part: that `docker build` resolves the
base images and that `docker compose up` starts. Run
`docker compose up --build` once Docker Desktop is installed.

---

## Requirement coverage

Every functional requirement maps to at least one task.

| FR | Tasks | FR | Tasks |
| --- | --- | --- | --- |
| FR-001 | T305 | FR-015 | T111, T501 |
| FR-002 | T106, T115 | FR-016 | T111, T501 |
| FR-003 | T306 | FR-017 | T111, T503 |
| FR-004 | T104, T307 | FR-018 | T204, T502 |
| FR-005 | T106, T115 | FR-019 | T109, T402 |
| FR-006 | T107, T307 | FR-020 | T110, T601 |
| FR-007 | T107, T308 | FR-021 | T110, T601 |
| FR-008 | T107, T116 | FR-022 | T110, T602 |
| FR-009 | T108 | FR-023 | T110, T602 |
| FR-010 | T108, T307 | FR-024 | T110, T602, T603 |
| FR-011 | T109, T307 | FR-025 | T308 |
| FR-012 | T109, T308 | FR-026 | T401 |
| FR-013 | T109, T307 | FR-027 | T207, T401, T403 |
| FR-014 | T109, T308 | FR-028 | T122, T206, T404 |
| | | FR-029 | T111, T120b, T501 |
| | | FR-030 | T109, T111, T503 |
