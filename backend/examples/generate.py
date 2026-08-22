"""Regenerate the built-in example datasets.

Run from the backend directory:

    python examples/generate.py

The examples exist for two reasons (FR-028). A first-time user needs something
to press before they have prepared a file of their own, and development needs a
fixture whose correct answer is known, so that "did I break something?" has an
answer that does not depend on anyone's real data.

They are therefore generated from stated parameters rather than copied from a
paper, and the parameters are written into the file header. Realistic scatter is
added so that the fit has something to do and reports a standard error; without
it every residual would be zero and the uncertainty machinery would never be
exercised by the examples.

This script is a development tool, not part of the application. It is the only
place in the project that writes a file.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core import gap_models as gm            # noqa: E402
from app.core import lambda_solver as ls         # noqa: E402
from app.core.constants import KB, PHI0          # noqa: E402
from app.core.types import GapModel              # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def build(*, tc, lambda0_nm, coupling_ratio, kappa, model, n_points,
          t_min_over_tc, t_max_over_tc, jc_scatter, seed):
    """Synthesise Jc(T) from the stated parameters, with multiplicative scatter."""
    delta0 = 0.5 * coupling_ratio * KB * tc
    lambda0 = lambda0_nm * 1e-9
    t = np.linspace(t_min_over_tc * tc, t_max_over_tc * tc, n_points)

    lam = gm.lambda_of_T(t, lambda0, delta0, tc, model)
    xi = lam / kappa
    jc = np.asarray(ls.jc_model(lam, xi), dtype=float)

    rng = np.random.default_rng(seed)
    jc = jc * rng.lognormal(0.0, jc_scatter, jc.size)

    hc2 = PHI0 / (2.0 * np.pi * xi**2)
    return {"t": t, "jc_A_per_cm2": jc / 1e4, "hc2_T": hc2, "xi_nm": xi * 1e9,
            "delta0": delta0, "lambda0": lambda0}


EXAMPLES = [
    {
        "name": "nbti_like",
        "title": "NbTi-like film: weak-coupling, clean limit, with Hc2",
        "note": (
            "Roughly the parameters of a NbTi thin film. Single-band s-wave, "
            "weak-coupling, no nodes, comfortably strong type-II. The coupling "
            "ratio is the BCS value, so the analysis reports WEAK_COUPLING_BCS. "
            "The scatter on Jc is deliberately small, 0.2 %, because that is "
            "what it takes to tell the clean limit from the dirty limit at all; "
            "this example therefore demonstrates a decisive model preference. "
            "See nb3sn_like for what happens at realistic scatter."
        ),
        "coherence_source": "FROM_HC2",
        "columns": ["T_K", "Jc_A_per_cm2", "Hc2_T"],
        "truth": dict(tc=9.2, lambda0_nm=250.0, coupling_ratio=3.53, kappa=45.0,
                      model=GapModel.CLEAN, n_points=22,
                      t_min_over_tc=0.05, t_max_over_tc=0.93,
                      jc_scatter=0.002, seed=20260823),
        "expects_model_preference": True,
        "suggested_settings": {
            "coherence_source": "FROM_HC2",
            "gap_model": "CLEAN",
            "fit_route": "TWO_STEP",
        },
    },
    {
        "name": "nb3sn_like",
        "title": "Nb3Sn-like film: strong-coupling, dirty limit, fixed kappa",
        "note": (
            "Roughly the parameters of an Nb3Sn film. Still single-band and "
            "nodeless, but strongly coupled and in the dirty limit, so the "
            "analysis reports MODERATELY_STRONG. No Hc2 column, so a fixed "
            "kappa is used. The scatter on Jc is a realistic 3 %, at which the "
            "clean and dirty limits are NOT separable: the analysis reports "
            "MODELS_INDISTINGUISHABLE and declines to name a preferred model. "
            "That is the correct answer for data of this quality, and it is "
            "why this example is shipped alongside nbti_like."
        ),
        "coherence_source": "FIXED_KAPPA",
        "columns": ["T_K", "Jc_A_per_cm2"],
        "truth": dict(tc=17.8, lambda0_nm=120.0, coupling_ratio=4.30, kappa=30.0,
                      model=GapModel.DIRTY, n_points=25,
                      t_min_over_tc=0.06, t_max_over_tc=0.94,
                      jc_scatter=0.03, seed=20260824),
        "expects_model_preference": False,
        "suggested_settings": {
            "coherence_source": "FIXED_KAPPA",
            "kappa_fixed": 30.0,
            "gap_model": "DIRTY",
            "fit_route": "TWO_STEP",
        },
    },
]


def main() -> None:
    manifest = []
    for spec in EXAMPLES:
        truth = spec["truth"]
        data = build(**truth)

        lines = [
            f"# {spec['title']}",
            "#",
        ]
        lines += ["# " + line for line in _wrap(spec["note"], 74)]
        lines += [
            "#",
            "# Synthetic data, generated by examples/generate.py from these values:",
            f"#     Tc            = {truth['tc']} K",
            f"#     lambda(0)     = {truth['lambda0_nm']} nm",
            f"#     2 D(0)/kB Tc  = {truth['coupling_ratio']}"
            f"   ->  Delta(0) = {data['delta0'] / 1.602176634e-22:.4f} meV",
            f"#     kappa         = {truth['kappa']}",
            f"#     gap model     = {truth['model'].value}",
            f"#     Jc scatter    = {truth['jc_scatter'] * 100:.0f} % (1 sigma, log-normal)",
            "#",
            "# A correct analysis recovers those values. That is what makes this",
            "# usable as a regression fixture as well as a demonstration.",
            "#",
            "# " + "  ".join(f"{name:>16}" for name in spec["columns"]),
        ]

        columns = [data["t"], data["jc_A_per_cm2"]]
        if "Hc2_T" in spec["columns"]:
            columns.append(data["hc2_T"])
        for row in zip(*columns):
            lines.append("  " + "  ".join(f"{value:16.6g}" for value in row))

        path = HERE / f"{spec['name']}.txt"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {path.name}  ({truth['n_points']} points, "
              f"{len(spec['columns'])} columns)")

        manifest.append({
            "name": spec["name"],
            "title": spec["title"],
            "file": path.name,
            "coherence_source": spec["coherence_source"],
            "n_points": truth["n_points"],
            "expects_model_preference": spec["expects_model_preference"],
            "suggested_settings": spec["suggested_settings"],
            "truth": {
                "tc_K": truth["tc"],
                "lambda0_nm": truth["lambda0_nm"],
                "delta0_meV": data["delta0"] / 1.602176634e-22,
                "coupling_ratio": truth["coupling_ratio"],
                "kappa": truth["kappa"],
                "gap_model": truth["model"].value,
            },
        })

    (HERE / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote manifest.json")


def _wrap(text: str, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines


if __name__ == "__main__":
    main()
