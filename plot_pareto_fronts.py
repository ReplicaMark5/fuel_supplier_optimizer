#!/usr/bin/env python3
"""Plot combined Pareto fronts for NSGA-II and ε-constraint results.

Reads the curated CSV exports, filters to the non-dominated points for each
method, and saves a comparison plot as a PNG for thesis figures.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot Pareto-front comparison")
    parser.add_argument(
        "--nsga",
        type=Path,
        default=Path("Output Data/nsga_front_20250925T194546Z.csv"),
        help="Path to NSGA-II front CSV",
    )
    parser.add_argument(
        "--econ",
        type=Path,
        default=Path("Output Data/econstraint_front_20250925T194546Z.csv"),
        help="Path to ε-constraint front CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("Output Data/pareto_front_comparison.png"),
        help="Output path for the PNG figure",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Dots-per-inch for the saved figure",
    )
    parser.add_argument(
        "--cost-scale",
        type=float,
        default=1e9,
        help="Value used to scale costs for readability (e.g. 1e9 -> billions)",
    )
    parser.add_argument(
        "--score-scale",
        type=float,
        default=1.0,
        help="Value used to scale scores if desired",
    )
    return parser.parse_args()


def load_and_filter(path: Path, method_label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Could not find data file: {path}")

    df = pd.read_csv(path)
    if "cost" not in df.columns or "score" not in df.columns:
        missing = {"cost", "score"} - set(df.columns)
        raise ValueError(f"File {path} missing required column(s): {missing}")

    pareto_df = pareto_filter(df[["cost", "score"]]).copy()
    pareto_df["method"] = method_label
    pareto_df.sort_values("cost", inplace=True)
    pareto_df.reset_index(drop=True, inplace=True)
    return pareto_df


def pareto_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Return non-dominated rows assuming cost is minimised and score maximised."""
    data = df.to_numpy(dtype=float)
    n_points = data.shape[0]
    is_pareto = np.ones(n_points, dtype=bool)
    eps = 1e-6

    for i in range(n_points):
        if not is_pareto[i]:
            continue
        cost_i, score_i = data[i]
        dominated = (
            (data[:, 0] <= cost_i + eps)
            & (data[:, 1] >= score_i - eps)
            & ((data[:, 0] < cost_i - eps) | (data[:, 1] > score_i + eps))
        )
        dominated[i] = False
        is_pareto[dominated] = False

    return df[is_pareto]


def main() -> None:
    args = parse_args()

    nsga_df = load_and_filter(args.nsga, "NSGA-II")
    econ_df = load_and_filter(args.econ, "ε-Constraint")

    # Apply scaling for readability (e.g. billions of currency units)
    cost_scale = args.cost_scale
    score_scale = args.score_scale

    nsga_cost = nsga_df["cost"] / cost_scale
    nsga_score = nsga_df["score"] / score_scale
    econ_cost = econ_df["cost"] / cost_scale
    econ_score = econ_df["score"] / score_scale

    plt.figure(figsize=(7.5, 5.0))
    plt.plot(
        nsga_cost,
        nsga_score,
        marker="s",
        linestyle="-",
        linewidth=1.0,
        markersize=3.0,
        label="NSGA-II",
        color="#d62728",
    )
    plt.plot(
        econ_cost,
        econ_score,
        marker="o",
        linestyle="-",
        linewidth=1.0,
        markersize=3.0,
        label="ε-Constraint",
        color="#1f77b4",
    )

    plt.xlabel("Total Cost (billions)")
    plt.ylabel("Supplier Score")
    plt.title("Pareto Front Comparison: NSGA-II vs ε-Constraint")
    plt.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
    plt.legend()
    plt.tight_layout()

    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=args.dpi)
    plt.close()
    print(f"Saved Pareto comparison plot to {output_path}")


if __name__ == "__main__":
    main()
