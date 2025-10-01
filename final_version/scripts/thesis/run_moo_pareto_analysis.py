#!/usr/bin/env python3
"""
Multi-Objective Optimization (MOO) Pareto Front Analysis Script for Thesis

This script runs the multi-objective ε-constraint optimization to generate Pareto
front solutions trading off cost minimization vs strategic supplier score maximization.

Outputs:
  - Pareto front visualization (PNG)
  - Pareto solutions data (CSV, JSON)
  - Representative solutions table (LaTeX)
  - Trade-off analysis summary
  - Comprehensive results JSON

Run from project root:
  python scripts/thesis/run_moo_pareto_analysis.py
"""

import sys
import json
import csv
from pathlib import Path
from typing import Dict, Any, List
import logging
import numpy as np

# Add parent to path to enable src imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.pareto_front_generator import ParetoFrontGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_pareto_front() -> tuple:
    """
    Generate Pareto front using ε-constraint method.
    Uses settings from optimization_config.json.

    Returns:
        Tuple of (generator, pareto_solutions)
    """
    logger.info("=" * 80)
    logger.info("MULTI-OBJECTIVE PARETO FRONT GENERATION")
    logger.info("=" * 80)

    logger.info("\nInitializing Pareto front generator (settings from config)...")

    generator = ParetoFrontGenerator()
    logger.info(f"Config: {generator.num_epsilon_points} ε-constraint points, "
               f"tolerance: cost={generator.cost_decimals}dp, score={generator.score_decimals}dp")

    pareto_solutions = generator.generate_pareto_front()

    if not pareto_solutions:
        raise RuntimeError("No Pareto solutions generated")

    logger.info(f"\n✓ Generated {len(pareto_solutions)} Pareto-optimal solutions")

    return generator, pareto_solutions


def export_pareto_plot(generator: ParetoFrontGenerator, out_dir: Path) -> None:
    """Export Pareto front visualization."""
    logger.info("\n1. Creating Pareto front plot...")

    plot_path = out_dir / "pareto_front_fuel_optimization.png"
    generator.plot_pareto_front(save_path=str(plot_path))

    logger.info(f"   ✓ PNG plot: {plot_path}")


def export_pareto_data(pareto_solutions: List[Dict[str, Any]], out_dir: Path) -> None:
    """Export Pareto solutions data as CSV and JSON."""
    logger.info("\n2. Exporting Pareto solutions data...")

    # CSV export
    csv_path = out_dir / "pareto_solutions.csv"
    with csv_path.open("w", newline="") as f:
        if pareto_solutions:
            writer = csv.DictWriter(f, fieldnames=sorted(pareto_solutions[0].keys()))
            writer.writeheader()
            writer.writerows(pareto_solutions)
    logger.info(f"   ✓ CSV: {csv_path}")

    # JSON export
    json_path = out_dir / "pareto_solutions.json"
    with json_path.open("w") as f:
        json.dump(pareto_solutions, f, indent=2, default=str)
    logger.info(f"   ✓ JSON: {json_path}")


def find_knee_point(pareto_solutions: List[Dict[str, Any]]) -> int:
    """
    Find the knee point on the Pareto front using perpendicular distance method.

    Args:
        pareto_solutions: List of Pareto solutions

    Returns:
        Index of knee point
    """
    # Extract costs and strategic scores
    costs = np.array([sol['cost_rand'] for sol in pareto_solutions])
    scores = np.array([sol['strategic_score'] for sol in pareto_solutions])

    # Normalize to [0, 1]
    costs_norm = (costs - costs.min()) / (costs.max() - costs.min())
    scores_norm = (scores - scores.min()) / (scores.max() - scores.min())

    # Calculate perpendicular distance from line connecting extremes
    # Line from (0, 0) to (1, 1) in normalized space
    distances = np.abs(costs_norm - scores_norm) / np.sqrt(2)

    # Knee is the point with maximum perpendicular distance
    knee_idx = np.argmax(distances)

    return knee_idx


def export_representative_solutions_table(pareto_solutions: List[Dict[str, Any]], out_dir: Path) -> None:
    """
    Export representative solutions table in LaTeX format.

    Includes: Min Cost, Knee Point, Max Strategic Score
    """
    logger.info("\n3. Creating representative solutions table...")

    # Find extreme points
    costs = [sol['cost_rand'] for sol in pareto_solutions]
    scores = [sol['strategic_score'] for sol in pareto_solutions]

    min_cost_idx = costs.index(min(costs))
    max_score_idx = scores.index(max(scores))
    knee_idx = find_knee_point(pareto_solutions)

    # Get solutions
    min_cost_sol = pareto_solutions[min_cost_idx]
    knee_sol = pareto_solutions[knee_idx]
    max_score_sol = pareto_solutions[max_score_idx]

    # Calculate deltas
    base_cost = min_cost_sol['cost_rand']
    base_score = min_cost_sol['strategic_score']

    def calc_delta_pct(value, base):
        return ((value - base) / base) * 100

    # Prepare table data
    table_data = [
        {
            'point': 'Min Cost',
            'cost': min_cost_sol['cost_rand'],
            'score': min_cost_sol['strategic_score'],
            'delta_cost_pct': 0.0,
            'delta_score_pct': 0.0
        },
        {
            'point': 'Knee',
            'cost': knee_sol['cost_rand'],
            'score': knee_sol['strategic_score'],
            'delta_cost_pct': calc_delta_pct(knee_sol['cost_rand'], base_cost),
            'delta_score_pct': calc_delta_pct(knee_sol['strategic_score'], base_score)
        },
        {
            'point': 'Max Score',
            'cost': max_score_sol['cost_rand'],
            'score': max_score_sol['strategic_score'],
            'delta_cost_pct': calc_delta_pct(max_score_sol['cost_rand'], base_cost),
            'delta_score_pct': calc_delta_pct(max_score_sol['strategic_score'], base_score)
        }
    ]

    # Export as LaTeX table rows
    tex_path = out_dir / "representative_solutions_rows.tex"
    with tex_path.open("w", encoding="utf-8") as f:
        for row in table_data:
            f.write(
                f"{row['point']} & {row['cost']:,.2f} & {row['score']:.0f} & "
                f"{row['delta_cost_pct']:.4f} & {row['delta_score_pct']:.2f} \\\\\n"
            )
    logger.info(f"   ✓ LaTeX rows: {tex_path}")

    # Also export as CSV for reference
    csv_path = out_dir / "representative_solutions.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            'point', 'cost', 'score', 'delta_cost_pct', 'delta_score_pct'
        ])
        writer.writeheader()
        writer.writerows(table_data)
    logger.info(f"   ✓ CSV: {csv_path}")


def export_tradeoff_analysis(pareto_solutions: List[Dict[str, Any]], out_dir: Path) -> None:
    """Export trade-off analysis summary."""
    logger.info("\n4. Creating trade-off analysis...")

    costs = [sol['cost_rand'] for sol in pareto_solutions]
    scores = [sol['strategic_score'] for sol in pareto_solutions]

    # Calculate statistics
    min_cost = min(costs)
    max_cost = max(costs)
    cost_range = max_cost - min_cost
    cost_range_pct = (cost_range / min_cost) * 100

    min_score = min(scores)
    max_score = max(scores)
    score_range = max_score - min_score
    score_range_pct = (score_range / min_score) * 100

    # Calculate marginal rates of substitution (MRS)
    mrs_values = []
    for i in range(1, len(pareto_solutions)):
        delta_cost = costs[i] - costs[i-1]
        delta_score = scores[i] - scores[i-1]
        if delta_score != 0:
            mrs = delta_cost / delta_score
            mrs_values.append(mrs)

    analysis = {
        'num_solutions': len(pareto_solutions),
        'cost_statistics': {
            'min': min_cost,
            'max': max_cost,
            'range': cost_range,
            'range_pct': cost_range_pct
        },
        'score_statistics': {
            'min': min_score,
            'max': max_score,
            'range': score_range,
            'range_pct': score_range_pct
        },
        'marginal_rates': {
            'mean_mrs': np.mean(mrs_values) if mrs_values else 0,
            'median_mrs': np.median(mrs_values) if mrs_values else 0,
            'max_mrs': max(mrs_values) if mrs_values else 0,
            'min_mrs': min(mrs_values) if mrs_values else 0
        }
    }

    # Export as JSON
    json_path = out_dir / "tradeoff_analysis.json"
    with json_path.open("w") as f:
        json.dump(analysis, f, indent=2, default=str)
    logger.info(f"   ✓ JSON: {json_path}")

    # Export human-readable summary
    summary_path = out_dir / "tradeoff_summary.txt"
    with summary_path.open("w") as f:
        f.write("=" * 80 + "\n")
        f.write("PARETO FRONT TRADE-OFF ANALYSIS\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Number of Pareto Solutions: {analysis['num_solutions']}\n\n")

        f.write("COST ANALYSIS:\n")
        f.write(f"  Minimum Cost:       R {min_cost:,.2f}\n")
        f.write(f"  Maximum Cost:       R {max_cost:,.2f}\n")
        f.write(f"  Cost Range:         R {cost_range:,.2f} ({cost_range_pct:.2f}%)\n\n")

        f.write("STRATEGIC SCORE ANALYSIS:\n")
        f.write(f"  Minimum Score:      {min_score:,.0f}\n")
        f.write(f"  Maximum Score:      {max_score:,.0f}\n")
        f.write(f"  Score Range:        {score_range:,.0f} ({score_range_pct:.2f}%)\n\n")

        if mrs_values:
            f.write("MARGINAL RATES OF SUBSTITUTION (R per Score Point):\n")
            f.write(f"  Mean MRS:           R {analysis['marginal_rates']['mean_mrs']:,.2f}\n")
            f.write(f"  Median MRS:         R {analysis['marginal_rates']['median_mrs']:,.2f}\n")
            f.write(f"  Range:              R {analysis['marginal_rates']['min_mrs']:,.2f} - "
                   f"R {analysis['marginal_rates']['max_mrs']:,.2f}\n\n")

        f.write("=" * 80 + "\n")

    logger.info(f"   ✓ Summary: {summary_path}")


def print_summary(pareto_solutions: List[Dict[str, Any]]) -> None:
    """Print Pareto front summary."""
    logger.info("\n" + "=" * 80)
    logger.info("PARETO FRONT SUMMARY")
    logger.info("=" * 80)

    costs = [sol['cost_rand'] for sol in pareto_solutions]
    scores = [sol['strategic_score'] for sol in pareto_solutions]

    logger.info(f"Solutions Generated:  {len(pareto_solutions)}")
    logger.info(f"\nCost Range:")
    logger.info(f"  Min: R {min(costs):,.2f}")
    logger.info(f"  Max: R {max(costs):,.2f}")
    logger.info(f"  Δ:   R {max(costs) - min(costs):,.2f} ({((max(costs) - min(costs)) / min(costs)) * 100:.2f}%)")

    logger.info(f"\nStrategic Score Range:")
    logger.info(f"  Min: {min(scores):,.0f}")
    logger.info(f"  Max: {max(scores):,.0f}")
    logger.info(f"  Δ:   {max(scores) - min(scores):,.0f} ({((max(scores) - min(scores)) / min(scores)) * 100:.2f}%)")

    # Find and display knee point
    knee_idx = find_knee_point(pareto_solutions)
    knee_sol = pareto_solutions[knee_idx]
    logger.info(f"\nKnee Point (Recommended):")
    logger.info(f"  Cost:            R {knee_sol['cost_rand']:,.2f}")
    logger.info(f"  Strategic Score: {knee_sol['strategic_score']:,.0f}")
    logger.info(f"  Δ Cost:          +{((knee_sol['cost_rand'] - min(costs)) / min(costs)) * 100:.4f}%")
    logger.info(f"  Δ Score:         +{((knee_sol['strategic_score'] - min(scores)) / min(scores)) * 100:.2f}%")

    logger.info("=" * 80)


def main():
    """Main execution function."""
    # Setup paths
    base_dir = Path(__file__).resolve().parents[2]
    out_dir = base_dir / "outputs/thesis_results/moo_pareto"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output directory: {out_dir}")

    try:
        # Generate Pareto front using config settings
        # Note: Duplicates/dominated solutions will be filtered out automatically
        generator, pareto_solutions = generate_pareto_front()

        # Export all outputs
        export_pareto_plot(generator, out_dir)
        export_pareto_data(pareto_solutions, out_dir)
        export_representative_solutions_table(pareto_solutions, out_dir)
        export_tradeoff_analysis(pareto_solutions, out_dir)

        # Print summary
        print_summary(pareto_solutions)

        logger.info(f"\n✓ All MOO Pareto outputs saved to: {out_dir}")
        logger.info("\nGenerated files:")
        logger.info("  - pareto_front_fuel_optimization.png")
        logger.info("  - pareto_solutions.csv")
        logger.info("  - pareto_solutions.json")
        logger.info("  - representative_solutions.csv")
        logger.info("  - representative_solutions_rows.tex")
        logger.info("  - tradeoff_analysis.json")
        logger.info("  - tradeoff_summary.txt")

    except Exception as e:
        logger.error(f"\n✗ Error during MOO Pareto analysis: {e}")
        raise


if __name__ == "__main__":
    main()