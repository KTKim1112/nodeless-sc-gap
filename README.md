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
console window stops it. Confirmed on a second machine, where the browser came
up on its own and a real dataset gave the same numbers as the source build.

54 MB as one file and 12.6 s to start, against 55 MB zipped and 5.0 s; the
difference is the bootloader unpacking 54 MB into a temporary directory on
every launch.

**Antivirus software objects to the one-file build.** Observed, not predicted:
it was flagged on the machine it was carried to, and ran once allowed through.
Unpacking an executable into a temporary directory and running it from there is
also what a dropper does, and a heuristic cannot tell the difference; UPX
compression is already off in `packaging/NodelessSC.spec` for the same reason.
The one-folder build does not unpack anything at startup, so prefer `-OneDir`
for anything handed to someone else, and expect to tell them why the warning
appears. Nothing short of a code-signing certificate removes it entirely.

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
- plots of the superfluid density, the penetration depth and the critical
  current density, each with the fit drawn through the measured points, and the
  residuals;
- optionally, the measurement uncertainty propagated through the whole chain by
  Monte Carlo;
- and, alongside every result, the assumptions it rests on and any that the data
  appear to violate.

**No dataset is distributed with this tool.** There were two generated ones,
so that a new user had something to press; they were withdrawn. A manufactured
dataset shipped beside a measurement tool reads as an example of what the tool
is for, and that is a claim about real samples nobody took an instrument to,
however plainly the file says otherwise. Bring your own file: the empty page
shows the column layout it expects.

Generated data with a known answer has not gone away, because nothing else can
check the chain end to end -- no measured film has a `lambda(0)` known
independently to check a fit against. It lives in `backend/tests/data/` now,
where it is a fixture and is not distributed as an example of anything.

### When this is the right tool

Self-field **transport** `Jc(T)`, from a **thin film** free of weak links,
comfortably **strong type-II**, whose gap is **single-band, nodeless and
s-wave**. Those four are restrictions: a sample failing any of them wants a
different program, and *Related work* below names the obvious one.

The fifth item on the list is not a restriction but the reason to reach for this
one. If `Hc2(T)` was measured in the same cooldown -- and it usually was, on the
same sample, in the same run -- then `xi(T)` is read off it at every temperature
instead of being replaced by a single fixed `kappa`. The temperature dependence
of the coherence length comes out of the measurement rather than being assumed
away.

**`Hc2` is not required.** An independently known `xi(T)` does the same job, and
so does a fixed `kappa`. What that last choice costs is measured and tabulated
below rather than left for the reader to worry about.

### The coherence length is measured, not assumed

Equation (1) needs `xi(T)` as well as `lambda(T)`. The simplest way to supply it
is to fix the Ginzburg-Landau parameter `kappa = lambda/xi` and let `xi` follow
`lambda`, and this tool will do that. It also accepts `Hc2(T)`, from which
`xi(T) = sqrt(PHI0 / (2 pi Bc2(T)))` at every measured temperature, so that
`kappa(T)` comes out as a **result** that can be looked at rather than going in
as an assumption.

That matters for two reasons, one practical and one numerical.

The practical one is that `Hc2` comes out of the same four-probe transport
measurement as `Jc`, on the same sample, in the same cooldown. `kappa` does not
come from anywhere: fixing it means already knowing the ratio of the two
lengths this analysis exists to determine.

The numerical one is smaller than it looks, and is stated here rather than
implied. Synthetic `Jc(T)` was generated at `lambda(0) = 250 nm`,
`Delta(0) = 1.400 meV`, `Tc = 9.2 K` for three temperature dependences of
`Bc2`, then fitted both ways:

| `Bc2(T)` | `kappa` range | from `Hc2` | fixed `kappa`, at its mean |
| --- | --- | --- | --- |
| `1 - (T/Tc)^2`, the usual form | 43.4 – 45.6, 1.05x | exact | `Delta(0)` low by 0.36 % |
| `1 - T/Tc` | 32.0 – 44.4, 1.39x | exact | low by 2.99 % |
| `(1 - (T/Tc)^2)^2` | 17.0 – 45.6, 2.69x | exact | low by 4.31 % |

Reading `xi(T)` off `Hc2` recovers the generating parameters whatever `kappa`
does. Fixing `kappa` costs a few tenths of a per cent when `kappa` is nearly
constant, which is the ordinary case, and a few per cent when it is not.
`kappa` enters equation (1) only inside a logarithm, which is why even a
`kappa` wrong by half still moves `lambda(0)` by only about 3 %, and why
`Delta(0)` — which depends on the *shape* of `rho_s(T)` and not on its scale —
is the more robust of the two.

So this is a convenience rather than a correction for most data. The reason to
prefer it is that it removes a number nobody measured.

### Related work

W. Crump's [BCS-theory-critical-current-fit](https://github.com/WayneCrump/BCS-theory-critical-current-fit)
fits `Jc(T)` to the same self-field relation, in MATLAB, and is wider than this
in most directions: type I as well as type II, d-wave as well as s-wave, one
band and an alpha model and two independent bands and a Uemura coupling, and 2D,
3D rectangular and wire geometries with anisotropy. It takes `kappa` as one
fixed number entered per fit -- `kap = log(kappa) + 0.5`, evaluated once -- and
no upper critical field appears anywhere in it. Read 2026-08-26; it may have
moved on.

The trade runs both ways, and the four restrictions listed under *When this is
the right tool* are what decides it: a d-wave gap, two bands, or a wire rather
than a film are exactly the cases section 9 of the specification declines here
on purpose, and exactly the cases that program covers. What the narrower scope
buys is the `Hc2(T)` route above, and the room to carry an assumption list, a
Monte Carlo, and a clean-versus-dirty comparison alongside every number.

This is an independent implementation of the published relation. It was written
from the equations in the paper, and `specs/001-jc-to-gap/research.md` and the
commit history record that: the specification and the physics were fixed before
any code existed.

### What it does not do

Multi-band or two-gap models, gap models with nodes, anisotropic `Hc2`,
correlated input uncertainties, sample geometries other than the thin-film
limit, and `Jc` measured in an applied field. `specs/001-jc-to-gap/spec.md`
section 9 says why for each.

---

## Three things worth knowing before trusting a number

**A wrong `Jc` unit does not fail.** A/cm² and A/m² are both physically
possible, so nothing can detect the mistake. It moves `lambda(0)` by a factor of
21.5 and produces a perfectly plausible answer. Check the unit selector.

**Clean and dirty limits are hard to tell apart.** They differ by at most 0.097
in `rho_s`, so separating them needs scatter on `Jc` below about half a per
cent. Above roughly 2 % the tool will say it cannot choose -- and the two models
give gaps about 20 % apart, so which one was used has to be reported.

**Data that stop well below `Tc` do not determine the coupling ratio.** Below
about a third of `Tc` the superfluid density is flat against one, so a
measurement taken only in a liquid-helium bath carries almost no information
about how the curve bends -- and `2 Delta(0) / kB Tc` depends on exactly that.
The fit still returns a number; the tool now declines to name a coupling regime
from it and says why. Fixing `Tc` to its measured value does not help, measured
at a factor-of-three error either way. `lambda(0)` is unaffected, and with `Tc`
free so is `Delta(0)` whenever its own error bar is small. Measure to at least
`0.4 Tc`.

---

## Layout

    .specify/memory/constitution.md   the rules this project does not break
    specs/001-jc-to-gap/              what is being built and why, and the physics
    backend/app/core/                 the physics. No web framework, ever
    backend/app/                      the HTTP layer over it
    backend/tests/                    202 tests, and the fixtures they run on
    frontend/src/                     the page. Its Korean lives here
    frontend/e2e/                     the acceptance walkthrough, executed
    docs/                             how this was built, for the maintainer
    legacy/                           the archived command-line prototypes

`backend/app/core/` imports no web framework and does no I/O, and a test
enforces that. The physics can be used from a notebook, or under a different
interface, without any of the rest.

---

## Checking it

    cd backend && .\.venv\Scripts\python.exe -m pytest -v      # 202 tests
    cd frontend && npm run test:e2e                             # 28 tests, starts both servers
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

---

## Licence and attribution

MIT, in `LICENSE`. Use it, change it, publish it; keep the notice; no warranty.

The physics is Talantsev and Tallon's, and this is an independent
implementation of the published relation rather than a derivative of any
existing code. Their paper is open access under CC BY 4.0:

> E. F. Talantsev and J. L. Tallon, *Universal self-field critical current for
> thin-film superconductors*, Nature Communications **6**, 7820 (2015).
> DOI [10.1038/ncomms8820](https://doi.org/10.1038/ncomms8820)

`specs/001-jc-to-gap/research.md` cites the source of every equation and
constant, including Tinkham for the dirty-limit superfluid density. Dependencies
are BSD, MIT, or Apache-2.0 throughout; none imposes conditions on this code.
