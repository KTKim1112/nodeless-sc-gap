"""Unit conversion.

The only place in the project where a non-SI number becomes an SI one or the
reverse (constitution V). Everything downstream may then assume SI without
asking.
"""

from __future__ import annotations

import numpy as np

from .constants import MEV_TO_J
from .errors import UnknownUnit
from .types import FloatArray, JcUnit, XiUnit

#: Multiply by this to reach A/m^2.
_JC_TO_SI: dict[JcUnit, float] = {
    JcUnit.A_PER_CM2: 1e4,
    JcUnit.A_PER_M2: 1.0,
}

#: Multiply by this to reach metres.
_XI_TO_SI: dict[XiUnit, float] = {
    XiUnit.M: 1.0,
    XiUnit.NM: 1e-9,
    XiUnit.UM: 1e-6,
}


def _factor(table: dict, unit, kind: str) -> float:
    try:
        return table[unit]
    except (KeyError, TypeError):
        raise UnknownUnit(unit=str(unit), kind=kind) from None


def jc_to_si(values, unit: JcUnit) -> FloatArray:
    """Critical current density to A/m^2."""
    return np.asarray(values, dtype=float) * _factor(_JC_TO_SI, unit, "jc")


def jc_from_si(values, unit: JcUnit) -> FloatArray:
    return np.asarray(values, dtype=float) / _factor(_JC_TO_SI, unit, "jc")


def xi_to_si(values, unit: XiUnit) -> FloatArray:
    """Coherence length to metres."""
    return np.asarray(values, dtype=float) * _factor(_XI_TO_SI, unit, "xi")


def xi_from_si(values, unit: XiUnit) -> FloatArray:
    return np.asarray(values, dtype=float) / _factor(_XI_TO_SI, unit, "xi")


def m_to_nm(values):
    """Metres to nanometres. Scalars stay scalars."""
    return values * 1e9 if np.isscalar(values) else np.asarray(values, dtype=float) * 1e9


def nm_to_m(values):
    return values * 1e-9 if np.isscalar(values) else np.asarray(values, dtype=float) * 1e-9


def j_to_meV(values):
    """Joules to millielectronvolts."""
    return (values / MEV_TO_J if np.isscalar(values)
            else np.asarray(values, dtype=float) / MEV_TO_J)


def meV_to_j(values):
    return (values * MEV_TO_J if np.isscalar(values)
            else np.asarray(values, dtype=float) * MEV_TO_J)
