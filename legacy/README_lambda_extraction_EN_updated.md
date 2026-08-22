# Penetration-depth extraction from self-field critical current density

## 1. Purpose

This package contains three Python programs for extracting the London
penetration depth, lambda(T), of a type-II superconducting thin film from
self-field transport critical-current-density data.

The three entry points are:

1. `lambda_from_T_Jc_Hc2.py`
   - Input: T, Jc, Hc2
   - Calculates xi(T) from Hc2(T)
   - Solves for lambda(T) with a temperature-dependent
     kappa(T) = lambda(T)/xi(T)

2. `lambda_from_T_Jc_xi.py`
   - Input: T, Jc, xi
   - Uses the supplied xi(T)
   - Solves for lambda(T) with a temperature-dependent
     kappa(T) = lambda(T)/xi(T)

3. `lambda_from_T_Jc_constant_kappa.py`
   - Input: T, Jc
   - User supplies one fixed kappa = lambda/xi
   - Calculates lambda(T) explicitly and also reports inferred xi(T)

All three programs can propagate user-specified relative experimental
uncertainties to lambda by Monte Carlo.

---


## 2. Symbols, variables, and physical quantities

This section defines the quantities used throughout the programs and the README.
Unless otherwise noted, all calculations are carried out internally in SI units.

### T — Temperature

`T` is the sample temperature.

    Symbol: T
    Typical input unit: K
    SI unit used internally: K

Each row of an input file corresponds to one temperature point. The programs do
not assume any particular analytical form for the temperature dependence of the
input data; they calculate xi(T), lambda(T), and kappa(T) independently at each
temperature.

### Jc — Critical current density

`Jc` is the superconducting critical current density. In the present method it
must correspond to the **self-field transport critical current density**, i.e.
the current density measured without an intentionally applied external magnetic
field, within the assumptions of the Talantsev-Tallon thin-film analysis.

    Symbol: Jc
    Accepted input units: A/cm^2 or A/m^2
    Internal SI unit: A/m^2

If `Jc` is calculated from a measured critical current Ic,

    Jc = Ic / A

where `A` is the current-carrying cross-sectional area of the bridge or film.
Consequently, uncertainty in bridge width and film thickness can contribute
directly to the uncertainty of Jc.

A larger Jc generally corresponds to a smaller extracted lambda because Eq. (4)
contains approximately

    Jc proportional to lambda^(-3),

apart from the logarithmic kappa correction.

### Hc2 / Bc2 — Upper critical field

`Hc2` denotes the upper critical field of a type-II superconductor: the field at
which superconductivity is destroyed and the material enters the normal state.

    Symbol commonly used experimentally: Hc2
    Input unit in Program 1: T

Strictly, magnetic field strength `H` has SI units A/m, whereas magnetic
induction `B` has units tesla. Experimental superconductivity literature
commonly reports the quantity called "Hc2" directly in tesla. In Program 1, a
supplied Hc2 value in tesla is therefore treated numerically as

    Bc2 = mu0 Hc2

expressed in tesla.

The standard isotropic/effective Ginzburg-Landau relation used in Program 1 is

    Bc2(T) = PHI0 / [2*pi*xi(T)^2].

Thus, increasing Hc2 corresponds to a decreasing GL coherence length xi.

### xi — Superconducting coherence length

`xi` (Greek letter xi, ξ) is the superconducting coherence length. Within
Ginzburg-Landau theory it characterizes the characteristic spatial length scale
over which the superconducting order parameter can vary.

    Symbol: xi = ξ
    Accepted input units in Program 2: m, nm, or um
    Internal SI unit: m

In Program 1, xi is calculated from Hc2 according to

    xi(T) = sqrt[PHI0 / (2*pi*Bc2(T))].

The xi obtained this way should be regarded as a Ginzburg-Landau or effective
coherence length associated with the supplied Hc2 data. It is not necessarily
identical to a microscopic Cooper-pair size, especially when Pauli limiting,
multiband superconductivity, strong anisotropy, vortex dynamics, or a broad
resistive transition affects the experimentally defined Hc2.

### lambda — London penetration depth

`lambda` (Greek letter lambda, λ) is the London magnetic penetration depth. It
describes the characteristic distance over which a magnetic field penetrates
into a superconductor.

    Symbol: lambda = λ
    Internal SI unit: m
    Output units provided by the programs: m and nm

Within London electrodynamics,

    lambda^(-2) proportional to ns / m*

where `ns` is the superconducting superfluid density and `m*` is an effective
carrier mass. Thus a larger lambda generally corresponds to a smaller
superfluid stiffness.

The purpose of the present programs is to extract lambda(T) from self-field Jc
using the type-II thin-film relation of Talantsev and Tallon.

### kappa — Ginzburg-Landau parameter

`kappa` (κ) is the Ginzburg-Landau parameter,

    kappa(T) = lambda(T) / xi(T).

It compares the magnetic penetration length with the coherence length.

    Symbol: kappa = κ
    Unit: dimensionless

The conventional type-I/type-II boundary is

    kappa = 1/sqrt(2).

For a clear type-II superconductor, kappa is larger than this value, and in many
materials of interest here kappa is much larger than 1.

Programs 1 and 2 recalculate kappa at every temperature after lambda has been
found. Program 3 instead assumes one user-specified constant kappa at all
temperatures.

### Hc1 — Lower critical field

`Hc1` is the lower critical field of a type-II superconductor. Below Hc1 the
bulk remains in the Meissner state; above Hc1 magnetic flux begins to penetrate
in the form of vortices.

The Talantsev-Tallon thin-film self-field relation used here can be written as

    Jc^II(sf) = Hc1 / lambda.

Using the standard large-kappa approximation for Hc1 leads to the form used in
Eq. (4),

    Jc^II(sf)
      = PHI0 / (4*pi*MU0*lambda^3) * [ln(kappa) + 0.5].

Hc1 is not supplied directly to any of the three programs.

### PHI0 — Magnetic flux quantum

`PHI0` is the superconducting magnetic flux quantum,

    PHI0 = h / (2e)
         = 2.067833848e-15 Wb.

    Symbol: Phi0 = Φ0
    SI unit: weber (Wb)

It is a fundamental constant and is fixed inside all three programs.

### MU0 — Vacuum permeability

`MU0` is the vacuum permeability,

    MU0 = 4*pi*10^(-7) H/m.

    Symbol: mu0 = μ0
    SI unit: H/m

It is also fixed internally by the programs.

### Ic — Critical current

`Ic` is the experimentally measured current at which the chosen criterion for
the superconducting-to-resistive transition is reached.

    Symbol: Ic
    Typical unit: A

The programs do not use Ic directly. If the experiment provides Ic rather than
Jc, the user must first convert it to current density using the sample
cross-sectional area.

### Film thickness and bridge width

The present code does not explicitly require film thickness or bridge width if
Jc has already been calculated. However, these geometrical quantities matter
in two ways:

1. They enter the conversion from Ic to Jc.
2. The Talantsev-Tallon model is a thin-film/self-field model, so the film
   thickness must remain within the regime where the adopted thin-film
   expression is physically appropriate.

### Self-field

`Self-field` means the magnetic field generated by the transport current itself,
without an intentionally imposed external magnetic field. The Jc used in the
Talantsev-Tallon Eq. (4) should therefore be a self-field transport Jc.

### Error percentage, sigma, and confidence interval

The command-line quantities such as

    --jc-error-percent
    --hc2-error-percent
    --xi-error-percent
    --kappa-error-percent

are interpreted as relative one-standard-deviation uncertainties.

For example,

    --jc-error-percent 5

means

    sigma_Jc / Jc = 0.05.

The Monte Carlo procedure propagates these input uncertainties through the
nonlinear equations to obtain the distribution and error bar of lambda.

`--confidence 68.27` requests the central 68.27% interval, approximately
equivalent to ±1 sigma for a Gaussian distribution.

### Quick symbol summary

| Quantity | Symbol | Meaning | Typical/input unit |
| --- | --- | --- | --- |
| Temperature | T | Sample temperature | K |
| Critical current density | Jc | Self-field transport critical current density | A/cm^2 or A/m^2 |
| Upper critical field | Hc2 / Bc2 | Field suppressing superconductivity | T |
| Coherence length | xi (ξ) | GL spatial scale of the order parameter | m, nm, um |
| Penetration depth | lambda (λ) | Magnetic penetration length | m, nm |
| GL parameter | kappa (κ) | lambda/xi | dimensionless |
| Lower critical field | Hc1 | Onset field for vortex penetration | A/m or commonly quoted as mu0 Hc1 in T |
| Flux quantum | PHI0 (Φ0) | h/(2e) | Wb |
| Vacuum permeability | MU0 (μ0) | Magnetic constant | H/m |
| Critical current | Ic | Critical transport current before conversion to Jc | A |

---

## 3. Primary reference and equation

The implementation is based on:

E. F. Talantsev and J. L. Tallon,
"Universal self-field critical current for thin-film superconductors,"
Nature Communications 6, 7820 (2015).
DOI: 10.1038/ncomms8820

For a type-II thin-film superconductor in the self-field regime, their
Eq. (4) is

    Jc^II(sf) = Hc1/lambda
              = PHI0 / (4*pi*MU0*lambda^3) * [ln(kappa) + 0.5]

with

    kappa = lambda/xi.

Therefore,

    Jc = PHI0 / (4*pi*MU0*lambda^3)
         * [ln(lambda/xi) + 0.5]

when xi is known independently.

The paper emphasizes transport self-field Jc and a thin-film geometry.
In its model the full film thickness is written as 2b; the analysis is
intended for the regime where the relevant thickness scale is not larger
than order lambda. The paper's Methods also emphasizes transport (rather
than magnetization-derived) Jc, self-field conditions, and weak-link-free
films.

Important distinction:
- The original paper often treats kappa as approximately temperature
  independent because it appears only inside a logarithm and because its
  temperature dependence has a relatively weak effect.
- Programs 1 and 2 intentionally do NOT impose constant kappa. They
  implement the user's requested self-consistent procedure:
      xi(T) -> solve lambda(T) -> kappa(T)=lambda(T)/xi(T)
  at every temperature.
- Program 3 implements the constant-kappa approximation directly.

---

## 4. Program 1: T-Jc-Hc2 -> xi(T) -> lambda(T)

### Input

Three columns in this order:

    T(K)    Jc    Hc2(T)

The file may be whitespace-, tab-, comma-, or semicolon-separated.
A header is optional.

Default Jc unit:
    A/cm^2

You may instead use:
    --jc-unit A/m2

### Step A: coherence length from Hc2

The program uses the standard Ginzburg-Landau orbital upper-critical-field
relation

    Bc2(T) = PHI0 / [2*pi*xi(T)^2]

so that

    xi(T) = sqrt[ PHI0 / (2*pi*Bc2(T)) ].

When an experimental paper or data table reports "Hc2" in tesla, the
program treats that numerical value as Bc2 = mu0 Hc2 in tesla. This is the
usual experimental convention for critical-field plots labeled in T.

### Step B: implicit solution for lambda

After xi(T) is determined, the code solves

    Jc(T) = PHI0/(4*pi*MU0*lambda(T)^3)
            * { ln[lambda(T)/xi(T)] + 0.5 }

independently at each temperature.

Because lambda appears both as lambda^-3 and inside ln(lambda/xi), there
is no simple elementary explicit expression for lambda when xi is fixed.
The code therefore uses Brent's bracketing root solver (`scipy.optimize.brentq`).

The solved branch is lambda > xi, appropriate to the strong type-II
systems for which this method is normally being used.

### Output

The output CSV includes:

    T_K
    Jc_input
    Jc_A_per_m2
    Hc2_T
    xi_m
    xi_nm
    lambda_m
    lambda_nm
    kappa_lambda_over_xi

If uncertainty propagation is enabled, it also includes Monte-Carlo
mean, standard deviation, confidence limits, and relative lambda error.

### Example

    python lambda_from_T_Jc_Hc2.py sample_Hc2.txt \
        --jc-unit A/cm2 \
        --jc-error-percent 5 \
        --hc2-error-percent 3 \
        --mc-samples 10000 \
        --confidence 68.27 \
        --output result_Hc2.csv

---

## 5. Program 2: T-Jc-xi -> lambda(T)

### Input

Three columns:

    T(K)    Jc    xi

Defaults:
    Jc unit = A/m^2
    xi unit = m

Alternative units:

    --jc-unit A/cm2
    --xi-unit nm
    --xi-unit um

### Calculation

For each row, the program directly solves

    Jc(T) = PHI0/(4*pi*MU0*lambda(T)^3)
            * { ln[lambda(T)/xi(T)] + 0.5 }.

Again,

    kappa(T) = lambda(T)/xi(T)

is not fixed; it is recalculated separately at every temperature.

### Example

    python lambda_from_T_Jc_xi.py sample_xi.txt \
        --jc-unit A/m2 \
        --xi-unit m \
        --jc-error-percent 5 \
        --xi-error-percent 4 \
        --mc-samples 10000 \
        --output result_xi.csv

---

## 6. Program 3: T-Jc with constant lambda/xi ratio

If kappa = lambda/xi is held fixed, Eq. (4) becomes

    Jc(T) = PHI0/(4*pi*MU0*lambda(T)^3)
            * [ln(kappa) + 0.5].

Now lambda is explicit:

    lambda(T)
      = { PHI0/[4*pi*MU0*Jc(T)]
          * [ln(kappa)+0.5] }^(1/3).

Thus no numerical root finding is required.

After lambda is calculated,

    xi(T) = lambda(T)/kappa

is also reported.

### Required input

Two columns:

    T(K)    Jc

and a user-specified constant kappa, for example

    --kappa 40

### Example

    python lambda_from_T_Jc_constant_kappa.py sample_Jc.txt \
        --jc-unit A/cm2 \
        --kappa 40 \
        --jc-error-percent 5 \
        --kappa-error-percent 3 \
        --mc-samples 10000 \
        --output result_constant_kappa.csv

---

## 7. Experimental uncertainty / error bars

The options ending in `--error-percent` are interpreted as relative
one-standard-deviation (1-sigma) uncertainties.

Examples:

    --jc-error-percent 5

means

    sigma_Jc / Jc = 0.05.

For Program 1:

    --jc-error-percent
    --hc2-error-percent

For Program 2:

    --jc-error-percent
    --xi-error-percent

For Program 3:

    --jc-error-percent
    --kappa-error-percent

### Monte Carlo procedure

For each temperature:

1. Generate random positive samples of each uncertain input.
2. The sampling distribution is log-normal, parameterized so that its
   relative standard deviation equals the requested percentage.
3. Recalculate xi if necessary.
4. Re-solve Eq. (4) for lambda for every random sample.
5. Report:
   - Monte-Carlo mean lambda
   - 1-sigma standard deviation
   - central confidence interval
   - relative standard deviation in percent

Log-normal sampling is used because Jc, Hc2, xi, and kappa are positive
physical quantities; ordinary Gaussian sampling can generate negative
values when uncertainties are not very small.

### Confidence interval

Default:

    --confidence 68.27

which is the Gaussian-equivalent approximately 1-sigma central interval.

For approximately 95%:

    --confidence 95

### Number of Monte Carlo samples

Default:

    --mc-samples 5000

For final publication-quality uncertainty estimates, 10000-50000 samples
are generally safer, especially if the uncertainty is large or the
nonlinearity is strong.

Increasing `--mc-samples` improves the statistical stability of the
reported uncertainty, but it does not reduce the experimental uncertainty.

---

## 8. Numerical accuracy versus experimental uncertainty

These are different concepts.

### Experimental uncertainty

Controlled by:

    --jc-error-percent
    --hc2-error-percent
    --xi-error-percent
    --kappa-error-percent

These determine the physical error bar on lambda.

### Numerical root accuracy

Programs 1 and 2 additionally allow:

    --root-xtol
    --root-rtol

Defaults:

    --root-xtol 1e-15  [m]
    --root-rtol 1e-12

These are the stopping tolerances of Brent's root solver.

In realistic superconductivity data, the numerical root error at these
defaults is vastly smaller than the experimental uncertainty. Therefore,
one should normally change the experimental uncertainty settings rather
than making the numerical tolerance unnecessarily tighter.

Program 3 is an explicit formula and therefore does not need a root
solver.

---

## 9. Important physical assumptions and limitations

### A. Jc must be self-field transport Jc

The Talantsev-Tallon analysis concerns the self-field critical current
density. A Jc measured in a substantial externally applied magnetic field
should not automatically be inserted into Eq. (4).

### B. Thin-film regime

The model was developed for thin conductors where the transverse
thickness scale is comparable to or smaller than lambda. If the sample
is substantially thicker than lambda, the original paper discusses a
thickness correction and a crossover of the lambda scaling.

### C. Weak links / sample quality

The original paper's data selection emphasizes weak-link-free films.
A measured Jc suppressed by cracks, weak links, connectivity loss,
inhomogeneous current paths, or a nonintrinsic voltage criterion can
cause Eq. (4) to return an apparent lambda that is too large.

### D. Hc2-derived xi is a model-dependent coherence length

Program 1 uses

    xi = sqrt[PHI0/(2*pi*Hc2)].

This is the standard GL orbital relation. If the experimentally defined
Hc2 is strongly affected by Pauli limiting, multiband effects, a broad
resistive transition, vortex dynamics, dimensional crossover, or an
arbitrary resistive criterion, the resulting xi should be interpreted
as an effective GL coherence length.

### E. kappa near the type-I/type-II boundary

The numerical solvers intentionally use the lambda > xi branch, because
the intended application here is a clearly type-II material. If the
system is close to kappa = 1/sqrt(2), the simple strong-type-II treatment
and the approximate Hc1 expression containing ln(kappa)+0.5 need more
care.

### F. Constant-kappa program

Program 3 is appropriate only when treating kappa as temperature
independent is justified or intentionally desired. It is the closest of
the three programs to the simplification adopted in much of the 2015
Talantsev-Tallon analysis.

---


### G. Anisotropic superconductors and Hc2 orientation

Program 1 uses the isotropic/effective GL expression

    Bc2 = PHI0/(2*pi*xi^2).

For an anisotropic superconductor, the coherence length obtained from Hc2
depends on field orientation. For example, in a uniaxial GL description,

    Bc2^c  = PHI0/(2*pi*xi_ab^2)

whereas

    Bc2^ab = PHI0/(2*pi*xi_ab*xi_c).

Therefore, if the material is strongly anisotropic, Program 1 should be
interpreted as extracting the coherence length appropriate to the supplied
Hc2 geometry, or the code should be modified to use the anisotropic GL
relation appropriate to the experiment.

### H. Correlated uncertainties

The built-in Monte Carlo assumes the user-specified uncertainties in Jc,
Hc2/xi, and kappa are statistically independent. If two quantities share a
common systematic source (for example thickness calibration, temperature
calibration, or a common fitting procedure), their errors may be correlated.
In that case, independent Monte Carlo can under- or over-estimate the final
lambda uncertainty. The scripts can be extended to sample a covariance
matrix if correlated errors are known.

### I. Geometry uncertainty in Jc

If Jc was calculated from Ic divided by a cross-sectional area, uncertainty
in film thickness and bridge width should normally be folded into the Jc
uncertainty. For independent errors in Ic, width w, and thickness d, a
first-order estimate is

    (sigma_Jc/Jc)^2
      approximately
    (sigma_Ic/Ic)^2 + (sigma_w/w)^2 + (sigma_d/d)^2.

Use the resulting percentage as `--jc-error-percent`.

---

## 10. Why lambda changes only weakly when xi changes

For Programs 1 and 2,

    Jc proportional to [ln(lambda/xi)+0.5] / lambda^3.

xi enters only through a logarithm, whereas lambda enters primarily as
lambda^-3. Consequently, even a noticeable change in xi often changes
the extracted lambda by a smaller fractional amount. This is also why
the original paper considered the temperature variation of kappa to be
a relatively weak correction.

---

## 11. Dependencies

Python 3.10 or newer is recommended.

Install:

    pip install numpy pandas scipy

The programs produce CSV files and do not require Excel or plotting
libraries.

---

## 12. Recommended workflow for your data

For a data set with measured T, self-field Jc, and Hc2:

1. Use Program 1.
2. Inspect xi(T), lambda(T), and kappa(T).
3. Confirm kappa remains safely in the type-II regime.
4. Compare lambda(T) with Program 3 using a representative constant
   kappa to quantify how important the temperature dependence of kappa is.
5. Repeat with realistic Jc and Hc2 uncertainties.
6. Only after that fit the low-temperature lambda(T) or superfluid
   density lambda^-2(T) to a gap model.

For a data set where xi(T) has already been independently determined,
use Program 2 and skip the Hc2-to-xi conversion.
