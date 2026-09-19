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

**AS-9 — Withdrawn**
The system shipped two generated example datasets so that a first-time user had
something to run before preparing a file of their own. They were removed: the
numbers in them were computed from stated parameters rather than measured, and
distributing manufactured measurements alongside a measurement tool is not a
trade this project is willing to make, however plainly the files said what they
were. Section 9 records the consequence.

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
  computation to be reproduced exactly. Every saved file MUST carry it too,
  since a saved file is what survives into a notebook or a paper and the screen
  does not: how the coherence length was established and the fixed
  Ginzburg-Landau parameter if one was used, the gap model, the extraction
  route, a critical temperature that was held fixed, and for a propagated
  uncertainty every stated input uncertainty, the correlation mode, the number
  of draws, the confidence level and the seed -- and every warning the
  propagation raised, not only those the fit raised.

  *Why the file and not only the screen.* An adversarial review found the
  saved files recorded the seed and the draw count but not the stated input
  uncertainties, so the same seed with a different "5 %" gave a different
  interval that the file could not explain. Checking that finding turned up two
  more omissions of the same kind: the method used for the coherence length --
  and with it the fixed Ginzburg-Landau parameter, one of the numbers that sets
  the penetration depth -- appeared in neither file, and the propagation's own
  warnings, one of which says the interval may be too narrow, were not written
  at all.
- **FR-018** While a long-running uncertainty computation is in progress, the
  system MUST show that it is running and how far along it is, and MUST keep the
  page usable. Because the page stays usable, the data can change while the
  computation runs, and its result MUST then be attached only to the analysis
  it was started for -- never to whichever analysis is showing when it
  arrives.

  *Why this is stated.* An adversarial review suspected it and an end-to-end
  test reproduced it: with the start request held until a second sample had
  been analysed, the first sample's interval appeared beside the second
  sample's fit -- a penetration depth of 120 nm with an interval centred on
  250 nm -- and would have gone into the exported file. With two similar
  samples nothing on the screen would have shown it.
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
- **FR-023a** The system MUST say so, in words, when the data do not determine
  the coupling ratio -- and MUST NOT name a coupling regime in that case. It
  MUST also say what that means for the zero-temperature gap itself, which is
  not the same thing: with the critical temperature free, the gap can still be
  determined when the ratio is not, and its own uncertainty says when; with the
  critical temperature fixed, the two are one quantity and neither is.

  *Why this is separate from FR-023.* The failure it describes happens at the
  other end of the temperature range. Below about a third of the critical
  temperature the superfluid density is flat against one to within the scatter,
  so data that stop there carry almost no information about the gap, and a
  measurement taken in a liquid-helium bath and nowhere else is exactly such a
  dataset. The fit still returns a gap. It returns it with an enormous
  uncertainty, and often with a parameter resting against one of the limits the
  fit is confined to -- but FR-021 then characterises the coupling regime from
  the central value alone, and a weak-coupling superconductor measured this way
  is reported as strongly coupled.

  The fitted zero-temperature penetration depth is not affected and MUST still
  be reported: it is set by the coldest data, which such a dataset has plenty
  of.

  *What fixing the critical temperature does not do.* It is the obvious remedy
  and it does not work. With the critical temperature held at its true value
  the gap from such data is still wrong by a factor of three, because the
  information that is missing is the shape of the superfluid density, not the
  temperature at which it ends. The warning MUST NOT suggest it. What it can
  honestly say is that measurements closer to the critical temperature are
  needed.
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
  temperature, showing the measured values and the fitted curve together, on
  the same terms as FR-026.

  *Where that curve is allowed to exist.* The predicted critical current
  density needs the coherence length as well as the penetration depth. Under a
  fixed Ginzburg-Landau parameter the coherence length follows from the fit and
  the curve MUST be drawn over the whole range the other two are. From an upper
  critical field or a supplied coherence length it is known only where a
  measurement was taken, and there the curve MUST be drawn between the coldest
  and hottest measurement and nowhere else: reaching past them would require
  assuming a temperature dependence for the upper critical field, which section
  9 excludes.

  Between the measurements the coherence length MUST be obtained by
  interpolation, and the system MUST state on screen that this is what the
  curve rests on. Interpolating between two measurements is a far weaker claim
  than extending past the last one, and the difference is why one is done and
  the other refused.

  *What the curve must not become.* The same model MUST also be reported at
  each measured temperature, since that is what the results table carries and
  what the residuals of the direct extraction route measure; the curve and that
  column MUST be one model sampled twice rather than two expressions of it. The
  reported values and those residuals MUST agree exactly rather than
  approximately.

  Where the curve has no value, the system MUST say so as an absence — a gap in
  the line, an empty cell in a file — and never as a zero.
- **FR-027** The system MUST let the user save the numerical results as a table
  that spreadsheet software can open, and each plot as an image file. That
  table MUST carry the predicted critical current density beside the measured
  one, since both have one value per measurement.
- **FR-027a** The system MUST let the user save the fitted curve as numbers on
  the same terms: a table that spreadsheet software can open, carrying every
  curve that was drawn and not a different sampling of any of them, and stating
  the conditions it was produced under.

  *Why this is separate from FR-027.* An image cannot be replotted. A user
  preparing a figure needs the model curve as numbers to draw it beside their
  own measurements in their own tool, and the per-temperature table of FR-027
  does not contain it: that table has one row per measurement, and the curve is
  sampled independently of where the measurements happen to lie.
- **FR-029a** With no data entered, the system MUST show the column layout it
  expects and the separators it accepts, since that is what a built-in example
  used to demonstrate by being pressed. Any numbers shown to illustrate the
  layout MUST be too few to analyse, so that a layout illustration cannot be
  mistaken for a dataset -- which is the mistake FR-028 was withdrawn over.
- **FR-028** *Withdrawn.* The system MUST NOT distribute measurement data it did
  not measure, generated or otherwise. A dataset shipped beside an analysis tool
  is read as an example of what the tool is for, and a manufactured one makes a
  claim about real samples that nobody took an instrument to.

  *What this costs, stated rather than glossed over.* A first-time user now has
  to bring a file before anything happens, which is a worse first minute than
  pressing a button. And generated data with a known answer is the only thing
  that can verify the whole chain end to end -- no real film has a known
  `lambda(0)` to check against -- so that verification does not disappear; it
  moves out of the product and into the test suite, where it is not distributed
  as an example of anything. FR-029a says what the user sees instead.

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
- **Shipping any dataset at all.** Nothing that looks like a measurement is
  distributed with this tool. Generated data was tried and withdrawn (FR-028);
  data taken from a published figure was considered and not pursued, because
  the only candidates with the right gap symmetry have their numbers in figures
  rather than in tables, and reading points off a plot to ship as an example
  would put digitisation error into the one file a new user judges the tool by.
  A user brings their own data, or reads FR-029a and prepares a file.

## 10. Resolved decisions

| Question | Decision |
| --- | --- |
| Which gap models? | Single-band nodeless, clean limit and dirty limit only. |
| Which extraction route? | Both the two-step and the direct route. |
| Command-line access? | Not provided. The browser is the only interface. |
| Display language? | Korean on screen; English in code and documents. |
| Second display language? | Not built. Deferred until actually required. |
| Ship example datasets? | No. Generated ones were shipped and then withdrawn; see FR-028. |
