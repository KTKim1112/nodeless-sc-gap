#!/usr/bin/env python3
"""
lambda_from_T_Jc_Hc2.py

Input columns (in this order):
    Temperature [K], Jc [A/cm^2 or A/m^2], Hc2 [T]

Method
------
1) Convert Hc2 to coherence length:
       xi(T) = sqrt(PHI0 / (2*pi*Hc2(T)))
   Here Hc2 in tesla is interpreted as B_c2 = mu0*H_c2, as is usual when
   experimental upper critical field values are reported in T.

2) Solve the Talantsev-Tallon type-II thin-film self-field equation:
       Jc = PHI0/(4*pi*MU0*lambda^3) * [ln(lambda/xi) + 0.5]

   lambda occurs both algebraically and inside the logarithm, so the program
   solves the equation numerically at every temperature.

Optional uncertainty propagation
--------------------------------
Relative input uncertainties are interpreted as independent 1-sigma
uncertainties and propagated by Monte Carlo using positive log-normal
sampling. Set error percentages to zero to disable Monte Carlo.

Example
-------
python lambda_from_T_Jc_Hc2.py data.txt \
    --jc-unit A/cm2 \
    --jc-error-percent 5 \
    --hc2-error-percent 3 \
    --mc-samples 5000 \
    --confidence 68.27 \
    --output result.csv
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq

PHI0 = 2.067833848e-15  # Wb
MU0 = 4.0 * np.pi * 1e-7  # H/m


def _first_data_tokens(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            return [x for x in __import__("re").split(r"[\s,;]+", line) if x]
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
    df = pd.read_csv(
        path, sep=r"[\s,;]+", engine="python", comment="#",
        header=header
    )
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
    raise ValueError("Unsupported Jc unit. Use A/cm2 or A/m2.")


def xi_from_hc2(hc2_t):
    hc2_t = np.asarray(hc2_t, dtype=float)
    if np.any(hc2_t <= 0):
        raise ValueError("All Hc2 values must be > 0.")
    return np.sqrt(PHI0 / (2.0 * np.pi * hc2_t))


def jc_model(lam, xi):
    return PHI0 / (4.0 * np.pi * MU0 * lam**3) * (np.log(lam / xi) + 0.5)


def solve_lambda(jc_si, xi, root_xtol=1e-15, root_rtol=1e-12):
    """
    Solve Eq. (4) on the strong type-II branch lambda > xi.
    On this branch the model Jc(lambda) is monotonic decreasing.
    """
    if jc_si <= 0 or xi <= 0:
        raise ValueError("Jc and xi must both be > 0.")

    lo = xi * (1.0 + 1e-10)
    flo = jc_model(lo, xi) - jc_si
    if flo < 0:
        raise ValueError(
            "No solution found on the lambda > xi branch. "
            "The supplied Jc is too large for this xi under Eq. (4), "
            "or the strong type-II assumption is not appropriate."
        )

    hi = max(10.0 * xi, 1e-7)
    fhi = jc_model(hi, xi) - jc_si
    n_expand = 0
    while fhi > 0 and n_expand < 30:
        hi *= 10.0
        fhi = jc_model(hi, xi) - jc_si
        n_expand += 1

    if fhi > 0:
        raise RuntimeError("Could not bracket lambda root after expanding upper bound.")

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
    return rng.lognormal(mean=mu_ln, sigma=sigma_ln, size=n)


def mc_lambda(jc_si, hc2_t, jc_err_pct, hc2_err_pct, n, confidence,
              root_xtol, root_rtol, rng):
    jc_s = lognormal_samples(jc_si, jc_err_pct, n, rng)
    h_s = lognormal_samples(hc2_t, hc2_err_pct, n, rng)
    xi_s = xi_from_hc2(h_s)

    lam_s = []
    kap_s = []
    xi_valid = []
    for j, x in zip(jc_s, xi_s):
        try:
            l = solve_lambda(j, x, root_xtol, root_rtol)
            lam_s.append(l)
            kap_s.append(l / x)
            xi_valid.append(x)
        except Exception:
            pass

    lam_s = np.asarray(lam_s)
    kap_s = np.asarray(kap_s)
    xi_valid = np.asarray(xi_valid)
    if len(lam_s) < max(100, int(0.5 * n)):
        raise RuntimeError(
            f"Too many Monte Carlo samples failed ({len(lam_s)}/{n} valid). "
            "Check uncertainties and physical consistency."
        )

    alpha = (100.0 - confidence) / 2.0
    return {
        "mc_valid_samples": len(lam_s),
        "xi_mc_mean_m": np.mean(xi_valid),
        "xi_mc_std_m": np.std(xi_valid, ddof=1),
        "lambda_mc_mean_m": np.mean(lam_s),
        "lambda_mc_std_m": np.std(lam_s, ddof=1),
        "lambda_ci_low_m": np.percentile(lam_s, alpha),
        "lambda_ci_high_m": np.percentile(lam_s, 100.0 - alpha),
        "kappa_mc_mean": np.mean(kap_s),
        "kappa_mc_std": np.std(kap_s, ddof=1),
    }


def main():
    p = argparse.ArgumentParser(
        description="Extract xi(T) from Hc2(T), then lambda(T) from self-field Jc(T)."
    )
    p.add_argument("input", help="Input text/CSV file: T, Jc, Hc2")
    p.add_argument("--jc-unit", default="A/cm2", choices=["A/cm2", "A/m2"])
    p.add_argument("--output", default="lambda_from_T_Jc_Hc2.csv")
    p.add_argument("--jc-error-percent", type=float, default=0.0,
                   help="Relative 1-sigma uncertainty of Jc in percent.")
    p.add_argument("--hc2-error-percent", type=float, default=0.0,
                   help="Relative 1-sigma uncertainty of Hc2 in percent.")
    p.add_argument("--mc-samples", type=int, default=5000)
    p.add_argument("--confidence", type=float, default=68.27,
                   help="Central Monte Carlo confidence interval in percent.")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--root-xtol", type=float, default=1e-15,
                   help="Absolute root tolerance for lambda, in meters.")
    p.add_argument("--root-rtol", type=float, default=1e-12,
                   help="Relative root tolerance.")
    args = p.parse_args()

    if not (0 < args.confidence < 100):
        raise ValueError("--confidence must be between 0 and 100.")
    if args.mc_samples < 100:
        raise ValueError("--mc-samples should be at least 100.")

    raw = read_numeric_table(args.input, 3)
    T = raw.iloc[:, 0].to_numpy(float)
    jc_input = raw.iloc[:, 1].to_numpy(float)
    hc2 = raw.iloc[:, 2].to_numpy(float)
    jc_si = convert_jc_to_si(jc_input, args.jc_unit)
    xi = xi_from_hc2(hc2)

    lam = np.array([
        solve_lambda(j, x, args.root_xtol, args.root_rtol)
        for j, x in zip(jc_si, xi)
    ])
    kappa = lam / xi

    out = pd.DataFrame({
        "T_K": T,
        "Jc_input": jc_input,
        "Jc_A_per_m2": jc_si,
        "Hc2_T": hc2,
        "xi_m": xi,
        "xi_nm": xi * 1e9,
        "lambda_m": lam,
        "lambda_nm": lam * 1e9,
        "kappa_lambda_over_xi": kappa,
    })

    if args.jc_error_percent > 0 or args.hc2_error_percent > 0:
        rng = np.random.default_rng(args.seed)
        mc_rows = [
            mc_lambda(j, h, args.jc_error_percent, args.hc2_error_percent,
                      args.mc_samples, args.confidence,
                      args.root_xtol, args.root_rtol, rng)
            for j, h in zip(jc_si, hc2)
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
        out["assumed_Hc2_1sigma_percent"] = args.hc2_error_percent
        out["confidence_interval_percent"] = args.confidence

    out.to_csv(args.output, index=False)
    print(out.to_string(index=False))
    print(f"\nSaved: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
