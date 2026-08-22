# Research — physical model, numerical form, and sources

**Feature:** 001-jc-to-gap
**Purpose:** Fix every equation, every constant, and every numerical safeguard
before any code is written, so that implementation is transcription rather than
invention.

---

## R0. Constants

| Symbol | Value | Unit | Source |
| --- | --- | --- | --- |
| `PHI0` | `2.067833848e-15` | Wb | Flux quantum `h/(2e)`, CODATA |
| `MU0` | `4*pi*1e-7` | H/m | Vacuum permeability |
| `KB` | `1.380649e-23` | J/K | Boltzmann constant, exact by SI definition |
| `MEV_TO_J` | `1.602176634e-22` | J/meV | Elementary charge, exact by SI definition |
| `BCS_RATIO` | `3.52775` | — | `2 Delta(0) / (kB Tc)` at weak coupling |
| `BCS_ALPHA` | `1.763875` | — | `Delta(0) / (kB Tc)` at weak coupling |

`MU0` is kept at the pre-2019 exact value `4*pi*1e-7` rather than the CODATA
measured value `1.25663706212e-6`. They differ by 1.5e-10 relative, far below
any experimental uncertainty here, and using the same value as the `legacy/`
scripts keeps the cross-check in R9 exact rather than approximate.

---

## R1. Self-field critical current density (thin-film, type-II)

Source: E. F. Talantsev and J. L. Tallon, *Universal self-field critical current
for thin-film superconductors*, Nature Communications **6**, 7820 (2015),
DOI 10.1038/ncomms8820, equation (4).

    Jc_sf = Hc1 / lambda
          = PHI0 / (4 * pi * MU0 * lambda^3) * ( ln(kappa) + 0.5 )

with `kappa = lambda / xi`. Expanded:

    Jc(T) = PHI0 / (4*pi*MU0*lambda(T)^3) * ( ln(lambda(T)/xi(T)) + 0.5 )   ... (1)

`lambda` appears both as `lambda^-3` and inside the logarithm, so (1) cannot be
inverted in closed form when `xi` is fixed.

**Domain of validity.** `Jc` must be self-field *transport* critical current
density (not magnetisation-derived, no applied field), measured on a thin film
free of weak links, whose thickness is not large compared with `lambda`.

**Monotonicity.** On the branch `lambda > xi` the right-hand side of (1) is
monotonically decreasing in `lambda`, because `lambda^-3` falls faster than
`ln(lambda/xi)` grows. A bracketed root finder is therefore guaranteed to
converge to the unique solution on that branch.

**Sign condition.** `ln(kappa) + 0.5 > 0` requires `kappa > exp(-0.5) = 0.6065`.
Below that the model gives a negative `Jc` and is meaningless. Note this is
close to, but not the same as, the type-I/type-II boundary `1/sqrt(2) = 0.7071`.

---

## R2. Coherence length from the upper critical field

Standard isotropic Ginzburg-Landau orbital relation:

    Bc2(T) = PHI0 / (2 * pi * xi(T)^2)
    =>  xi(T) = sqrt( PHI0 / (2 * pi * Bc2(T)) )                            ... (2)

Experimental values reported as `Hc2` in tesla are used numerically as
`Bc2 = MU0 * Hc2` in tesla, which is the usual convention in the literature.

**Caveat to surface in diagnostics.** If the experimental `Hc2` is affected by
Pauli limiting, multiband effects, a broad resistive transition, vortex
dynamics, or an arbitrary resistive criterion, then (2) yields an *effective*
Ginzburg-Landau coherence length, not the microscopic pair size. For an
anisotropic superconductor the value depends on field orientation
(`Bc2_c = PHI0/(2 pi xi_ab^2)` versus `Bc2_ab = PHI0/(2 pi xi_ab xi_c)`); only
the isotropic form is implemented, and this is declared, not corrected for.

---

## R3. Temperature dependence of the gap

BCS interpolation formula (the closed form used throughout the Talantsev group's
papers, accurate to better than 1 % against the full Muhlschlegel table):

    Delta(T) = Delta(0) * tanh{ 1.82 * [ 1.018 * (Tc/T - 1) ]^0.51 }    for T < Tc
    Delta(T) = 0                                                         for T >= Tc

Limits: `T -> 0` gives `tanh(inf) = 1`, so `Delta -> Delta(0)`.
`T -> Tc` gives `tanh(0) = 0`, so `Delta -> 0`. Both are correct.

Solving the self-consistent BCS gap equation instead would change results by
well under the experimental uncertainty and is deliberately not implemented
(constitution IX).

**Residual error of the interpolation at low temperature.** The formula
approaches 1 as `T -> 0` but not exponentially fast the way true BCS does. At
`T/Tc = 0.1` it gives `Delta(T)/Delta(0) = 0.999974`, a deficit of `2.6e-5`,
whereas the true BCS deficit at that temperature is smaller by orders of
magnitude. This is harmless for fitting — it is four orders of magnitude below
any experimental uncertainty — but it is large enough to dominate the
*difference* between the two superfluid-density models below `T/Tc ~ 0.25`,
where both are within `1e-3` of unity anyway. See the note in R5.

---

## R4. Normalised superfluid density, clean limit

The local London clean-limit result for an isotropic (nodeless) s-wave gap:

    rho_s(T) = lambda^2(0) / lambda^2(T)
             = 1 + 2 * INTEGRAL[Delta..inf] (df/dE) * E / sqrt(E^2 - Delta^2) dE

where `f(E) = 1/(1 + exp(E/(kB T)))` is the Fermi function and
`df/dE = -(1/(4 kB T)) * sech^2( E / (2 kB T) )`.

### Reduction to a dimensionless integral

Substitute `E = sqrt(eps^2 + Delta^2)`. Then as `E` runs from `Delta` to
infinity, `eps` runs from `0` to infinity, and

    dE * E / sqrt(E^2 - Delta^2) = d(eps)

so

    rho_s(T) = 1 - (1/(2 kB T)) * INTEGRAL[0..inf] sech^2( sqrt(eps^2 + Delta^2) / (2 kB T) ) d(eps)

Now substitute `u = eps / (2 kB T)` and define the single dimensionless parameter

    d = Delta(T) / (2 * kB * T)

The `2 kB T` prefactors cancel exactly and the result becomes

    rho_s(T) = 1 - INTEGRAL[0..inf] sech^2( sqrt(u^2 + d^2) ) du            ... (3)

**This is the form to implement.** It has no units, no large or small numbers,
and depends on exactly one argument `d`, which makes it cheap to cache and easy
to test.

### Verification of the limits

- `d = 0` (i.e. `T = Tc`): the integral is `INTEGRAL[0..inf] sech^2(u) du = [tanh u] = 1`,
  so `rho_s = 0`. Correct.
- `d -> inf` (i.e. `T -> 0`): `sech^2` is bounded by `4 exp(-2 d)`, so the
  integral vanishes and `rho_s -> 1`. Correct.

### Numerical treatment

`sech^2(x) ~ 4 exp(-2x)` for large `x`. Truncating the integrand where
`sqrt(u^2 + d^2) = 30` leaves a remainder below `4 exp(-60) ~ 4e-27`, which is
negligible against double precision. Therefore:

    if d >= 30:  integral = 0  (return rho_s = 1 exactly)
    else:        integrate u from 0 to sqrt(30^2 - d^2)

This removes the infinite upper limit, removes all underflow, and makes the
`T -> 0` limit exact rather than asymptotic. Adaptive quadrature is used on the
finite interval.

`T = 0` exactly is handled as `rho_s = 1` without evaluating `d`.

---

## R5. Normalised superfluid density, dirty limit

Tinkham's dirty-limit (diffusive) result:

    rho_s(T) = ( Delta(T) / Delta(0) ) * tanh( Delta(T) / (2 kB T) )
             = ( Delta(T) / Delta(0) ) * tanh(d)                            ... (4)

reusing the same `d` as in R4.

Limits: `T -> 0` gives `Delta(T)/Delta(0) = 1` and `tanh(inf) = 1`, so
`rho_s -> 1`. `T -> Tc` gives `Delta -> 0`, and since `tanh(d) ~ d` for small
`d`, `rho_s ~ Delta^2 / (2 kB T Delta(0)) -> 0`. Both correct.

For the same gap, the dirty limit lies above the clean limit across the
temperature range where the two differ measurably. With `Delta0 = 1.5 meV` and
`Tc = 10 K` the separation peaks at `rho_dirty - rho_clean = 0.097` near
`T/Tc = 0.7`, and exceeds `0.03` over the whole range `0.4 < T/Tc < 0.95`.
That separation is what makes the two distinguishable in a fit and is the basis
of the comparison required by FR-020.

**Do not read anything into the ordering below `T/Tc ~ 0.25`.** There the two
curves cross, with the dirty limit falling `2e-4` or less *below* the clean one.
That crossing is not physics: it is the residual error of the `Delta(T)`
interpolation of R3, which enters the dirty expression as a direct prefactor but
enters the clean expression only through an exponentially small integral. Both
models are within `1e-3` of unity there, so nothing observable depends on it,
but a test asserting `rho_dirty >= rho_clean` at all temperatures would fail for
this reason and must not be written.

---

## R6. Fitting

Free parameters in both routes: `lambda0` [m], `Delta0` [J], `Tc` [K].
`Tc` may be held fixed (FR-013). The model function is selected by
`GapModel in {CLEAN, DIRTY}` and enters through R4 or R5.

Modelled penetration depth:

    lambda_model(T) = lambda0 / sqrt( rho_s(T; Delta0, Tc) )                ... (5)

### Route A — two-step

Input: `lambda_data(T_i)` obtained by solving (1) at each temperature.
Residual, dimensionless and naturally weighted towards low temperature where the
superfluid density is largest:

    r_i = lambda0^2 / lambda_data(T_i)^2  -  rho_s(T_i; Delta0, Tc)

### Route B — direct global fit

Input: the measured `Jc(T_i)` themselves, plus whichever of `Hc2(T_i)`,
`xi(T_i)`, or fixed `kappa` establishes the coherence length.

For a trial `(lambda0, Delta0, Tc)`: compute `lambda_model(T_i)` from (5), then
`kappa_i = lambda_model(T_i) / xi(T_i)` (or the fixed `kappa`), then
`Jc_model(T_i)` from (1). Residual:

    r_i = ln( Jc_data(T_i) )  -  ln( Jc_model(T_i) )

The logarithm is used because `Jc` spans orders of magnitude across the
temperature range; a linear residual would let the lowest-temperature point
dominate the fit entirely.

Route B never inverts (1), so it cannot fail with "no admissible root", and it
does not accumulate the error of the intermediate inversion. Route A is faster
and lets the user inspect `lambda(T)` directly. Both are offered (FR-011).

### Initial guesses and bounds

| Parameter | Initial guess | Bounds |
| --- | --- | --- |
| `Tc` | `1.05 * max(T_data)`, or the user's fixed value | `(max(T_data)*1.001, max(T_data)*3)` |
| `Delta0` | `BCS_ALPHA * KB * Tc_guess` | `(0.2, 6.0) * KB * Tc_guess` |
| `lambda0` | route A: `lambda_data` at the lowest `T`; route B: solve (1) once at the lowest `T` | `(1e-9, 1e-4)` m |

### Parameter uncertainty

Least squares is solved by trust-region reflective minimisation. From the
returned Jacobian `J` at the solution, with `m` data points and `n` free
parameters:

    s^2   = 2 * cost / (m - n)          [cost is 0.5 * sum(r^2)]
    covar = s^2 * inv(J^T J)
    sigma_k = sqrt( covar[k,k] )

If `J^T J` is singular the standard errors are reported as unavailable rather
than as zero. This is the ordinary fit uncertainty; it does *not* include the
experimental uncertainty of the input, which is what R8 is for.

### Derived quantity

    coupling_ratio = 2 * Delta0 / (KB * Tc)

with uncertainty by first-order propagation from `sigma_Delta0` and `sigma_Tc`.

---

## R7. Fixed-kappa special case

When `kappa` is fixed, (1) becomes explicit and no root finding is needed:

    lambda(T) = [ PHI0 / (4*pi*MU0*Jc(T)) * ( ln(kappa) + 0.5 ) ]^(1/3)     ... (6)
    xi(T)     = lambda(T) / kappa

This is the closest of the three coherence-length modes to the simplification
used in the original 2015 paper, where `kappa` enters only inside a logarithm
and its temperature dependence is a weak correction.

---

## R8. Experimental uncertainty propagation

There are two different uncertainties on a fitted parameter and the tool must
not confuse them.

| | What it measures | Where it comes from |
| --- | --- | --- |
| **Fit uncertainty** | how tightly the data pin the parameter, given the model | the Jacobian at the solution, R6 |
| **Propagated input uncertainty** | how much the parameter moves if the measured `Jc`, `Hc2`, `xi`, or `kappa` were off by the amount the user says they might be | this section |

They answer different questions and are reported separately. Section R8.6
explains why they are not added together.

### R8.1 Why Monte Carlo and not a derivative

The usual first-order propagation formula

    sigma_y^2 = SUM_k ( dy/dx_k )^2 * sigma_{x_k}^2

needs the partial derivative of the output with respect to each input. Here the
output `Delta(0)` is produced by an iterative least-squares fit whose input is
itself produced by a numerical root solve of equation (1). No closed-form
derivative exists, and a finite-difference derivative would have to re-run the
whole fit anyway.

Monte Carlo needs no derivative and no linearisation: it re-runs the actual
computation on perturbed inputs and looks at the spread of the answers. It also
stays valid when the propagation is strongly non-linear or the output
distribution is skewed, which the first-order formula does not.

The cost is that the answer is itself a statistical estimate. R8.5 quantifies
that.

### R8.2 Log-normal sampling

A measured positive quantity `X` is drawn from a log-normal distribution: `ln X`
is Gaussian. Given a target mean `m` and target relative standard deviation
`cv = sigma_X / m`, the parameters follow from the log-normal moments

    E[X]   = exp( mu + sigma^2 / 2 )
    Var[X] = ( exp(sigma^2) - 1 ) * exp( 2 mu + sigma^2 )

Dividing the second by the square of the first gives `cv^2 = exp(sigma^2) - 1`,
hence

    sigma = sqrt( ln( 1 + cv^2 ) )                                          ... (7)
    mu    = ln(m) - sigma^2 / 2                                             ... (8)

which reproduce the requested mean and relative standard deviation exactly.

Two reasons for log-normal rather than Gaussian.

*Positivity.* A Gaussian `N(m, (cv*m)^2)` places probability `Phi(-1/cv)` below
zero: 0.04 % at `cv = 0.3`, 2.3 % at `cv = 0.5`. A negative `Jc` or `Hc2` is not
merely unphysical, it makes the root solve fail, so those draws would be
discarded and the surviving sample would be biased.

*Shape.* `Jc = Ic / (w * t)` is a product and ratio of measured quantities. The
product of independent positive quantities tends to a log-normal by the
multiplicative central limit theorem, so this is the natural family here, not a
convenience.

For small `cv` the two coincide: expanding (7) gives `sigma = cv - cv^3/4 + ...`,
so at `cv = 0.05` they differ by 0.03 %.

Note that the log-normal median is `exp(mu) = m / sqrt(1 + cv^2)`, slightly below
the mean. This is a property of the distribution, not an error.

### R8.3 What is correlated with what

This choice changes the answer more than any other in this section.

A stated relative uncertainty on `Jc` can mean two physically different things.

**Independent mode.** Each temperature point is perturbed by its own draw:

    Jc_i^(k) = Jc_i * L_i^(k),      L_i^(k) i.i.d. log-normal, mean 1

This represents point-to-point measurement scatter. Fitting `n` points averages
it down, so the resulting parameter uncertainty falls roughly as `1/sqrt(n)`.

**Systematic mode.** One draw is shared by every temperature point:

    Jc_i^(k) = Jc_i * L^(k),        one L^(k) per Monte Carlo draw

This represents a calibration error common to the whole dataset — a bridge width,
a film thickness, a contact geometry, a current shunt. It does not average down
with more points, because every point is wrong in the same direction.

The distinction has a sharp consequence that is worth stating in full, because
it is not obvious and it is testable.

**A common multiplicative error in `Jc` moves `lambda(0)` but leaves `Delta(0)`
and `Tc` untouched.** In fixed-`kappa` mode this is exact. From (6),
`lambda(T) = C * Jc(T)^(-1/3)`, so scaling every `Jc` by `f` scales every
`lambda(T)` by `f^(-1/3)`. The fitted `lambda0` scales by the same factor, and
the normalised superfluid density

    rho_s(T) = lambda0^2 / lambda(T)^2

is a ratio of two quantities that were scaled identically, so it is unchanged.
`Delta0` and `Tc` are determined only by the shape of `rho_s(T)`, so they do not
move at all.

In `FROM_HC2` mode it is very nearly exact rather than exact, because the
scaling coefficient `-L/(3L-1)` of R8.4 depends weakly on `kappa` and therefore
on temperature. At `kappa = 40` the coefficient is `-0.36215`; at `kappa = 20`
it is `-0.36847`. A 5 % common error in `Jc` therefore distorts the *shape* of
`rho_s(T)` by about 0.03 %, which is negligible beside the roughly 2 % it moves
`lambda0`.

Both modes are therefore implemented, selected by
`UncertaintySettings.correlation_mode`, and the mode is reported with the
result. Reporting a `Delta(0)` uncertainty of a few per cent that in fact came
from a geometry calibration error would be simply wrong, and this is the
mechanism by which the tool avoids it.

Correlations *between different quantities* — say a common temperature
calibration affecting `Jc` and `Hc2` together — are still not modelled. That
limitation is declared with every uncertainty result as
`CROSS_QUANTITY_CORRELATION_IGNORED`, which also carries the correlation mode
that was used.

### R8.4 Closed-form sensitivities, for sanity and for tests

Differentiating equation (1) logarithmically, with `L = ln(kappa) + 0.5` held at
its value at the solution:

    d ln Jc = d ln lambda * ( -3 + 1/L )  -  d ln xi / L

so

    d ln lambda / d ln Jc  = -L / (3L - 1)                                  ... (9)
    d ln lambda / d ln xi  = -1 / (3L - 1)                                  ... (10)

and since `xi = sqrt( PHI0 / (2 pi Bc2) )` gives `d ln xi / d ln Hc2 = -1/2`,

    d ln lambda / d ln Hc2 = +1 / ( 2 (3L - 1) )                            ... (11)

In fixed-`kappa` mode equation (6) is explicit and gives directly

    d ln lambda / d ln Jc    = -1/3                                         ... (12)
    d ln lambda / d ln kappa = 1 / (3L)                                     ... (13)

All five were checked against finite differences on the actual root solve and
agree to 1e-10 (see `verify_sensitivity.py`).

First-order combination then predicts, for independent inputs,

    ( sigma_lambda / lambda )^2 =
        (9)^2  * ( sigma_Jc  / Jc  )^2
      + (11)^2 * ( sigma_Hc2 / Hc2 )^2

**Worked example.** `kappa = 40`, so `L = 4.1889` and `3L - 1 = 11.567`.
Coefficients: `(9) = -0.36215`, `(11) = +0.043228`. With a 5 % uncertainty on
`Jc` and 3 % on `Hc2`:

    sigma_lambda/lambda = sqrt( (0.36215 * 0.05)^2 + (0.043228 * 0.03)^2 )
                        = sqrt( 0.018108^2 + 0.001297^2 )
                        = 1.815 %

A direct Monte Carlo of the same case gives 1.817 %. The two agree because the
propagation is nearly linear at this level of uncertainty; the Monte Carlo earns
its cost at larger uncertainties and for the fitted parameters, where it is not.

Note what the worked example shows: the `Hc2` term contributes 0.130 % against
the `Jc` term's 1.811 %. The upper critical field is almost irrelevant to the
extracted penetration depth, for the reason given in R11. This gives a concrete
test the implementation must reproduce (R9).

### R8.5 Statistics of the output, and how many draws

For each draw `k = 1..N` the whole chain is re-run, giving parameter vectors
`theta^(k) = (lambda0, Delta0, Tc)^(k)`. Draws that fail physically — no
admissible root, a fit that does not converge — are discarded, leaving `M`
survivors. Over the survivors:

    mean    = (1/M) SUM_k theta^(k)
    std     = sqrt( (1/(M-1)) SUM_k ( theta^(k) - mean )^2 )
    ci_low  = percentile( theta, alpha/2 )
    ci_high = percentile( theta, 100 - alpha/2 )        with alpha = 100 - confidence

The interval is taken from percentiles rather than as `mean +/- z * std`, because
`lambda ~ Jc^(-1/3)` is non-linear and the resulting distribution is skewed; a
symmetric interval would misplace both ends.

**Discarding is dangerous and is bounded.** Failed draws are not missing at
random — they are systematically the ones with extreme inputs. If more than half
are lost, the surviving sample is biased and the result would be misleadingly
narrow, so the computation is reported as failed via `MC_TOO_MANY_FAILURES`
rather than reported at all. Any discarding at all is reported through
`MC_SAMPLES_DISCARDED` with the counts.

**How many draws.** The reported `std` is itself an estimate. For a roughly
Gaussian output its own relative standard error is

    sigma( std ) / std = 1 / sqrt( 2 (M - 1) )                              ... (14)

| `M` | relative error of the reported uncertainty |
| --- | --- |
| 100 | 7.1 % |
| 1000 | 2.2 % |
| 5000 | 1.0 % |
| 20000 | 0.50 % |
| 50000 | 0.32 % |

Hence the default of 5000: it puts the uncertainty on the uncertainty at 1 %,
well below the accuracy to which anyone states an experimental error bar.
Percentile estimates of the interval edges converge more slowly than the
standard deviation, which is the argument for 10000 to 50000 draws when a number
is going into a paper.

Increasing `N` does not make the reported uncertainty smaller. It makes it
steadier. If a larger `N` changes the answer materially, the cause is usually a
non-linearity or a discarding problem, not sampling noise.

### R8.6 Why the two uncertainties are reported separately

It is tempting to combine them as

    sigma_total^2 = sigma_fit^2 + sigma_MC^2

That is only valid when the two are independent, which depends on the
correlation mode of R8.3.

- In **independent** mode they overlap: point-to-point scatter in `Jc` is
  already part of what the fit residuals see, so the same randomness is being
  counted twice and the sum overestimates.
- In **systematic** mode they are genuinely independent — a common calibration
  offset produces no residual scatter at all — and adding in quadrature is
  legitimate.

Rather than making that judgement on the user's behalf, both numbers are
reported with their meaning attached. Combining them, when it is appropriate, is
a decision that belongs to the person writing the paper.

### R8.7 Turning experimental reality into a number for `Jc`

The user has to supply `sigma_Jc / Jc`, which is usually not measured directly.
If `Jc = Ic / (w * t)` with independent errors in the critical current, the
bridge width, and the film thickness, then to first order

    ( sigma_Jc / Jc )^2 = ( sigma_Ic / Ic )^2
                        + ( sigma_w  / w  )^2
                        + ( sigma_t  / t  )^2                               ... (15)

Note which mode each term belongs to under R8.3. Width and thickness are fixed
properties of one sample: an error in either is the *same* at every temperature,
which is systematic mode. Scatter in `Ic` from the voltage criterion or from
noise is redrawn at every temperature, which is independent mode. Where both
matter, run the computation twice and see which dominates.

---

## R9. Verification strategy

| Check | Expected |
| --- | --- |
| `rho_s` at `T = 0` | exactly 1, clean and dirty |
| `rho_s` at `T = Tc` | 0, clean and dirty |
| `rho_s` monotonic decreasing in `T` | true on `(0, Tc)`, both models |
| Clean-limit integral at `d = 0` | `INTEGRAL sech^2(u) du = 1` |
| `Delta0 = BCS_ALPHA * KB * Tc` | `coupling_ratio = 3.52775` |
| Round trip, route A and route B | recover `lambda0 = 200 nm`, `Delta0 = 1.5 meV`, `Tc = 10 K`, `kappa = 40` from synthetic data to within 1 % |
| Solving (1) then substituting back | reproduces the input `Jc` to 1e-9 relative |
| Fixed-kappa explicit form (6) versus the root finder | agree to 1e-9 relative |
| `lambda(T)` versus the three `legacy/` scripts | agree to 1e-9 relative on identical input |

The round-trip test is the one that would catch a wrong factor, a wrong sign, or
a wrong unit anywhere in the chain, and is therefore treated as the primary
correctness gate (constitution II).

### Pre-implementation check of the R4 reduction

The dimensionless reduction (3) was verified numerically before any application
code was written, by evaluating the original physical form independently. The
singularity at `E = Delta` was removed with a different substitution
(`E = Delta cosh(s)`, giving `dE * E / sqrt(E^2 - Delta^2) = Delta cosh(s) ds`)
so that the two evaluations share no algebra.

| `T` [K] | `Delta` [meV] | `d` | physical form | equation (3) | difference |
| --- | --- | --- | --- | --- | --- |
| 1.0 | 1.5 | 8.7034 | 0.9999997056 | 0.9999997056 | 0 |
| 2.0 | 1.5 | 4.3517 | 0.9987214064 | 0.9987214064 | 0 |
| 5.0 | 1.5 | 1.7407 | 0.8480943892 | 0.8480943892 | 0 |
| 8.0 | 1.0 | 0.7253 | 0.3405737282 | 0.3405737282 | 1.1e-16 |
| 9.5 | 0.4 | 0.2443 | 0.0491733688 | 0.0491733688 | 2.2e-16 |

Agreement is at machine precision, so (3) may be implemented directly. The
truncation of R4 was checked at the same time: the integral at `d = 29` is
`1.2e-24`, confirming that the `d >= 30` short circuit discards nothing
representable in double precision.

---

## R10. Diagnostic thresholds

These are the judgements the system is required to make in FR-019 to FR-024.
Values are stated here so they are reviewable rather than buried in code.

**Ginzburg-Landau parameter.**

| Condition | Report |
| --- | --- |
| `kappa <= 0.6065` (`exp(-0.5)`) | error: the model is undefined |
| `kappa <= 0.7071` (`1/sqrt(2)`) | error: not a type-II superconductor |
| `0.7071 < kappa < 5` | warning: near the type-II boundary; the large-kappa form of `Hc1` used in (1) is a poor approximation here |
| `kappa >= 5` | no warning |

**Low-temperature coverage.** With `t_min = min(T_data) / Tc`:

| Condition | Report |
| --- | --- |
| `t_min <= 0.3` | no warning |
| `0.3 < t_min <= 0.5` | warning: `Delta(0)` is weakly constrained |
| `t_min > 0.5` | warning, stronger: `Delta(0)` is essentially an extrapolation |

**Clean versus dirty.** Fit both, compare reduced chi-squared. If the better
model's value is more than 20 % below the other's, declare it the better
description; otherwise report that the data do not distinguish them.

**Coupling regime.** From `R = 2 Delta0 / (kB Tc)`:

| Range | Characterisation |
| --- | --- |
| `R < 3.3` | below weak-coupling BCS; check the data and the assumed `Tc` |
| `3.3 <= R < 3.8` | consistent with weak-coupling BCS |
| `3.8 <= R < 5.0` | moderately strong coupling |
| `R >= 5.0` | strong coupling |

**Thin-film regime.** If the user supplies a film thickness `t`, warn when
`t > 2 * lambda0`, since the relation in R1 was derived for a conductor whose
transverse dimension is not large compared with `lambda`.

**Always stated, never conditional.** That `Jc` must be self-field transport
data from a weak-link-free film. Weak links, cracks, poor connectivity, or a
non-intrinsic voltage criterion all reduce `Jc` and therefore inflate the
apparent `lambda`.

---

## R11. Why `lambda` is insensitive to errors in `xi`

From (1), `Jc ~ [ln(lambda/xi) + 0.5] / lambda^3`. The coherence length enters
only through a logarithm while `lambda` enters as a cube. A 10 % error in `xi`
therefore moves the extracted `lambda` by well under 1 % for typical
`kappa ~ 40`. This is why the original paper could treat `kappa` as
temperature-independent, and it is a useful sanity check: if the extracted
`lambda` is seen to be strongly sensitive to `xi`, something else is wrong.
