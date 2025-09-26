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

from fuel_optimizer_docplex import FuelDepotOptimizerDocplex
from precomputation import FuelOptimizationPrecomputation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParetoFrontGenerator:
    """Class to generate Pareto front for multi-objective fuel depot optimization."""
    
    def __init__(self, db_path: str = "fuel_data.db", config_path: str = "optimization_config.json"):
        """Initialize the Pareto front generator."""
        self.db_path = db_path
        self.config_path = config_path
        self.pareto_solutions = []
        
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
    
    def generate_pareto_front(self, num_points: int = 20) -> List[Dict[str, Any]]:
        """
        Generate Pareto front using ε-constraint method.
        
        Args:
            num_points: Number of points to generate on the Pareto front
            
        Returns:
            List of solution dictionaries with cost and strategic score
        """
        logger.info(f"Generating Pareto front with {num_points} points using ε-constraint method...")
        
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
        
        logger.info(f"Generated {len(pareto_points)} Pareto-optimal solutions")
        self.pareto_solutions = pareto_points
        return pareto_points
    
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
        
        # Extract data for plotting
        costs = [sol['cost_rand'] for sol in self.pareto_solutions]
        strategic_scores = [sol['strategic_score'] for sol in self.pareto_solutions]
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        # Plot Pareto front
        plt.scatter(costs, strategic_scores, c='blue', s=60, alpha=0.7, label='Pareto Optimal Solutions')
        plt.plot(costs, strategic_scores, 'b--', alpha=0.5, linewidth=1)
        
        # Add labels for some points
        for i in range(0, len(self.pareto_solutions), max(1, len(self.pareto_solutions)//5)):
            sol = self.pareto_solutions[i]
            plt.annotate(f'Point {i+1}', 
                        (sol['cost_rand'], sol['strategic_score']),
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=8, alpha=0.7)
        
        plt.xlabel('Total Annual Cost (R)', fontsize=12)
        plt.ylabel('Total Strategic Supplier Score', fontsize=12)
        plt.title('Pareto Front: Cost vs Strategic Supplier Score\n(Fuel Depot Allocation Optimization)', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Format axes
        plt.ticklabel_format(style='plain', axis='x')
        plt.tight_layout()
        
        # Save plot
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
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