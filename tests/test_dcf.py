import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dcf  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def a():
    return dcf.Assumptions.from_json(ROOT / "assumptions.json")


def test_wacc_matches_hand_calculation(a):
    re = 0.043 + 1.10 * 0.055
    kd = 0.055 * (1 - 0.23)
    expected = (9000 / 11200) * re + (2200 / 11200) * kd
    assert dcf.wacc(a) == pytest.approx(expected)


def test_first_year_fcf(a):
    fcf = dcf.project_fcf(a)
    rev = 3000 * 1.06
    ebitda = rev * 0.24
    da = rev * 0.03
    nopat = (ebitda - da) * 0.77
    capex = rev * 0.03
    change_nwc = rev * 0.10 - 300
    assert fcf.loc[1, "Unlevered FCF"] == pytest.approx(nopat + da - capex - change_nwc)


def test_equity_bridge(a):
    res = dcf.value(a)["Perpetuity Growth"]
    assert res["Equity Value"] == pytest.approx(res["Enterprise Value"] - 2200 + 400)
    assert res["Share Price"] == pytest.approx(res["Equity Value"] / 150)


def test_implied_metrics_round_trip(a):
    """Plugging the implied growth back in should reproduce the exit multiple value."""
    res = dcf.value(a)
    g = res["Exit Multiple"]["Implied Perpetuity Growth"]
    round_trip = dcf.value(a, g=g)["Perpetuity Growth"]["Enterprise Value"]
    assert round_trip == pytest.approx(res["Exit Multiple"]["Enterprise Value"])


def test_higher_wacc_lowers_price(a):
    low = dcf.value(a, rate=0.08)["Perpetuity Growth"]["Share Price"]
    high = dcf.value(a, rate=0.10)["Perpetuity Growth"]["Share Price"]
    assert high < low


def test_wacc_below_growth_raises(a):
    with pytest.raises(ValueError):
        dcf.value(a, rate=0.02, g=0.03)
