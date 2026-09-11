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

## Phase 8 — Exporting the fitted curve

Added after Phase 7, on the observation that the per-temperature table cannot
hold the curve: it has one row per measurement and the curve does not.

| Id | Task | Depends on |
| --- | --- | --- |
| T801 | [done] `spec.md`: FR-027a, and FR-026 gains the requirement that the drawn curve begin at absolute zero | — |
| T802 | [done] `data-model.md`: `SuperfluidCurve` is sampled from `T = 0`, with why both gap models are total there | T801 |
| T803 | [done] `contracts/openapi.yaml`: `POST /api/export/curve.csv`, and the reason it is a separate resource rather than more columns | T801 |
| T804 | [done] `core/pipeline.py`: `build_curve` starts at zero and no longer takes `t_min` | T802 |
| T805 | [done] `app/api/routes.py`: `_write_conditions` extracted so both exports carry it; `rho_s_measured` and `fit_residual` added to the per-measurement table; `/export/curve.csv` added | T803, T804 |
| T806 | [done] `tests/test_api.py`: the curve export equals the curve in the response value by value; the table's new columns line up with the fit; `T = 0` and `lambda(0)` are exact, not approximate | T805 |
| T807 | [done] `npm run gen:api`, `client.ts` `downloadCurveCsv`, second button in `App.tsx` | T805 |
| T808 | [done] `e2e/acceptance.spec.ts`: download the curve and check its first row against the `lambda(0)` read off the screen | T807 |

**Gate:** quickstart step 9, extended. **Met**: 169 backend tests and 24
end-to-end tests pass, and the screenshots were retaken because the plots
changed.

Why the curve is exported rather than recomputed at export time: a file that
disagrees with the figure beside it is a defect that surfaces only in someone
else's paper. `test_export_curve_is_the_curve_that_was_plotted` asserts value
by value rather than by shape, because no property of the file's shape would
reveal that failure.

Why `T = 0` and not the coldest measurement. `lambda(0)` and `Delta(0)` are the
results, and the curve used to start wherever the data happened to stop, so the
intercept was never on the plot. Both gap models are total at zero -- verified
before the change rather than assumed: `rho_s` returns exactly `1.0`, so
`lambda` there is bit-for-bit the fitted `lambda(0)` in both the clean and the
dirty limit. The tests assert equality, not closeness, for that reason.

---

## Phase 9 — A build for someone who has no Python

Distribution, not a feature: the analysis behaves identically, and the only new
thing is a way to start it on a machine that has nothing installed. No
functional requirement changes.

| Id | Task | Depends on |
| --- | --- | --- |
| T901 | [done] `app/resources.py`: one function deciding where `static/` and `examples/` are, from source or from a frozen bundle | — |
| T902 | [done] `main.py` and `examples_store.py` use it instead of computing paths from `__file__` each | T901 |
| T903 | [done] `app/desktop.py`: bind a loopback socket on an OS-chosen port, hand it to uvicorn, open a browser once the server answers | T902 |
| T904 | [done] `packaging/entry.py`, `packaging/NodelessSC.spec`, `packaging/build.ps1` | T903 |
| T905 | [done] `tests/test_resources.py`: both branches of `root()`, including the frozen one that nothing else reaches | T901 |
| T906 | [done] `.gitignore`: `packaging/build/`, `packaging/dist/` | T904 |

**Gate:** the executable runs a full analysis and returns the values the source
build returns. **Met on this machine**: `lambda(0) = 250.0422 nm`,
`Delta(0) = 1.40030 meV`, `Tc = 9.2002 K`, `2 Delta(0)/kB Tc = 3.5325`, and the
curve's first row is `T = 0` at `250.042240 nm` — identical to
`python -m app.desktop`. 171 backend tests pass.

**Met on a second machine, 2026-08-26.** The executable was carried to another
computer and opened. The browser came up by itself, and the maintainer's own
measured `Jc(T)` — not one of the shipped examples — produced the same result
there as it does from source. Nothing on that machine had to be installed
first.

One thing that was not asked at the time and so is not claimed: whether that
machine had Python on it. The point of the build is that it should not matter,
and everything else about the run is consistent with that, but the observation
does not by itself establish it.

**What the trip found instead.** Antivirus software objected to the one-file
executable, and it ran after being allowed through. This was not predicted and
is the more useful result of the two: a recipient who does not know to expect
the warning is a recipient who deletes the file.

The cause is the design of a one-file build. It unpacks 54 MB into a temporary
directory at every launch and executes from there, which is also the shape of a
dropper, and a heuristic scanner has no way to distinguish them. UPX was
already off for exactly this reason (`packaging/NodelessSC.spec`), and turning
off the one remaining trigger means not unpacking at startup at all — which is
what `-OneDir` does.

So the one-file versus one-folder choice is no longer only about startup time.
It now reads: one file is more convenient to send and more likely to be
quarantined; one folder starts faster and does not trip the scanner. Both stay
buildable, and `README.md` recommends `-OneDir` for anything given away.

Code signing would remove the warning properly. It needs a certificate, which
costs money and is not obtainable from this machine, so it is recorded here as
the known fix rather than done.

Two measurements decided the shape of the build.

*One file against one folder.* One file was specified. Measured: it starts in
12.6 s, because the bootloader unpacks 54 MB into a temporary directory on
every launch and shows nothing on screen while it does; a cold first run took
19.4 s. One folder starts in 5.0 s. Both are built by the same spec — the
`-OneDir` switch — because which one is right depends on whether the recipient
minds unzipping, not on anything technical.

*A port is chosen by the operating system, not named.* A fixed port is a guess
about a machine nobody has seen, and 8000 is already taken on a great many. The
socket is bound first and handed to uvicorn, so nothing can take the port
between choosing it and listening on it.

The first build was 11 MB and should have been 54. PyInstaller runs its entry
point as `__main__`, so `app/desktop.py`'s `from .main import app` failed — at
analysis time as well as at runtime, and everything past that import went
unbundled, numpy and scipy included. The size was the only visible symptom
before the executable was run. `packaging/entry.py` exists solely to make that
import absolute.

---

## Phase 10 — The critical current density the fit predicts

A plot and a column, added after the tool was already in use: the two existing
plots show what the fit did to the derived quantities, and nothing showed it
against the measurement itself. FR-026a, and an extension to FR-027.

| Id | Task | Depends on |
| --- | --- | --- |
| T1001 | [done] spec: FR-026a, with the reason the curve is not dense; FR-027 gains the predicted column | — |
| T1002 | [done] `data-model.md`: `FitResult.jc_model`, and which `xi` each coherence source contributes | T1001 |
| T1003 | [done] `core/fitting.py`: `_predicted_jc`, one call site for route B's residual and for the reported value | T1002 |
| T1004 | [done] route A carries `xi` and `kappa_fixed` too, so the prediction exists whichever route ran | T1003 |
| T1005 | [done] `types.py`, `schemas.py`, `contracts/openapi.yaml`, and regenerated frontend types | T1003 |
| T1006 | [done] `routes.py`: one `_ROW_COLUMNS` replaces the two lists, so the predicted column can sit beside the measured one | T1005 |
| T1007 | [done] `Charts.tsx`: a fourth tab, sorted by temperature, log axis in powers of ten | T1005 |
| T1008 | [done] tests: the exact identity with route B's residual, the round trip in all three coherence modes, the CSV column, the tab | T1006, T1007 |

**Gate:** the plotted prediction and the direct route's residual are one
quantity rather than two that agree. Met, and asserted as exact equality rather
than to a tolerance: `ln(Jc) - ln(jc_model)` equals `residuals` element for
element under both gap models, because both leave `_predicted_jc` at a single
call site. Approximate agreement there would mean a second expression had
appeared somewhere.

176 backend tests, 25 e2e tests.

*Why this plot alone is not a dense curve.* **Superseded by Phase 11**, which
found the argument below to be half right. Kept as written, because what was
wrong with it is the useful part.

*Why this plot alone is not a dense curve.* The other two need only the fitted
parameters, so they can be sampled at any temperature. Equation (1) needs the
coherence length as well, and that comes from the fit only under
`FIXED_KAPPA`; from an upper critical field or a supplied coherence length it
exists only where a measurement put it. Filling the gaps would mean assuming a
form for the temperature dependence of the upper critical field, which spec
section 9 excludes. The prediction is therefore reported at the measured
temperatures in all three modes — one branch instead of three, and no
assumption the analysis has not already stated. At the 22 and 25 points of the
shipped examples the polyline is indistinguishable from a curve; at five points
it would look like what it is, which is honest.

*What it cost to keep the two consistent.* Route A never looks at `Jc` while it
is fitting, so it had no reason to hold a coherence length. It carries one now
purely so the reported prediction exists for that route too. The alternative —
computing the prediction in `pipeline.py` after the fit — would have left the
identity with route B's residual as a coincidence to be maintained by hand
instead of one that cannot break.

*One presentation defect, found by looking.* The first screenshot of the new
tab labelled the axis `10B`, which is how Plotly abbreviates ten to the tenth.
A billion is a word with two meanings and the axis carries a unit, so the ticks
are powers of ten instead. Nothing but looking at the picture would have caught
that.

---

## Phase 11 — The critical current density as a fitted curve

Phase 10 drew the prediction as a polyline through the measured temperatures.
Reported from use: it does not read as a fit. It reads as a second data series,
which is close to what it was -- the fitted `lambda` combined with the measured
`xi`, so that every wiggle in `Hc2` appeared in the line that was supposed to
be the model. FR-026a rewritten, and the curve drawn like the other two.

| Id | Task | Depends on |
| --- | --- | --- |
| T1101 | [done] measure which interpolant: `Bc2` against `xi`, PCHIP against spline, against three analytic `Bc2(T)` forms with and without scatter | — |
| T1102 | [done] `research.md` R12: the tables, and what a `xi` error is worth in the drawn `Jc` | T1101 |
| T1103 | [done] spec: FR-026a rewritten -- interpolate between, never extrapolate past; state it on screen; absence is never a zero | T1102 |
| T1104 | [done] `data-model.md`: `SuperfluidCurve.jc`, and why the gaps travel on the shared grid | T1103 |
| T1105 | [done] `core/lambda_solver.py`: `interpolate_xi`, PCHIP on `PHI0 / (2 pi xi^2)`, NaN outside the data | T1104 |
| T1106 | [done] `core/pipeline.py`: `build_curve` takes the table and the settings and returns `jc` too | T1105 |
| T1107 | [done] `schemas.py` `_list_or_null`, `contracts/openapi.yaml`, regenerated frontend types | T1106 |
| T1108 | [done] `routes.py`: the curve export gains the column, blank where the model has none | T1107 |
| T1109 | [done] `Charts.tsx`: the dense curve replaces the polyline; axis range from the measured values | T1107 |
| T1110 | [done] tests: `test_curve.py`, the null encoding, the blank CSV cell, the e2e hint and header | T1108, T1109 |

**Gate:** the `Jc` tab shows a fitted curve, and the curve and the reported
per-point column are one model. **Met.** The curve is smooth, passes through
the measurements it was fitted to, and stops where the data stop unless `kappa`
was fixed. `test_the_drawn_curve_is_the_same_model_as_the_reported_prediction`
evaluates the curve's own recipe at the measured temperatures and gets
`FitResult.jc_model` back, so the figure and the exported table cannot drift
apart.

191 backend tests, 25 e2e tests.

*What Phase 10 got wrong.* It treated interpolating between two measurements
and extrapolating past the last one as the same act, and refused both. They are
not the same. Inside the data an interpolant is pinned on both sides and the
choice of form is worth a fraction of a per cent; outside it, the value is
entirely whatever form was chosen, which is the assumption about `Bc2(T)` that
spec section 9 declines. The new curve interpolates and still refuses to
extrapolate, and the plot shows the difference: it stops at the coldest and
hottest measurement, while under `FIXED_KAPPA` -- where the coherence length
was assumed rather than measured -- the same curve runs from absolute zero to
`Tc`.

*What Phase 10 got right.* That the prediction must exist per measured point as
well, because that is what the results table carries and what the direct
route's residual measures. Both survive; `FitResult.jc_model` is unchanged.

*Measured, not argued.* Interpolating `xi` directly is the obvious choice and
is thirty to a hundred times worse than interpolating `Bc2` and converting,
because `xi` goes as `Bc2^(-1/2)` and turns sharply upward exactly where
measurements are sparsest. A cubic spline beats PCHIP on noiseless data and
loses on data with 1 % scatter or more, where it adds about three times as much
oscillation that the model does not have. Research R12 has both tables. The
same section records that none of it moves the drawn curve by much -- a 1 %
error in `xi` is 0.23 % in `Jc` at `kappa = 45` -- which is a conclusion worth
having rather than an excuse for not measuring.

*One thing that had to be got right or the page would go blank.* The gaps are
`NaN` in the core and `null` at the API boundary. Python's JSON encoder will
write the bare token `NaN`, which `JSON.parse` rejects, so a single gap would
have taken down the whole response rather than one plot. A test asserts on the
raw response text, because a parsed body would have turned the token into a
float before the test could see it.

*A presentation consequence, again found by looking.* Under a fixed `kappa` the
curve runs to `Tc`, where `Jc` has fallen more than two decades below anything
measured. Left to itself the logarithmic axis fits all of that in and squashes
the measurements into a strip at the top. The axis range is taken from the
measured values instead, so the curve leaves the frame rather than the data
leaving the eye, and `06b-chart-jc-fixed-kappa.png` is in the screenshot set so
that this stays visible.

*Asked for, built, measured, and taken back out.* The next question after this
phase was whether the curve could reach absolute zero and `Tc` like the two
beside it, and it was implemented: `xi` past the data by holding `kappa` at its
edge value, the extrapolated part dashed, a `KAPPA_TREND_EXTRAPOLATED` warning
when the data's own trend said that assumption was unsafe, and a flag column in
the exported curve.

It was then removed, on the strength of what the measurement said. Research R13
has the tables. The short version is that holding `kappa` is accurate to about
1 % exactly when `kappa` is nearly constant -- a case that already has its own
mode, which does the same thing on purpose -- and wrong by tens to hundreds of
per cent exactly when `kappa` varies with temperature, which is the case this
tool exists for. Accurate where it is unnecessary, wrong where it would be
wanted.

Two things are worth carrying forward from the attempt. Nothing fitted depends
on the extension, so it was decoration; and making the decoration safe took a
diagnostic, a threshold, an export column, a second plot trace and a sentence
of explanation. When the safeguards outweigh the feature, that is the answer.

The measurement is kept in R13 so the question can be closed by reading rather
than by re-deriving it.

---

## Phase 12 — Removing the shipped datasets

Asked for directly, after a question about where the example data came from.
The answer was that it came from nowhere: both files were computed from stated
parameters by a generator in the repository. The objection was not that this
was hidden -- the header, the generator, the README and both manuals all said
so -- but that a manufactured dataset should not be shipped beside a
measurement tool at all.

That objection is right, and it is sharper than it first sounds. A dataset
distributed with an analysis tool is read as an example of what the tool is
*for*. Ours put two material names in front of a new user, and a material name
reads as a measurement of that material whatever the header says.

| Id | Task | Depends on |
| --- | --- | --- |
| T1201 | [done] spec: FR-028 withdrawn, AS-9 withdrawn, FR-029a added, section 9 and section 10 record the decision | — |
| T1202 | [done] `backend/examples/` -> `backend/tests/data/`, renamed for the regime rather than a material | T1201 |
| T1203 | [done] `examples_store.py` deleted; `/api/examples` and `/api/examples/{name}` removed; `Example`/`ExampleSummary` schemas removed; `EXAMPLE_NOT_FOUND` removed | T1202 |
| T1204 | [done] `contracts/openapi.yaml` loses both paths and both schemas; frontend types regenerated | T1203 |
| T1205 | [done] `DataInput.tsx` loses the example buttons and the fetch behind them; `App.tsx` loses `onExampleChosen` | T1204 |
| T1206 | [done] the placeholder carries the format instead (FR-029a), and the box is tall enough to show all of it | T1205 |
| T1207 | [done] `NodelessSC.spec` and `Dockerfile` stop copying the directory | T1202 |
| T1208 | [done] `test_examples.py` -> `test_whole_chain.py`, reading `tests/data/`; `test_api.py` fixture reads the file; `test_resources.py` asserts the directory is gone | T1202 |
| T1209 | [done] e2e pastes fixture text and sets the settings by hand, in place of `loadExample`; a new test pins that nothing on the page hands out data | T1205 |
| T1210 | [done] README, both manuals, `quickstart.md`, endpoint counts | T1209 |

**Gate:** nothing that looks like a measurement leaves this repository as part
of the product, and the verification that needed generated data still runs.
**Met.** 191 backend tests and 26 e2e tests pass; the executable and the
container image no longer carry a data directory; `test_the_api_serves_no_data_of_its_own`
fails if an endpoint serving data comes back.

*What was kept, and why that is not a contradiction.* The same generated files
are still in the repository, under `backend/tests/data/`. The objection was to
distributing manufactured measurements, not to testing with known answers --
and `test_whole_chain.py` is the only test that runs parsing, unit conversion,
the inversion, the fit and the diagnostics together. No real dataset could
replace it: no measured film has a `lambda(0)` known independently, so real
data can only confirm that a number came out, never that it was the right one.
Deleting the fixtures would have removed the project's ability to detect a
wrong constant in exchange for nothing.

*What it costs, since the specification says to say so.* A first-time user now
has to bring a file before anything happens. That is a worse first minute, and
it was the reason FR-028 existed. The placeholder does what it can.

*What was searched for first.* A real, citable dataset was looked for before
accepting the loss: the source paper is CC BY but tabulates no `Jc(T)`, the
open repositories carry nothing for an s-wave film, and the public REBCO data
are d-wave, which section 9 excludes. Every candidate has its numbers in a
figure, and reading points off a plot would have put digitisation error into
the one file a new user judges the tool by. Recorded in section 9 so the search
does not have to be repeated.

*One test that had to be rewritten twice.* The check that no data endpoint
survives first asserted a 404 from `/api/examples`, which passes for the wrong
reason -- the single-page catch-all answers any unknown GET with the page
itself. Then it read `app.routes`, which holds an included router rather than
its paths, so `/api/parse` was not in it either. It reads the generated OpenAPI
schema now, which is the list that is actually published.

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
| FR-012 | T109, T308 | FR-026 | T401, T804 |
| FR-013 | T109, T307 | FR-027 | T207, T401, T403, T1006 |
| | | FR-026a | T1001, T1003, T1007, T1008, T1103, T1105, T1109, T1110 |
| | | FR-027a | T805, T806, T807, T808, T1108 |
| FR-014 | T109, T308 | FR-028 | *withdrawn* by T1201 |
| | | FR-029 | T111, T120b, T501 |
| | | FR-029a | T1201, T1206, T1209 |
| | | FR-030 | T109, T111, T503 |
