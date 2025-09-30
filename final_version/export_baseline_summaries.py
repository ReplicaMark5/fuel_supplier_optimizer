#!/usr/bin/env python3
"""
Export baseline (cost-only) supplier utilization and capacity summary tables
for the thesis Results section.

Outputs (in chapters_copy/ by default):
  - supplier_utilization_baseline.csv
  - capacity_summary_baseline.csv
  - supplier_utilization_rows.tex (LaTeX table rows)
  - capacity_summary_rows.tex (LaTeX table rows)

Run:
  python final_version/export_baseline_summaries.py
"""

import csv
import os
from pathlib import Path
from typing import Dict, Any

from precomputation import FuelOptimizationPrecomputation
from fuel_optimizer_docplex import FuelDepotOptimizerDocplex


def _format_int(n: float) -> str:
    try:
        return f"{int(round(n)):,}"
    except Exception:
        return str(n)


def _format_currency(n: float) -> str:
    try:
        return f"{n:,.2f}"
    except Exception:
        return str(n)


def run_baseline() -> Dict[str, Any]:
    # Resolve paths relative to this file to avoid CWD issues
    here = Path(__file__).resolve().parent
    config_path = str(here / "optimization_config.json")
    db_path = str(here / "fuel_data.db")

    precomp = FuelOptimizationPrecomputation(config_path=config_path, db_path=db_path)
    precomputed = precomp.run_complete_precomputation()
    optimizer = FuelDepotOptimizerDocplex(precomputed, config_path=config_path, db_path=db_path)
    results = optimizer.run_optimization()  # cost_only by default
    if results.get("status") != "optimal":
        raise RuntimeError(f"Optimization status: {results.get('status')}")
    return results


def export_supplier_utilization(results: Dict[str, Any], out_dir: Path) -> None:
    # Aggregate by supplier
    supplier_stats: Dict[str, Dict[str, float]] = {}
    for alloc in results.get("allocations", []):
        sname = alloc.get("supplier_name", "Unknown")
        d = supplier_stats.setdefault(
            sname,
            {"count": 0, "total_volume": 0.0, "total_cost": 0.0},
        )
        d["count"] += 1
        d["total_volume"] += float(alloc.get("annual_volume", 0) or 0)
        d["total_cost"] += float(alloc.get("total_cost", 0) or 0)

    rows = []
    for sname in sorted(supplier_stats.keys()):
        d = supplier_stats[sname]
        avg_cost_per_litre = (d["total_cost"] / d["total_volume"]) if d["total_volume"] else 0.0
        rows.append(
            {
                "Supplier": sname,
                "Allocations": int(d["count"]),
                "Total Volume (L)": int(round(d["total_volume"])) ,
                "Total Cost (R)": round(d["total_cost"], 2),
                "Avg Cost/L (R)": round(avg_cost_per_litre, 4),
            }
        )

    out_csv = out_dir / "supplier_utilization_baseline.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "Supplier",
                "Allocations",
                "Total Volume (L)",
                "Total Cost (R)",
                "Avg Cost/L (R)",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # LaTeX rows
    out_tex = out_dir / "supplier_utilization_rows.tex"
    with out_tex.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(
                f"{r['Supplier']} & {r['Allocations']} & {_format_int(r['Total Volume (L)'])} & {_format_currency(r['Total Cost (R)'])} & {r['Avg Cost/L (R)']:.4f} \\\n"
            )


def export_capacity_summary(results: Dict[str, Any], out_dir: Path) -> None:
    util = results.get("supplier_depot_utilization", {}) or {}

    # Build list: show binding first, then near-capacity; otherwise top 10 by utilisation
    binding = results.get("binding_capacity_constraints", []) or []
    near = results.get("near_capacity_constraints", []) or []

    def _mk_row(e: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Supplier Depot (ID)": str(e.get("supplier_depot_id")),
            "Supplier": e.get("supplier_name", ""),
            "Used Volume (L)": int(round(float(e.get("used_volume", 0) or 0))),
            "Capacity Limit (L)": int(round(float(e.get("capacity_limit", 0) or 0))),
            "Utilisation (%)": float(e.get("utilization_pct", 0) or 0),
        }

    rows = []
    rows.extend([_mk_row(e) for e in binding])
    rows.extend([_mk_row(e) for e in near])

    if not rows:
        # Fallback: top 10 utilised depots with a capacity limit
        items = [
            (k, v)
            for k, v in util.items()
            if (v.get("capacity_limit", 0) or 0) > 0
        ]
        items.sort(key=lambda kv: kv[1].get("utilization_pct", 0), reverse=True)
        for k, v in items[:10]:
            rows.append(
                {
                    "Supplier Depot (ID)": str(k),
                    "Supplier": v.get("supplier_name", ""),
                    "Used Volume (L)": int(round(float(v.get("used_volume", 0) or 0))),
                    "Capacity Limit (L)": int(round(float(v.get("capacity_limit", 0) or 0))),
                    "Utilisation (%)": float(v.get("utilization_pct", 0) or 0),
                }
            )

    out_csv = out_dir / "capacity_summary_baseline.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "Supplier Depot (ID)",
                "Supplier",
                "Used Volume (L)",
                "Capacity Limit (L)",
                "Utilisation (%)",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    out_tex = out_dir / "capacity_summary_rows.tex"
    with out_tex.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(
                f"{r['Supplier Depot (ID)']} ({r['Supplier']}) & {_format_int(r['Used Volume (L)'])} & {_format_int(r['Capacity Limit (L)'])} & {r['Utilisation (%)']:.1f} \\\n"
            )


def main():
    out_dir = Path("final_version/chapters_copy").resolve()
    os.makedirs(out_dir, exist_ok=True)
    results = run_baseline()
    export_supplier_utilization(results, out_dir)
    export_capacity_summary(results, out_dir)
    print("Wrote:")
    print(" -", out_dir / "supplier_utilization_baseline.csv")
    print(" -", out_dir / "capacity_summary_baseline.csv")
    print(" -", out_dir / "supplier_utilization_rows.tex")
    print(" -", out_dir / "capacity_summary_rows.tex")


if __name__ == "__main__":
    main()
