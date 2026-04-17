#!/usr/bin/env python3

import argparse
from pathlib import Path
from typing import Tuple, Optional

import matplotlib.pyplot as plt
import pandas as pd


POLICY_ORDER = ["unrestricted_smt", "constrained_smt", "no_smt"]
POLICY_LABELS = {
    "unrestricted_smt": "Unrestricted SMT",
    "constrained_smt": "Constrained SMT",
    "no_smt": "No SMT",
}


def load_results(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    required = {"pair_name", "policy", "throughput_inst_per_simsec"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    df = df[df["policy"].isin(POLICY_ORDER)].copy()
    if df.empty:
        raise ValueError("No usable rows found in CSV after filtering policies.")

    df["throughput_inst_per_simsec"] = pd.to_numeric(
        df["throughput_inst_per_simsec"], errors="coerce"
    )
    df = df.dropna(subset=["throughput_inst_per_simsec"])

    if df.empty:
        raise ValueError("No valid throughput values found in CSV.")

    return df


def compute_ylim(values, zoom: bool) -> Tuple[Optional[float], Optional[float]]:
    clean = [float(v) for v in values if pd.notna(v)]
    if not clean:
        return None, None

    y_min = min(clean)
    y_max = max(clean)

    if y_min == y_max:
        margin = max(abs(y_max) * 0.05, 1.0)
        return y_min - margin, y_max + margin

    if zoom:
        margin = 0.08 * (y_max - y_min)
        lower = max(0.0, y_min - margin)
        upper = y_max + margin
    else:
        upper = y_max * 1.08
        lower = 0.0

    return lower, upper


def annotate_bars(ax, bars, values, units: str) -> None:
    for bar, value in zip(bars, values):
        if pd.isna(value):
            continue

        if units == "M":
            label = f"{value / 1e6:.1f}M"
        elif units == "ratio":
            label = f"{value:.2f}x"
        else:
            label = f"{value:.2f}"

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            label,
            ha="center",
            va="bottom",
            fontsize=9,
        )


def build_plot(
    df: pd.DataFrame,
    title: str,
    output_path: Path,
    zoom_yaxis: bool,
) -> None:
    pair_order = list(df["pair_name"].drop_duplicates())

    pivot = (
        df.pivot(index="pair_name", columns="policy", values="throughput_inst_per_simsec")
        .reindex(index=pair_order, columns=POLICY_ORDER)
    )

    x = list(range(len(pair_order)))
    width = 0.24

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, policy in enumerate(POLICY_ORDER):
        offsets = [xi + (i - 1) * width for xi in x]
        values = pivot[policy].tolist()
        bars = ax.bar(offsets, values, width=width, label=POLICY_LABELS[policy])
        annotate_bars(ax, bars, values, units="M")

    lower, upper = compute_ylim(pivot.values.flatten(), zoom=zoom_yaxis)
    if lower is not None and upper is not None:
        ax.set_ylim(lower, upper)

    ax.set_title(title)
    ax.set_xlabel("Workload Pair")
    ax.set_ylabel("Throughput (inst/simsec)")
    ax.set_xticks(x)
    ax.set_xticklabels(pair_order)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot grouped throughput bars from a phase1 results CSV."
    )
    parser.add_argument("--input-csv", required=True, help="Path to input CSV")
    parser.add_argument("--output-png", required=True, help="Path to output PNG")
    parser.add_argument(
        "--title",
        default="SMT Policy Throughput Comparison",
        help="Plot title",
    )
    parser.add_argument(
        "--no-zoom-yaxis",
        action="store_true",
        help="Start y-axis at zero instead of zooming to the data range.",
    )
    args = parser.parse_args()

    csv_path = Path(args.input_csv).resolve()
    output_path = Path(args.output_png).resolve()

    df = load_results(csv_path)
    build_plot(
        df=df,
        title=args.title,
        output_path=output_path,
        zoom_yaxis=not args.no_zoom_yaxis,
    )

    print(f"Wrote plot to {output_path}")


if __name__ == "__main__":
    main()