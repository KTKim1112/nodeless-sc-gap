"""Numerically verify the clean-limit reduction derived in research.md R4.

Claim under test:

    rho_s(T) = 1 + 2 * INT[Delta..inf] (df/dE) * E / sqrt(E^2 - Delta^2) dE
             = 1 -     INT[0..inf]    sech^2( sqrt(u^2 + d^2) ) du

with d = Delta / (2 kB T).

The left-hand form is evaluated in physical variables with a substitution that
removes the integrable singularity at E = Delta; the right-hand form is the
dimensionless one we intend to implement. They must agree to high precision.
"""
import numpy as np

KB = 1.380649e-23


def rho_s_physical(delta_J: float, T_K: float) -> float:
    """Original form, in joules and kelvin.

    The integrand has an inverse-square-root singularity at E = Delta.
    Substituting E = Delta * cosh(s) makes dE * E / sqrt(E^2 - Delta^2) = Delta * cosh(s) ds,
    which is smooth, so a plain high-resolution quadrature is trustworthy here.
    This substitution is used ONLY in this check, to keep the two sides
    independent of each other.
    """
    kt = KB * T_K
    s = np.linspace(0.0, 40.0, 4_000_001)
    E = delta_J * np.cosh(s)
    dfdE = -(1.0 / (4.0 * kt)) * (1.0 / np.cosh(E / (2.0 * kt))) ** 2
    integrand = dfdE * delta_J * np.cosh(s)
    return 1.0 + 2.0 * np.trapezoid(integrand, s)


def rho_s_dimensionless(d: float) -> float:
    """The form research.md R4 tells us to implement."""
    if d >= 30.0:
        return 1.0
    u_max = np.sqrt(30.0**2 - d**2)
    u = np.linspace(0.0, u_max, 4_000_001)
    integrand = (1.0 / np.cosh(np.sqrt(u * u + d * d))) ** 2
    return 1.0 - np.trapezoid(integrand, u)


print("--- 1. the two forms agree ---")
print(f"{'T [K]':>8} {'Delta [meV]':>12} {'d':>10} {'physical':>14} {'dimensionless':>15} {'diff':>12}")
for T_K, delta_meV in [(1.0, 1.5), (2.0, 1.5), (5.0, 1.5), (8.0, 1.0), (9.5, 0.4)]:
    delta_J = delta_meV * 1.602176634e-22
    d = delta_J / (2.0 * KB * T_K)
    a = rho_s_physical(delta_J, T_K)
    b = rho_s_dimensionless(d)
    print(f"{T_K:8.2f} {delta_meV:12.3f} {d:10.4f} {a:14.10f} {b:15.10f} {abs(a - b):12.2e}")

print()
print("--- 2. analytic limits ---")
print(f"d = 0     -> rho_s = {rho_s_dimensionless(0.0):.12f}   (must be 0, i.e. T = Tc)")
print(f"d = 30    -> rho_s = {rho_s_dimensionless(30.0):.12f}   (must be 1, i.e. T -> 0)")
print(f"d = 29.99 -> rho_s = {rho_s_dimensionless(29.99):.12f}   (must be 1 to double precision)")

print()
print("--- 3. the d >= 30 short circuit is safe ---")
d = 29.0
u = np.linspace(0.0, np.sqrt(900.0 - d * d), 2_000_001)
tail = np.trapezoid((1.0 / np.cosh(np.sqrt(u * u + d * d))) ** 2, u)
print(f"integral at d = 29 is {tail:.3e}  (bound 4*exp(-2*29) = {4 * np.exp(-58):.3e})")

print()
print("--- 4. monotonic decreasing in T, both models ---")
delta0_J = 1.5 * 1.602176634e-22
Tc = 10.0


def delta_of_T(T):
    if T >= Tc:
        return 0.0
    return delta0_J * np.tanh(1.82 * (1.018 * (Tc / T - 1.0)) ** 0.51)


def rho_dirty(T):
    if T <= 0:
        return 1.0
    dl = delta_of_T(T)
    if dl <= 0:
        return 0.0
    return (dl / delta0_J) * np.tanh(dl / (2.0 * KB * T))


Ts = np.linspace(0.5, 9.9, 20)
clean = [rho_s_dimensionless(delta_of_T(T) / (2 * KB * T)) for T in Ts]
dirty = [rho_dirty(T) for T in Ts]
print(f"clean strictly decreasing: {all(np.diff(clean) < 0)}")
print(f"dirty strictly decreasing: {all(np.diff(dirty) < 0)}")
print(f"clean at T/Tc=0.05: {clean[0]:.6f}   dirty: {dirty[0]:.6f}")
print(f"clean at T/Tc=0.99: {clean[-1]:.6f}   dirty: {dirty[-1]:.6f}")
print("dirty above clean at every T (expected, slower low-T fall-off): "
      f"{all(np.array(dirty) >= np.array(clean))}")

print()
print("--- 5. weak-coupling BCS ratio ---")
alpha = 1.7639
print(f"2 * {alpha} = {2 * alpha:.4f}   (research.md R0 states 3.5279)")
