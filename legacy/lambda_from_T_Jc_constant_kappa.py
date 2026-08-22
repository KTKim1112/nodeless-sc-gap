#!/usr/bin/env python3
"""
lambda_from_T_Jc_constant_kappa.py

Input columns (in this order):
    Temperature [K], Jc [A/cm^2 or A/m^2]

Assumption:
    kappa = lambda/xi is a user-specified constant at every temperature.

Then Talantsev-Tallon Eq. (4) becomes explicit:
    lambda(T) = {
        PHI0/[4*pi*MU0*Jc(T)] * [ln(kappa)+0.5]
    }^(1/3)

and:
    xi(T) = lambda(T)/kappa

Optional uncertainties in Jc and kappa are interpreted as independent
relative 1-sigma errors and propagated by Monte Carlo.

Example
-------
python lambda_from_T_Jc_constant_kappa.py data.txt \
    --jc-unit A/cm2 --kappa 40 \
    --jc-error-percent 5 --kappa-error-percent 3 \
    --mc-samples 5000 --output result.csv
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

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


def lambda_constant_kappa(jc_si, kappa):
    if np.any(np.asarray(jc_si) <= 0):
        raise ValueError("All Jc values must be > 0.")
    if kappa <= np.exp(-0.5):
        raise ValueError(
            "kappa is too small: ln(kappa)+0.5 must be positive. "
            "For the intended type-II use, kappa should normally be > 1."
        )
    prefactor = PHI0 / (4.0 * np.pi * MU0) * (np.log(kappa) + 0.5)
    return (prefactor / np.asarray(jc_si, dtype=float)) ** (1.0 / 3.0)


def lognormal_samples(mean, rel_sigma_percent, n, rng):
    if rel_sigma_percent <= 0:
        return np.full(n, mean, dtype=float)
    cv = rel_sigma_percent / 100.0
    sigma_ln = np.sqrt(np.log1p(cv**2))
    mu_ln = np.log(mean) - 0.5 * sigma_ln**2
    return rng.lognormal(mu_ln, sigma_ln, size=n)


def mc_lambda(jc_si, kappa, jc_err_pct, kappa_err_pct, n, confidence, rng):
    jc_s = lognormal_samples(jc_si, jc_err_pct, n, rng)
    kap_s = lognormal_samples(kappa, kappa_err_pct, n, rng)

    valid = kap_s > np.exp(-0.5)
    jc_s = jc_s[valid]
    kap_s = kap_s[valid]
    if len(jc_s) < max(100, int(0.5 * n)):
        raise RuntimeError("Too many Monte Carlo kappa samples were unphysical.")

    lam_s = (
        PHI0 / (4.0 * np.pi * MU0 * jc_s) *
        (np.log(kap_s) + 0.5)
    ) ** (1.0 / 3.0)
    xi_s = lam_s / kap_s

    alpha = (100.0 - confidence) / 2.0
    return {
        "mc_valid_samples": len(lam_s),
        "lambda_mc_mean_m": np.mean(lam_s),
        "lambda_mc_std_m": np.std(lam_s, ddof=1),
        "lambda_ci_low_m": np.percentile(lam_s, alpha),
        "lambda_ci_high_m": np.percentile(lam_s, 100.0 - alpha),
        "xi_mc_mean_m": np.mean(xi_s),
        "xi_mc_std_m": np.std(xi_s, ddof=1),
    }


def main():
    p = argparse.ArgumentParser(
        description="Extract lambda(T) from Jc(T) assuming constant kappa=lambda/xi."
    )
    p.add_argument("input", help="Input text/CSV file: T, Jc")
    p.add_argument("--jc-unit", default="A/cm2", choices=["A/cm2", "A/m2"])
    p.add_argument("--kappa", type=float, required=True,
                   help="Constant kappa=lambda/xi used at all temperatures.")
    p.add_argument("--output", default="lambda_from_T_Jc_constant_kappa.csv")
    p.add_argument("--jc-error-percent", type=float, default=0.0)
    p.add_argument("--kappa-error-percent", type=float, default=0.0)
    p.add_argument("--mc-samples", type=int, default=5000)
    p.add_argument("--confidence", type=float, default=68.27)
    p.add_argument("--seed", type=int, default=12345)
    args = p.parse_args()

    if not (0 < args.confidence < 100):
        raise ValueError("--confidence must be between 0 and 100.")

    raw = read_numeric_table(args.input, 2)
    T = raw.iloc[:, 0].to_numpy(float)
    jc_input = raw.iloc[:, 1].to_numpy(float)
    jc_si = convert_jc_to_si(jc_input, args.jc_unit)

    lam = lambda_constant_kappa(jc_si, args.kappa)
    xi = lam / args.kappa

    out = pd.DataFrame({
        "T_K": T,
        "Jc_input": jc_input,
        "Jc_A_per_m2": jc_si,
        "kappa_assumed": args.kappa,
        "lambda_m": lam,
        "lambda_nm": lam * 1e9,
        "xi_m_inferred": xi,
        "xi_nm_inferred": xi * 1e9,
    })

    if args.jc_error_percent > 0 or args.kappa_error_percent > 0:
        rng = np.random.default_rng(args.seed)
        mc_rows = [
            mc_lambda(j, args.kappa, args.jc_error_percent,
                      args.kappa_error_percent, args.mc_samples,
                      args.confidence, rng)
            for j in jc_si
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
        out["assumed_kappa_1sigma_percent"] = args.kappa_error_percent
        out["confidence_interval_percent"] = args.confidence

    out.to_csv(args.output, index=False)
    print(out.to_string(index=False))
    print(f"\nSaved: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
