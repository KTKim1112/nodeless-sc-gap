"""Check the closed-form sensitivity coefficients derived for research.md R8.

Equation (1):   Jc = A * lambda^-3 * (ln(lambda/xi) + 0.5),   A = PHI0/(4 pi MU0)

Writing L = ln(kappa) + 0.5 and differentiating logarithmically:

    dlnJc = dlnlambda * (-3 + 1/L)  -  dlnxi / L

so

    dlnlambda/dlnJc = -L / (3L - 1)
    dlnlambda/dlnxi = -1 / (3L - 1)

and since xi = sqrt(PHI0 / (2 pi Bc2)) gives dlnxi/dlnHc2 = -1/2,

    dlnlambda/dlnHc2 = +1 / (2*(3L - 1))

The point of this file is to confirm those against brute-force finite
differences on the actual root solve before they are written into the spec.
"""
import numpy as np
from scipy.optimize import brentq

PHI0 = 2.067833848e-15
MU0 = 4.0 * np.pi * 1e-7
A = PHI0 / (4.0 * np.pi * MU0)


def jc_model(lam, xi):
    return A / lam**3 * (np.log(lam / xi) + 0.5)


def solve_lambda(jc, xi):
    lo = xi * (1.0 + 1e-10)
    hi = max(10.0 * xi, 1e-7)
    while jc_model(hi, xi) - jc > 0:
        hi *= 10.0
    return brentq(lambda l: jc_model(l, xi) - jc, lo, hi, xtol=1e-18, rtol=1e-14)


def xi_from_hc2(b):
    return np.sqrt(PHI0 / (2.0 * np.pi * b))


# A representative point: kappa about 40, lambda about 200 nm
lam_true = 200e-9
kappa = 40.0
xi_true = lam_true / kappa
jc_true = jc_model(lam_true, xi_true)
hc2_true = PHI0 / (2.0 * np.pi * xi_true**2)

L = np.log(kappa) + 0.5
print(f"lambda = {lam_true*1e9:.1f} nm, xi = {xi_true*1e9:.3f} nm, kappa = {kappa}")
print(f"Jc = {jc_true:.4e} A/m^2 = {jc_true/1e4:.4e} A/cm^2,  Hc2 = {hc2_true:.3f} T")
print(f"L = ln(kappa) + 0.5 = {L:.6f}")
print()

h = 1e-6  # relative step for the finite difference


def dln(f, x0):
    """d ln(f) / d ln(x) by central difference in log space."""
    fp = f(x0 * (1 + h))
    fm = f(x0 * (1 - h))
    return (np.log(fp) - np.log(fm)) / (np.log(1 + h) - np.log(1 - h))


num_jc = dln(lambda j: solve_lambda(j, xi_true), jc_true)
ana_jc = -L / (3 * L - 1)

num_xi = dln(lambda x: solve_lambda(jc_true, x), xi_true)
ana_xi = -1.0 / (3 * L - 1)

num_hc2 = dln(lambda b: solve_lambda(jc_true, xi_from_hc2(b)), hc2_true)
ana_hc2 = 1.0 / (2 * (3 * L - 1))

print(f"{'coefficient':>28} {'numerical':>14} {'closed form':>14} {'diff':>11}")
for name, n, a in [
    ("dln(lambda)/dln(Jc)", num_jc, ana_jc),
    ("dln(lambda)/dln(xi)", num_xi, ana_xi),
    ("dln(lambda)/dln(Hc2)", num_hc2, ana_hc2),
]:
    print(f"{name:>28} {n:14.9f} {a:14.9f} {abs(n-a):11.2e}")

print()
print("--- fixed-kappa case, where lambda is explicit ---")
# lambda = (A * L / Jc)^(1/3)
num_jc_k = dln(lambda j: (A * L / j) ** (1 / 3), jc_true)
num_kap = dln(lambda k: (A * (np.log(k) + 0.5) / jc_true) ** (1 / 3), kappa)
print(f"{'dln(lambda)/dln(Jc)':>28} {num_jc_k:14.9f} {-1/3:14.9f} {abs(num_jc_k+1/3):11.2e}")
print(f"{'dln(lambda)/dln(kappa)':>28} {num_kap:14.9f} {1/(3*L):14.9f} {abs(num_kap-1/(3*L)):11.2e}")

print()
print("--- worked example: 5% on Jc, 3% on Hc2 ---")
s = np.hypot(ana_jc * 0.05, ana_hc2 * 0.03)
print(f"sigma_lambda/lambda = sqrt(({ana_jc:.4f}*0.05)^2 + ({ana_hc2:.4f}*0.03)^2) = {s*100:.3f} %")
print(f"  the Jc term alone contributes {abs(ana_jc)*0.05*100:.3f} %")
print(f"  the Hc2 term alone contributes {abs(ana_hc2)*0.03*100:.3f} %")

print()
print("--- Monte Carlo cross-check of that number (fixed kappa mode, 200000 draws) ---")
rng = np.random.default_rng(12345)
N = 200_000


def lognorm(mean, cv, n):
    sig = np.sqrt(np.log1p(cv**2))
    return rng.lognormal(np.log(mean) - 0.5 * sig**2, sig, n)


jc_s = lognorm(jc_true, 0.05, N)
hc2_s = lognorm(hc2_true, 0.03, N)
xi_s = xi_from_hc2(hc2_s)
lam_s = np.array([solve_lambda(j, x) for j, x in zip(jc_s[:20000], xi_s[:20000])])
print(f"MC relative std of lambda = {lam_s.std(ddof=1)/lam_s.mean()*100:.3f} %"
      f"   (first-order prediction {s*100:.3f} %)")
print(f"MC mean lambda = {lam_s.mean()*1e9:.4f} nm   (input {lam_true*1e9:.4f} nm)")

print()
print("--- estimator precision: how good is a std estimated from M draws? ---")
for M in [100, 1000, 5000, 20000, 50000]:
    print(f"  M = {M:6d}  ->  relative error of the reported sigma = {100/np.sqrt(2*(M-1)):.2f} %")
