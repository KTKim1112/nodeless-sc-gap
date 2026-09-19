# Working on this repository

Extracts the London penetration depth and the single-band nodeless
superconducting gap from self-field transport critical current density. See
`README.md` for what it is and how to run it.

## Read these before changing anything

| File | Why |
| --- | --- |
| `.specify/memory/constitution.md` | Nine rules this project does not break. Two are enforced by tests. |
| `specs/001-jc-to-gap/spec.md` | What is being built and why. Names no technology, deliberately. |
| `specs/001-jc-to-gap/research.md` | Every equation, constant and numerical safeguard, with the measurements behind them. Do not re-derive; it is all there. |
| `specs/001-jc-to-gap/tasks.md` | What is done and what the gates were. |

`git log` is the argument for each decision. The messages are long on purpose.

## How work is done here

**Specification first.** Change the document, then the code. Where a
measurement contradicted the specification -- the quadrature rule, the residual
definition, the model-comparison criterion -- `research.md` was corrected first
and the numbers recorded. Keep doing that.

**Measure, do not assume.** Four design decisions in this project were reversed
by measurement, and each one looked obviously right beforehand. If a choice
between two approaches can be measured, measure it and put the table in
`research.md`.

**Physics belongs in `backend/app/core/`.** It imports no web framework and does
no I/O, and `tests/test_core_purity.py` fails the build if that changes. Do not
compute a physical quantity in TypeScript, even a one-line one -- `rho_s`
measured points were moved to the backend for exactly this reason.

## Conventions

- **Code, comments, documents, commit messages: English. Screen text: Korean.**
  Korean prose lives in exactly two places: `frontend/src/errorMessages.ts`, and
  `docs/`, which constitution VIII 1.1.0 exempts because it teaches the
  maintainer rather than instructing whoever changes the code. Nowhere else --
  a Korean sentence anywhere under `specs/`, `backend/`, or the root is a bug.
- The backend never returns a sentence for a human. Failures are
  `{"code", "params"}`; `errorMessages.ts` turns a code into a sentence. A test
  asserts no API response contains non-ASCII.
- SI everywhere inside `core/`. Units convert only in `backend/app/schemas.py`.
  A variable holding a non-SI value carries the unit in its name.
- Frontend API types are **generated**, never hand-written. After changing a
  request or response model: `cd frontend && npm run gen:api` with the backend
  running. A backend change should surface as a TypeScript error.

## Verifying

    cd backend && .\.venv\Scripts\python.exe -m pytest -q     # 202 tests
    cd frontend && npm run test:e2e                           # 28 tests, starts both servers
    cd frontend && npm run shots                              # screenshots into e2e/.shots for review by eye

`.\dev.ps1` starts both servers and opens the page.

The test that matters most is the round trip in `backend/tests/test_fitting.py`:
synthetic `Jc(T)` generated from known parameters, fitted back. A wrong factor,
sign, or unit anywhere in the chain shows up there and essentially nowhere else,
because every one of those mistakes still produces a believable number.

**Nothing is shipped as data.** FR-028 was withdrawn in Phase 12: a manufactured
dataset distributed beside a measurement tool reads as a claim about real
samples, so the built-in examples, the endpoints that served them, and the data
directory inside the executable and the image are all gone. Do not add one back
-- `test_the_api_serves_no_data_of_its_own` fails if an endpoint serving data
reappears, and the reasoning is in spec section 9.

The generated data itself stayed, under `backend/tests/data/`, written by
`tests/data/generate.py` from stated parameters recorded in each file header.
`test_whole_chain.py` is the only test that runs parsing, units, the inversion,
the fit and the diagnostics together, and it can only do that because the
answer is known: no measured film has a `lambda(0)` known independently to check
a fit against. Name a fixture for the regime it creates, never for a material.

## Things that will surprise you

- **`rho_s` is exactly 1, flat, below about `T/Tc = 0.05`.** The difference from
  1 there is `1e-24`. Not a bug; pinned by a test.
- **Clean and dirty superfluid densities cross below `T/Tc = 0.25`.** That is
  the residual error of the `tanh` gap interpolation, not physics. Never assert
  the ordering there.
- **Inverting equation (1) can only return `kappa > 1`.** `Jc` at the ceiling is
  exactly `kappa = 1`, so `NO_ROOT_TYPE_II` is a statement about the data.
  Fixed-`kappa` mode has no such limit, and the asymmetry is deliberate.
- **A wrong `Jc` unit does not fail.** It moves `lambda(0)` by 21.5x and returns
  a plausible answer. Nothing can detect it.
- **Clean and dirty are usually indistinguishable.** Separating them needs
  scatter on `Jc` below about half a per cent. The tool saying it cannot choose
  is the correct outcome, not a defect.

## The person you are working with

An experimental physicist, not a programmer, learning spec-driven development by
building this. Explain the concepts a step introduces before doing the step, in
Korean, without assuming programming background. State plainly what was verified
and what was not -- for example the Docker image has never been built, because
Docker is not installed on this machine, and `tasks.md` says exactly which parts
of Phase 7 were checked without it.
