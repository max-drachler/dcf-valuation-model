"""
Discounted cash flow (DCF) valuation model.

Projects unlevered free cash flow, discounts it at the weighted average
cost of capital (WACC), and calculates enterprise value, equity value and
implied share price using both the perpetuity growth and exit multiple
methods for terminal value.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class Assumptions:
    company: str
    base_revenue: float                 # last fiscal year revenue ($mm)
    revenue_growth: list[float]         # one growth rate per projection year
    ebitda_margin: list[float]          # one margin per projection year
    da_pct_revenue: float               # depreciation & amortization as % of revenue
    capex_pct_revenue: float            # capital expenditures as % of revenue
    nwc_pct_revenue: float              # net working capital as % of revenue
    base_nwc: float                     # last fiscal year net working capital ($mm)
    tax_rate: float
    # WACC inputs
    risk_free_rate: float
    equity_risk_premium: float
    beta: float
    pre_tax_cost_of_debt: float
    market_cap: float                   # current equity value ($mm)
    total_debt: float                   # ($mm)
    cash: float                         # ($mm)
    shares_outstanding: float           # (mm)
    # Terminal value
    terminal_growth: float
    exit_multiple: float                # EV / EBITDA
    mid_year_convention: bool = True
    years: int = field(init=False)

    def __post_init__(self) -> None:
        if len(self.revenue_growth) != len(self.ebitda_margin):
            raise ValueError("revenue_growth and ebitda_margin must be the same length")
        self.years = len(self.revenue_growth)

    @classmethod
    def from_json(cls, path: str | Path) -> "Assumptions":
        with open(path) as f:
            return cls(**json.load(f))


def cost_of_equity(a: Assumptions) -> float:
    """CAPM: Re = Rf + Beta x ERP."""
    return a.risk_free_rate + a.beta * a.equity_risk_premium


def wacc(a: Assumptions) -> float:
    """Weighted average cost of capital using market value weights."""
    e, d = a.market_cap, a.total_debt
    after_tax_kd = a.pre_tax_cost_of_debt * (1 - a.tax_rate)
    return (e / (e + d)) * cost_of_equity(a) + (d / (e + d)) * after_tax_kd


def project_fcf(a: Assumptions) -> pd.DataFrame:
    """Build the unlevered free cash flow projection."""
    rows = []
    revenue, prior_nwc = a.base_revenue, a.base_nwc
    for i in range(a.years):
        revenue *= 1 + a.revenue_growth[i]
        ebitda = revenue * a.ebitda_margin[i]
        da = revenue * a.da_pct_revenue
        ebit = ebitda - da
        nopat = ebit * (1 - a.tax_rate)
        capex = revenue * a.capex_pct_revenue
        nwc = revenue * a.nwc_pct_revenue
        change_nwc = nwc - prior_nwc
        prior_nwc = nwc
        ufcf = nopat + da - capex - change_nwc
        rows.append({
            "Year": i + 1,
            "Revenue": revenue,
            "EBITDA": ebitda,
            "D&A": da,
            "EBIT": ebit,
            "NOPAT": nopat,
            "CapEx": capex,
            "Change in NWC": change_nwc,
            "Unlevered FCF": ufcf,
        })
    return pd.DataFrame(rows).set_index("Year")


def discount_factors(a: Assumptions, rate: float) -> pd.Series:
    periods = pd.Series(range(1, a.years + 1), index=range(1, a.years + 1), dtype=float)
    if a.mid_year_convention:
        periods -= 0.5
    return 1 / (1 + rate) ** periods


def value(a: Assumptions, rate: float | None = None, g: float | None = None,
          multiple: float | None = None) -> dict:
    """Run the full valuation. Optional overrides make sensitivity tables easy."""
    rate = wacc(a) if rate is None else rate
    g = a.terminal_growth if g is None else g
    multiple = a.exit_multiple if multiple is None else multiple
    if rate <= g:
        raise ValueError("WACC must be greater than terminal growth")

    fcf = project_fcf(a)
    df = discount_factors(a, rate)
    pv_fcf = (fcf["Unlevered FCF"] * df).sum()

    # Terminal value is discounted from the end of the final year
    final_df = 1 / (1 + rate) ** a.years
    final_fcf = fcf["Unlevered FCF"].iloc[-1]
    final_ebitda = fcf["EBITDA"].iloc[-1]

    tv_perpetuity = final_fcf * (1 + g) / (rate - g)
    tv_multiple = final_ebitda * multiple

    results = {}
    for method, tv in (("Perpetuity Growth", tv_perpetuity), ("Exit Multiple", tv_multiple)):
        pv_tv = tv * final_df
        ev = pv_fcf + pv_tv
        equity = ev - a.total_debt + a.cash
        results[method] = {
            "PV of FCF": pv_fcf,
            "Terminal Value": tv,
            "PV of Terminal Value": pv_tv,
            "Enterprise Value": ev,
            "Equity Value": equity,
            "Share Price": equity / a.shares_outstanding,
            "TV % of EV": pv_tv / ev,
        }
    # Cross-checks: what each terminal value implies about the other method
    results["Perpetuity Growth"]["Implied Exit Multiple"] = tv_perpetuity / final_ebitda
    results["Exit Multiple"]["Implied Perpetuity Growth"] = (
        (tv_multiple * rate - final_fcf) / (tv_multiple + final_fcf)
    )
    return results


def sensitivity(a: Assumptions, method: str, rates: list[float], second_axis: list[float]) -> pd.DataFrame:
    """Share price sensitivity: WACC (rows) vs terminal growth or exit multiple (columns)."""
    table = {}
    for x in second_axis:
        col = []
        for r in rates:
            kwargs = {"rate": r}
            if method == "Perpetuity Growth":
                kwargs["g"] = x
            else:
                kwargs["multiple"] = x
            col.append(value(a, **kwargs)[method]["Share Price"])
        table[x] = col
    return pd.DataFrame(table, index=rates)
