"""Utilities for evaluating and comparing Pareto fronts and allocations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

ALLOCATION_TOKEN_PREFIXES = {"C": "Collection", "D": "Delivery"}


def parse_allocation_string(allocation_str: str) -> List[Dict[str, int]]:
    """Parse allocation strings like "C(1,2) D(3,1)" into structured records."""
    if not allocation_str or allocation_str.lower() in {"none", "no", "no solution"}:
        return []

    tokens = []
    for raw in allocation_str.split():
        if not raw or "(" not in raw or ")" not in raw:
            continue
        op = raw[0]
        if op not in ALLOCATION_TOKEN_PREFIXES:
            continue
        payload = raw[2:-1]
        if "," not in payload:
            continue
        depot_str, supplier_str = payload.split(",", 1)
        try:
            depot = int(depot_str)
            supplier = int(supplier_str)
        except ValueError:
            continue
        tokens.append({"operation": op, "depot": depot, "supplier": supplier})
    return tokens


def solution_operational_metrics(
    allocation_str: str,
    optimizer: Optional[object] = None,
) -> Dict[str, Optional[float]]:
    """Compute per-solution operational metrics from an allocation string."""

    tokens = parse_allocation_string(allocation_str)
    if not tokens:
        return {
            "unique_suppliers": 0,
            "unique_depots": 0,
            "total_operations": 0,
            "collection_operations": 0,
            "delivery_operations": 0,
            "collection_share": None,
            "supplier_diversity": None,
            "operations_per_depot": None,
        }

    collection_count = sum(1 for token in tokens if token["operation"] == "C")
    delivery_count = sum(1 for token in tokens if token["operation"] == "D")
    total_ops = collection_count + delivery_count
    unique_suppliers = len({token["supplier"] for token in tokens})
    unique_depots = len({token["depot"] for token in tokens})

    depot_count = getattr(optimizer, "n_depots", None)
    supplier_diversity = (
        unique_suppliers / depot_count if depot_count else None
    )
    operations_per_depot = (
        total_ops / depot_count if depot_count else None
    )
    collection_share = (
        collection_count / total_ops if total_ops else None
    )

    return {
        "unique_suppliers": unique_suppliers,
        "unique_depots": unique_depots,
        "total_operations": total_ops,
        "collection_operations": collection_count,
        "delivery_operations": delivery_count,
        "collection_share": collection_share,
        "supplier_diversity": supplier_diversity,
        "operations_per_depot": operations_per_depot,
    }


def aggregate_operational_metrics(
    df: pd.DataFrame,
    optimizer: Optional[object] = None,
) -> pd.DataFrame:
    """Add operational KPI columns to a Pareto front DataFrame."""

    if df.empty or "allocations" not in df.columns:
        return pd.DataFrame()

    records: List[Dict[str, Optional[float]]] = []
    for row in df.itertuples():
        metrics = solution_operational_metrics(getattr(row, "allocations", ""), optimizer)
        metrics["cost"] = getattr(row, "cost", np.nan)
        metrics["score"] = getattr(row, "score", np.nan)
        metrics["allocations"] = getattr(row, "allocations", "")
        records.append(metrics)

    return pd.DataFrame(records)


def summarise_operational_metrics(metrics_df: pd.DataFrame) -> Dict[str, Optional[float]]:
    """Return summary statistics for operational KPIs."""

    if metrics_df.empty:
        return {}

    summary: Dict[str, Optional[float]] = {}
    for column in [
        "unique_suppliers",
        "collection_share",
        "supplier_diversity",
        "operations_per_depot",
    ]:
        if column in metrics_df.columns:
            series = metrics_df[column].dropna()
            if not series.empty:
                summary[f"{column}_mean"] = float(series.mean())
                summary[f"{column}_std"] = float(series.std(ddof=0))
    return summary


def to_minimisation_array(df: pd.DataFrame) -> np.ndarray:
    """Convert cost-score DataFrame to a minimisation array (cost, -score)."""

    if df.empty:
        return np.empty((0, 2))

    costs = pd.to_numeric(df["cost"], errors="coerce").to_numpy()
    scores = pd.to_numeric(df["score"], errors="coerce").to_numpy()
    return np.column_stack([costs, -scores])


def normalise_points(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Min-max normalise point set, returning (normalised, mins, maxs)."""

    if points.size == 0:
        return points, np.zeros(2), np.ones(2)

    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    span = np.where(maxs > mins, maxs - mins, 1.0)
    normalised = (points - mins) / span
    return normalised, mins, maxs


def compute_normalisation_bounds(
    dataframes: Iterable[pd.DataFrame],
    cost_col: str = "cost",
    score_col: str = "score",
) -> Dict[str, float]:
    """Return shared min/max bounds for cost and score across multiple DataFrames."""

    cost_values: List[float] = []
    score_values: List[float] = []

    for df in dataframes:
        if df is None or df.empty:
            continue
        if cost_col in df.columns:
            cost_values.extend(pd.to_numeric(df[cost_col], errors="coerce").dropna().tolist())
        if score_col in df.columns:
            score_values.extend(pd.to_numeric(df[score_col], errors="coerce").dropna().tolist())

    if not cost_values or not score_values:
        return {
            "cost_min": float("nan"),
            "cost_max": float("nan"),
            "score_min": float("nan"),
            "score_max": float("nan"),
        }

    return {
        "cost_min": min(cost_values),
        "cost_max": max(cost_values),
        "score_min": min(score_values),
        "score_max": max(score_values),
    }


def apply_normalisation(
    df: pd.DataFrame,
    bounds: Dict[str, float],
    cost_col: str = "cost",
    score_col: str = "score",
    suffix: str = "_norm",
) -> pd.DataFrame:
    """Attach normalised cost/score columns using provided bounds."""

    if df.empty:
        return df

    cost_min = bounds.get("cost_min")
    cost_max = bounds.get("cost_max")
    score_min = bounds.get("score_min")
    score_max = bounds.get("score_max")

    def _normalise(series: pd.Series, lower: float, upper: float) -> pd.Series:
        span = (upper - lower) if upper is not None and lower is not None else None
        if span is None or span == 0:
            return pd.Series(np.zeros(len(series)), index=series.index)
        return (series - lower) / span

    df = df.copy()
    if cost_col in df.columns and pd.notna(cost_min) and pd.notna(cost_max):
        df[f"{cost_col}{suffix}"] = _normalise(pd.to_numeric(df[cost_col], errors="coerce"), cost_min, cost_max)
    if score_col in df.columns and pd.notna(score_min) and pd.notna(score_max):
        df[f"{score_col}{suffix}"] = _normalise(pd.to_numeric(df[score_col], errors="coerce"), score_min, score_max)
    return df


def hypervolume_2d(points: np.ndarray, reference: np.ndarray) -> float:
    """Compute 2D hypervolume for minimisation objectives."""

    if points.size == 0:
        return 0.0

    sorted_points = points[np.argsort(points[:, 0])[::-1]]  # sort descending by first objective
    hv = 0.0
    prev_f1 = reference[0]
    min_f2 = reference[1]

    for f1, f2 in sorted_points:
        width = max(0.0, prev_f1 - f1)
        min_f2 = min(min_f2, f2)
        height = max(0.0, reference[1] - min_f2)
        hv += width * height
        prev_f1 = f1
    return hv


def filter_nondominated(points: np.ndarray) -> np.ndarray:
    """Return nondominated subset for minimisation objectives."""

    if points.size == 0:
        return points

    mask = np.ones(len(points), dtype=bool)
    for i, p in enumerate(points):
        if not mask[i]:
            continue
        for j, q in enumerate(points):
            if i == j or not mask[j]:
                continue
            if dominates_minimisation(q, p):
                mask[i] = False
                break
    return points[mask]


def dominates_minimisation(a: np.ndarray, b: np.ndarray) -> bool:
    """Return True if a dominates b in minimisation space."""

    return np.all(a <= b) and np.any(a < b)


def inverted_generational_distance(
    approximate: np.ndarray,
    reference: np.ndarray,
) -> Optional[float]:
    """Compute IGD between approximate and reference fronts (minimisation space)."""

    if approximate.size == 0 or reference.size == 0:
        return None

    distances = cdist(reference, approximate)
    min_dist = distances.min(axis=1)
    return float(min_dist.mean())


def spacing(points: np.ndarray) -> Optional[float]:
    """Spacing metric based on nearest-neighbour distances (normalized minimisation space)."""

    if len(points) < 2:
        return None

    distance_matrix = cdist(points, points)
    np.fill_diagonal(distance_matrix, np.inf)
    nearest = distance_matrix.min(axis=1)
    return float(nearest.std(ddof=0))


def dominance_coverage(cost_score_a: np.ndarray, cost_score_b: np.ndarray) -> Optional[float]:
    """Fraction of solutions in B dominated by at least one solution in A."""

    if len(cost_score_b) == 0:
        return None

    dominated = 0
    for b in cost_score_b:
        if any(dominates_cost_score(a, b) for a in cost_score_a):
            dominated += 1
    return dominated / len(cost_score_b)


def dominates_cost_score(a: np.ndarray, b: np.ndarray) -> bool:
    """Dominance check in mixed orientation (cost min, score max)."""

    return (a[0] <= b[0] and a[1] >= b[1]) and (a[0] < b[0] or a[1] > b[1])


def build_reference_point(points: np.ndarray, margin: float = 0.1) -> np.ndarray:
    """Construct a dominated reference point for minimisation hypervolume."""

    if points.size == 0:
        return np.array([1.0, 1.0])

    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    span = np.maximum(maxs - mins, 1e-9)
    return maxs + margin * span


def compare_fronts(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    method_a: str = "Method A",
    method_b: str = "Method B",
) -> Dict[str, Dict[str, Optional[float]]]:
    """Compute Pareto quality metrics for two fronts."""

    points_a = to_minimisation_array(df_a)
    points_b = to_minimisation_array(df_b)
    combined = (
        np.vstack([points_a, points_b])
        if combined_size(points_a, points_b)
        else np.empty((0, 2))
    )

    reference_front = filter_nondominated(combined) if combined.size else np.empty((0, 2))

    if combined.size:
        _, mins, maxs = normalise_points(combined)
        denom = np.where((maxs - mins) > 0, (maxs - mins), 1.0)
        normalised_reference = (
            (reference_front - mins) / denom if reference_front.size else np.empty((0, 2))
        )
    else:
        mins = np.zeros(2)
        denom = np.ones(2)
        normalised_reference = np.empty((0, 2))

    ref_point = build_reference_point(combined)

    def method_metrics(points: np.ndarray, label: str) -> Dict[str, Optional[float]]:
        if points.size == 0:
            return {"hypervolume": 0.0, "igd": None, "spacing": None, "points": 0}

        normalised = (points - mins) / denom if points.size else points

        return {
            "label": label,
            "points": int(len(points)),
            "hypervolume": float(hypervolume_2d(points, ref_point)),
            "igd": inverted_generational_distance(normalised, normalised_reference)
            if normalised_reference.size
            else None,
            "spacing": spacing(normalised),
        }

    metrics_a = method_metrics(points_a, method_a)
    metrics_b = method_metrics(points_b, method_b)

    cost_score_a = df_a[["cost", "score"]].to_numpy() if not df_a.empty else np.empty((0, 2))
    cost_score_b = df_b[["cost", "score"]].to_numpy() if not df_b.empty else np.empty((0, 2))

    pairwise = {
        "coverage_a_dom_b": dominance_coverage(cost_score_a, cost_score_b),
        "coverage_b_dom_a": dominance_coverage(cost_score_b, cost_score_a),
    }

    return {"methods": {method_a: metrics_a, method_b: metrics_b}, "pairwise": pairwise}


def combined_size(points_a: np.ndarray, points_b: np.ndarray) -> int:
    return points_a.size + points_b.size


__all__ = [
    "aggregate_operational_metrics",
    "compare_fronts",
    "parse_allocation_string",
    "solution_operational_metrics",
    "summarise_operational_metrics",
]
