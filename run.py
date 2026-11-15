"""
Run the DCF on an assumptions file and save the outputs.

Usage:
    python run.py                      # uses assumptions.json
    python run.py my_company.json      # uses your own inputs
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import dcf

OUT = Path(__file__).parent / "output"


def money(x: float) -> str:
    return f"${x:,.0f}"


def main(path: str = "assumptions.json") -> None:
    a = dcf.Assumptions.from_json(path)
    OUT.mkdir(exist_ok=True)

    fcf = dcf.project_fcf(a)
    results = dcf.value(a)
    r = dcf.wacc(a)

    print(f"\nDCF Valuation: {a.company}  ($ in millions, except per share)\n")
    print(f"Cost of equity (CAPM): {dcf.cost_of_equity(a):.2%}")
    print(f"WACC:                  {r:.2%}\n")
    print(fcf.round(1).T.to_string())
    print()

    for method, res in results.items():
        print(method)
        for k, v in res.items():
            if "%" in k or "Growth" in k:
                print(f"  {k:<28}{v:>10.1%}")
            elif "Multiple" in k:
                print(f"  {k:<28}{v:>9.1f}x")
            elif k == "Share Price":
                print(f"  {k:<28}{'$' + format(v, ',.2f'):>10}")
            else:
                print(f"  {k:<28}{money(v):>10}")
        print()

    # Sensitivity tables
    rates = [r + d for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    growths = [0.015, 0.02, 0.025, 0.03, 0.035]
    multiples = [10.0, 11.0, 12.0, 13.0, 14.0]
    sens_g = dcf.sensitivity(a, "Perpetuity Growth", rates, growths)
    sens_m = dcf.sensitivity(a, "Exit Multiple", rates, multiples)

    for title, table, fmt in (("terminal growth", sens_g, "{:.1%}"), ("exit multiple", sens_m, "{:.1f}x")):
        t = table.copy()
        t.index = [f"{x:.2%}" for x in t.index]
        t.columns = [fmt.format(c) for c in t.columns]
        print(f"Share price sensitivity: WACC (rows) vs {title} (columns)")
        print(t.map(lambda v: f"${v:,.2f}").to_string())
        print()

    fcf.round(2).to_csv(OUT / "fcf_projection.csv")
    sens_g.round(2).to_csv(OUT / "sensitivity_perpetuity.csv")
    sens_m.round(2).to_csv(OUT / "sensitivity_exit_multiple.csv")

    # Chart 1: FCF build
    fig, ax = plt.subplots(figsize=(8, 4.5))
    years = [f"Year {i}" for i in fcf.index]
    ax.bar(years, fcf["EBITDA"], color="#9fb8d6", label="EBITDA")
    ax.bar(years, fcf["Unlevered FCF"], color="#1f4e79", label="Unlevered FCF", width=0.5)
    ax.set_title(f"{a.company}: EBITDA and Unlevered FCF ($mm)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "fcf_chart.png", dpi=150)
    plt.close(fig)

    # Chart 2: sensitivity heatmap (perpetuity growth)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    data = sens_g.values
    im = ax.imshow(data, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(growths)), [f"{g:.1%}" for g in growths])
    ax.set_yticks(range(len(rates)), [f"{x:.2%}" for x in rates])
    ax.set_xlabel("Terminal growth rate")
    ax.set_ylabel("WACC")
    ax.set_title("Implied share price sensitivity")
    mid = np.nanmean(data)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"${data[i, j]:,.0f}", ha="center", va="center",
                    color="white" if data[i, j] > mid else "black", fontsize=9)
    fig.colorbar(im, ax=ax, label="$ per share")
    fig.tight_layout()
    fig.savefig(OUT / "sensitivity_heatmap.png", dpi=150)
    plt.close(fig)

    print(f"Outputs saved to {OUT}/")


if __name__ == "__main__":
    main(*sys.argv[1:])
