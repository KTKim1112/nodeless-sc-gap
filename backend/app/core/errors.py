"""Domain errors.

Every failure the physics can produce is one of these. Each carries a stable
`code` and a dictionary of structured `params`, and never a sentence meant for a
human reader -- rendering is the frontend's job (constitution IV).

The catalogue is fixed in specs/001-jc-to-gap/data-model.md. A code may be added
but an existing code must not change meaning, because the frontend maps codes to
Korean sentences by exact match.

This module lives in `core/` and the API layer imports it. Not the reverse: the
dependency arrows of plan.md section 2 point one way only. Nothing here knows
about HTTP; the mapping from code to status lives in `app/main.py`.
"""

from __future__ import annotations

from typing import Any


class CoreError(Exception):
    """Base class. Subclasses set `code`; instances carry `params`."""

    code: str = "INTERNAL"

    def __init__(self, **params: Any) -> None:
        self.params: dict[str, Any] = params
        super().__init__(f"{self.code} {params}")

    def payload(self) -> dict[str, Any]:
        """The wire representation, identical for every subclass."""
        return {"code": self.code, "params": self.params}


# --- input parsing -----------------------------------------------------------

class EmptyInput(CoreError):
    code = "EMPTY_INPUT"


class ColumnCountMismatch(CoreError):
    """params: expected, found"""
    code = "COLUMN_COUNT_MISMATCH"


class NotANumber(CoreError):
    """params: row, line, column, value"""
    code = "NOT_A_NUMBER"


class NonPositiveValue(CoreError):
    """params: row, column, value"""
    code = "NON_POSITIVE_VALUE"


class TooFewPoints(CoreError):
    """params: found, required"""
    code = "TOO_FEW_POINTS"


class UnknownUnit(CoreError):
    """params: unit"""
    code = "UNKNOWN_UNIT"


class LengthMismatch(CoreError):
    """params: name, expected, found"""
    code = "LENGTH_MISMATCH"


class MissingColumn(CoreError):
    """params: coherence_source, missing"""
    code = "MISSING_COLUMN"


# --- penetration depth extraction --------------------------------------------

class KappaTooSmall(CoreError):
    """kappa <= exp(-0.5): ln(kappa) + 0.5 is not positive and the model is
    undefined. params: kappa, floor"""
    code = "KAPPA_TOO_SMALL"


class NotTypeII(CoreError):
    """params: kappa, boundary"""
    code = "NOT_TYPE_II"


class NoRootTypeII(CoreError):
    """The supplied Jc exceeds the largest value equation (1) can produce for
    this xi, so no solution exists on the lambda > xi branch.
    params: temperature_K, jc, xi, jc_max"""
    code = "NO_ROOT_TYPE_II"


class RootBracketingFailed(CoreError):
    """params: temperature_K"""
    code = "ROOT_BRACKETING_FAILED"


# --- fitting -----------------------------------------------------------------

class TcFixedBelowData(CoreError):
    """params: tc_fixed_K, t_max_K"""
    code = "TC_FIXED_BELOW_DATA"


class FitDidNotConverge(CoreError):
    """params: route, model, status"""
    code = "FIT_DID_NOT_CONVERGE"


# --- uncertainty -------------------------------------------------------------

class MonteCarloTooManyFailures(CoreError):
    """params: n_valid, n_requested, n_required"""
    code = "MC_TOO_MANY_FAILURES"


# --- jobs --------------------------------------------------------------------

class JobNotFound(CoreError):
    """params: job_id"""
    code = "JOB_NOT_FOUND"
