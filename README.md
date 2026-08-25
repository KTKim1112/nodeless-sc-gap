# Nodeless SC gap extractor

Extracts the London penetration depth `lambda(T)` and the single-band nodeless
superconducting gap `Delta(0)` from self-field transport critical current
density measured as a function of temperature.

The point is an asymmetry in measurement cost. `Jc` and `Hc2` come out of an
ordinary four-probe transport measurement that most laboratories can do on their
own samples in a day. `lambda` needs muon spin rotation, a tunnel-diode
oscillator, or a microwave cavity; `Delta` needs tunnelling spectroscopy or
ARPES. Established thin-film theory connects the two, and this turns that
connection into a tool.

    Jc(T)  --(1)-->  lambda(T)  ----->  rho_s(T)  --fit-->  Delta(0)

Based on E. F. Talantsev and J. L. Tallon, *Universal self-field critical
current for thin-film superconductors*, Nature Communications **6**, 7820
(2015), equation (4).

---

## Running it

### In a container

    docker compose up --build

Then open <http://localhost:8000>. One image, one port; the same process serves
the page and the API.

### As a standalone Windows executable

    .\packaging\build.ps1              # one file,   packaging/dist/NodelessSC.exe
    .\packaging\build.ps1 -OneDir      # one folder, zipped, starts faster

For a recipient with no Python, no Node, and no administrator rights: they open
it, a browser opens on a port the operating system picked, and closing the
console window stops it. 54 MB as one file and 12.6 s to start, against 55 MB
zipped and 5.0 s; the difference is the bootloader unpacking itself on every
launch.

It has never been run on a machine without Python. See the Phase 9 gate in
`specs/001-jc-to-gap/tasks.md` for what was checked instead.

### For development

    .\dev.ps1

Starts the backend on 8000 with reload, the Vite dev server on 5173, waits for
both, and opens the page. `Ctrl+C` stops both.

First time only:

    cd backend
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

    cd ..\frontend
    nvm use            # reads .nvmrc
    npm install
    npx playwright install chromium

---

## What it does

Give it a table of temperature and self-field critical current density, plus
either the upper critical field, an independently known coherence length, or a
fixed Ginzburg-Landau parameter. It reports:

- `xi`, `lambda` and `kappa` at every measured temperature;
- fitted `lambda(0)`, `Delta(0)`, `Tc` and `2 Delta(0) / (kB Tc)`, each with a
  standard uncertainty;
- plots of the superfluid density and the penetration depth with the fitted
  curve through the measured points, and the residuals;
- optionally, the measurement uncertainty propagated through the whole chain by
  Monte Carlo;
- and, alongside every result, the assumptions it rests on and any that the data
  appear to violate.

Two built-in examples run the whole thing without any data of your own.

### What it does not do

Multi-band or two-gap models, gap models with nodes, anisotropic `Hc2`,
correlated input uncertainties, sample geometries other than the thin-film
limit, and `Jc` measured in an applied field. `specs/001-jc-to-gap/spec.md`
section 9 says why for each.

---

## Two things worth knowing before trusting a number

**A wrong `Jc` unit does not fail.** A/cm² and A/m² are both physically
possible, so nothing can detect the mistake. It moves `lambda(0)` by a factor of
21.5 and produces a perfectly plausible answer. Check the unit selector.

**Clean and dirty limits are hard to tell apart.** They differ by at most 0.097
in `rho_s`, so separating them needs scatter on `Jc` below about half a per
cent. Above roughly 2 % the tool will say it cannot choose -- and the two models
give gaps about 20 % apart, so which one was used has to be reported.

---

## Layout

    .specify/memory/constitution.md   the rules this project does not break
    specs/001-jc-to-gap/              what is being built and why, and the physics
    backend/app/core/                 the physics. No web framework, ever
    backend/app/                      the HTTP layer over it
    backend/tests/                    176 tests
    frontend/src/                     the page. Its Korean lives here
    frontend/e2e/                     the acceptance walkthrough, executed
    docs/                             how this was built, for the maintainer
    legacy/                           the archived command-line prototypes

`backend/app/core/` imports no web framework and does no I/O, and a test
enforces that. The physics can be used from a notebook, or under a different
interface, without any of the rest.

---

## Checking it

    cd backend && .\.venv\Scripts\python.exe -m pytest -v      # 176 tests
    cd frontend && npm run test:e2e                             # 25 tests, starts both servers
    cd frontend && npm run shots                                # screenshots for review by eye

The test that matters most generates `Jc(T)` from known parameters and checks
that the fit gives them back. A wrong factor, sign, or unit anywhere in the
chain shows up there and essentially nowhere else, because every one of those
mistakes still produces a believable number.

---

## How this was built

Specification first: `specs/001-jc-to-gap/` was written and reviewed before any
code existed, and `research.md` fixes every equation, constant, and numerical
safeguard with the measurements behind them. Where implementation contradicted
the specification -- the quadrature rule, the residual definition, the
model-comparison criterion -- the specification was corrected first and the
reason recorded. `git log` is the argument for each.

`docs/manual.en.md` narrates the whole of it -- what was installed, what each
phase did, and what came out -- for a reader with no programming background.
`docs/manual.ko.md` is the same document in Korean, which constitution VIII
permits under `docs/` alone.
