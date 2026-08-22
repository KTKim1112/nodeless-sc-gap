"""Turn pasted or uploaded text into a numeric table.

No physics and no units here. The point of keeping this separate is FR-003: the
user gets to see how their file was read before anything is computed with it,
so a misread column is caught immediately rather than as a strange result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from .errors import ColumnCountMismatch, EmptyInput, NotANumber, TooFewPoints
from .types import FloatArray

#: Any run of whitespace, comma, or semicolon separates columns.
_SEPARATOR = re.compile(r"[\s,;]+")

#: Fewer than this and there is no residual degree of freedom left after
#: fitting three parameters (data-model.md).
MIN_POINTS = 4


@dataclass(frozen=True)
class ParsedTable:
    values: FloatArray            # shape (n_rows, n_columns)
    column_names: list[str]
    header_detected: bool
    #: 1-based line number in the original text for each data row, so that an
    #: error can point the user at a line they can actually find in an editor.
    source_lines: list[int]

    @property
    def n_rows(self) -> int:
        return int(self.values.shape[0])

    @property
    def n_columns(self) -> int:
        return int(self.values.shape[1])


def _is_number(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def _split(line: str) -> list[str]:
    return [t for t in _SEPARATOR.split(line.strip()) if t]


def parse_table(text: str, comment_prefix: str = "#") -> ParsedTable:
    """Read `text` as a whitespace-, comma-, or semicolon-separated table.

    A first row whose leading cells are not all numeric is taken as a header.
    Blank lines and lines starting with `comment_prefix` are skipped, but the
    line numbers of the surviving rows are kept so errors stay locatable.
    """
    rows: list[tuple[int, list[str]]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or (comment_prefix and stripped.startswith(comment_prefix)):
            continue
        rows.append((lineno, _split(stripped)))

    if not rows:
        raise EmptyInput()

    n_columns = len(rows[0][1])
    header_detected = not all(_is_number(t) for t in rows[0][1])
    if header_detected:
        column_names = list(rows[0][1])
        rows = rows[1:]
        if not rows:
            raise EmptyInput()
    else:
        column_names = [f"column_{i + 1}" for i in range(n_columns)]

    if len(rows) < MIN_POINTS:
        raise TooFewPoints(found=len(rows), required=MIN_POINTS)

    values = np.empty((len(rows), n_columns), dtype=float)
    for r, (lineno, tokens) in enumerate(rows):
        if len(tokens) != n_columns:
            raise ColumnCountMismatch(
                expected=n_columns, found=len(tokens), row=r + 1, line=lineno
            )
        for c, token in enumerate(tokens):
            try:
                values[r, c] = float(token)
            except ValueError:
                raise NotANumber(
                    row=r + 1, line=lineno, column=c + 1, value=token
                ) from None

    return ParsedTable(
        values=values,
        column_names=column_names,
        header_detected=header_detected,
        source_lines=[lineno for lineno, _ in rows],
    )
