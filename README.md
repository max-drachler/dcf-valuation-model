# DCF Valuation Model

A discounted cash flow model in Python. It projects unlevered free cash flow, discounts it at WACC, and calculates enterprise value, equity value and implied share price using both terminal value methods. All inputs live in one JSON file, so the same model can value any company.

## What it does

1. **Builds the FCF projection.** Revenue, EBITDA, D&A, EBIT, NOPAT, CapEx and change in net working capital for each projection year.
2. **Calculates WACC.** Cost of equity from CAPM, after-tax cost of debt, market value weights.
3. **Values the company two ways.**
   - Perpetuity growth (Gordon growth) terminal value
   - Exit multiple (EV / EBITDA) terminal value
4. **Cross-checks the methods.** Shows the exit multiple implied by the perpetuity method and the growth rate implied by the exit multiple method. If these look unreasonable, the assumptions need another look.
5. **Runs sensitivity tables.** Share price across a range of WACC vs terminal growth, and WACC vs exit multiple.

Uses the mid-year convention for discounting cash flows (cash arrives through the year, not all on December 31). Terminal value is discounted from the end of the final year.

## Example output

The example values a hypothetical mid-cap industrial technology company. The inputs are illustrative, not a real company.

| | Perpetuity Growth | Exit Multiple |
|---|---|---|
| PV of FCF ($mm) | 2,328 | 2,328 |
| PV of Terminal Value ($mm) | 6,664 | 7,784 |
| Enterprise Value ($mm) | 8,992 | 10,112 |
| Equity Value ($mm) | 7,192 | 8,312 |
| **Implied Share Price** | **$47.95** | **$55.42** |
| Terminal value % of EV | 74.1% | 77.0% |
| Cross-check | 10.3x implied exit multiple | 3.4% implied growth |

WACC is 9.15% (cost of equity 10.35% from CAPM, 5.5% pre-tax cost of debt).

~~~mermaid
xychart-beta
    title "EBITDA (light) and Unlevered FCF (dark), $mm"
    x-axis ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
    y-axis "$mm" 0 --> 1100
    bar [763, 826, 885, 948, 1005]
    bar [496, 539, 583, 626, 670]
~~~

**Share price sensitivity: WACC vs terminal growth (perpetuity method)**

| WACC | 1.5% | 2.0% | 2.5% | 3.0% | 3.5% |
|---|---|---|---|---|---|
| 8.15% | $49.94 | $53.93 | $58.63 | $64.24 | $71.06 |
| 8.65% | $45.56 | $48.93 | $52.85 | $57.46 | $62.97 |
| **9.15%** | $41.76 | $44.64 | **$47.95** | $51.79 | $56.32 |
| 9.65% | $38.43 | $40.91 | $43.73 | $46.98 | $50.76 |
| 10.15% | $35.49 | $37.64 | $40.07 | $42.84 | $46.03 |

**Share price sensitivity: WACC vs exit multiple**

| WACC | 10.0x | 11.0x | 12.0x | 13.0x | 14.0x |
|---|---|---|---|---|---|
| 8.15% | $49.16 | $53.69 | $58.22 | $62.75 | $67.27 |
| 8.65% | $47.95 | $52.37 | $56.80 | $61.22 | $65.65 |
| **9.15%** | $46.77 | $51.09 | **$55.42** | $59.74 | $64.06 |
| 9.65% | $45.61 | $49.84 | $54.07 | $58.30 | $62.52 |
| 10.15% | $44.49 | $48.63 | $52.76 | $56.89 | $61.02 |

**Takeaway:** The two methods differ by about $7 per share because a 12.0x exit multiple implies 3.4% perpetual growth, which is aggressive against a 2.5% base case. Terminal value is roughly three quarters of enterprise value, which is typical, and is why the sensitivity tables matter more than any single point estimate.

## How to run

~~~bash
pip install -r requirements.txt
python run.py                  # runs the example in assumptions.json
python run.py my_company.json  # runs your own inputs
pytest                         # runs the tests
~~~

To value a real company, copy `assumptions.json` and fill it in from the latest 10-K (revenue, margins, D&A, CapEx, working capital, debt, cash, share count) and market data (beta, share price, Treasury yield).

## Files

| File | Purpose |
|---|---|
| `dcf.py` | Model logic: FCF projection, WACC, terminal value, valuation, sensitivity |
| `run.py` | Runs the model, prints results, saves CSVs and charts to `output/` |
| `assumptions.json` | All model inputs |
| `tests/test_dcf.py` | Checks WACC, FCF and equity bridge against hand calculations |

## Key formulas

- Unlevered FCF = EBIT x (1 - tax rate) + D&A - CapEx - change in NWC
- Cost of equity = risk-free rate + beta x equity risk premium
- WACC = E/(D+E) x cost of equity + D/(D+E) x cost of debt x (1 - tax rate)
- Terminal value (perpetuity) = final year FCF x (1 + g) / (WACC - g)
- Terminal value (exit multiple) = final year EBITDA x exit multiple
- Equity value = enterprise value - debt + cash
