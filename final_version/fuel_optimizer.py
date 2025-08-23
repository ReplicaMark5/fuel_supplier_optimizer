#!/usr/bin/env python3
"""
Fuel Depot Allocation Optimizer using CPLEX

Phase 1: Core framework with base costs only
- Basic CPLEX optimizer class structure  
- Data preparation from precomputed dictionary
- Base-cost-only objective function
- Depot assignment constraints
"""

import json
import logging
from typing import Dict, Any, List

try:
    import cplex
    from cplex.exceptions import CplexError
except ImportError:
    raise ImportError("CPLEX not found. Please install IBM CPLEX Python API.")

from precomputation import FuelOptimizationPrecomputation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FuelDepotOptimizer:
    """
    CPLEX-based optimizer for fuel depot allocation with volume tier support.
    
    Phase 1: Base cost optimization only
    Phase 2: Volume tier integration with conditional costs
    """
    
    def __init__(self, precomputed_data: Dict[str, Any], config_path: str = "optimization_config.json"):
        """
        Initialize optimizer with precomputed cost data.
        
        Args:
            precomputed_data: Output from FuelOptimizationPrecomputation
            config_path: Path to optimization configuration file
        """
        self.precomputed_data = precomputed_data
        self.config_path = config_path
        
        # CPLEX model
        self.model = cplex.Cplex()
        self.model.set_log_stream(None)  # Suppress CPLEX output for now
        self.model.set_error_stream(None)
        self.model.set_warning_stream(None)
        self.model.set_results_stream(None)
        
        # Data structures
        self.customer_depots = {}
        self.supplier_depots = {}
        self.cost_matrices = {}
        self.availability_matrix = {}
        self.variable_names = []
        self.variable_indices = {}
        
        # Option types (base costs)
        self.option_types = ['coc_cash', 'coc_30', 'coc_45', 'coc_60', 'del_own', 'del_buy', 'del_rent']
        
        # Phase 2: Volume tier structures
        self.tier_configurations = {}
        self.tier_costs = {}
        self.tier_variable_names = []
        self.tier_variable_indices = {}
        
        # Load volume tier config
        self._load_tier_configuration()
        
        logger.info("FuelDepotOptimizer initialized for Phase 2 (with volume tiers)")
    
    def _load_tier_configuration(self):
        """Load volume tier configurations from config file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            self.tier_configurations = config.get('volume_tier_configurations', {})
            logger.info(f"Loaded {len(self.tier_configurations)} volume tier configurations")
            
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_path}")
            self.tier_configurations = {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            self.tier_configurations = {}
    
    def _prepare_tier_costs(self):
        """Extract tier cost data from precomputed dictionary."""
        logger.info("Preparing volume tier cost data...")
        
        costs_data = self.precomputed_data['costs']
        tier_cost_count = 0
        
        for depot_id, supplier_depots in costs_data.items():
            if depot_id not in self.tier_costs:
                self.tier_costs[depot_id] = {}
            
            for supplier_depot_id, depot_data in supplier_depots.items():
                tier_costs = depot_data.get('tier_costs', {})
                if tier_costs:
                    self.tier_costs[depot_id][supplier_depot_id] = tier_costs
                    tier_cost_count += len(tier_costs)
        
        logger.info(f"Prepared {tier_cost_count} volume tier cost options")
    
    def prepare_data(self):
        """
        Extract and structure data from precomputed dictionary for CPLEX.
        """
        logger.info("Preparing data structures for CPLEX...")
        
        # Extract customer depot information
        self.customer_depots = self.precomputed_data['depots'].copy()
        logger.info(f"Loaded {len(self.customer_depots)} customer depots")
        
        # Extract supplier information  
        self.suppliers = self.precomputed_data['suppliers'].copy()
        logger.info(f"Loaded {len(self.suppliers)} suppliers")
        
        # Build cost matrices and availability matrix
        costs_data = self.precomputed_data['costs']
        
        for depot_id, supplier_depots in costs_data.items():
            if depot_id not in self.cost_matrices:
                self.cost_matrices[depot_id] = {}
                self.availability_matrix[depot_id] = {}
            
            for supplier_depot_id, depot_data in supplier_depots.items():
                # Store base costs only (Phase 1)
                base_costs = depot_data['base_costs']
                self.cost_matrices[depot_id][supplier_depot_id] = base_costs.copy()
                
                # Store available options
                available_options = depot_data.get('available_options', list(base_costs.keys()))
                self.availability_matrix[depot_id][supplier_depot_id] = available_options
                
                # Track supplier depot info
                if supplier_depot_id not in self.supplier_depots:
                    self.supplier_depots[supplier_depot_id] = {
                        'supplier_id': depot_data.get('supplier_id'),
                        'supplier_name': depot_data.get('supplier_name'),
                        'distance_km': depot_data.get('distance_km')
                    }
        
        total_combinations = sum(len(sd) for sd in self.cost_matrices.values())
        logger.info(f"Prepared cost data for {total_combinations} depot-supplier_depot combinations")
        
        # Phase 2: Prepare tier cost data
        self._prepare_tier_costs()
        
        return self
    
    def setup_decision_variables(self):
        """
        Create binary decision variables for depot-supplier-option combinations and volume tiers.
        """
        logger.info("Setting up decision variables...")
        
        variable_count = 0
        
        # Phase 1: Base allocation variables
        for depot_id in self.cost_matrices:
            for supplier_depot_id in self.cost_matrices[depot_id]:
                available_options = self.availability_matrix[depot_id][supplier_depot_id]
                
                for option_type in self.option_types:
                    if option_type in available_options:
                        var_name = f"{option_type}_{depot_id}_{supplier_depot_id}"
                        self.variable_names.append(var_name)
                        self.variable_indices[var_name] = variable_count
                        variable_count += 1
        
        # Phase 2: Volume tier variables
        for tier_name in self.tier_configurations:
            var_name = f"VT_{tier_name}"
            self.tier_variable_names.append(var_name)
            self.tier_variable_indices[var_name] = variable_count + len(self.tier_variable_names) - 1
        
        # Add all variables to CPLEX model
        all_variable_names = self.variable_names + self.tier_variable_names
        self.model.variables.add(
            names=all_variable_names,
            types=['B'] * len(all_variable_names)  # All binary variables
        )
        
        logger.info(f"Created {len(self.variable_names)} allocation variables + {len(self.tier_variable_names)} tier variables")
        return self
    
    def setup_objective_function(self):
        """
        Simplified objective: Use base costs only, tier costs handled via penalty approach.
        
        This approach avoids complex auxiliary variables by using base costs in objective
        and implementing tier cost differences via constraints.
        """
        logger.info("Setting up simplified objective function...")
        
        objective_coefficients = []
        
        for var_name in self.variable_names:
            # Parse variable name
            parts = var_name.split('_')
            option_type = parts[0] + '_' + parts[1] if parts[1] in ['cash', '30', '45', '60', 'own', 'buy', 'rent'] else parts[0]
            depot_id = int(parts[-2])
            supplier_depot_id = int(parts[-1])
            
            # Use base cost for objective
            cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id][option_type]
            depot_volume = self.customer_depots[depot_id]['annual_volume']
            total_cost_coefficient = depot_volume * cost_per_litre
            objective_coefficients.append(total_cost_coefficient)
        
        # Add tier variables with zero cost (they modify via constraints)
        for tier_var in self.tier_variable_names:
            objective_coefficients.append(0.0)
        
        # Set objective (minimize)
        all_variables = self.variable_names + self.tier_variable_names
        self.model.objective.set_sense(self.model.objective.sense.minimize)
        self.model.objective.set_linear(list(zip(all_variables, objective_coefficients)))
        
        logger.info(f"Base objective set with {len(self.variable_names)} allocation costs")
        return self
    
    def _get_applicable_tiers(self, depot_id: int, supplier_depot_id: int) -> List[str]:
        """
        Get applicable tier configurations for a depot-supplier combination.
        
        Args:
            depot_id: Customer depot ID
            supplier_depot_id: Supplier depot ID
            
        Returns:
            List of applicable tier configuration names
        """
        applicable_tiers = []
        
        # Get supplier info for this supplier depot
        supplier_info = self.supplier_depots.get(supplier_depot_id, {})
        supplier_id = supplier_info.get('supplier_id')
        supplier_name = supplier_info.get('supplier_name', '')
        
        for tier_name, tier_config in self.tier_configurations.items():
            # Check supplier filter
            tier_suppliers = tier_config.get('suppliers', [])
            if tier_suppliers != ['*'] and supplier_name not in tier_suppliers:
                continue
                
            # Check supplier depot filter
            tier_supplier_depots = tier_config.get('supplier_depots', ['*'])
            if tier_supplier_depots != ['*'] and str(supplier_depot_id) not in tier_supplier_depots:
                continue
            
            applicable_tiers.append(tier_name)
        
        return applicable_tiers
    
    def setup_constraints(self):
        """
        Set up constraints for depot allocation and volume tier activation.
        """
        logger.info("Setting up constraints...")
        
        constraint_count = 0
        
        # Constraint 1: Each customer depot gets exactly one allocation
        for depot_id in self.cost_matrices:
            constraint_vars = []
            constraint_coeffs = []
            
            for supplier_depot_id in self.cost_matrices[depot_id]:
                available_options = self.availability_matrix[depot_id][supplier_depot_id]
                
                for option_type in self.option_types:
                    if option_type in available_options:
                        var_name = f"{option_type}_{depot_id}_{supplier_depot_id}"
                        if var_name in self.variable_indices:
                            constraint_vars.append(var_name)
                            constraint_coeffs.append(1.0)
            
            # Add constraint: sum of all options for this depot = 1
            if constraint_vars:
                self.model.linear_constraints.add(
                    lin_expr=[cplex.SparsePair(ind=constraint_vars, val=constraint_coeffs)],
                    senses=['E'],  # Equality
                    rhs=[1.0],
                    names=[f"depot_assignment_{depot_id}"]
                )
                constraint_count += 1
        
        # Constraint 2: Volume tier activation thresholds
        for tier_name, tier_config in self.tier_configurations.items():
            tier_var_name = f"VT_{tier_name}"
            tier_supplier_depots = tier_config.get('supplier_depots', [])
            tier_modes = tier_config.get('modes', [])
            
            # Get volume threshold (use highest band's min_volume)
            bands = tier_config.get('bands', [])
            tier_threshold = 0
            for band in bands:
                if band.get('rebate', 0) > 0:  # Find first band with positive rebate
                    tier_threshold = band.get('min_volume', 0)
                    break
            
            if tier_threshold > 0:
                constraint_vars = []
                constraint_coeffs = []
                
                # Sum volume across participating depots and modes
                for depot_id in self.cost_matrices:
                    depot_volume = self.customer_depots[depot_id]['annual_volume']
                    
                    for supplier_depot_id in self.cost_matrices[depot_id]:
                        # Check if this supplier depot participates in tier
                        if tier_supplier_depots != ['*'] and str(supplier_depot_id) not in tier_supplier_depots:
                            continue
                            
                        available_options = self.availability_matrix[depot_id][supplier_depot_id]
                        
                        for option_type in self.option_types:
                            if option_type in available_options:
                                # Check if this option matches tier modes
                                option_mode = 'COC' if option_type.startswith('coc_') else 'DEL'
                                if option_mode in tier_modes:
                                    var_name = f"{option_type}_{depot_id}_{supplier_depot_id}"
                                    if var_name in self.variable_indices:
                                        constraint_vars.append(var_name)
                                        constraint_coeffs.append(depot_volume)
                
                # Add big-M constraint: volume >= threshold * VT_bin
                if constraint_vars:
                    constraint_vars.append(tier_var_name)
                    constraint_coeffs.append(-tier_threshold)
                    
                    self.model.linear_constraints.add(
                        lin_expr=[cplex.SparsePair(ind=constraint_vars, val=constraint_coeffs)],
                        senses=['G'],  # Greater than or equal
                        rhs=[0.0],
                        names=[f"tier_threshold_{tier_name}"]
                    )
                    constraint_count += 1
        
        # Constraint 3: At most one tier per supplier-mode combination
        supplier_mode_tiers = {}
        for tier_name, tier_config in self.tier_configurations.items():
            suppliers = tier_config.get('suppliers', [])
            modes = tier_config.get('modes', [])
            
            for supplier in suppliers:
                for mode in modes:
                    key = f"{supplier}_{mode}"
                    if key not in supplier_mode_tiers:
                        supplier_mode_tiers[key] = []
                    supplier_mode_tiers[key].append(f"VT_{tier_name}")
        
        for key, tier_vars in supplier_mode_tiers.items():
            if len(tier_vars) > 1:  # Only add constraint if multiple tiers exist
                constraint_coeffs = [1.0] * len(tier_vars)
                self.model.linear_constraints.add(
                    lin_expr=[cplex.SparsePair(ind=tier_vars, val=constraint_coeffs)],
                    senses=['L'],  # Less than or equal
                    rhs=[1.0],
                    names=[f"tier_exclusion_{key}"]
                )
                constraint_count += 1
        
        logger.info(f"Added {constraint_count} total constraints (assignment + tier)")
        return self
    
    def solve_optimization(self) -> Dict[str, Any]:
        """
        Solve the optimization problem using CPLEX.
        
        Returns:
            Dict containing solution status and results
        """
        logger.info("Solving optimization problem...")
        
        try:
            # Solve the model
            self.model.solve()
            
            # Get solution status
            status = self.model.solution.get_status()
            status_string = self.model.solution.status[status]
            
            if status in [self.model.solution.status.optimal, self.model.solution.status.MIP_optimal]:
                logger.info(f"Optimal solution found! Status: {status_string}")
                
                # Get solution values
                variable_values = self.model.solution.get_values()
                objective_value = self.model.solution.get_objective_value()
                
                return {
                    'status': 'optimal',
                    'status_code': status,
                    'status_string': status_string,
                    'objective_value': objective_value,
                    'variable_values': dict(zip(self.variable_names, variable_values)),
                    'solution_summary': self._extract_solution_summary(variable_values)
                }
            else:
                logger.warning(f"Solution not optimal: {status_string}")
                return {
                    'status': status_string,
                    'status_code': status,
                    'objective_value': None,
                    'variable_values': None,
                    'solution_summary': None
                }
                
        except CplexError as e:
            logger.error(f"CPLEX error during optimization: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'objective_value': None,
                'variable_values': None,
                'solution_summary': None
            }
    
    def _extract_solution_summary(self, variable_values: List[float]) -> Dict[str, Any]:
        """
        Extract readable solution summary from variable values.
        
        Args:
            variable_values: List of variable values from CPLEX solution
            
        Returns:
            Dictionary with solution summary
        """
        allocations = []
        total_cost = 0
        
        for i, var_name in enumerate(self.variable_names):
            if variable_values[i] > 0.5:  # Binary variable is "1"
                # Parse variable name
                parts = var_name.split('_')
                option_type = parts[0] + '_' + parts[1] if parts[1] in ['cash', '30', '45', '60', 'own', 'buy', 'rent'] else parts[0]
                depot_id = int(parts[-2])
                supplier_depot_id = int(parts[-1])
                
                # Get allocation details
                cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id][option_type]
                depot_volume = self.customer_depots[depot_id]['annual_volume']
                total_depot_cost = depot_volume * cost_per_litre
                
                allocation = {
                    'customer_depot_id': depot_id,
                    'customer_depot_name': self.customer_depots[depot_id]['name'],
                    'supplier_depot_id': supplier_depot_id,
                    'supplier_name': self.supplier_depots[supplier_depot_id]['supplier_name'],
                    'option_type': option_type,
                    'annual_volume': depot_volume,
                    'cost_per_litre': cost_per_litre,
                    'total_cost': total_depot_cost,
                    'distance_km': self.supplier_depots[supplier_depot_id]['distance_km']
                }
                
                allocations.append(allocation)
                total_cost += total_depot_cost
        
        # Extract tier activation info
        active_tiers = []
        for tier_var in self.tier_variable_names:
            tier_index = len(self.variable_names) + self.tier_variable_names.index(tier_var)
            if tier_index < len(variable_values) and variable_values[tier_index] > 0.5:
                tier_name = tier_var.replace('VT_', '')
                active_tiers.append(tier_name)
        
        return {
            'total_allocations': len(allocations),
            'total_annual_cost': total_cost,
            'allocations': allocations,
            'active_tiers': active_tiers,
            'tier_count': len(active_tiers)
        }
    
    def run_optimization(self) -> Dict[str, Any]:
        """
        Run complete optimization pipeline (Phase 2 with volume tiers).
        
        Returns:
            Complete optimization results
        """
        logger.info("Starting Phase 2 optimization pipeline...")
        
        try:
            # Execute pipeline
            self.prepare_data()
            self.setup_decision_variables()
            self.setup_objective_function()
            self.setup_constraints()
            
            # Solve and return results
            results = self.solve_optimization()
            
            logger.info("Phase 2 optimization pipeline completed!")
            return results
            
        except Exception as e:
            logger.error(f"Error in optimization pipeline: {e}")
            return {
                'status': 'pipeline_error',
                'error': str(e),
                'objective_value': None,
                'variable_values': None,
                'solution_summary': None
            }


def main():
    """
    Test Phase 2 implementation with volume tiers
    """
    logger.info("Testing Phase 2 Fuel Depot Optimizer with Volume Tiers...")
    
    # Load precomputed data
    precomp = FuelOptimizationPrecomputation()
    precomputed_data = precomp.run_complete_precomputation()
    
    # Create optimizer and run
    optimizer = FuelDepotOptimizer(precomputed_data)
    results = optimizer.run_optimization()
    
    # Display results
    if results['status'] == 'optimal':
        summary = results['solution_summary']
        print(f"\n=== PHASE 2 OPTIMIZATION RESULTS ===")
        print(f"Status: {results['status']}")
        print(f"Total Annual Cost: R {summary['total_annual_cost']:,.2f}")
        print(f"Total Allocations: {summary['total_allocations']}")
        print(f"Active Volume Tiers: {summary['tier_count']}")
        
        if summary['active_tiers']:
            print(f"Activated Tiers: {', '.join(summary['active_tiers'])}")
        else:
            print("No volume tiers activated")
            
        print(f"\nSample Allocations:")
        for i, allocation in enumerate(summary['allocations'][:5]):
            print(f"  {i+1}. Depot {allocation['customer_depot_id']} → Supplier Depot {allocation['supplier_depot_id']}")
            print(f"     Option: {allocation['option_type']}, Volume: {allocation['annual_volume']:,} L")
            print(f"     Cost: R {allocation['cost_per_litre']:.4f}/L, Total: R {allocation['total_cost']:,.2f}")
    else:
        print(f"Optimization failed: {results['status']}")
        if 'error' in results:
            print(f"Error: {results['error']}")


if __name__ == "__main__":
    main()