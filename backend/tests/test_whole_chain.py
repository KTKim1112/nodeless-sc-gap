"""The whole chain, on data whose answer is known.

These run parsing, unit conversion, the inversion, the fit and the diagnostics
together, starting from raw text exactly as a user's file arrives. No other
test covers the chain end to end.

The fixtures were generated from stated parameters, so the recovered values are
checked against the truth recorded in the manifest. That is the part no real
measurement could stand in for: no measured film has a known `lambda(0)`, so a
real dataset could only confirm that some number came out, not that it was the
right one.

They were once shipped with the application as built-in examples. FR-028 was
withdrawn -- a manufactured dataset distributed beside a measurement tool reads
as a claim about real samples -- so they live under `tests/data/` now, where
they are fixtures and are not distributed at all.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from app.core import pipeline
from app.core.constants import MEV_TO_J
from app.core.diagnostics import DELTA_AIC_THRESHOLD
from app.core.parsing import parse_table
from app.core.types import (
    AnalysisSettings,
    CoherenceSource,
    CouplingRegime,
    GapModel,
)
from app.core.units import jc_to_si
from app.core.types import JcUnit
from app.core.validation import build_dataset

EXAMPLES = pathlib.Path(__file__).resolve().parent / "data"
MANIFEST = json.loads((EXAMPLES / "manifest.json").read_text(encoding="utf-8"))


def _analyse(entry: dict):
    table = parse_table((EXAMPLES / entry["file"]).read_text(encoding="utf-8"))
    columns = [table.values[:, i] for i in range(table.n_columns)]

    source = CoherenceSource(entry["coherence_source"])
    jc = jc_to_si(columns[1], JcUnit.A_PER_CM2)
    hc2 = columns[2] if source is CoherenceSource.FROM_HC2 else None

    dataset = build_dataset(columns[0], jc, hc2=hc2)
    suggested = entry["suggested_settings"]
    settings = AnalysisSettings(
        coherence_source=source,
        kappa_fixed=suggested.get("kappa_fixed"),
        gap_model=GapModel(suggested["gap_model"]),
    )
    return pipeline.run_analysis(dataset, settings), table


@pytest.mark.parametrize("entry", MANIFEST, ids=[e["name"] for e in MANIFEST])
def test_example_parses_as_advertised(entry):
    table = parse_table((EXAMPLES / entry["file"]).read_text(encoding="utf-8"))
    assert table.n_rows == entry["n_points"]
    assert table.n_columns == (3 if entry["coherence_source"] == "FROM_HC2" else 2)


@pytest.mark.parametrize("entry", MANIFEST, ids=[e["name"] for e in MANIFEST])
def test_example_recovers_the_parameters_it_was_built_from(entry):
    """2 % to 3 % scatter was added to Jc, so the recovered values will not be
    exact. The tolerance is set by what that scatter actually permits, not by
    what would look impressive."""
    result, _ = _analyse(entry)
    truth = entry["truth"]

    assert result.fit.converged
    assert result.fit.tc.value == pytest.approx(truth["tc_K"], rel=0.02)
    assert result.fit.lambda0.value * 1e9 == pytest.approx(truth["lambda0_nm"], rel=0.03)
    assert result.fit.delta0.value / MEV_TO_J == pytest.approx(
        truth["delta0_meV"], rel=0.05
    )
    assert result.fit.coupling_ratio.value == pytest.approx(
        truth["coupling_ratio"], rel=0.05
    )


@pytest.mark.parametrize("entry", MANIFEST, ids=[e["name"] for e in MANIFEST])
def test_example_reports_standard_errors(entry):
    """The scatter is there so that the uncertainty machinery is exercised.
    If an example ever became noiseless, this would catch it."""
    result, _ = _analyse(entry)
    for parameter in (result.fit.lambda0, result.fit.delta0, result.fit.coupling_ratio):
        assert parameter.stderr is not None and parameter.stderr > 0.0
    assert result.fit.chi2_reduced > 0.0


@pytest.mark.parametrize("entry", MANIFEST, ids=[e["name"] for e in MANIFEST])
def test_example_ranks_the_model_it_was_built_with_first(entry):
    """Whatever the verdict, the generating model must at least fit better.

    Ranking is a weaker claim than declaring a preference, and it is the one
    that should hold even when the data are too noisy to be decisive.
    """
    result, _ = _analyse(entry)
    truth = GapModel(entry["truth"]["gap_model"])
    chi = {GapModel.CLEAN: result.diagnostics.chi2_clean,
           GapModel.DIRTY: result.diagnostics.chi2_dirty}
    assert min(chi, key=chi.get) is truth
    assert result.diagnostics.preferred_model_weight > 0.5


@pytest.mark.parametrize("entry", MANIFEST, ids=[e["name"] for e in MANIFEST])
def test_example_declares_a_preference_only_when_its_data_support_one(entry):
    """FR-020, and the point of shipping two examples.

    The clean and dirty limits differ by at most 0.097 in rho_s, so telling
    them apart needs scatter on Jc below about half a per cent (research R10).
    One example is generated clean enough to manage it; the other carries a
    realistic 3 % and must honestly decline.
    """
    result, _ = _analyse(entry)
    diagnostics = result.diagnostics
    codes = {w.code for w in diagnostics.warnings}

    if entry["expects_model_preference"]:
        assert diagnostics.preferred_model is GapModel(entry["truth"]["gap_model"])
        assert diagnostics.delta_aic >= DELTA_AIC_THRESHOLD
        assert "MODELS_INDISTINGUISHABLE" not in codes
    else:
        assert diagnostics.preferred_model is None
        assert diagnostics.delta_aic < DELTA_AIC_THRESHOLD
        assert "MODELS_INDISTINGUISHABLE" in codes


def test_the_weak_coupling_example_is_classified_as_weak_coupling():
    entry = next(e for e in MANIFEST if e["name"] == "weak_coupling_clean_hc2")
    result, _ = _analyse(entry)
    assert result.diagnostics.coupling_regime is CouplingRegime.WEAK_COUPLING_BCS


def test_the_strong_coupling_example_is_classified_as_stronger():
    entry = next(e for e in MANIFEST if e["name"] == "strong_coupling_dirty_kappa")
    result, _ = _analyse(entry)
    assert result.diagnostics.coupling_regime is CouplingRegime.MODERATELY_STRONG


@pytest.mark.parametrize("entry", MANIFEST, ids=[e["name"] for e in MANIFEST])
def test_example_raises_no_data_quality_warning(entry):
    """A shipped example that trips its own warnings would teach the user to
    ignore them."""
    codes = {w.code for w in result_codes(entry)}
    assert "LOW_T_COVERAGE_WEAK" not in codes
    assert "LOW_T_COVERAGE_INSUFFICIENT" not in codes
    assert "KAPPA_NEAR_TYPE_I_BOUNDARY" not in codes
    assert "SELF_FIELD_TRANSPORT_REQUIRED" in codes


def result_codes(entry: dict):
    result, _ = _analyse(entry)
    return result.diagnostics.warnings


def test_two_examples_are_shipped_covering_different_modes():
    assert len(MANIFEST) >= 2
    sources = {e["coherence_source"] for e in MANIFEST}
    assert {"FROM_HC2", "FIXED_KAPPA"} <= sources
    for entry in MANIFEST:
        assert (EXAMPLES / entry["file"]).is_file()
