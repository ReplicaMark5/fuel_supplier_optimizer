#!/usr/bin/env python3
"""
Baseline Cost-Only Optimization Script for Thesis

This script runs the single-objective cost minimization optimization and generates
all required outputs for the thesis baseline results section.

Outputs:
  - Baseline optimization results (cost, allocations)
  - Supplier utilization summary (CSV + LaTeX)
  - Capacity summary (CSV + LaTeX)
  - Interactive HTML map of optimized allocations
  - Comprehensive JSON results

Run from project root:
  python scripts/thesis/run_baseline_optimization.py
"""

import sys
import json
import csv
from pathlib import Path
from typing import Dict, Any
import logging

# Add parent to path to enable src imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.precomputation import FuelOptimizationPrecomputation
from src.fuel_optimizer_docplex import FuelDepotOptimizerDocplex
from src.visualization.optimization_map import OptimizationMapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _format_int(n: float) -> str:
    """Format number as integer with thousand separators."""
    try:
        return f"{int(round(n)):,}"
    except Exception:
        return str(n)


def _format_currency(n: float) -> str:
    """Format number as currency with 2 decimal places."""
    try:
        return f"{n:,.2f}"
    except Exception:
        return str(n)


def run_baseline_optimization(config_path: str, db_path: str) -> Dict[str, Any]:
    """
    Run cost-only optimization.

    Args:
        config_path: Path to optimization_config.json
        db_path: Path to fuel_data.db

    Returns:
        Dictionary containing optimization results
    """
    logger.info("=" * 80)
    logger.info("BASELINE COST-ONLY OPTIMIZATION")
    logger.info("=" * 80)

    # Run precomputation
    logger.info("\n1. Running precomputation...")
    precomp = FuelOptimizationPrecomputation(config_path=config_path, db_path=db_path)
    precomputed = precomp.run_complete_precomputation()
    logger.info(f"   ✓ Precomputed {len(precomputed['costs'])} depot cost options")

    # Run optimization (cost_only mode is default)
    logger.info("\n2. Running cost minimization optimization...")
    optimizer = FuelDepotOptimizerDocplex(
        precomputed,
        config_path=config_path,
        db_path=db_path
    )
    results = optimizer.run_optimization()

    if results.get("status") != "optimal":
        raise RuntimeError(f"Optimization failed with status: {results.get('status')}")

    logger.info(f"   ✓ Optimization complete - Status: {results['status']}")
    logger.info(f"   ✓ Total Annual Cost: R {results['total_annual_cost']:,.2f}")
    logger.info(f"   ✓ Allocations: {len(results['allocations'])}")

    return results, precomputed


def export_supplier_utilization(results: Dict[str, Any], out_dir: Path) -> None:
    """Export supplier utilization summary tables."""
    logger.info("\n3. Exporting supplier utilization summaries...")

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
                "Total Volume (L)": int(round(d["total_volume"])),
                "Total Cost (R)": round(d["total_cost"], 2),
                "Avg Cost/L (R)": round(avg_cost_per_litre, 4),
            }
        )

    # Export CSV
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
    logger.info(f"   ✓ CSV: {out_csv}")

    # Export LaTeX rows
    out_tex = out_dir / "supplier_utilization_rows.tex"
    with out_tex.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(
                f"{r['Supplier']} & {r['Allocations']} & {_format_int(r['Total Volume (L)'])} & "
                f"{_format_currency(r['Total Cost (R)'])} & {r['Avg Cost/L (R)']:.4f} \\\\\n"
            )
    logger.info(f"   ✓ LaTeX: {out_tex}")


def export_capacity_summary(results: Dict[str, Any], out_dir: Path) -> None:
    """Export capacity utilization summary tables."""
    logger.info("\n4. Exporting capacity summary...")

    util = results.get("supplier_depot_utilization", {}) or {}
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
        # Fallback: top 10 utilised depots
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

    # Export CSV
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
    logger.info(f"   ✓ CSV: {out_csv}")

    # Export LaTeX rows
    out_tex = out_dir / "capacity_summary_rows.tex"
    with out_tex.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(
                f"{r['Supplier Depot (ID)']} ({r['Supplier']}) & {_format_int(r['Used Volume (L)'])} & "
                f"{_format_int(r['Capacity Limit (L)'])} & {r['Utilisation (%)']:.1f} \\\\\n"
            )
    logger.info(f"   ✓ LaTeX: {out_tex}")


def create_optimization_map(results: Dict[str, Any], precomputed: Dict[str, Any], out_dir: Path) -> None:
    """Create interactive HTML map of optimization results."""
    logger.info("\n5. Creating optimization map...")

    # Prepare comprehensive data for mapper
    comprehensive_data = {
        'optimization_results': results,
        'all_route_costs': precomputed,  # Contains costs, depots, suppliers
        'capacity_limits': precomputed.get('capacity_limits', {}),
        'optimization_metadata': {
            'objective_mode': 'cost_only',
            'total_cost': results['total_annual_cost'],
            'num_allocations': len(results['allocations'])
        }
    }

    # Create map
    mapper = OptimizationMapper()
    map_path = out_dir / "baseline_optimization_map.html"
    mapper.create_enhanced_allocation_map(comprehensive_data, save_path=str(map_path))

    logger.info(f"   ✓ Interactive map: {map_path}")


def export_comprehensive_json(results: Dict[str, Any], out_dir: Path) -> None:
    """Export comprehensive results as JSON."""
    logger.info("\n6. Exporting comprehensive JSON results...")

    json_path = out_dir / "baseline_results_complete.json"
    with json_path.open("w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"   ✓ JSON: {json_path}")


def print_summary(results: Dict[str, Any]) -> None:
    """Print optimization summary."""
    logger.info("\n" + "=" * 80)
    logger.info("BASELINE OPTIMIZATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Status:             {results['status']}")
    logger.info(f"Total Annual Cost:  R {results['total_annual_cost']:,.2f}")
    logger.info(f"Total Allocations:  {len(results['allocations'])}")

    # Calculate supplier counts
    supplier_counts = {}
    for alloc in results['allocations']:
        sname = alloc.get('supplier_name', 'Unknown')
        supplier_counts[sname] = supplier_counts.get(sname, 0) + 1

    logger.info(f"\nSuppliers Used:     {len(supplier_counts)}")
    for supplier, count in sorted(supplier_counts.items()):
        logger.info(f"  - {supplier}: {count} allocations")

    logger.info("=" * 80)


def main():
    """Main execution function."""
    # Setup paths
    base_dir = Path(__file__).resolve().parents[2]
    config_path = str(base_dir / "data/config/optimization_config.json")
    db_path = str(base_dir / "data/databases/fuel_data.db")
    out_dir = base_dir / "outputs/thesis_results/baseline"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output directory: {out_dir}")

    try:
        # Run optimization
        results, precomputed = run_baseline_optimization(config_path, db_path)

        # Export all outputs
        export_supplier_utilization(results, out_dir)
        export_capacity_summary(results, out_dir)
        create_optimization_map(results, precomputed, out_dir)
        export_comprehensive_json(results, out_dir)

        # Print summary
        print_summary(results)

        logger.info(f"\n✓ All baseline outputs saved to: {out_dir}")
        logger.info("\nGenerated files:")
        logger.info("  - supplier_utilization_baseline.csv")
        logger.info("  - supplier_utilization_rows.tex")
        logger.info("  - capacity_summary_baseline.csv")
        logger.info("  - capacity_summary_rows.tex")
        logger.info("  - baseline_optimization_map.html")
        logger.info("  - baseline_results_complete.json")

    except Exception as e:
        logger.error(f"\n✗ Error during baseline optimization: {e}")
        raise


if __name__ == "__main__":
    main()