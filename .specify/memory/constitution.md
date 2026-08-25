# Project Constitution — Nodeless SC Gap Extractor

**Version:** 1.1.0
**Ratified:** 2026-08-22
**Amended:** 2026-08-25 — VIII gains an exemption for teaching material
**Status:** Active

These are the non-negotiable rules of this project. They outrank convenience,
performance, and personal preference. Any change that violates a principle must
either be rejected, or the constitution must be amended first (see Amendment
Procedure) — never silently broken.

---

## I. The physics core is framework-agnostic

`backend/app/core/` MUST NOT import FastAPI, Pydantic, Starlette, HTTP types, or
any web concept. It MUST NOT read files, parse command-line arguments, print, or
log to stdout. It receives plain Python and NumPy values and returns plain
Python and NumPy values.

**Why.** The scientific content of this project is the physics, not the web app.
Frameworks are replaced every few years; the Talantsev-Tallon relation is not.
Anything entangled with a framework dies with that framework. Keeping the core
clean means the UI layer can be rewritten, or the physics reused from a
notebook, without touching validated code.

**Test.** `backend/tests/test_core_purity.py` scans every module under `core/`
for forbidden imports and fails the build if one appears.

---

## II. No physics without a test that pins it down

Every function in `core/` that computes a physical quantity MUST have at least
one test that checks it against something independently known: an analytic
limit, a closed-form special case, a published value, or a round-trip through
synthetic data generated from known parameters.

**Why.** A fitting routine that is subtly wrong does not crash. It returns a
plausible number with a plausible error bar, and that number ends up in a paper.
Type checkers and code review cannot catch a misplaced factor of two. Only a
test against a known answer can.

**Minimum required checks.**

- `rho_s(T -> 0) = 1` and `rho_s(T -> Tc) = 0`, for both clean and dirty limits.
- Round-trip: generate synthetic `Jc(T)` from known `(lambda0, Delta0, Tc, kappa)`,
  fit it back, and recover the inputs. This is the single most important test in
  the project.
- Weak-coupling BCS: `Delta0 = 1.764 kB Tc` must yield `2 Delta0 / (kB Tc) = 3.53`.
- Agreement with `legacy/` scripts on `lambda(T)` for identical input.

---

## III. Specification precedes implementation

Work proceeds in the order: constitution -> spec -> plan -> tasks -> code.
When implementation reveals that the spec was wrong, the spec is corrected
first, and the correction is committed before the code that depends on it.

`spec.md` describes only observable behaviour and user-facing outcomes. It MUST
NOT name a language, library, framework, protocol, database, or file format.
Those belong in `plan.md`.

**Why.** A specification that leaks implementation details cannot survive a
technology change, and stops being a record of intent. The separation is what
makes the spec useful two years from now.

---

## IV. The backend emits data and error codes, never display prose

API responses MUST NOT contain sentences intended for a human reader. Failures
are reported as a stable machine-readable code plus structured parameters:

    {"code": "NO_ROOT_TYPE_II", "params": {"temperature_K": 4.2, "jc_A_per_m2": 1.2e10}}

Rendering that into a sentence is the frontend's job.

**Why.** The UI of this project is in Korean while the code and documents are in
English; mixing display language into the backend would scatter Korean strings
through English source. It also keeps error handling testable — a test asserts a
code, not a sentence that someone may later reword.

---

## V. SI internally, explicit units at the boundary

Inside `core/`, every quantity is in SI base units: metres, amperes per square
metre, tesla, kelvin, joules. Conversion happens only at the input boundary
(when parsing user data) and the output boundary (when formatting results).

Any variable holding a non-SI value MUST carry the unit in its name
(`lambda_nm`, `delta0_meV`, `jc_A_per_cm2`). Bare names such as `lambda_` or
`delta0` always mean SI.

**Why.** Unit confusion is the most common source of silent numerical error in
physics code, and this project mixes conventions that invite it: `Jc` is
reported in A/cm^2, `xi` in nm, `Delta` in meV, `Hc2` in tesla.

---

## VI. Model assumptions travel with the result

Any result derived under an assumption that could invalidate it MUST be returned
together with a machine-readable statement of that assumption and of any
detected violation. The application must not present a number as if it were
unconditional.

At minimum the following are checked and reported:

- `Jc` must be self-field transport `Jc`; magnetisation-derived data is invalid.
- The thin-film regime assumed by the Talantsev-Tallon relation.
- `kappa` remaining in the strong type-II range (`kappa >> 1/sqrt(2)`).
- Sufficient low-temperature data for `Delta(0)` to be determined at all.
- Whether clean-limit or dirty-limit is the better description of the data.

**Why.** The equation will return a number for input that violates every one of
its assumptions. The user cannot see that from the number alone.

---

## VII. Stochastic results are reproducible

Every Monte Carlo computation MUST accept an explicit seed, default to a fixed
one, and report the seed used alongside the result. Re-running with the same
inputs and seed MUST reproduce the output exactly.

**Why.** An error bar that changes between runs cannot be cited, checked by a
reviewer, or debugged.

---

## VIII. English for the code, Korean for the screen

Source code, comments, docstrings, identifiers, documents, and commit messages
are written in English. Text displayed in the browser is written in Korean.

Korean UI strings live in the frontend only. No general internationalisation
framework is used; if a second display language is ever required, that is a
future amendment, not a present cost.

**Exemption (added 1.1.0).** Material written to teach the maintainer rather
than to instruct whoever changes the code is written in the language its reader
reads, and lives under `docs/` and nowhere else. The exemption reaches nothing
outside that directory: `specs/`, `README.md`, `CLAUDE.md`, source code,
identifiers, and commit messages stay English, because they are read by whoever
edits the code, by a future contributor, and by tools.

**Why.** The rule above exists to stop two languages from interleaving in one
file and to keep error handling testable, not to stop the maintainer from
having notes he can read. A teaching document held to English is a document
that does not get written, or gets written and not read; either way the rule
would be costing more than it protects. Confining the exemption to one
directory keeps the boundary checkable by eye.

---

## IX. Simplicity is the default; complexity must be justified

Prefer the smaller construct: a function over a class, a module over a package,
a plain dict over a bespoke type, no dependency over a new dependency. Adding a
runtime dependency, a layer of abstraction, or a background process requires a
written justification in `plan.md`.

**Why.** The maintainer of this project is a researcher, not a full-time
software engineer. Every abstraction is a thing that must be re-understood
before the next change can be made safely. Complexity that is not paying for
itself is a defect.

---

## Amendment Procedure

1. State which principle is being changed and why, in the pull request or commit
   message that changes this file.
2. Bump the version: MAJOR for removing or reversing a principle, MINOR for
   adding one, PATCH for clarification that does not change meaning.
3. Update any document or test that the amendment invalidates in the same
   commit, so the repository is never internally inconsistent.

## Compliance

`specs/001-jc-to-gap/plan.md` contains a Constitution Check section that must be
completed before implementation begins, and re-checked after the design is
detailed. Deviations are recorded there with justification, or the design is
changed.
