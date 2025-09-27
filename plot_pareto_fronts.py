#!/usr/bin/env python3
"""Plot combined Pareto fronts for NSGA-II and ε-constraint results.

Reads the curated CSV exports, filters to the non-dominated points for each
method, and saves a comparison plot as a PNG for thesis figures.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot Pareto-front comparison")
    parser.add_argument(
        "--nsga",
        type=Path,
        default=None,
        help="Path to NSGA-II front CSV (defaults to latest nsga_front_*.csv)",
    )
    parser.add_argument(
        "--econ",
        type=Path,
        default=None,
        help="Path to ε-constraint front CSV (defaults to latest econstraint_front_*.csv)",
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


def resolve_latest(path: Optional[Path], stem: str) -> Path:
    """Return user path or most recent CSV matching stem across Output Data directories."""

    if path is not None:
        return path

    candidates: list[Path] = []
    for base in Path.cwd().glob("Output Data*"):
        if base.is_dir():
            candidates.extend(base.glob(f"{stem}_*.csv"))

    if not candidates:
        raise FileNotFoundError(
            f"Could not locate any files matching '{stem}_*.csv'. "
            "Run comparison_experiment.py first or provide explicit paths via --nsga/--econ."
        )

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def load_and_filter(path: Path, method_label: str) -> tuple[pd.DataFrame, str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Could not find data file: {path}")

    df = pd.read_csv(path)
    if "cost" not in df.columns or "score" not in df.columns:
        missing = {"cost", "score"} - set(df.columns)
        raise ValueError(f"File {path} missing required column(s): {missing}")

    cost_col = "cost_norm" if "cost_norm" in df.columns else "cost"
    score_col = "score_norm" if "score_norm" in df.columns else "score"

    selected = df[[cost_col, score_col]].rename(columns={cost_col: "cost", score_col: "score"})
    pareto_selected = pareto_filter(selected)
    pareto_df = df.loc[pareto_selected.index].copy()
    pareto_df["method"] = method_label
    pareto_df.sort_values(cost_col, inplace=True)
    pareto_df.reset_index(drop=True, inplace=True)
    return pareto_df, cost_col, score_col


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

    nsga_path = resolve_latest(args.nsga, "nsga_front")
    econ_path = resolve_latest(args.econ, "econstraint_front")

    nsga_df, nsga_cost_col, nsga_score_col = load_and_filter(nsga_path, "NSGA-II")
    econ_df, econ_cost_col, econ_score_col = load_and_filter(econ_path, "ε-Constraint")

    # Apply scaling for readability (e.g. billions of currency units)
    using_normalised = nsga_cost_col.endswith("_norm") and econ_cost_col.endswith("_norm")

    cost_scale = args.cost_scale
    if using_normalised and math.isclose(cost_scale, 1e9):
        cost_scale = 1.0
    score_scale = args.score_scale
    if using_normalised and math.isclose(score_scale, 1.0):
        score_scale = 1.0

    nsga_cost = pd.to_numeric(nsga_df[nsga_cost_col], errors="coerce") / cost_scale
    nsga_score = pd.to_numeric(nsga_df[nsga_score_col], errors="coerce") / score_scale
    econ_cost = pd.to_numeric(econ_df[econ_cost_col], errors="coerce") / cost_scale
    econ_score = pd.to_numeric(econ_df[econ_score_col], errors="coerce") / score_scale

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

    if using_normalised:
        plt.xlabel("Normalised Cost (0 = best)")
        plt.ylabel("Normalised Score (1 = best)")
        plt.title("Normalised Pareto Front (MVP comparison)")
    else:
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
