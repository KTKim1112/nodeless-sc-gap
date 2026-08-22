"""Unit conversion. Constitution V says this is the only place it happens, so
this is the only place it can go wrong."""

from __future__ import annotations

import numpy as np
import pytest

from app.core import units
from app.core.constants import MEV_TO_J
from app.core.errors import UnknownUnit
from app.core.types import JcUnit, XiUnit


def test_jc_cm2_to_m2():
    # 1 A/cm^2 is 1e4 A/m^2. Getting this backwards would move the extracted
    # lambda by a factor of 1e4^(1/3) = 21.5, which looks plausible enough to
    # go unnoticed.
    assert units.jc_to_si([1.0], JcUnit.A_PER_CM2)[0] == pytest.approx(1e4)
    assert units.jc_to_si([1.0], JcUnit.A_PER_M2)[0] == pytest.approx(1.0)


@pytest.mark.parametrize("unit", list(JcUnit))
def test_jc_round_trip(unit):
    values = np.array([1.0, 1234.5, 6.7e9])
    back = units.jc_from_si(units.jc_to_si(values, unit), unit)
    assert np.allclose(back, values, rtol=0, atol=0)


@pytest.mark.parametrize(
    "unit,factor", [(XiUnit.M, 1.0), (XiUnit.NM, 1e-9), (XiUnit.UM, 1e-6)]
)
def test_xi_factors(unit, factor):
    assert units.xi_to_si([1.0], unit)[0] == pytest.approx(factor)


@pytest.mark.parametrize("unit", list(XiUnit))
def test_xi_round_trip(unit):
    values = np.array([1.0, 5.0, 250.0])
    assert np.allclose(units.xi_from_si(units.xi_to_si(values, unit), unit), values)


def test_energy_conversion():
    assert units.meV_to_j(1.0) == pytest.approx(MEV_TO_J)
    assert units.j_to_meV(MEV_TO_J) == pytest.approx(1.0)
    assert units.j_to_meV(units.meV_to_j(1.5)) == pytest.approx(1.5)


def test_length_conversion():
    assert units.m_to_nm(2e-7) == pytest.approx(200.0)
    assert units.nm_to_m(200.0) == pytest.approx(2e-7)


def test_unknown_unit_is_a_domain_error():
    with pytest.raises(UnknownUnit) as excinfo:
        units.jc_to_si([1.0], "A/furlong^2")
    assert excinfo.value.code == "UNKNOWN_UNIT"
    assert "unit" in excinfo.value.params
