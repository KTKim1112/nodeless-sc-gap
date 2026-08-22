"""Physical constants and unit factors.

Values and their justification are fixed in specs/001-jc-to-gap/research.md R0.
Everything here is SI unless the name says otherwise.
"""

import math

#: Superconducting magnetic flux quantum h/(2e), in weber.
PHI0 = 2.067833848e-15

#: Vacuum permeability, in henry per metre.
#:
#: Deliberately the pre-2019 exact value 4*pi*1e-7 rather than the CODATA
#: measured 1.25663706212e-6. They differ by 1.5e-10 relative, far below any
#: experimental uncertainty here, and using the same value as the archived
#: legacy scripts keeps the cross-check in tests/test_legacy_agreement.py exact.
MU0 = 4.0 * math.pi * 1e-7

#: Boltzmann constant, in joule per kelvin. Exact by SI definition.
KB = 1.380649e-23

#: Joules per millielectronvolt. Exact by SI definition of the elementary charge.
MEV_TO_J = 1.602176634e-22

#: Weak-coupling BCS gap ratio Delta(0) / (kB Tc), equal to pi / exp(euler_gamma).
BCS_ALPHA = 1.763875

#: Weak-coupling BCS coupling ratio 2 Delta(0) / (kB Tc), equal to 2 pi / exp(euler_gamma).
BCS_RATIO = 2.0 * BCS_ALPHA

#: Ginzburg-Landau parameter below which ln(kappa) + 0.5 turns negative and
#: equation (1) of research R1 stops having any meaning at all.
KAPPA_MODEL_FLOOR = math.exp(-0.5)

#: The classical type-I / type-II boundary.
KAPPA_TYPE_II_BOUNDARY = 1.0 / math.sqrt(2.0)

#: Below this the large-kappa form of Hc1 used in equation (1) is a poor
#: approximation even though the equation still returns a number (research R10).
KAPPA_STRONG_TYPE_II = 5.0
