#!/usr/bin/env python3
"""
Fuel Depot Allocation Optimizer using DOcplex (IBM Decision Optimization CPLEX Modeling for Python)

This implementation uses the high-level docplex modeling API which provides:
- Cleaner, more intuitive syntax
- Automatic variable management  
- Simplified constraint definitions
- Better debugging capabilities
- More readable code structure
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path

try:
    from docplex.mp.model import Model
except ImportError:
    raise ImportError("docplex not found. Please install IBM Decision Optimization CPLEX Modeling for Python: pip install docplex")

from precomputation import FuelOptimizationPrecomputation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FuelDepotOptimizerDocplex:
    """
    DOcplex-based optimizer for fuel depot allocation with volume tier support.
    
    Much cleaner implementation using high-level modeling API.
    """
    
    def __init__(self, precomputed_data: Dict[str, Any], config_path: str = "optimization_config.json"):
        """Initialize optimizer with precomputed cost data."""
        self.precomputed_data = precomputed_data
        self.config_path = config_path
        
        # Create DOcplex model
        self.model = Model(name="FuelDepotAllocation")
        
        # Data structures
        self.customer_depots = {}
        self.supplier_depots = {}
        self.cost_matrices = {}
        self.availability_matrix = {}
        self.tier_configurations = {}
        self.tier_costs = {}
        
        # Decision variables (will be created by docplex)
        self.allocation_vars = {}  # [depot_id, supplier_depot_id, option] -> Variable
        self.tier_vars = {}        # [tier_name] -> Variable
        
        # Option types (base, RAC, and volume tier enhanced)
        self.base_option_types = ['coc_cash', 'coc_30', 'coc_45', 'coc_60', 'del_own', 'del_buy', 'del_rent']
        self.rac_option_types = ['rac_coc_cash', 'rac_coc_30', 'rac_coc_45', 'rac_coc_60', 'rac_del_own', 'rac_del_buy', 'rac_del_rent']
        self.tier_option_types = []  # Will be populated dynamically from cost data
        self.all_option_types = self.base_option_types + self.rac_option_types  # Tier options added dynamically
        
        # Load configuration
        self._load_configuration()
        
        logger.info("FuelDepotOptimizerDocplex initialized")
    
    def _load_configuration(self):
        """Load volume tier configurations."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            self.tier_configurations = config.get('volume_tier_configurations', {})
            logger.info(f"Loaded {len(self.tier_configurations)} volume tier configurations")
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
            self.tier_configurations = {}
    
    def prepare_data(self):
        """Extract and structure data from precomputed dictionary."""
        logger.info("Preparing data structures...")
        
        # Extract depot information
        self.customer_depots = self.precomputed_data['depots'].copy()
        self.suppliers = self.precomputed_data['suppliers'].copy()
        
        # Extract cost matrices and availability
        costs_data = self.precomputed_data['costs']
        
        # Discover tier option types from cost data
        tier_options_discovered = set()
        
        for depot_id, supplier_depots in costs_data.items():
            if depot_id not in self.cost_matrices:
                self.cost_matrices[depot_id] = {}
                self.availability_matrix[depot_id] = {}
                self.tier_costs[depot_id] = {}
            
            for supplier_depot_id, depot_data in supplier_depots.items():
                # All costs are now at the same level (base + RAC + tier enhanced costs)
                self.cost_matrices[depot_id][supplier_depot_id] = depot_data.copy()
                
                # Extract available options from cost keys
                available_options = list(depot_data.keys())
                self.availability_matrix[depot_id][supplier_depot_id] = available_options
                
                # Discover tier options (options with 'tier_' in the name)
                for option in available_options:
                    if 'tier_' in option and ('coc_' in option or 'del_' in option):
                        tier_options_discovered.add(option)
                
                # Supplier depot info
                if supplier_depot_id not in self.supplier_depots:
                    self.supplier_depots[supplier_depot_id] = {
                        'supplier_id': depot_data.get('supplier_id'),
                        'supplier_name': depot_data.get('supplier_name'),
                        'distance_km': depot_data.get('distance_km')
                    }
        
        # Update tier option types and all option types
        self.tier_option_types = sorted(list(tier_options_discovered))
        self.all_option_types = self.base_option_types + self.rac_option_types + self.tier_option_types
        
        total_combinations = sum(len(sd) for sd in self.cost_matrices.values())
        logger.info(f"Prepared {total_combinations} depot-supplier combinations")
        logger.info(f"Discovered {len(self.tier_option_types)} volume tier enhanced cost options: {self.tier_option_types[:5]}...")
        return self
    
    def create_decision_variables(self):
        """Create decision variables using docplex."""
        logger.info("Creating decision variables...")
        
        # Allocation variables: binary[depot, supplier_depot, option]
        allocation_count = 0
        for depot_id in self.cost_matrices:
            for supplier_depot_id in self.cost_matrices[depot_id]:
                available_options = self.availability_matrix[depot_id][supplier_depot_id]
                
                for option_type in self.all_option_types:
                    if option_type in available_options:
                        var_name = f"alloc_{depot_id}_{supplier_depot_id}_{option_type}"
                        var = self.model.binary_var(name=var_name)
                        self.allocation_vars[(depot_id, supplier_depot_id, option_type)] = var
                        allocation_count += 1
        
        # Volume tier variables: binary[tier_name]
        for tier_name in self.tier_configurations:
            var_name = f"tier_{tier_name}"
            var = self.model.binary_var(name=var_name)
            self.tier_vars[tier_name] = var
        
        logger.info(f"Created {allocation_count} allocation variables + {len(self.tier_vars)} tier variables")
        return self
    
    def set_objective(self):
        """
        Set simplified objective function using all precomputed costs directly.
        
        All cost options (base, RAC, and volume tier enhanced) are now precomputed 
        and available in the cost matrix, so we can use them directly.
        """
        logger.info("Setting up objective function with all precomputed costs...")
        
        objective_terms = []
        
        for (depot_id, supplier_depot_id, option_type), allocation_var in self.allocation_vars.items():
            # Validate data inputs
            depot_volume = self.customer_depots[depot_id]['annual_volume']
            cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id][option_type]
            
            # Check for invalid values
            if depot_volume is None or str(depot_volume).lower() in ['nan', 'inf', '-inf']:
                logger.warning(f"Invalid depot volume for depot {depot_id}: {depot_volume}")
                continue
                
            if cost_per_litre is None or str(cost_per_litre).lower() in ['nan', 'inf', '-inf']:
                logger.warning(f"Invalid cost for depot {depot_id}, supplier depot {supplier_depot_id}, option {option_type}: {cost_per_litre}")
                continue
            
            try:
                depot_volume = float(depot_volume)
                cost_per_litre = float(cost_per_litre)
                total_cost = depot_volume * cost_per_litre
            except (ValueError, TypeError) as e:
                logger.warning(f"Error converting to float: depot_volume={depot_volume}, cost={cost_per_litre}, error={e}")
                continue
            
            # Add cost term to objective (all costs are precomputed)
            objective_terms.append(total_cost * allocation_var)
        
        # Set objective: minimize total cost
        objective_expr = self.model.sum(objective_terms)
        self.model.minimize(objective_expr)
        
        logger.info(f"Objective function set with {len(objective_terms)} cost terms")
        return self
    
    def add_constraints(self):
        """Add all constraints to the model."""
        logger.info("Adding constraints...")
        
        constraint_count = 0
        
        # Constraint 1: Each customer depot gets exactly one allocation
        for depot_id in self.cost_matrices:
            depot_vars = []
            
            for supplier_depot_id in self.cost_matrices[depot_id]:
                for option_type in self.all_option_types:
                    if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                        depot_vars.append(self.allocation_vars[(depot_id, supplier_depot_id, option_type)])
            
            if depot_vars:
                constraint_name = f"depot_assignment_{depot_id}"
                self.model.add_constraint(
                    self.model.sum(depot_vars) == 1,
                    ctname=constraint_name
                )
                constraint_count += 1
        
        # Constraint 2: Volume tier logical constraints
        # Simplified approach: tier options can only be used if the total volume for that tier is met
        for tier_name, tier_config in self.tier_configurations.items():
            tier_supplier_depots = tier_config.get('supplier_depots', [])
            tier_suppliers = tier_config.get('suppliers', [])
            tier_modes = tier_config.get('transport_modes', [])
            is_rac_tier = tier_config.get('Rebate_adjustment_clause', False)
            
            # Get volume threshold for this tier
            tier_threshold = self._get_tier_threshold(tier_config)
            
            if tier_threshold > 0 and not is_rac_tier:  # Skip RAC tiers for now, handle separately
                # Find all tier option variables that belong to this tier
                tier_option_vars = []
                volume_contributing_vars = []
                
                for depot_id in self.cost_matrices:
                    depot_volume = self.customer_depots[depot_id]['annual_volume']
                    
                    for supplier_depot_id in self.cost_matrices[depot_id]:
                        # Check if this supplier depot participates in this tier
                        supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                        
                        if (tier_suppliers != ['*'] and supplier_name not in tier_suppliers):
                            continue
                        if (tier_supplier_depots != ['*'] and str(supplier_depot_id) not in tier_supplier_depots):
                            continue
                        
                        for option_type in self.all_option_types:
                            if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                                var = self.allocation_vars[(depot_id, supplier_depot_id, option_type)]
                                
                                # Check if this option belongs to this tier
                                if 'tier_' in option_type and self._option_belongs_to_tier(option_type, tier_name):
                                    tier_option_vars.append(var)
                                
                                # Check if this option contributes to tier volume calculation
                                option_mode = self._get_option_transport_mode(option_type)
                                if (option_mode in tier_modes and 
                                    'tier_' not in option_type and 
                                    not option_type.startswith('rac_')):  # Only base options count for volume
                                    volume_contributing_vars.append(depot_volume * var)
                
                if tier_option_vars and volume_contributing_vars:
                    # Big M constraint: tier options can only be used if volume threshold is met
                    big_M = len(tier_option_vars)  # Maximum number of tier options that can be selected
                    
                    # If total volume < threshold, then no tier options can be used
                    # This is implemented as: sum(tier_options) <= big_M * (volume >= threshold)
                    # Where (volume >= threshold) is modeled using an auxiliary binary variable
                    
                    tier_var = self.tier_vars[tier_name]
                    
                    # Constraint: If tier is not active, no tier options can be selected
                    self.model.add_constraint(
                        self.model.sum(tier_option_vars) <= big_M * tier_var,
                        ctname=f"tier_options_require_activation_{tier_name}"
                    )
                    constraint_count += 1
                    
                    # Constraint: Tier is active only if volume threshold is met
                    total_volume = self.model.sum(volume_contributing_vars)
                    self.model.add_constraint(
                        total_volume >= tier_threshold * tier_var,
                        ctname=f"tier_threshold_{tier_name}"
                    )
                    constraint_count += 1
        
        logger.info(f"Added {constraint_count} constraints")
        return self
    
    def _get_tier_threshold(self, tier_config: Dict[str, Any]) -> float:
        """Extract volume threshold from tier configuration."""
        bands = tier_config.get('bands', [])
        
        # For RAC tiers, the threshold is the second band (where commitment kicks in)
        if tier_config.get('Rebate_adjustment_clause', False):
            if len(bands) >= 2:
                return bands[1].get('min_volume', 0)
        else:
            # For standard tiers, find first band with non-zero min_volume
            for band in bands:
                min_vol = band.get('min_volume', 0)
                if min_vol > 0:
                    return min_vol
        return 0
    
    def _group_tiers_by_supplier_mode(self) -> Dict[str, List[str]]:
        """Group tier configurations by supplier-mode to enforce mutual exclusion."""
        groups = {}
        
        for tier_name, tier_config in self.tier_configurations.items():
            suppliers = tier_config.get('suppliers', [])
            modes = tier_config.get('modes', [])
            
            for supplier in suppliers:
                for mode in modes:
                    group_key = f"{supplier}_{mode}"
                    if group_key not in groups:
                        groups[group_key] = []
                    groups[group_key].append(tier_name)
        
        return groups
    
    def _get_option_transport_mode(self, option_type: str) -> str:
        """Extract transport mode from option type (handles both base and RAC options)."""
        if 'coc' in option_type:
            return 'COC'
        elif 'del' in option_type:
            return 'DEL'
        else:
            return 'UNKNOWN'
    
    def _option_belongs_to_tier(self, option_type: str, tier_name: str) -> bool:
        """Check if a tier option belongs to a specific tier configuration."""
        # Extract tier band from option name (e.g., "coc_30_tier_15M_to_20M" -> "15M_to_20M")
        if 'tier_' not in option_type:
            return False
        
        tier_part = option_type.split('tier_')[1]  # Get part after 'tier_'
        
        # Get tier configuration bands
        tier_config = self.tier_configurations.get(tier_name, {})
        bands = tier_config.get('bands', [])
        
        # Check if this tier part matches any band in the configuration
        for band in bands:
            min_vol = band.get('min_volume', 0)
            max_vol = band.get('max_volume')
            
            # Convert band to expected tier name format
            if min_vol > 0:
                min_str = f"{min_vol//1000000}M" if min_vol >= 1000000 else str(min_vol)
                if max_vol:
                    max_str = f"{max_vol//1000000}M" if max_vol >= 1000000 else str(max_vol)
                    expected_band = f"{min_str}_to_{max_str}"
                else:
                    expected_band = f"{min_str}_plus"
                
                if expected_band in tier_part:
                    return True
        
        return False
    
    def _get_applicable_tiers_for_allocation(self, depot_id: int, supplier_depot_id: int, option_type: str) -> List[str]:
        """Get tiers that apply to a specific allocation."""
        applicable_tiers = []
        
        # Get supplier info
        supplier_info = self.supplier_depots.get(supplier_depot_id, {})
        supplier_name = supplier_info.get('supplier_name', '')
        
        for tier_name, tier_config in self.tier_configurations.items():
            # Check supplier match
            tier_suppliers = tier_config.get('suppliers', [])
            if tier_suppliers != ['*'] and supplier_name not in tier_suppliers:
                continue
            
            # Check supplier depot match
            tier_supplier_depots = tier_config.get('supplier_depots', ['*'])
            if tier_supplier_depots != ['*'] and str(supplier_depot_id) not in tier_supplier_depots:
                continue
            
            # Check mode match
            tier_modes = tier_config.get('transport_modes', tier_config.get('modes', []))
            option_mode = 'COC' if option_type.startswith('coc_') else 'DEL'
            if option_mode in tier_modes:
                applicable_tiers.append(tier_name)
        
        return applicable_tiers
    
    def _get_tier_cost(self, depot_id: int, supplier_depot_id: int, tier_name: str, option_type: str) -> float:
        """Get tier cost per litre for a specific allocation-tier combination."""
        tier_costs = self.tier_costs.get(depot_id, {}).get(supplier_depot_id, {})
        
        if tier_name in tier_costs:
            tier_cost_data = tier_costs[tier_name]
            
            if isinstance(tier_cost_data, dict):
                # Tier costs stored as nested dict with option-specific costs
                for tier_option, tier_cost_per_litre in tier_cost_data.items():
                    if (option_type.replace('_', '') in tier_option or 
                        option_type in tier_option or
                        tier_option.endswith('30') and option_type.endswith('30')):
                        # Check for NaN or invalid values
                        if tier_cost_per_litre is not None and str(tier_cost_per_litre).lower() not in ['nan', 'inf', '-inf']:
                            try:
                                return float(tier_cost_per_litre)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid tier cost value: {tier_cost_per_litre}")
                                return None
                        return None
                return None  # No matching tier option found
            else:
                # Direct tier cost value - validate
                if tier_cost_data is not None and str(tier_cost_data).lower() not in ['nan', 'inf', '-inf']:
                    try:
                        return float(tier_cost_data)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid tier cost value: {tier_cost_data}")
                        return None
        
        return None
    
    def solve(self) -> Dict[str, Any]:
        """Solve the optimization model."""
        logger.info("Solving optimization model...")
        
        # Solve the model
        solution = self.model.solve()
        
        if solution:
            logger.info(f"Optimal solution found! Objective value: R {solution.objective_value:,.2f}")
            
            # Extract solution details
            results = self._extract_solution(solution)
            results['status'] = 'optimal'
            results['objective_value'] = solution.objective_value
            
            return results
        else:
            logger.error("No solution found")
            return {
                'status': 'no_solution',
                'objective_value': None,
                'allocations': [],
                'active_tiers': [],
                'solve_details': self.model.solve_details
            }
    
    def _extract_solution(self, solution) -> Dict[str, Any]:
        """Extract readable solution from docplex solution object."""
        allocations = []
        total_cost = 0
        
        # Extract allocations
        for (depot_id, supplier_depot_id, option_type), var in self.allocation_vars.items():
            if solution.get_value(var) > 0.5:  # Variable is selected
                depot_volume = self.customer_depots[depot_id]['annual_volume']
                
                # Get actual cost used (this is already the correct cost from precomputation)
                actual_cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id][option_type]
                
                # Determine cost type based on option name
                if 'tier_' in option_type:
                    cost_type = "tier_enhanced"
                    active_tier = self._extract_tier_from_option(option_type)
                    base_option_type = self._get_base_option_from_tier(option_type)
                    base_cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id].get(base_option_type)
                elif option_type.startswith('rac_'):
                    cost_type = "rac_penalty"
                    active_tier = None
                    base_option_type = option_type.replace('rac_', '')
                    base_cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id].get(base_option_type)
                else:
                    cost_type = "base"
                    active_tier = None
                    base_cost_per_litre = actual_cost_per_litre
                
                total_depot_cost = depot_volume * actual_cost_per_litre
                
                allocation = {
                    'customer_depot_id': depot_id,
                    'customer_depot_name': self.customer_depots[depot_id]['name'],
                    'supplier_depot_id': supplier_depot_id,
                    'supplier_name': self.supplier_depots[supplier_depot_id]['supplier_name'],
                    'option_type': option_type,
                    'annual_volume': depot_volume,
                    'cost_per_litre': actual_cost_per_litre,
                    'total_cost': total_depot_cost,
                    'distance_km': self.supplier_depots[supplier_depot_id]['distance_km'],
                    'cost_type': cost_type,
                    'base_cost_per_litre': base_cost_per_litre,
                    'active_tier': active_tier
                }
                allocations.append(allocation)
                total_cost += total_depot_cost
        
        # Extract active tiers from tier variables
        active_tiers = []
        for tier_name, var in self.tier_vars.items():
            if solution.get_value(var) > 0.5:
                active_tiers.append(tier_name)
        
        # Debug: print some allocation details
        print(f"\n=== SOLUTION DEBUG ===")
        print(f"CPLEX objective value: R {solution.objective_value:,.2f}")
        print(f"Manual cost calculation: R {total_cost:,.2f}")
        print(f"Active tier variables: {active_tiers}")
        print(f"Sample allocations with costs:")
        for i, alloc in enumerate(allocations[:5]):
            savings_info = ""
            if alloc['base_cost_per_litre'] and alloc['cost_per_litre'] != alloc['base_cost_per_litre']:
                savings = alloc['base_cost_per_litre'] - alloc['cost_per_litre']
                savings_info = f" (saves R{savings:.4f}/L vs base R{alloc['base_cost_per_litre']:.4f}/L)"
            print(f"  Depot {alloc['customer_depot_id']}: {alloc['annual_volume']:,.0f}L × R{alloc['cost_per_litre']:.4f}/L = R{alloc['total_cost']:,.2f} ({alloc['cost_type']}){savings_info}")
        
        return {
            'total_allocations': len(allocations),
            'total_annual_cost': total_cost,
            'allocations': allocations,
            'active_tiers': active_tiers,
            'tier_count': len(active_tiers)
        }
    
    def _extract_tier_from_option(self, option_type: str) -> str:
        """Extract tier name from tier option (e.g., 'coc_30_tier_15M_to_20M' -> '15M_to_20M')."""
        if 'tier_' in option_type:
            return option_type.split('tier_')[1]
        return None
    
    def _get_base_option_from_tier(self, tier_option: str) -> str:
        """Get base option from tier option (e.g., 'coc_30_tier_15M_to_20M' -> 'coc_30')."""
        if 'tier_' in tier_option:
            return tier_option.split('_tier_')[0]
        return tier_option
    
    def run_optimization(self) -> Dict[str, Any]:
        """Run complete optimization pipeline."""
        logger.info("Starting DOcplex optimization pipeline...")
        
        try:
            # Execute pipeline
            self.prepare_data()
            self.create_decision_variables()
            self.set_objective()
            self.add_constraints()
            
            # Solve and return results
            results = self.solve()
            
            logger.info("DOcplex optimization pipeline completed!")
            return results
            
        except Exception as e:
            logger.error(f"Error in optimization pipeline: {e}")
            return {
                'status': 'pipeline_error',
                'error': str(e),
                'objective_value': None,
                'allocations': [],
                'active_tiers': []
            }
    
    def print_model_info(self):
        """Print model statistics for debugging."""
        print(f"\n=== MODEL INFORMATION ===")
        print(f"Variables: {self.model.number_of_variables}")
        print(f"Binary Variables: {self.model.number_of_binary_variables}")
        print(f"Constraints: {self.model.number_of_constraints}")
        print(f"Linear Constraints: {self.model.number_of_linear_constraints}")


def main():
    """Test DOcplex implementation."""
    logger.info("Testing DOcplex Fuel Depot Optimizer...")
    
    # Load precomputed data
    precomp = FuelOptimizationPrecomputation()
    precomputed_data = precomp.run_complete_precomputation()
    
    # Create optimizer
    optimizer = FuelDepotOptimizerDocplex(precomputed_data)
    
    # Run optimization
    results = optimizer.run_optimization()
    
    # Print model info
    optimizer.print_model_info()
    
    # Display results
    if results['status'] == 'optimal':
        print(f"\n=== DOCPLEX OPTIMIZATION RESULTS ===")
        print(f"Status: {results['status']}")
        print(f"Total Annual Cost: R {results['total_annual_cost']:,.2f}")
        print(f"Total Allocations: {results['total_allocations']}")
        print(f"Active Volume Tiers: {results['tier_count']}")
        
        if results['active_tiers']:
            print(f"Activated Tiers: {', '.join(results['active_tiers'])}")
        else:
            print("No volume tiers activated")
            
        print(f"\nSample Allocations:")
        for i, allocation in enumerate(results['allocations'][:5]):
            print(f"  {i+1}. Depot {allocation['customer_depot_id']} → Supplier Depot {allocation['supplier_depot_id']}")
            print(f"     Option: {allocation['option_type']}, Volume: {allocation['annual_volume']:,} L")
            print(f"     Cost: R {allocation['cost_per_litre']:.4f}/L, Total: R {allocation['total_cost']:,.2f}")
    else:
        print(f"Optimization failed: {results['status']}")
        if 'error' in results:
            print(f"Error: {results['error']}")


if __name__ == "__main__":
    main()