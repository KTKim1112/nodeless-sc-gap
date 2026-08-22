# legacy/ — Reference only, not maintained

These files are the original command-line prototypes that extract the London
penetration depth `lambda(T)` from self-field critical current density data
using the Talantsev-Tallon thin-film relation.

**They are kept as a physics reference and as a numerical cross-check target.
They are not part of the application and are not maintained.**

| File | Role |
| --- | --- |
| `lambda_from_T_Jc_Hc2.py` | T, Jc, Hc2 -> xi(T) -> lambda(T) |
| `lambda_from_T_Jc_xi.py` | T, Jc, xi -> lambda(T) |
| `lambda_from_T_Jc_constant_kappa.py` | T, Jc + fixed kappa -> lambda(T), xi(T) |
| `README_lambda_extraction_KR_updated.md` | Full derivation and assumptions (Korean) |
| `README_lambda_extraction_EN_updated.md` | Same document (English) |

## How they are used by the new project

1. **Physics source.** The Talantsev-Tallon equation, the `lambda > xi` root
   branch selection, and the log-normal Monte Carlo sampling strategy were
   taken from here as design input.
2. **Numerical oracle.** `backend/tests/test_legacy_agreement.py` feeds the same
   input to these scripts and to `backend/app/core/` and asserts that the
   resulting `lambda(T)` values agree.

Code is **not** copied from these files into `backend/app/core/`. The new core is
written against a different architecture (pure functions, vectorised arrays,
typed domain errors, no file or CLI concerns).

## Running them standalone

    cd legacy
    pip install -r requirements.txt
    python lambda_from_T_Jc_Hc2.py data.txt --jc-unit A/cm2 --output result.csv
