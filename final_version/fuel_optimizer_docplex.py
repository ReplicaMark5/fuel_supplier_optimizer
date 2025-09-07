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
from optimization_map import OptimizationMapper

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
        self.supplier_depot_capacity_limits = {}
        
        # Decision variables (will be created by docplex)
        self.allocation_vars = {}  # [depot_id, supplier_depot_id, option] -> Variable
        self.tier_vars = {}        # [tier_name] -> Variable
        
        # Initialize mapper for visualization
        try:
            self.mapper = OptimizationMapper()
        except Exception as e:
            logger.warning(f"Could not initialize mapper: {e}")
            self.mapper = None
        
        # Option types (base, RAC, and volume tier enhanced)
        self.base_option_types = ['coc_cash', 'coc_30', 'coc_45', 'coc_60', 'del_own', 'del_buy', 'del_rent']
        self.rac_option_types = ['rac_coc_30', 'rac_del_own', 'rac_del_buy', 'rac_del_rent']
        self.tier_option_types = []  # Will be populated dynamically from cost data
        self.all_option_types = self.base_option_types + self.rac_option_types  # Tier options added dynamically
        
        # Load configuration
        self._load_configuration()
        
        logger.info("FuelDepotOptimizerDocplex initialized")
    
    def _load_configuration(self):
        """Load volume tier configurations and supplier capacity limits."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            self.contract_configurations = config.get('supplier_contract_configurations', {})
            self.supplier_depot_capacity_limits = config.get('supplier_depot_capacity_limits', {})
            # Remove description field if present
            if 'description' in self.supplier_depot_capacity_limits:
                del self.supplier_depot_capacity_limits['description']
            logger.info(f"Loaded {len(self.contract_configurations)} supplier contract configurations")
            logger.info(f"Loaded capacity limits for {len(self.supplier_depot_capacity_limits)} supplier depots")
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
            self.contract_configurations = {}
            self.supplier_depot_capacity_limits = {}
    
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
        
        # Contract variables: binary[contract_name] 
        for contract_name in self.contract_configurations:
            var_name = f"contract_{contract_name}"
            var = self.model.binary_var(name=var_name)
            self.tier_vars[contract_name] = var
        
        logger.info(f"Created {allocation_count} allocation variables + {len(self.tier_vars)} contract variables")
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
        
        # Constraint 2: Volume tier reward contract constraints
        # Volume tier rewards can only be used if the total volume for that contract is met
        for contract_name, contract_config in self.contract_configurations.items():
            # Skip RAC contracts - handled separately
            if contract_config.get('contract_type') == 'rebate_adjustment_clause':
                continue
            
            # Only handle volume tier reward contracts here
            if contract_config.get('contract_type') != 'volume_tier_rewards':
                continue
                
            contract_supplier_depots = contract_config.get('supplier_depots', [])
            contract_suppliers = contract_config.get('suppliers', [])
            transport_modes = contract_config.get('transport_modes', [])
            volume_calculation_modes = contract_config.get('volume_calculation_modes', transport_modes)
            
            # Get volume threshold for this contract
            contract_threshold = self._get_contract_threshold(contract_config)
            
            if contract_threshold > 0:
                # Find all tier option variables that belong to this tier
                tier_option_vars = []
                volume_contributing_vars = []
                
                for depot_id in self.cost_matrices:
                    depot_volume = self.customer_depots[depot_id]['annual_volume']
                    
                    for supplier_depot_id in self.cost_matrices[depot_id]:
                        # Check if this supplier depot participates in this contract
                        supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                        
                        if (contract_suppliers != ['*'] and supplier_name not in contract_suppliers):
                            continue
                        if (contract_supplier_depots != ['*'] and str(supplier_depot_id) not in contract_supplier_depots):
                            continue
                        
                        for option_type in self.all_option_types:
                            if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                                var = self.allocation_vars[(depot_id, supplier_depot_id, option_type)]
                                
                                # Check if this option belongs to this contract
                                if 'tier_' in option_type and self._option_belongs_to_contract(option_type, contract_name):
                                    tier_option_vars.append(var)
                                
                                # Check if this option contributes to volume calculation
                                option_mode = self._get_option_transport_mode(option_type)
                                if option_mode in volume_calculation_modes:
                                    # Include base options (excluding RAC)
                                    if 'tier_' not in option_type and not option_type.startswith('rac_'):
                                        volume_contributing_vars.append(depot_volume * var)
                                    # Also include tier options that belong to this contract and match transport modes
                                    elif 'tier_' in option_type and self._option_belongs_to_contract(option_type, contract_name):
                                        volume_contributing_vars.append(depot_volume * var)
                
                if tier_option_vars and volume_contributing_vars:
                    # Big M constraint: tier options can only be used if volume threshold is met
                    big_M = len(tier_option_vars)  # Maximum number of tier options that can be selected
                    
                    # If total volume < threshold, then no tier options can be used
                    # This is implemented as: sum(tier_options) <= big_M * (volume >= threshold)
                    # Where (volume >= threshold) is modeled using an auxiliary binary variable
                    
                    contract_var = self.tier_vars[contract_name]
                    
                    # Constraint: If contract is not active, no tier options can be selected
                    self.model.add_constraint(
                        self.model.sum(tier_option_vars) <= big_M * contract_var,
                        ctname=f"contract_options_require_activation_{contract_name}"
                    )
                    constraint_count += 1
                    
                    # Constraint: Contract is active only if volume threshold is met
                    total_volume = self.model.sum(volume_contributing_vars)
                    self.model.add_constraint(
                        total_volume >= contract_threshold * contract_var,
                        ctname=f"contract_threshold_{contract_name}"
                    )
                    constraint_count += 1
        
        # Constraint 3: RAC contract constraints (different logic than volume tier rewards)
        for contract_name, contract_config in self.contract_configurations.items():
            if contract_config.get('contract_type') == 'rebate_adjustment_clause':
                rac_threshold = self._get_contract_threshold(contract_config)
                rac_suppliers = contract_config.get('suppliers', [])
                rac_modes = contract_config.get('transport_modes', [])
                
                if rac_threshold > 0:
                    # RAC logic: if volume >= threshold, use base costs; if volume < threshold, use RAC costs
                    # This is modeled as mutual exclusion between base and RAC options for the same supplier
                    
                    rac_option_vars = []
                    base_option_vars = []
                    volume_contributing_vars = []
                    
                    for depot_id in self.cost_matrices:
                        depot_volume = self.customer_depots[depot_id]['annual_volume']
                        
                        for supplier_depot_id in self.cost_matrices[depot_id]:
                            supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                            
                            # Check if this supplier participates in this RAC contract
                            if (rac_suppliers != ['*'] and supplier_name not in rac_suppliers):
                                continue
                            
                            for option_type in self.all_option_types:
                                if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                                    var = self.allocation_vars[(depot_id, supplier_depot_id, option_type)]
                                    option_mode = self._get_option_transport_mode(option_type)
                                    
                                    # Check if this option is in RAC contract modes
                                    if option_mode in rac_modes:
                                        if option_type.startswith('rac_'):
                                            rac_option_vars.append(var)
                                        elif 'tier_' not in option_type:  # Base options only
                                            base_option_vars.append(var)
                                            volume_contributing_vars.append(depot_volume * var)
                    
                    if rac_option_vars and base_option_vars and volume_contributing_vars:
                        # RAC contract binary variable
                        contract_var = self.tier_vars[contract_name]
                        big_M = len(rac_option_vars + base_option_vars)
                        
                        # Constraint: If volume commitment is met (contract active), RAC options cannot be used
                        self.model.add_constraint(
                            self.model.sum(rac_option_vars) <= big_M * (1 - contract_var),
                            ctname=f"rac_penalty_when_volume_not_met_{contract_name}"
                        )
                        constraint_count += 1
                        
                        # Constraint: Contract is active only if volume threshold is met
                        total_volume = self.model.sum(volume_contributing_vars)
                        self.model.add_constraint(
                            total_volume >= rac_threshold * contract_var,
                            ctname=f"rac_contract_threshold_{contract_name}"
                        )
                        constraint_count += 1
                        
                        # Constraint: If volume commitment is not met (contract not active), base options cannot be used
                        # This enforces mutual exclusion: either base options (when commitment met) OR RAC options (when commitment not met)
                        self.model.add_constraint(
                            self.model.sum(base_option_vars) <= big_M * contract_var,
                            ctname=f"rac_force_penalty_when_volume_not_met_{contract_name}"
                        )
                        constraint_count += 1
                        
                        logger.info(f"Added RAC contract constraints for {contract_name}: {len(rac_option_vars)} RAC options, {len(base_option_vars)} base options")
        
        # Constraint 4: Supplier depot capacity limits
        capacity_constraint_count = 0
        for supplier_depot_id_str, capacity_limit in self.supplier_depot_capacity_limits.items():
            supplier_depot_id = int(supplier_depot_id_str)  # Convert string key to int
            if capacity_limit <= 0:
                continue
                
            # Find all allocation variables for this specific supplier depot
            depot_allocation_vars = []
            
            for depot_id in self.cost_matrices:
                if supplier_depot_id in self.cost_matrices[depot_id]:
                    depot_volume = self.customer_depots[depot_id]['annual_volume']
                    
                    # Add all allocation variables for this supplier depot
                    for option_type in self.all_option_types:
                        if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                            var = self.allocation_vars[(depot_id, supplier_depot_id, option_type)]
                            # Volume allocated = depot_volume * allocation_variable
                            depot_allocation_vars.append(depot_volume * var)
            
            if depot_allocation_vars:
                # Constraint: Total volume allocated to this supplier depot ≤ capacity limit
                total_depot_volume = self.model.sum(depot_allocation_vars)
                self.model.add_constraint(
                    total_depot_volume <= capacity_limit,
                    ctname=f"supplier_depot_capacity_{supplier_depot_id}"
                )
                capacity_constraint_count += 1
                supplier_depot_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', 'Unknown')
                logger.info(f"Added capacity constraint for supplier depot {supplier_depot_id} ({supplier_depot_name}): max {capacity_limit:,} litres from {len(depot_allocation_vars)} allocation variables")
        
        constraint_count += capacity_constraint_count
        logger.info(f"Added {constraint_count} total constraints ({capacity_constraint_count} supplier depot capacity constraints)")
        return self
    
    def _get_contract_threshold(self, contract_config: Dict[str, Any]) -> float:
        """Extract volume threshold from contract configuration."""
        if contract_config.get('contract_type') == 'rebate_adjustment_clause':
            # For RAC contracts, use the commitment threshold directly
            return contract_config.get('commitment_threshold', 0)
        elif contract_config.get('contract_type') == 'volume_tier_rewards':
            # For reward contracts, find first band with non-zero min_volume
            reward_bands = contract_config.get('reward_bands', [])
            for band in reward_bands:
                min_vol = band.get('min_volume', 0)
                if min_vol > 0:
                    return min_vol
        return 0
    
    
    def _get_option_transport_mode(self, option_type: str) -> str:
        """Extract transport mode from option type (handles both base and RAC options)."""
        if 'coc' in option_type:
            return 'COC'
        elif 'del' in option_type:
            return 'DEL'
        else:
            return 'UNKNOWN'
    
    def _option_belongs_to_contract(self, option_type: str, contract_name: str) -> bool:
        """Check if a tier option belongs to a specific contract configuration."""
        # Extract tier band from option name (e.g., "coc_30_tier_15M_to_20M" -> "15M_to_20M")
        if 'tier_' not in option_type:
            return False
        
        tier_part = option_type.split('tier_')[1]  # Get part after 'tier_'
        
        # Get contract configuration reward bands
        contract_config = self.contract_configurations.get(contract_name, {})
        reward_bands = contract_config.get('reward_bands', [])
        
        # Check if this tier part matches any band in the configuration
        for band in reward_bands:
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
        
        # Calculate supplier depot capacity utilization
        supplier_depot_utilization = {}
        for allocation in allocations:
            supplier_depot_id = allocation['supplier_depot_id']
            volume = allocation['annual_volume']
            
            if supplier_depot_id not in supplier_depot_utilization:
                supplier_depot_utilization[supplier_depot_id] = {
                    'used_volume': 0,
                    'capacity_limit': self.supplier_depot_capacity_limits.get(str(supplier_depot_id), 0),
                    'supplier_name': allocation['supplier_name'],
                    'depot_name': f"Supplier Depot {supplier_depot_id}"
                }
            
            supplier_depot_utilization[supplier_depot_id]['used_volume'] += volume
        
        # Calculate utilization percentages and identify binding constraints
        binding_constraints = []
        near_capacity_constraints = []
        
        for supplier_depot_id, util_data in supplier_depot_utilization.items():
            if util_data['capacity_limit'] > 0:  # Only process depots with defined capacity limits
                utilization_pct = (util_data['used_volume'] / util_data['capacity_limit']) * 100
                util_data['utilization_pct'] = utilization_pct
                
                # Consider binding if >= 99.5% utilized (accounting for numerical precision)
                if utilization_pct >= 99.5:
                    binding_constraints.append({
                        'supplier_depot_id': supplier_depot_id,
                        'supplier_name': util_data['supplier_name'],
                        'depot_name': util_data['depot_name'],
                        'used_volume': util_data['used_volume'],
                        'capacity_limit': util_data['capacity_limit'],
                        'utilization_pct': utilization_pct
                    })
                # Consider near capacity if >= 90% utilized
                elif utilization_pct >= 90:
                    near_capacity_constraints.append({
                        'supplier_depot_id': supplier_depot_id,
                        'supplier_name': util_data['supplier_name'],
                        'depot_name': util_data['depot_name'],
                        'used_volume': util_data['used_volume'],
                        'capacity_limit': util_data['capacity_limit'],
                        'utilization_pct': utilization_pct
                    })
        
        # Debug: print some allocation details
        print(f"\n=== SOLUTION DEBUG ===")
        print(f"CPLEX objective value: R {solution.objective_value:,.2f}")
        print(f"Manual cost calculation: R {total_cost:,.2f}")
        print(f"Active tier variables: {active_tiers}")
        
        # Print capacity utilization summary
        print(f"\n=== SUPPLIER DEPOT CAPACITY UTILIZATION ===")
        if binding_constraints:
            print(f"🔴 BINDING CONSTRAINTS ({len(binding_constraints)} depots at capacity):")
            for constraint in binding_constraints:
                print(f"  Depot {constraint['supplier_depot_id']} ({constraint['supplier_name']}): {constraint['used_volume']:,.0f}L / {constraint['capacity_limit']:,.0f}L ({constraint['utilization_pct']:.1f}%)")
        
        if near_capacity_constraints:
            print(f"🟡 NEAR CAPACITY ({len(near_capacity_constraints)} depots >90% utilized):")
            for constraint in near_capacity_constraints:
                print(f"  Depot {constraint['supplier_depot_id']} ({constraint['supplier_name']}): {constraint['used_volume']:,.0f}L / {constraint['capacity_limit']:,.0f}L ({constraint['utilization_pct']:.1f}%)")
        
        if not binding_constraints and not near_capacity_constraints:
            print("✅ No capacity constraints reached (all depots <90% utilized)")
        
        # Print top 5 most utilized depots
        sorted_utilization = sorted(
            [(k, v) for k, v in supplier_depot_utilization.items() if v['capacity_limit'] > 0], 
            key=lambda x: x[1]['utilization_pct'], 
            reverse=True
        )[:5]
        
        print(f"\n📊 TOP 5 MOST UTILIZED SUPPLIER DEPOTS:")
        for depot_id, util_data in sorted_utilization:
            print(f"  Depot {depot_id} ({util_data['supplier_name']}): {util_data['used_volume']:,.0f}L / {util_data['capacity_limit']:,.0f}L ({util_data['utilization_pct']:.1f}%)")
        
        print(f"\nAll allocations with costs:")
        for i, alloc in enumerate(allocations):
            savings_info = ""
            if alloc['base_cost_per_litre'] and alloc['cost_per_litre'] != alloc['base_cost_per_litre']:
                savings = alloc['base_cost_per_litre'] - alloc['cost_per_litre']
                savings_info = f" (saves R{savings:.4f}/L vs base R{alloc['base_cost_per_litre']:.4f}/L)"
            print(f"  Depot {alloc['customer_depot_id']} → Supplier Depot {alloc['supplier_depot_id']} ({alloc['supplier_name']}): {alloc['annual_volume']:,.0f}L × R{alloc['cost_per_litre']:.4f}/L = R{alloc['total_cost']:,.2f} ({alloc['cost_type']}){savings_info}")
        
        return {
            'total_allocations': len(allocations),
            'total_annual_cost': total_cost,
            'allocations': allocations,
            'active_tiers': active_tiers,
            'tier_count': len(active_tiers),
            'supplier_depot_utilization': supplier_depot_utilization,
            'binding_capacity_constraints': binding_constraints,
            'near_capacity_constraints': near_capacity_constraints,
            'capacity_summary': {
                'total_supplier_depots_used': len(supplier_depot_utilization),
                'binding_constraints_count': len(binding_constraints),
                'near_capacity_count': len(near_capacity_constraints)
            }
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
    
    def generate_allocation_map(self, results: Dict[str, Any], save_path: str = "optimization_allocation_map.html") -> str:
        """
        Generate an enhanced interactive map showing all routes and optimization results.
        
        Args:
            results: Optimization results containing allocations and capacity data
            save_path: Path to save the HTML map file
            
        Returns:
            str: Path to the generated map file
        """
        if not self.mapper:
            logger.warning("Mapper not initialized - cannot generate map")
            return None
        
        try:
            # Create comprehensive data package for enhanced mapping
            comprehensive_data = {
                'optimization_results': results,              # Current optimization results
                'all_route_costs': self.precomputed_data,     # Complete precomputed cost dictionary
                'capacity_limits': self.supplier_depot_capacity_limits,  # Capacity constraints
                'optimization_metadata': {
                    'total_cost': results.get('total_annual_cost'),
                    'active_tiers': results.get('active_tiers', []),
                    'binding_constraints': results.get('binding_capacity_constraints', []),
                    'near_capacity_constraints': results.get('near_capacity_constraints', []),
                    'total_allocations': results.get('total_allocations', 0)
                }
            }
            
            # Use enhanced allocation mapping
            map_path = self.mapper.create_enhanced_allocation_map(comprehensive_data, save_path)
            logger.info(f"Enhanced allocation map generated: {map_path}")
            
            return map_path
            
        except Exception as e:
            logger.error(f"Failed to generate map: {e}")
            return None
    
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
            
            # Generate allocation map if optimization was successful
            if results['status'] == 'optimal' and results.get('allocations'):
                try:
                    map_path = self.generate_allocation_map(results)
                    if map_path:
                        results['map_path'] = map_path
                        logger.info(f"Interactive allocation map saved to: {map_path}")
                except Exception as e:
                    logger.warning(f"Could not generate allocation map: {e}")
            
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
        
        # Supplier summary
        supplier_stats = {}
        for allocation in results['allocations']:
            supplier_name = allocation['supplier_name']
            if supplier_name not in supplier_stats:
                supplier_stats[supplier_name] = {
                    'count': 0,
                    'total_volume': 0,
                    'total_cost': 0
                }
            supplier_stats[supplier_name]['count'] += 1
            supplier_stats[supplier_name]['total_volume'] += allocation['annual_volume']
            supplier_stats[supplier_name]['total_cost'] += allocation['total_cost']
        
        print(f"\n=== SUPPLIER UTILIZATION ===")
        for supplier_name, stats in sorted(supplier_stats.items()):
            print(f"{supplier_name}:")
            print(f"  - Allocations: {stats['count']}")
            print(f"  - Total Volume: {stats['total_volume']:,} L")
            print(f"  - Total Cost: R {stats['total_cost']:,.2f}")
            print(f"  - Avg Cost/L: R {stats['total_cost']/stats['total_volume']:.4f}")
            
        print(f"\nAll Allocations:")
        for i, allocation in enumerate(results['allocations']):
            print(f"  {i+1}. Depot {allocation['customer_depot_id']} → Supplier Depot {allocation['supplier_depot_id']} ({allocation['supplier_name']})")
            print(f"     Option: {allocation['option_type']}, Volume: {allocation['annual_volume']:,} L")
            print(f"     Cost: R {allocation['cost_per_litre']:.4f}/L, Total: R {allocation['total_cost']:,.2f}")
    else:
        print(f"Optimization failed: {results['status']}")
        if 'error' in results:
            print(f"Error: {results['error']}")


if __name__ == "__main__":
    main()