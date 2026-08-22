#!/usr/bin/env python3
"""
lambda_from_T_Jc_xi.py

Input columns (in this order):
    Temperature [K], Jc [A/m^2 or A/cm^2], xi [m, nm, or um]

The program directly solves:
    Jc = PHI0/(4*pi*MU0*lambda^3) * [ln(lambda/xi) + 0.5]

at each temperature.

Optional uncertainties in Jc and xi are interpreted as independent relative
1-sigma errors and propagated with Monte Carlo.

Example
-------
python lambda_from_T_Jc_xi.py data.txt \
    --jc-unit A/m2 --xi-unit m \
    --jc-error-percent 5 --xi-error-percent 4 \
    --mc-samples 5000 --output result.csv
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq

PHI0 = 2.067833848e-15  # Wb
MU0 = 4.0 * np.pi * 1e-7  # H/m


def _first_data_tokens(path):
    import re
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            return [x for x in re.split(r"[\s,;]+", line) if x]
    raise ValueError("Input file contains no data.")


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def read_numeric_table(path, ncols):
    tokens = _first_data_tokens(path)
    header = None if all(_is_number(x) for x in tokens[:ncols]) else 0
    df = pd.read_csv(path, sep=r"[\s,;]+", engine="python", comment="#", header=header)
    if df.shape[1] < ncols:
        raise ValueError(f"Expected at least {ncols} columns, found {df.shape[1]}.")
    df = df.iloc[:, :ncols].copy()
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="raise")
    return df


def convert_jc_to_si(jc, unit):
    unit = unit.lower().replace("^", "")
    if unit in {"a/cm2", "a/cm²"}:
        return np.asarray(jc, dtype=float) * 1e4
    if unit in {"a/m2", "a/m²"}:
        return np.asarray(jc, dtype=float)
    raise ValueError("Unsupported Jc unit.")


def convert_xi_to_m(xi, unit):
    u = unit.lower().replace("µ", "u")
    factors = {"m": 1.0, "nm": 1e-9, "um": 1e-6}
    if u not in factors:
        raise ValueError("Unsupported xi unit. Use m, nm, or um.")
    return np.asarray(xi, dtype=float) * factors[u]


def jc_model(lam, xi):
    return PHI0 / (4.0 * np.pi * MU0 * lam**3) * (np.log(lam / xi) + 0.5)


def solve_lambda(jc_si, xi, root_xtol=1e-15, root_rtol=1e-12):
    if jc_si <= 0 or xi <= 0:
        raise ValueError("Jc and xi must both be > 0.")

    lo = xi * (1.0 + 1e-10)
    flo = jc_model(lo, xi) - jc_si
    if flo < 0:
        raise ValueError(
            "No solution on lambda > xi branch. Check Jc, xi, units, "
            "or the applicability of Eq. (4)."
        )

    hi = max(10.0 * xi, 1e-7)
    fhi = jc_model(hi, xi) - jc_si
    n_expand = 0
    while fhi > 0 and n_expand < 30:
        hi *= 10.0
        fhi = jc_model(hi, xi) - jc_si
        n_expand += 1
    if fhi > 0:
        raise RuntimeError("Could not bracket lambda root.")

    return brentq(
        lambda lam: jc_model(lam, xi) - jc_si,
        lo, hi, xtol=root_xtol, rtol=root_rtol, maxiter=300
    )


def lognormal_samples(mean, rel_sigma_percent, n, rng):
    if rel_sigma_percent <= 0:
        return np.full(n, mean, dtype=float)
    cv = rel_sigma_percent / 100.0
    sigma_ln = np.sqrt(np.log1p(cv**2))
    mu_ln = np.log(mean) - 0.5 * sigma_ln**2
    return rng.lognormal(mu_ln, sigma_ln, size=n)


def mc_lambda(jc_si, xi, jc_err_pct, xi_err_pct, n, confidence,
              root_xtol, root_rtol, rng):
    jc_s = lognormal_samples(jc_si, jc_err_pct, n, rng)
    xi_s = lognormal_samples(xi, xi_err_pct, n, rng)

    lam_s = []
    kap_s = []
    for j, x in zip(jc_s, xi_s):
        try:
            l = solve_lambda(j, x, root_xtol, root_rtol)
            lam_s.append(l)
            kap_s.append(l / x)
        except Exception:
            pass

    lam_s = np.asarray(lam_s)
    kap_s = np.asarray(kap_s)
    if len(lam_s) < max(100, int(0.5 * n)):
        raise RuntimeError(
            f"Too many Monte Carlo samples failed ({len(lam_s)}/{n} valid)."
        )

    alpha = (100.0 - confidence) / 2.0
    return {
        "mc_valid_samples": len(lam_s),
        "lambda_mc_mean_m": np.mean(lam_s),
        "lambda_mc_std_m": np.std(lam_s, ddof=1),
        "lambda_ci_low_m": np.percentile(lam_s, alpha),
        "lambda_ci_high_m": np.percentile(lam_s, 100.0 - alpha),
        "kappa_mc_mean": np.mean(kap_s),
        "kappa_mc_std": np.std(kap_s, ddof=1),
    }


def main():
    p = argparse.ArgumentParser(
        description="Extract lambda(T) from T, Jc(T), and xi(T) using Eq. (4)."
    )
    p.add_argument("input", help="Input text/CSV file: T, Jc, xi")
    p.add_argument("--jc-unit", default="A/m2", choices=["A/cm2", "A/m2"])
    p.add_argument("--xi-unit", default="m", choices=["m", "nm", "um"])
    p.add_argument("--output", default="lambda_from_T_Jc_xi.csv")
    p.add_argument("--jc-error-percent", type=float, default=0.0)
    p.add_argument("--xi-error-percent", type=float, default=0.0)
    p.add_argument("--mc-samples", type=int, default=5000)
    p.add_argument("--confidence", type=float, default=68.27)
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--root-xtol", type=float, default=1e-15,
                   help="Absolute root tolerance for lambda, in meters.")
    p.add_argument("--root-rtol", type=float, default=1e-12)
    args = p.parse_args()

    if not (0 < args.confidence < 100):
        raise ValueError("--confidence must be between 0 and 100.")

    raw = read_numeric_table(args.input, 3)
    T = raw.iloc[:, 0].to_numpy(float)
    jc_input = raw.iloc[:, 1].to_numpy(float)
    xi_input = raw.iloc[:, 2].to_numpy(float)

    jc_si = convert_jc_to_si(jc_input, args.jc_unit)
    xi = convert_xi_to_m(xi_input, args.xi_unit)

    lam = np.array([
        solve_lambda(j, x, args.root_xtol, args.root_rtol)
        for j, x in zip(jc_si, xi)
    ])
    kappa = lam / xi

    out = pd.DataFrame({
        "T_K": T,
        "Jc_input": jc_input,
        "Jc_A_per_m2": jc_si,
        "xi_input": xi_input,
        "xi_m": xi,
        "xi_nm": xi * 1e9,
        "lambda_m": lam,
        "lambda_nm": lam * 1e9,
        "kappa_lambda_over_xi": kappa,
    })

    if args.jc_error_percent > 0 or args.xi_error_percent > 0:
        rng = np.random.default_rng(args.seed)
        mc_rows = [
            mc_lambda(j, x, args.jc_error_percent, args.xi_error_percent,
                      args.mc_samples, args.confidence,
                      args.root_xtol, args.root_rtol, rng)
            for j, x in zip(jc_si, xi)
        ]
        mc = pd.DataFrame(mc_rows)
        for col in mc.columns:
            out[col] = mc[col].to_numpy()
        out["lambda_mc_mean_nm"] = out["lambda_mc_mean_m"] * 1e9
        out["lambda_mc_std_nm"] = out["lambda_mc_std_m"] * 1e9
        out["lambda_ci_low_nm"] = out["lambda_ci_low_m"] * 1e9
        out["lambda_ci_high_nm"] = out["lambda_ci_high_m"] * 1e9
        out["lambda_rel_std_percent"] = (
            100.0 * out["lambda_mc_std_m"] / out["lambda_mc_mean_m"]
        )
        out["assumed_Jc_1sigma_percent"] = args.jc_error_percent
        out["assumed_xi_1sigma_percent"] = args.xi_error_percent
        out["confidence_interval_percent"] = args.confidence

    out.to_csv(args.output, index=False)
    print(out.to_string(index=False))
    print(f"\nSaved: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
