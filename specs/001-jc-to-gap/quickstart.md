# Quickstart and acceptance walkthrough

**Feature:** 001-jc-to-gap

Two purposes. First, how to run the thing. Second, the exact sequence that
demonstrates every acceptance scenario in `spec.md`, so that "is it done?" has a
mechanical answer.

---

## Prerequisites

| Tool | Needed for | Check |
| --- | --- | --- |
| Python 3.11+ | phases 1-2 | `python --version` |
| Node.js 20 LTS | phases 3-6 | `node --version` |
| Docker Desktop | phase 7 | `docker --version` |

---

## Running during development

### Backend alone

    cd backend
    python -m venv .venv
    .venv/Scripts/activate          # Windows;  source .venv/bin/activate elsewhere
    pip install -e ".[dev]"
    pytest -v
    uvicorn app.main:app --reload --port 8000

Then open `http://localhost:8000/docs`. This is the interactive API browser
FastAPI generates from the route definitions; every endpoint can be called from
it with no frontend and no client code.

### Frontend alone (backend must be running)

    cd frontend
    npm install
    npm run dev

Then open `http://localhost:5173`. The dev server proxies `/api` to port 8000,
so both hot reload and the real API work at once.

### Regenerating the frontend API types

Whenever a backend request or response model changes:

    cd frontend
    npm run gen:api

This reads `http://localhost:8000/openapi.json` and rewrites
`src/api/generated.ts`. If a field was removed or renamed, TypeScript reports
every place that used it, at build time. That is the entire reason TypeScript is
in this project.

### Everything, in containers

    docker compose up --build

Then open `http://localhost:8000`.

---

## Acceptance walkthrough

Run in order. Each step names the scenario or requirement it demonstrates.

### 1. The tool works before you have data (AS-9, FR-028)

Open the page. Choose the built-in example `nbti_like`. Confirm the column
preview shows three columns and that the row count matches the file.

**Pass:** the analysis completes and a gap value appears without any file having
been prepared.

### 2. Full analysis from the upper critical field (AS-1, FR-006 to FR-012)

With the same example: coherence source `FROM_HC2`, gap model `CLEAN`, route
`TWO_STEP`.

**Pass:** a per-temperature table with `xi`, `lambda`, `kappa`; fitted
`lambda(0)` in nm, `Delta(0)` in meV, `Tc` in K, each with an uncertainty; and a
coupling ratio near 3.5 for a weak-coupling example.

### 3. Fixed Ginzburg-Landau parameter (AS-3, FR-006)

Choose the built-in example `nb3sn_like`, coherence source `FIXED_KAPPA`,
`kappa = 30`.

**Pass:** results appear, and the table now also reports the implied `xi(T)`.

### 4. The two routes agree (AS-5, FR-011)

On the same data, switch `fit_route` from `TWO_STEP` to `DIRECT`.

**Pass:** `Delta(0)` from the two routes agrees within the reported standard
errors. This is also asserted automatically in `test_fitting.py`; the manual
check is that the *user* can see it.

### 5. The two models are compared (AS-4, FR-020)

Switch `gap_model` between `CLEAN` and `DIRTY`.

**Pass:** the diagnostics panel reports both reduced chi-squared values, the
Akaike separation, and either names a preferred model or states that the data do
not distinguish them. On `nbti_like` it names one; on `nb3sn_like` it declines,
because 3 % scatter on `Jc` cannot separate the two (research R10). Both are
correct answers and the contrast is why two examples are shipped.

### 6. Uncertainty propagation (AS-6, FR-015 to FR-018)

Set the `Jc` uncertainty to 5 %, the `Hc2` uncertainty to 3 %, correlation mode
`SYSTEMATIC`, 5000 samples, confidence 68.27 %, seed 12345. Start it.

**Pass:** a progress indicator advances and the page stays usable; the result
gives an interval for `Delta(0)` and `lambda(0)`; the seed and the correlation
mode are shown; running it again with the same seed gives byte-identical
numbers; the fit standard errors are still shown separately and have not been
merged into these intervals.

Now switch the correlation mode to `INDEPENDENT` and repeat.

**Pass:** the `lambda(0)` interval barely changes while the `Delta(0)` interval
widens noticeably. That contrast is the whole point of FR-029: under
`SYSTEMATIC` a geometry calibration error moves the scale of `lambda` without
touching the shape of the superfluid density, so it cannot move the gap.

### 7. Assumptions are surfaced (AS-7, AS-8, FR-022 to FR-024)

- Note that `SELF_FIELD_TRANSPORT_REQUIRED` is shown on every result, always.
- Enter a film thickness ten times the fitted `lambda(0)`.
  **Pass:** `THIN_FILM_ASSUMPTION_STRAINED` appears.
- Delete every row below `0.6 Tc` and re-analyse.
  **Pass:** `LOW_T_COVERAGE_INSUFFICIENT` appears and the fit still runs.
- Set `kappa = 0.8`.
  **Pass:** `KAPPA_NEAR_TYPE_I_BOUNDARY` appears.
- Set `kappa = 0.5`.
  **Pass:** the request fails with `KAPPA_TOO_SMALL` and the page explains it in
  Korean rather than showing a stack trace or a blank screen.

### 8. Bad input is caught early (FR-003, FR-005)

Paste a table with a text value in the `Jc` column.

**Pass:** the failure names the offending row and column, before any physics ran.

### 9. Results can be taken away (AS-10, FR-027)

Download the table; open it in a spreadsheet. Save each plot as an image.

**Pass:** every column header carries its unit; the images are legible.

### 10. Nothing leaves the machine (QA-006)

Disconnect from the network and repeat step 2.

**Pass:** everything still works.

---

## Automated gates

    cd backend && pytest -v

Must be green before any phase is considered complete. The tests that matter
most, in order:

| Test | Guards against |
| --- | --- |
| `test_fitting.py::test_round_trip_route_a` and `..._route_b` | any wrong factor, sign, or unit anywhere in the chain |
| `test_gap_models.py::test_limits` | a superfluid density that is subtly wrong but plausible |
| `test_legacy_agreement.py` | the rewrite having changed the physics |
| `test_core_purity.py` | the physics core acquiring a framework dependency |
| `test_montecarlo.py::test_reproducible` | an error bar that cannot be cited |
| `test_api.py::test_no_display_prose` | Korean text leaking into the backend |
