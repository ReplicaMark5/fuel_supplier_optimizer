#!/usr/bin/env python3
"""
Pareto Front Generation for Multi-Objective Fuel Depot Optimization

This script generates a Pareto front using the ε-constraint method to optimize
between cost minimization and strategic supplier score maximization.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from typing import List, Tuple, Dict, Any
import json
from pathlib import Path

from .fuel_optimizer_docplex import FuelDepotOptimizerDocplex
from .precomputation import FuelOptimizationPrecomputation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParetoFrontGenerator:
    """Class to generate Pareto front for multi-objective fuel depot optimization."""
    
    def __init__(self, db_path: str = str(Path(__file__).resolve().parents[1] / "data/databases/fuel_data.db"), config_path: str = str(Path(__file__).resolve().parents[1] / "data/config/optimization_config.json")):
        """Initialize the Pareto front generator."""
        self.db_path = db_path
        self.config_path = config_path
        self.pareto_solutions = []

        # Load configuration
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Load Pareto-specific settings (with defaults)
        pareto_settings = config.get('pareto_front_settings', {})
        self.num_epsilon_points = pareto_settings.get('num_epsilon_points', 50)

        # Duplicate tolerance settings
        dup_tol = pareto_settings.get('duplicate_tolerance', {})
        self.cost_decimals = dup_tol.get('cost_decimals', 2)
        self.score_decimals = dup_tol.get('score_decimals', 4)

        # Plotting settings
        self.plot_settings = pareto_settings.get('plotting', {})

        # Initialize components
        self.precomputation = FuelOptimizationPrecomputation(config_path, db_path)
        
    def calculate_strategic_bounds(self) -> Tuple[float, float]:
        """
        Calculate the bounds for strategic scores.
        
        Returns:
            Tuple of (min_strategic_score, max_strategic_score)
        """
        logger.info("Calculating strategic score bounds...")
        
        # Get strategic scores from precomputed cost dictionary
        cost_data = self.precomputation.run_complete_precomputation()
        cost_dict = cost_data['costs']
        
        # Extract all strategic scores from cost dictionary
        strategic_scores = []
        for depot_id in cost_dict:
            for supplier_depot_id in cost_dict[depot_id]:
                strategic_score = cost_dict[depot_id][supplier_depot_id].get('strategic_score', 0.0)
                if strategic_score > 0:
                    strategic_scores.append(strategic_score)
        
        # For bounds, we need to consider the number of depots (60)
        # Min: all depots use worst supplier
        # Max: all depots use best supplier
        min_supplier_score = min(strategic_scores)
        max_supplier_score = max(strategic_scores)
        
        # Get depot count from cost data
        num_depots = len(cost_dict)
        
        min_total_strategic = min_supplier_score * num_depots
        max_total_strategic = max_supplier_score * num_depots
        
        logger.info(f"Strategic score bounds: [{min_total_strategic:.4f}, {max_total_strategic:.4f}]")
        logger.info(f"Based on {num_depots} depots and supplier scores [{min_supplier_score:.4f}, {max_supplier_score:.4f}]")
        
        return min_total_strategic, max_total_strategic
    
    def generate_pareto_front(self, num_points: int = None) -> List[Dict[str, Any]]:
        """
        Generate Pareto front using ε-constraint method.

        Args:
            num_points: Number of points to generate on the Pareto front (uses config default if None)

        Returns:
            List of solution dictionaries with cost and strategic score
        """
        # Use provided num_points or fall back to config
        if num_points is None:
            num_points = self.num_epsilon_points

        logger.info(f"Generating Pareto front with {num_points} ε-constraint points using config settings...")
        
        # Calculate strategic score bounds
        min_strategic, max_strategic = self.calculate_strategic_bounds()
        
        # Generate strategic constraint values (ε values)
        strategic_constraints = np.linspace(min_strategic, max_strategic, num_points)
        
        pareto_points = []
        
        # Run precomputation once (reuse for all epsilon constraint problems)
        cost_data = self.precomputation.run_complete_precomputation()
        
        for i, strategic_constraint in enumerate(strategic_constraints):
            logger.info(f"Solving ε-constraint problem {i+1}/{num_points} (ε = {strategic_constraint:.4f})...")
            
            try:
                # Create optimizer instance with precomputed data
                optimizer = FuelDepotOptimizerDocplex(cost_data)
                
                # Prepare data structures from precomputed data
                optimizer.prepare_data()
                
                # Create decision variables
                optimizer.create_decision_variables()
                
                # Set ε-constraint objective
                optimizer.set_objective(
                    objective_mode="epsilon_constraint",
                    strategic_constraint=strategic_constraint
                )
                
                # Add constraints
                optimizer.add_constraints()
                
                # Solve
                results = optimizer.solve()
                
                if results and results.get('status') == 'optimal':
                    # Calculate actual strategic score for this solution
                    actual_strategic_score = self._calculate_actual_strategic_score(
                        results['allocations'], optimizer
                    )
                    
                    pareto_point = {
                        'strategic_constraint': strategic_constraint,
                        'cost_rand': results['total_annual_cost'],
                        'strategic_score': actual_strategic_score,
                        'status': results['status'],
                        'num_allocations': len(results['allocations']),
                        'active_tiers': results.get('active_tiers', [])
                    }
                    
                    pareto_points.append(pareto_point)
                    logger.info(f"  Solution: Cost = R{results['total_annual_cost']:,.2f}, Strategic = {actual_strategic_score:.4f}")
                    
                else:
                    logger.warning(f"  No optimal solution found for ε = {strategic_constraint:.4f}")
                    
            except Exception as e:
                logger.error(f"Error solving ε-constraint problem {i+1}: {e}")
                continue
        
        logger.info(f"Generated {len(pareto_points)} solutions before filtering")

        # Filter and clean Pareto front
        filtered_points = self._filter_pareto_front(pareto_points)
        logger.info(f"After filtering: {len(filtered_points)} unique Pareto-optimal solutions")

        self.pareto_solutions = filtered_points
        return filtered_points
    
    def _calculate_actual_strategic_score(self, allocations: list, optimizer) -> float:
        """Calculate the actual strategic score for a given allocation solution."""
        total_strategic_score = 0.0

        for allocation in allocations:
            depot_id = allocation['customer_depot_id']
            supplier_depot_id = allocation['supplier_depot_id']

            # Get strategic score from cost matrices (now contains strategic scores)
            supplier_depot_data = optimizer.cost_matrices.get(depot_id, {}).get(supplier_depot_id, {})
            strategic_score = supplier_depot_data.get('strategic_score', 0.0)
            total_strategic_score += strategic_score

        return total_strategic_score

    def _filter_pareto_front(self, pareto_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter Pareto front to remove duplicates and dominated solutions.

        Args:
            pareto_points: Raw list of Pareto solutions

        Returns:
            Filtered and sorted list of unique non-dominated solutions
        """
        if not pareto_points:
            return []

        # Remove duplicates based on (cost, strategic_score) tuple with configurable tolerance
        unique_points = {}
        for point in pareto_points:
            key = (round(point['cost_rand'], self.cost_decimals),
                   round(point['strategic_score'], self.score_decimals))
            if key not in unique_points:
                unique_points[key] = point

        points_list = list(unique_points.values())
        logger.info(f"Removed {len(pareto_points) - len(points_list)} duplicate solutions")

        # Sort by cost (ascending)
        points_list.sort(key=lambda p: p['cost_rand'])

        # Remove dominated solutions (cost increases but strategic score doesn't)
        filtered = []
        max_score_so_far = -float('inf')

        for point in points_list:
            # For minimization-maximization: keep point if strategic score is better than any previous
            if point['strategic_score'] > max_score_so_far:
                filtered.append(point)
                max_score_so_far = point['strategic_score']

        logger.info(f"Removed {len(points_list) - len(filtered)} dominated solutions")

        return filtered
    
    def plot_pareto_front(self, save_path: str = "pareto_front.png"):
        """
        Plot the Pareto front.

        Args:
            save_path: Path to save the plot
        """
        if not self.pareto_solutions:
            logger.error("No Pareto solutions to plot. Run generate_pareto_front() first.")
            return

        logger.info(f"Plotting Pareto front with {len(self.pareto_solutions)} points...")

        # Solutions are already sorted by cost (from filtering)
        costs = np.array([sol['cost_rand'] for sol in self.pareto_solutions])
        strategic_scores = np.array([sol['strategic_score'] for sol in self.pareto_solutions])

        # Get plotting settings from config
        figsize = self.plot_settings.get('figure_size', [12, 8])
        dpi = self.plot_settings.get('dpi', 300)
        line_color = self.plot_settings.get('line_color', 'darkblue')
        show_stats = self.plot_settings.get('show_statistics_box', True)

        # Create the plot
        fig, ax = plt.subplots(figsize=figsize)

        # Plot Pareto front with solid line connecting points
        ax.plot(costs, strategic_scores, color=line_color, linewidth=2, alpha=0.6)
        ax.scatter(costs, strategic_scores, c=line_color, s=80, alpha=0.8, zorder=5, edgecolors='white', linewidth=1.5)

        # Labels and formatting
        ax.set_xlabel('Total Annual Cost (R)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Total Strategic Supplier Score', fontsize=13, fontweight='bold')
        ax.set_title('Pareto Front: Cost Minimization vs Strategic Supplier Score Maximization\n'
                    f'({len(self.pareto_solutions)} Pareto-Optimal Solutions)',
                    fontsize=14, fontweight='bold', pad=20)

        ax.grid(True, alpha=0.3, linestyle='--')

        # Format axes
        ax.ticklabel_format(style='plain', axis='x')
        ax.tick_params(labelsize=11)

        # Add info text box (if enabled in config)
        if show_stats:
            textstr = f'Solutions: {len(self.pareto_solutions)}\n' \
                     f'Cost Range: R{costs.min():,.0f} - R{costs.max():,.0f}\n' \
                     f'Cost Δ: {((costs.max() - costs.min()) / costs.min() * 100):.3f}%\n' \
                     f'Score Range: {strategic_scores.min():.0f} - {strategic_scores.max():.0f}\n' \
                     f'Score Δ: {((strategic_scores.max() - strategic_scores.min()) / strategic_scores.min() * 100):.2f}%'

            props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
            ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                   verticalalignment='top', bbox=props, family='monospace')

        plt.tight_layout()

        # Save plot with config DPI
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        logger.info(f"Pareto front plot saved to: {save_path}")

        # Show plot
        plt.show()
    
    def save_results(self, csv_path: str = "pareto_solutions.csv", json_path: str = "pareto_solutions.json"):
        """
        Save Pareto front results to files.
        
        Args:
            csv_path: Path to save CSV file
            json_path: Path to save JSON file
        """
        if not self.pareto_solutions:
            logger.error("No Pareto solutions to save.")
            return
        
        # Save to CSV
        df = pd.DataFrame(self.pareto_solutions)
        df.to_csv(csv_path, index=False)
        logger.info(f"Pareto solutions saved to CSV: {csv_path}")
        
        # Save to JSON (with better formatting)
        with open(json_path, 'w') as f:
            json.dump(self.pareto_solutions, f, indent=2, default=str)
        logger.info(f"Pareto solutions saved to JSON: {json_path}")
    
    def analyze_tradeoffs(self):
        """Analyze the trade-offs in the Pareto front."""
        if not self.pareto_solutions:
            logger.error("No Pareto solutions to analyze.")
            return
        
        logger.info("=== PARETO FRONT ANALYSIS ===")
        
        costs = [sol['cost_rand'] for sol in self.pareto_solutions]
        strategic_scores = [sol['strategic_score'] for sol in self.pareto_solutions]
        
        # Basic statistics
        logger.info(f"Number of Pareto-optimal solutions: {len(self.pareto_solutions)}")
        logger.info(f"Cost range: R{min(costs):,.2f} - R{max(costs):,.2f}")
        logger.info(f"Strategic score range: {min(strategic_scores):.4f} - {max(strategic_scores):.4f}")
        
        # Calculate efficiency improvements
        cost_range = max(costs) - min(costs)
        strategic_range = max(strategic_scores) - min(strategic_scores)
        
        logger.info(f"Cost variation: R{cost_range:,.2f} ({cost_range/min(costs)*100:.1f}%)")
        logger.info(f"Strategic score variation: {strategic_range:.4f} ({strategic_range/min(strategic_scores)*100:.1f}%)")
        
        # Show extreme points
        min_cost_idx = costs.index(min(costs))
        max_strategic_idx = strategic_scores.index(max(strategic_scores))
        
        logger.info("\n=== EXTREME POINTS ===")
        logger.info("Minimum Cost Solution:")
        logger.info(f"  Cost: R{self.pareto_solutions[min_cost_idx]['cost_rand']:,.2f}")
        logger.info(f"  Strategic Score: {self.pareto_solutions[min_cost_idx]['strategic_score']:.4f}")
        
        logger.info("Maximum Strategic Score Solution:")
        logger.info(f"  Cost: R{self.pareto_solutions[max_strategic_idx]['cost_rand']:,.2f}")
        logger.info(f"  Strategic Score: {self.pareto_solutions[max_strategic_idx]['strategic_score']:.4f}")


def main():
    """Main function to generate and analyze Pareto front."""
    logger.info("Starting Pareto front generation for multi-objective fuel depot optimization...")
    
    # Initialize generator
    generator = ParetoFrontGenerator()
    
    # Generate Pareto front
    pareto_solutions = generator.generate_pareto_front(num_points=15)  # Start with fewer points for testing
    
    if pareto_solutions:
        # Analyze trade-offs
        generator.analyze_tradeoffs()
        
        # Plot Pareto front
        generator.plot_pareto_front("pareto_front_fuel_optimization.png")
        
        # Save results
        generator.save_results("pareto_fuel_solutions.csv", "pareto_fuel_solutions.json")
        
        logger.info("Pareto front generation completed successfully!")
    else:
        logger.error("No Pareto solutions generated. Check optimization setup.")


if __name__ == "__main__":
    main()