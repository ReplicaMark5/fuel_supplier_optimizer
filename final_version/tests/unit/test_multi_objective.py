#!/usr/bin/env python3
"""
Test script for multi-objective fuel depot optimization.

This script tests the different optimization modes:
1. Cost-only optimization (baseline)
2. Strategic-only optimization 
3. ε-constraint optimization
"""

import logging
from src.fuel_optimizer_docplex import FuelDepotOptimizerDocplex
from src.precomputation import FuelOptimizationPrecomputation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_objective_modes():
    """Test different objective function modes."""
    logger.info("=== TESTING MULTI-OBJECTIVE OPTIMIZATION MODES ===")
    
    # First, run precomputation once to get the data
    logger.info("Running precomputation...")
    precomputation = FuelOptimizationPrecomputation()
    precomputed_data = precomputation.run_complete_precomputation()
    
    results = {}
    
    # Test 1: Cost-only optimization (baseline)
    logger.info("\n=== TEST 1: COST-ONLY OPTIMIZATION ===")
    try:
        optimizer_cost = FuelDepotOptimizerDocplex(precomputed_data)
        optimizer_cost.prepare_data()
        optimizer_cost.create_decision_variables()
        optimizer_cost.set_objective(objective_mode="cost_only")
        optimizer_cost.add_constraints()
        result_cost = optimizer_cost.solve()
        
        if result_cost and result_cost.get('status') == 'optimal':
            # Calculate strategic score for this solution
            strategic_score = calculate_solution_strategic_score(result_cost['allocations'], optimizer_cost)
            results['cost_only'] = {
                'total_cost': result_cost['total_cost'],
                'strategic_score': strategic_score,
                'status': result_cost['status']
            }
            logger.info(f"Cost-only result: Cost = R{result_cost['total_cost']:,.2f}, Strategic = {strategic_score:.4f}")
        else:
            logger.error("Cost-only optimization failed")
            
    except Exception as e:
        logger.error(f"Error in cost-only optimization: {e}")
    
    # Test 2: Strategic-only optimization  
    logger.info("\n=== TEST 2: STRATEGIC-ONLY OPTIMIZATION ===")
    try:
        optimizer_strategic = FuelDepotOptimizerDocplex(precomputed_data)
        optimizer_strategic.prepare_data()
        optimizer_strategic.create_decision_variables()
        optimizer_strategic.set_objective(objective_mode="strategic_only")
        optimizer_strategic.add_constraints()
        result_strategic = optimizer_strategic.solve()
        
        if result_strategic and result_strategic.get('status') == 'optimal':
            # Calculate strategic score for this solution
            strategic_score = calculate_solution_strategic_score(result_strategic['allocations'], optimizer_strategic)
            results['strategic_only'] = {
                'total_cost': result_strategic['total_cost'],
                'strategic_score': strategic_score,
                'status': result_strategic['status']
            }
            logger.info(f"Strategic-only result: Cost = R{result_strategic['total_cost']:,.2f}, Strategic = {strategic_score:.4f}")
        else:
            logger.error("Strategic-only optimization failed")
            
    except Exception as e:
        logger.error(f"Error in strategic-only optimization: {e}")
    
    # Test 3: ε-constraint optimization
    logger.info("\n=== TEST 3: ε-CONSTRAINT OPTIMIZATION ===")
    try:
        # Use a strategic constraint between min and max
        if 'cost_only' in results and 'strategic_only' in results:
            min_strategic = results['cost_only']['strategic_score']
            max_strategic = results['strategic_only']['strategic_score']
            target_strategic = (min_strategic + max_strategic) / 2  # Middle point
        else:
            target_strategic = 45.0  # Reasonable guess based on 60 depots * 0.75 avg score
        
        optimizer_epsilon = FuelDepotOptimizerDocplex(precomputed_data)
        optimizer_epsilon.prepare_data()
        optimizer_epsilon.create_decision_variables()
        optimizer_epsilon.set_objective(
            objective_mode="epsilon_constraint",
            strategic_constraint=target_strategic
        )
        optimizer_epsilon.add_constraints()
        result_epsilon = optimizer_epsilon.solve()
        
        if result_epsilon and result_epsilon.get('status') == 'optimal':
            # Calculate strategic score for this solution
            strategic_score = calculate_solution_strategic_score(result_epsilon['allocations'], optimizer_epsilon)
            results['epsilon_constraint'] = {
                'total_cost': result_epsilon['total_cost'],
                'strategic_score': strategic_score,
                'strategic_constraint': target_strategic,
                'status': result_epsilon['status']
            }
            logger.info(f"ε-constraint result (ε={target_strategic:.4f}): Cost = R{result_epsilon['total_cost']:,.2f}, Strategic = {strategic_score:.4f}")
        else:
            logger.error(f"ε-constraint optimization failed for constraint = {target_strategic:.4f}")
            
    except Exception as e:
        logger.error(f"Error in ε-constraint optimization: {e}")
    
    return results

def calculate_solution_strategic_score(allocations, optimizer):
    """Calculate the total strategic score for a solution."""
    total_strategic_score = 0.0
    
    for depot_id, allocation_info in allocations.items():
        supplier_depot_id = allocation_info['supplier_depot_id']
        supplier_id = optimizer.supplier_depots.get(supplier_depot_id, {}).get('supplier_id')
        
        if supplier_id in optimizer.supplier_strategic_scores:
            strategic_score = optimizer.supplier_strategic_scores[supplier_id]
            total_strategic_score += strategic_score
    
    return total_strategic_score

def analyze_results(results):
    """Analyze and compare the different optimization results."""
    logger.info("\n=== MULTI-OBJECTIVE OPTIMIZATION ANALYSIS ===")
    
    if not results:
        logger.error("No results to analyze")
        return
    
    logger.info("Optimization Mode Comparison:")
    logger.info(f"{'Mode':<20} {'Total Cost (R)':<15} {'Strategic Score':<15} {'Status'}")
    logger.info("-" * 65)
    
    for mode, result in results.items():
        cost_str = f"{result['total_cost']:,.2f}" if result['total_cost'] else "N/A"
        strategic_str = f"{result['strategic_score']:.4f}" if result['strategic_score'] else "N/A"
        logger.info(f"{mode:<20} {cost_str:<15} {strategic_str:<15} {result['status']}")
    
    # Calculate trade-offs
    if len(results) >= 2:
        logger.info("\n=== TRADE-OFF ANALYSIS ===")
        
        if 'cost_only' in results and 'strategic_only' in results:
            cost_diff = results['strategic_only']['total_cost'] - results['cost_only']['total_cost']
            strategic_diff = results['strategic_only']['strategic_score'] - results['cost_only']['strategic_score']
            
            if strategic_diff > 0:
                cost_per_strategic_point = cost_diff / strategic_diff
                logger.info(f"Cost per strategic score point: R{cost_per_strategic_point:,.2f}")
                logger.info(f"Total strategic improvement available: {strategic_diff:.4f} points")
                logger.info(f"Total additional cost for max strategic: R{cost_diff:,.2f}")
        
        if 'epsilon_constraint' in results and 'cost_only' in results:
            eps_result = results['epsilon_constraint']
            cost_result = results['cost_only']
            
            cost_increase = eps_result['total_cost'] - cost_result['total_cost']
            strategic_increase = eps_result['strategic_score'] - cost_result['strategic_score']
            
            logger.info(f"ε-constraint (middle point) trade-off:")
            logger.info(f"  Additional cost: R{cost_increase:,.2f} ({cost_increase/cost_result['total_cost']*100:.2f}%)")
            logger.info(f"  Strategic improvement: {strategic_increase:.4f} points ({strategic_increase/cost_result['strategic_score']*100:.2f}%)")

def main():
    """Main test function."""
    logger.info("Starting multi-objective optimization tests...")
    
    # Test different objective modes
    results = test_objective_modes()
    
    # Analyze results
    analyze_results(results)
    
    logger.info("Multi-objective optimization tests completed!")

if __name__ == "__main__":
    main()