"""The HTTP layer.

Three kinds of check here. That each endpoint does what the contract says; that
failures come back as the right code with the right status; and two
constitutional properties that are easy to break by accident and impossible to
notice by eye -- that no response contains Korean, and that the running API has
not drifted away from contracts/openapi.yaml.
"""

from __future__ import annotations

import json
import pathlib
import time

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import app

CONTRACT = (pathlib.Path(__file__).resolve().parents[2]
            / "specs" / "001-jc-to-gap" / "contracts" / "openapi.yaml")


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def example_request(client) -> dict:
    """A valid /api/analyze body, built the way the frontend will build one."""
    example = client.get("/api/examples/nbti_like").json()
    values = client.post("/api/parse", json={"text": example["text"]}).json()["values"]
    return {
        "dataset": {
            "temperature_K": [row[0] for row in values],
            "jc": [row[1] for row in values],
            "jc_unit": "A_PER_CM2",
            "hc2_T": [row[2] for row in values],
        },
        "settings": example["suggested_settings"],
    }


# --- happy paths -------------------------------------------------------------

def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_examples_are_listed_and_fetchable(client):
    listing = client.get("/api/examples")
    assert listing.status_code == 200
    entries = listing.json()
    assert len(entries) >= 2

    for entry in entries:
        example = client.get(f"/api/examples/{entry['name']}")
        assert example.status_code == 200
        body = example.json()
        assert body["text"].strip()
        assert body["suggested_settings"]["coherence_source"] == entry["coherence_source"]


def test_parse_reports_how_the_text_was_read(client):
    text = "T Jc Hc2\n2 1e6 12\n4 9e5 10\n6 6e5 8\n8 2e5 4\n"
    body = client.post("/api/parse", json={"text": text}).json()
    assert body["header_detected"] is True
    assert body["column_names"] == ["T", "Jc", "Hc2"]
    assert body["n_rows"] == 4 and body["n_columns"] == 3
    assert body["preview"][0] == [2.0, 1e6, 12.0]


def test_lambda_endpoint_returns_both_si_and_display_units(client, example_request):
    body = client.post("/api/lambda", json=example_request).json()
    n = len(body["temperature_K"])
    for key in ("jc_A_per_m2", "xi_m", "xi_nm", "lambda_m", "lambda_nm", "kappa"):
        assert len(body[key]) == n
    assert body["lambda_nm"][0] == pytest.approx(body["lambda_m"][0] * 1e9)
    assert body["xi_nm"][0] == pytest.approx(body["xi_m"][0] * 1e9)


def test_analyze_recovers_the_example_parameters(client, example_request):
    response = client.post("/api/analyze", json=example_request)
    assert response.status_code == 200
    body = response.json()

    fit = body["fit"]
    assert fit["converged"] is True
    assert fit["lambda0_nm"]["value"] == pytest.approx(250.0, rel=0.02)
    assert fit["delta0_meV"]["value"] == pytest.approx(1.3993, rel=0.03)
    assert fit["tc_K"]["value"] == pytest.approx(9.2, rel=0.01)
    assert fit["delta0_J"]["value"] == pytest.approx(
        fit["delta0_meV"]["value"] * 1.602176634e-22
    )

    diagnostics = body["diagnostics"]
    assert diagnostics["coupling_regime"] == "WEAK_COUPLING_BCS"
    assert diagnostics["preferred_model"] == "CLEAN"
    assert diagnostics["delta_aic"] > 10.0
    assert any(w["code"] == "SELF_FIELD_TRANSPORT_REQUIRED"
               for w in diagnostics["warnings"])

    assert len(body["curve"]["temperature_K"]) == 200
    assert body["uncertainty"] is None       # analyze never runs the Monte Carlo


def test_analyze_does_not_run_the_monte_carlo(client, example_request):
    """FR-018. If this ever became slow, the page would freeze."""
    start = time.perf_counter()
    client.post("/api/analyze", json=example_request)
    assert time.perf_counter() - start < 5.0


def test_export_csv_is_self_describing(client, example_request):
    analysis = client.post("/api/analyze", json=example_request).json()
    response = client.post("/api/export/csv", json=analysis)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    text = response.text
    # QA-004: every column carries its unit.
    assert "T_K,Jc_A_per_m2,xi_nm,lambda_nm,kappa" in text
    # Constitution VI: the assumptions travel with the numbers.
    assert "SELF_FIELD_TRANSPORT_REQUIRED" in text
    assert "lambda(0) [nm]" in text and "Delta(0) [meV]" in text
    data_rows = [line for line in text.splitlines()
                 if line and not line.startswith("#") and not line.startswith("T_K")]
    assert len(data_rows) == len(analysis["lambda_table"]["temperature_K"])


def test_export_csv_carries_the_fit_view_of_each_point(client, example_request):
    """The per-measurement table reports the fit at the measured points too.

    rho_s_measured and the residual are one value per measurement, in the same
    order as the inversion, so they belong in this table rather than in a
    second one. If that ever stops being true the zip in export_csv would
    silently truncate to the shorter of the two, so assert the width.
    """
    analysis = client.post("/api/analyze", json=example_request).json()
    text = client.post("/api/export/csv", json=analysis).text

    header = next(line for line in text.splitlines() if line.startswith("T_K"))
    assert header == "T_K,Jc_A_per_m2,xi_nm,lambda_nm,kappa,rho_s_measured,fit_residual"

    rows = [line.split(",") for line in text.splitlines()
            if line and not line.startswith("#") and not line.startswith("T_K")]
    assert len(rows) == len(analysis["fit"]["residuals"])
    assert all(len(row) == 7 for row in rows)
    assert float(rows[0][5]) == pytest.approx(analysis["fit"]["rho_s_measured"][0])
    assert float(rows[0][6]) == pytest.approx(analysis["fit"]["residuals"][0])


def test_export_curve_is_the_curve_that_was_plotted(client, example_request):
    """FR-027a. The exported curve must be the drawn one, not a resampling.

    Asserted value by value rather than by shape: a file that disagrees with
    the figure beside it is a defect that would surface only in someone else's
    paper, and nothing about the file's shape would reveal it.
    """
    analysis = client.post("/api/analyze", json=example_request).json()
    response = client.post("/api/export/curve.csv", json=analysis)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "nodeless_sc_curve.csv" in response.headers["content-disposition"]

    text = response.text
    assert "T_K,rho_s_model,lambda_model_nm" in text
    # Constitution VI: either file may be opened without the other.
    assert "SELF_FIELD_TRANSPORT_REQUIRED" in text
    assert "lambda(0) [nm]" in text

    rows = [line.split(",") for line in text.splitlines()
            if line and not line.startswith("#") and not line.startswith("T_K")]
    curve = analysis["curve"]
    assert len(rows) == len(curve["temperature_K"])
    for row, t, r, lam in zip(rows, curve["temperature_K"], curve["rho_s"],
                              curve["lambda_nm"]):
        assert float(row[0]) == pytest.approx(t)
        assert float(row[1]) == pytest.approx(r)
        assert float(row[2]) == pytest.approx(lam)


def test_curve_starts_at_absolute_zero_on_the_reported_intercept(client, example_request):
    """FR-026. The intercept the analysis reports has to be on the curve.

    Not approximately: rho_s is exactly 1 at T = 0 for both gap models, which
    test_gap_models pins, so lambda there is lambda0 / sqrt(1) and equality is
    exact. Asserting approx would let a curve that merely starts near zero pass.
    """
    analysis = client.post("/api/analyze", json=example_request).json()
    curve, fit = analysis["curve"], analysis["fit"]

    assert curve["temperature_K"][0] == 0.0
    assert curve["rho_s"][0] == 1.0
    assert curve["lambda_nm"][0] == fit["lambda0_nm"]["value"]
    # And still stops short of Tc, where lambda diverges.
    assert 0.0 < curve["temperature_K"][-1] < fit["tc_K"]["value"]


# --- failures ----------------------------------------------------------------

@pytest.mark.parametrize("mutate,expected_code,expected_status", [
    (lambda b: b["dataset"]["jc"].__setitem__(3, -1.0), "NON_POSITIVE_VALUE", 422),
    (lambda b: b["dataset"].__setitem__("hc2_T", None), "MISSING_COLUMN", 422),
    (lambda b: b["settings"].__setitem__("tc_fixed_K", 1.0), "TC_FIXED_BELOW_DATA", 422),
])
def test_domain_failures_come_back_as_codes(client, example_request,
                                            mutate, expected_code, expected_status):
    body = json.loads(json.dumps(example_request))
    mutate(body)
    response = client.post("/api/analyze", json=body)
    assert response.status_code == expected_status
    payload = response.json()
    assert payload["code"] == expected_code
    assert isinstance(payload["params"], dict)


def test_kappa_below_the_model_floor(client, example_request):
    body = json.loads(json.dumps(example_request))
    body["settings"] = {"coherence_source": "FIXED_KAPPA", "kappa_fixed": 0.5}
    response = client.post("/api/analyze", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "KAPPA_TOO_SMALL"


def test_kappa_between_the_floor_and_type_ii(client, example_request):
    body = json.loads(json.dumps(example_request))
    body["settings"] = {"coherence_source": "FIXED_KAPPA", "kappa_fixed": 0.65}
    assert client.post("/api/analyze", json=body).json()["code"] == "NOT_TYPE_II"


def test_unknown_example_and_job_are_404(client):
    assert client.get("/api/examples/no-such-thing").status_code == 404
    assert client.get("/api/examples/no-such-thing").json()["code"] == "EXAMPLE_NOT_FOUND"
    assert client.get("/api/jobs/deadbeef").status_code == 404
    assert client.get("/api/jobs/deadbeef").json()["code"] == "JOB_NOT_FOUND"


def test_malformed_body_is_rejected_before_any_physics(client):
    assert client.post("/api/analyze", json={"dataset": {}, "settings": {}}).status_code == 422
    assert client.post("/api/parse", json={}).status_code == 422


def test_unknown_field_is_rejected_rather_than_ignored(client, example_request):
    """A misspelled setting must not silently produce a plausible wrong answer."""
    body = json.loads(json.dumps(example_request))
    body["settings"]["gap_modle"] = "DIRTY"
    assert client.post("/api/analyze", json=body).status_code == 422


def test_too_few_points_is_refused(client):
    assert client.post("/api/parse", json={"text": "1 2\n3 4\n"}).json()["code"] == "TOO_FEW_POINTS"


# --- background jobs ---------------------------------------------------------

def test_uncertainty_returns_immediately_then_completes(client, example_request):
    """FR-018: accepted at once, progress observable, result when done."""
    body = dict(example_request)
    body["uncertainty"] = {
        "jc_error_percent": 5.0, "correlation_mode": "INDEPENDENT",
        "n_samples": 120, "confidence_percent": 68.27, "seed": 12345,
    }

    start = time.perf_counter()
    accepted = client.post("/api/uncertainty", json=body)
    assert accepted.status_code == 202
    assert time.perf_counter() - start < 5.0
    job_id = accepted.json()["job_id"]

    deadline = time.time() + 120
    while time.time() < deadline:
        status = client.get(f"/api/jobs/{job_id}").json()
        assert 0.0 <= status["progress"] <= 1.0
        if status["state"] in ("SUCCEEDED", "FAILED"):
            break
        time.sleep(0.2)

    assert status["state"] == "SUCCEEDED", status.get("error")
    assert status["progress"] == 1.0
    result = status["result"]
    assert result["n_valid"] > 0
    assert result["settings"]["seed"] == 12345          # constitution VII
    assert result["settings"]["correlation_mode"] == "INDEPENDENT"
    for name in ("lambda0_nm", "delta0_meV", "tc_K", "coupling_ratio"):
        assert result[name]["ci_low"] <= result[name]["mean"] <= result[name]["ci_high"]


def test_uncertainty_rejects_bad_input_before_starting_the_job(client, example_request):
    """Minutes of computation must not be spent on a request that cannot work."""
    body = json.loads(json.dumps(example_request))
    body["dataset"]["jc"][0] = -5.0
    body["uncertainty"] = {"jc_error_percent": 5.0, "n_samples": 100}
    response = client.post("/api/uncertainty", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "NON_POSITIVE_VALUE"


# --- constitutional properties ----------------------------------------------

def _endpoint_responses(client, example_request):
    analysis = client.post("/api/analyze", json=example_request).json()
    broken = json.loads(json.dumps(example_request))
    broken["dataset"]["jc"][2] = -1.0
    yield client.get("/api/health")
    yield client.get("/api/examples")
    yield client.get("/api/examples/nbti_like")
    yield client.post("/api/parse", json={"text": "1 2 3\n4 5 6\n7 8 9\n1 1 1\n"})
    yield client.post("/api/lambda", json=example_request)
    yield client.post("/api/analyze", json=example_request)
    yield client.post("/api/analyze", json=broken)
    yield client.post("/api/export/csv", json=analysis)
    yield client.get("/api/jobs/nonexistent")


def test_no_response_contains_display_prose(client, example_request):
    """Constitution IV and VIII.

    The UI is Korean while the backend is English. If a Korean sentence ever
    appears in a response, display text has started leaking into the backend and
    the separation that keeps error handling testable has been lost.

    The example files are the one legitimate source of non-ASCII-adjacent
    content, and they are ASCII too, so a blanket check is safe here.
    """
    offenders = []
    for response in _endpoint_responses(client, example_request):
        text = response.text
        if not text.isascii():
            non_ascii = {ch for ch in text if not ch.isascii()}
            offenders.append(f"{response.request.url.path}: {sorted(non_ascii)[:10]}")
    assert not offenders, "non-ASCII in responses:\n  " + "\n  ".join(offenders)


def test_every_failure_has_the_same_shape(client, example_request):
    """One failure shape everywhere means the frontend needs one code path."""
    broken = json.loads(json.dumps(example_request))
    broken["dataset"]["jc"][2] = -1.0
    for response in (client.post("/api/analyze", json=broken),
                     client.get("/api/jobs/nope"),
                     client.get("/api/examples/nope")):
        payload = response.json()
        assert set(payload) == {"code", "params"}
        assert payload["code"].isupper() and payload["code"].isascii()


# --- the contract ------------------------------------------------------------

def _contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


def test_contract_file_exists():
    assert CONTRACT.is_file(), f"design contract missing at {CONTRACT}"


def test_every_contracted_path_is_implemented(client):
    """The contract was written before the code. If they have drifted apart,
    one of them is wrong and the disagreement must be resolved, not tolerated.
    """
    generated = client.get("/openapi.json").json()
    missing = []
    for path, operations in _contract()["paths"].items():
        for method in operations:
            if path not in generated["paths"]:
                missing.append(f"{method.upper()} {path} (path absent)")
            elif method not in generated["paths"][path]:
                missing.append(f"{method.upper()} {path} (method absent)")
    assert not missing, "contracted but not implemented:\n  " + "\n  ".join(missing)


@pytest.mark.parametrize("schema_name,required", [
    ("ErrorPayload", ["code", "params"]),
    ("LambdaResponse", ["temperature_K", "jc_A_per_m2", "xi_m", "xi_nm",
                        "lambda_m", "lambda_nm", "kappa"]),
    ("FitResult", ["gap_model", "fit_route", "converged", "lambda0_nm",
                   "delta0_meV", "tc_K", "coupling_ratio", "chi2_reduced"]),
    ("DiagnosticReport", ["chi2_reduced", "coupling_ratio", "coupling_regime",
                          "bcs_ratio_reference", "t_min_over_tc",
                          "kappa_min", "kappa_max", "warnings"]),
])
def test_contracted_properties_are_present_in_the_generated_schema(
    client, schema_name, required
):
    generated = client.get("/openapi.json").json()["components"]["schemas"]
    # The generated names carry an "Out" or "In" suffix where the wire model and
    # the domain model would otherwise collide; match on the stem.
    candidates = [name for name in generated
                  if name.replace("Out", "").replace("In", "") == schema_name]
    assert candidates, f"no generated schema resembling {schema_name}"
    properties = set(generated[candidates[0]].get("properties", {}))
    assert set(required) <= properties, (
        f"{candidates[0]} is missing {sorted(set(required) - properties)}"
    )


def test_generated_document_is_servable(client):
    """/docs is how the API is exercised before any frontend exists."""
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
