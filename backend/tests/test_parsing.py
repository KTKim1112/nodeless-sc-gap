"""Reading a user's file. FR-002, FR-003, FR-005.

The failures here are the ones a user actually hits, and the requirement is not
just that they are rejected but that the rejection says *where*.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core.errors import ColumnCountMismatch, EmptyInput, NotANumber, TooFewPoints
from app.core.parsing import parse_table

BODY = [
    ("2.0", "1.1e6", "12.0"),
    ("4.0", "9.0e5", "10.5"),
    ("6.0", "6.0e5", "8.0"),
    ("8.0", "2.0e5", "4.0"),
]


def _render(separator: str, header: bool = False) -> str:
    lines = []
    if header:
        lines.append(separator.join(("T_K", "Jc", "Hc2_T")))
    lines.extend(separator.join(row) for row in BODY)
    return "\n".join(lines)


@pytest.mark.parametrize("separator", [" ", "\t", ",", ";", "   "])
def test_every_separator(separator):
    table = parse_table(_render(separator))
    assert table.n_rows == 4
    assert table.n_columns == 3
    assert table.values[0, 0] == pytest.approx(2.0)
    assert table.values[3, 1] == pytest.approx(2.0e5)


def test_header_detected_and_named():
    table = parse_table(_render(",", header=True))
    assert table.header_detected
    assert table.column_names == ["T_K", "Jc", "Hc2_T"]
    assert table.n_rows == 4


def test_header_absent_gets_generated_names():
    table = parse_table(_render(","))
    assert not table.header_detected
    assert table.column_names == ["column_1", "column_2", "column_3"]


def test_comments_and_blank_lines_are_skipped():
    text = "# measured 2026-08-20\n\n" + _render(" ") + "\n\n# end\n"
    table = parse_table(text)
    assert table.n_rows == 4


def test_non_numeric_cell_reports_its_location():
    # A stray text value is the commonest real failure: an instrument writes
    # "OL" or "---" for a point it could not measure.
    text = _render(" ").replace("6.0e5", "OL")
    with pytest.raises(NotANumber) as excinfo:
        parse_table(text)
    params = excinfo.value.params
    assert params["value"] == "OL"
    assert params["row"] == 3        # third data row
    assert params["column"] == 2     # Jc column
    assert params["line"] == 3       # third line of the text


def test_line_number_survives_comments():
    text = "# a comment\n# another\n" + _render(" ").replace("9.0e5", "nan!")
    with pytest.raises(NotANumber) as excinfo:
        parse_table(text)
    assert excinfo.value.params["row"] == 2
    assert excinfo.value.params["line"] == 4


def test_ragged_row_is_rejected():
    text = _render(" ") + "\n10.0 1.0e5"
    with pytest.raises(ColumnCountMismatch) as excinfo:
        parse_table(text)
    assert excinfo.value.params == {"expected": 3, "found": 2, "row": 5, "line": 5}


def test_too_few_rows():
    text = "\n".join(" ".join(r) for r in BODY[:3])
    with pytest.raises(TooFewPoints) as excinfo:
        parse_table(text)
    assert excinfo.value.params == {"found": 3, "required": 4}


def test_empty_input():
    with pytest.raises(EmptyInput):
        parse_table("\n\n#nothing here\n")


def test_header_only():
    with pytest.raises(EmptyInput):
        parse_table("T_K Jc Hc2_T\n")
