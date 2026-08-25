# Feature Specification — From self-field Jc to the superconducting gap

**Feature ID:** 001-jc-to-gap
**Status:** Draft
**Created:** 2026-08-22

> **Scope rule.** This document describes *what* the system does and *why*,
> in terms an experimentalist would use. It deliberately names no language,
> library, framework, protocol, or file format. Those decisions live in
> `plan.md` and may change without this document changing.

---

## 1. Problem

The quantities that characterise a superconductor are not equally easy to
measure. They divide sharply into two groups.

**Cheap.** The critical current density `Jc` and the upper critical field `Hc2`
come out of ordinary charge-transport measurements — a four-probe current-voltage
sweep and a resistance-versus-temperature curve in a magnetic field. Almost any
laboratory that can cool a sample can obtain them, on its own samples, in a day.

**Expensive.** The London penetration depth `lambda` requires a dedicated probe:
muon spin rotation, a tunnel-diode oscillator, a microwave cavity, or a mutual
inductance rig. The energy gap `Delta` requires tunnelling spectroscopy,
scanning tunnelling microscopy, or angle-resolved photoemission. These usually
mean beam time at an external facility, a collaboration, and months of waiting —
and they constrain which samples can be studied at all.

Yet `lambda` and `Delta` are the quantities that say what the pairing state
actually is. `lambda` fixes the superfluid stiffness `ns/m*`; `Delta(0)` and the
coupling ratio `2 Delta(0) / (kB Tc)` say whether the pairing is weak-coupling
BCS or something stronger, and can be compared directly against other materials.

Established theory closes this gap. The self-field critical current of a
type-II superconductor is set by the lower critical field and the penetration
depth, so measured `Jc(T)` — with `Hc2(T)` supplying the coherence length —
determines `lambda(T)`. The temperature dependence of `lambda` then gives the
superfluid density, and fitting that to a gap model gives `Delta(0)`.

That chain is well established but is not routinely available as a tool. It is
carried out by hand, differently each time, with the assumptions applied left
implicit and unrecorded.

## 2. Goal

Let a researcher obtain `lambda(T)` and `Delta(0)` from measurements they can
already make, in a browser, in seconds — with uncertainties, with the
assumptions used stated explicitly alongside every number, and with a warning
whenever the supplied data violate those assumptions.

The tool is a substitute for a dedicated `lambda` or `Delta` measurement only to
the extent that its assumptions hold. Making the reader aware of exactly which
assumptions are in play is therefore part of the deliverable, not a caveat
attached to it.

## 3. Users

**Primary user.** An experimental superconductivity researcher who has measured
critical current data. Comfortable with the physics; not necessarily comfortable
with programming. Works from their own laptop, on their own data, usually alone.

**Secondary user.** A collaborator or reviewer who wants to reproduce a
published number and check what was assumed to obtain it.

## 4. Primary user story

A researcher has a file containing temperature and self-field critical current
density for one sample, and knows the upper critical field of that sample. They open
the tool in a browser, provide the data, state which units it is in, and ask for
the analysis. Within a few seconds they see the penetration depth at each
temperature, the fitted zero-temperature gap with its uncertainty, the coupling
ratio compared against the BCS value, and a plot of the superfluid density with
the fitted curve drawn through the measured points. They save the table and the
plot for their paper.

## 5. Acceptance scenarios

**AS-1 — Analysis with upper critical field**
Given a dataset of temperature, self-field critical current density, and upper
critical field,
When the user requests the analysis,
Then the system reports the coherence length, penetration depth and
Ginzburg-Landau parameter at each temperature, and a fitted zero-temperature
penetration depth, zero-temperature gap, critical temperature, and coupling
ratio, each with an uncertainty.

**AS-2 — Analysis with an independently known coherence length**
Given a dataset where the coherence length is supplied directly instead of the
upper critical field,
When the user requests the analysis,
Then the system produces the same outputs as AS-1 without deriving the coherence
length itself.

**AS-3 — Analysis with a fixed Ginzburg-Landau parameter**
Given only temperature and critical current density, plus a single
temperature-independent Ginzburg-Landau parameter chosen by the user,
When the user requests the analysis,
Then the system produces the same outputs as AS-1 and additionally reports the
coherence length implied at each temperature.

**AS-4 — Choice of gap model**
Given a completed analysis,
When the user switches between the clean-limit and the dirty-limit description,
Then the fit is repeated and the system reports which of the two describes the
data better, together with the quantitative basis for that judgement.

**AS-5 — Choice of extraction route**
Given a dataset,
When the user selects either the two-step route (obtain the penetration depth at
each temperature first, then fit it) or the direct route (fit the measured
critical current data in one step),
Then the system reports results for the selected route, and the two routes agree
within their stated uncertainties on data that satisfy the model assumptions.

**AS-6 — Uncertainty propagation**
Given that the user states the relative measurement uncertainty of the critical
current density and of the upper critical field, coherence length, or
Ginzburg-Landau parameter, and states whether that uncertainty is common to the
whole dataset or varies from point to point,
When the user requests uncertainty propagation,
Then the system reports an uncertainty interval for the zero-temperature gap and
the zero-temperature penetration depth that reflects those input uncertainties,
and reports the settings used so the result can be reproduced exactly.

**AS-7 — Assumption violated**
Given data for which no physically admissible penetration depth exists at some
temperature, or for which the Ginzburg-Landau parameter falls outside the strong
type-II range,
When the user requests the analysis,
Then the system explains which assumption failed and at which temperature,
rather than silently returning a number or failing without explanation.

**AS-8 — Insufficient low-temperature data**
Given data that only cover temperatures near the critical temperature,
When the user requests a gap fit,
Then the system still reports the fit but warns that the zero-temperature gap is
poorly constrained by data of this temperature range.

**AS-9 — Trying the tool without data**
Given a first-time user with no data at hand,
When the user selects one of the built-in example datasets,
Then the full analysis runs on that dataset and produces results, so the user can
see what the tool does before preparing their own file.

**AS-10 — Taking results away**
Given a completed analysis,
When the user asks to save the results,
Then the numerical results are provided as a table that spreadsheet software can
open, and each plot can be saved as an image.

## 6. Functional requirements

### Data entry

- **FR-001** The system MUST accept measurement data either as an uploaded file
  or as text pasted directly into the page.
- **FR-002** The system MUST accept data whose columns are separated by spaces,
  tabs, commas, or semicolons, with or without a header row, and with comment
  lines that the user has marked.
- **FR-003** The system MUST show the user how it interpreted the columns before
  computing anything, so a misread file is caught immediately.
- **FR-004** The system MUST let the user state the units of the critical current
  density and of the coherence length, and MUST NOT assume a unit silently.
- **FR-005** The system MUST reject non-numeric, missing, zero, or negative
  values in physical quantities that must be positive, identifying the offending
  row.

### Penetration depth extraction

- **FR-006** The system MUST support three ways of establishing the coherence
  length: derived from the upper critical field, supplied directly by the user,
  or implied by a fixed Ginzburg-Landau parameter chosen by the user.
- **FR-007** The system MUST report, at each measured temperature, the coherence
  length, the penetration depth, and the Ginzburg-Landau parameter.
- **FR-008** The system MUST select the physically appropriate solution branch
  for a strong type-II superconductor, and MUST report an explicit failure when
  no such solution exists rather than returning an inadmissible one.

### Gap extraction

- **FR-009** The system MUST compute the normalised superfluid density from the
  penetration depth.
- **FR-010** The system MUST fit the data to a single-band nodeless gap model in
  both the clean limit and the dirty limit, at the user's choice.
- **FR-011** The system MUST offer both the two-step route and the direct route
  described in AS-5.
- **FR-012** The system MUST report the fitted zero-temperature penetration
  depth, zero-temperature gap, and critical temperature, each with a standard
  uncertainty, together with the coupling ratio `2 Delta(0) / (kB Tc)`.
- **FR-013** The system MUST allow the critical temperature to be held fixed at a
  value the user measured independently, instead of being fitted.
- **FR-014** The system MUST report a failure to converge as such, and MUST NOT
  present an unconverged fit as a result.

### Uncertainty

- **FR-015** The system MUST propagate user-stated relative measurement
  uncertainties on the input quantities through to uncertainty intervals on the
  fitted parameters.
- **FR-016** The system MUST let the user choose the confidence level of the
  reported interval.
- **FR-017** The system MUST report enough information for an uncertainty
  computation to be reproduced exactly.
- **FR-018** While a long-running uncertainty computation is in progress, the
  system MUST show that it is running and how far along it is, and MUST keep the
  page usable.
- **FR-029** The system MUST let the user state whether a quoted measurement
  uncertainty is a calibration error common to the whole dataset or scatter that
  varies from one temperature to the next, MUST default to the former, and MUST
  report which was assumed. The two imply materially different uncertainties on
  the gap, and the difference is not something the system can infer from the
  data.
- **FR-030** The system MUST report the uncertainty arising from the scatter of
  the data about the model separately from the uncertainty propagated from the
  stated measurement errors, and MUST NOT present a single combined figure,
  because whether the two may be combined depends on the answer to FR-029.

### Diagnostics

- **FR-019** The system MUST report the goodness of fit and let the user inspect
  the residuals.
- **FR-020** The system MUST compare the clean-limit and dirty-limit fits and
  state which describes the data better, with the quantitative basis.
- **FR-021** The system MUST compare the fitted coupling ratio against the
  weak-coupling BCS value and characterise the coupling regime.
- **FR-022** The system MUST warn when the Ginzburg-Landau parameter leaves the
  strong type-II range at any measured temperature.
- **FR-023** The system MUST warn when the temperature range of the data is too
  narrow at the low end to constrain the zero-temperature gap.
- **FR-024** The system MUST state, alongside every result, that the input is
  required to be self-field transport critical current density from a thin film
  free of weak links, and MUST warn when a film thickness the user supplies is
  inconsistent with the thin-film regime.

### Results and export

- **FR-025** The system MUST show the per-temperature results as a table.
- **FR-026** The system MUST plot the penetration depth against temperature and
  the superfluid density against temperature, showing measured points and the
  fitted curve together. The fitted curve MUST begin at absolute zero, so that
  the intercept the analysis reports is visible on the plot rather than
  inferred from where the curve happens to start.
- **FR-026a** The system MUST plot the critical current density against
  temperature, showing the measured values and what the fitted parameters
  predict for the same measurements together.

  *Why this one is not drawn as a smooth curve.* The predicted critical current
  density needs the coherence length as well as the penetration depth. Under a
  fixed Ginzburg-Landau parameter the coherence length follows from the fit and
  is known at every temperature; from an upper critical field or a supplied
  coherence length it is known only where a measurement was taken, and filling
  the gaps between them would require assuming a temperature dependence for the
  upper critical field, which section 9 excludes. The prediction is therefore
  reported at the measured temperatures in all three cases, so that what is
  plotted rests on no assumption the analysis has not already stated.

  This is what the residuals of the direct extraction route already measure, so
  the plot and those residuals MUST agree exactly rather than approximately.
- **FR-027** The system MUST let the user save the numerical results as a table
  that spreadsheet software can open, and each plot as an image file. That
  table MUST carry the predicted critical current density beside the measured
  one, since both have one value per measurement.
- **FR-027a** The system MUST let the user save the fitted curve as numbers on
  the same terms: a table that spreadsheet software can open, carrying the
  curve that was drawn and not a different sampling of it, and stating the
  conditions it was produced under.

  *Why this is separate from FR-027.* An image cannot be replotted. A user
  preparing a figure needs the model curve as numbers to draw it beside their
  own measurements in their own tool, and the per-temperature table of FR-027
  does not contain it: that table has one row per measurement, and the curve is
  sampled independently of where the measurements happen to lie.
- **FR-028** The system MUST provide at least two built-in example datasets that
  exercise the full analysis.

## 7. Key entities

| Entity | Meaning |
| --- | --- |
| **Measurement dataset** | Temperatures with the corresponding self-field critical current density, and optionally the upper critical field or the coherence length. |
| **Analysis settings** | Units of the supplied data, how the coherence length is established, which gap model, which extraction route, whether the critical temperature is fixed, stated input uncertainties, confidence level. |
| **Per-temperature result** | For one temperature: coherence length, penetration depth, Ginzburg-Landau parameter, normalised superfluid density. |
| **Fit result** | Zero-temperature penetration depth, zero-temperature gap, critical temperature, coupling ratio, each with a standard uncertainty; goodness of fit; residuals. |
| **Uncertainty result** | Interval and standard deviation for each fitted parameter, at a stated confidence level, with the settings needed to reproduce it. |
| **Diagnostic report** | Goodness of fit, clean-versus-dirty comparison, coupling-regime characterisation, and the list of assumption warnings that apply. |

## 8. Quality attributes

- **QA-001** An analysis without uncertainty propagation, on a dataset of up to
  200 temperature points, completes fast enough to feel immediate.
- **QA-002** An uncertainty computation on such a dataset completes within a few
  minutes and reports progress throughout.
- **QA-003** Repeating any computation with identical inputs and settings
  produces identical output.
- **QA-004** Every reported number carries its unit, on screen and in the saved
  table.
- **QA-005** The tool runs on a single machine with no external service and no
  network access after installation.
- **QA-006** No measurement data leaves the user's machine.

## 9. Out of scope for this feature

- **Sample geometries other than the thin-film limit.** The relation between the
  self-field critical current and the penetration depth carries a geometric
  factor that differs between a thin film, a tape, a round wire, and a bulk
  specimen. Only the thin-film form is implemented. A sample whose transverse
  dimension is large compared with `lambda` is outside the implemented model,
  which is why FR-024 requires this to be stated on every result and warned
  about when the user supplies a thickness inconsistent with it. Supporting
  other geometries is a candidate for a later feature, not this one.
- Multi-band or two-gap models, and gap models with nodes.
- Anisotropic treatment of the upper critical field.
- Correlated input uncertainties.
- Deriving `Jc` from a measured critical current and sample geometry.
- Fitting `Jc` measured in an applied magnetic field.
- User accounts, saved sessions, and multi-user operation.
- Comparing several samples in one view.

## 10. Resolved decisions

| Question | Decision |
| --- | --- |
| Which gap models? | Single-band nodeless, clean limit and dirty limit only. |
| Which extraction route? | Both the two-step and the direct route. |
| Command-line access? | Not provided. The browser is the only interface. |
| Display language? | Korean on screen; English in code and documents. |
| Second display language? | Not built. Deferred until actually required. |
