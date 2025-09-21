import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from etl_common import parse_number  # noqa: E402


def test_parse_number_locale_variants():
    cases = {
        "1.234,56": 1234.56,
        "1,234.56": 1234.56,
        "1234.56": 1234.56,
        "1.234.567,89": 1234567.89,
        "$1.234.567,89": 1234567.89,
        "1 234,56": 1234.56,
        "1\u00a0234,56": 1234.56,
        "(1.234,56)": -1234.56,
        "1.234,56-": -1234.56,
        "-1.234,56": -1234.56,
    }
    for raw, expected in cases.items():
        assert parse_number(raw) == pytest.approx(expected)


def test_parse_number_returns_zero_on_bad_input():
    assert parse_number(None) == 0.0
    assert parse_number("not-a-number") == 0.0
