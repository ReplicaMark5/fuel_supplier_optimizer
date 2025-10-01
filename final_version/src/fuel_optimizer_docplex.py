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
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

try:
    from docplex.mp.model import Model
except ImportError:
    raise ImportError("docplex not found. Please install IBM Decision Optimization CPLEX Modeling for Python: pip install docplex")

from .precomputation import FuelOptimizationPrecomputation
from .visualization.optimization_map import OptimizationMapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FuelDepotOptimizerDocplex:
    """
    DOcplex-based optimizer for fuel depot allocation with volume tier support.
    
    Much cleaner implementation using high-level modeling API.
    """
    
    def __init__(self, precomputed_data: Dict[str, Any], config_path: str = str(Path(__file__).resolve().parents[1] / "data/config/optimization_config.json"), db_path: str = str(Path(__file__).resolve().parents[1] / "data/databases/fuel_data.db")):
        """Initialize optimizer with precomputed cost data."""
        self.precomputed_data = precomputed_data
        self.config_path = config_path
        self.db_path = db_path
        
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
        self.tier_vars = {}        # [contract_name] -> Variable (for RAC contracts)
        self.tier_band_vars = {}   # [contract_name, tier_name] -> Variable (for volume tier bands)
        self.tier_selection_vars = {}  # [contract_name, tier_name] -> Variable (for all_units selection)
        self.band_volume_vars = {}     # [option_key, tier_name] -> Variable (for incremental s_{o,b})
        
        # Initialize mapper for visualization
        try:
            self.mapper = OptimizationMapper()
        except Exception as e:
            logger.warning(f"Could not initialize mapper: {e}")
            self.mapper = None
        
        # Option types (base, RAC, and volume tier enhanced)
        self.base_option_types = ['coc_cash', 'coc_30', 'coc_45', 'coc_60', 'del_own', 'del_rent']
        self.rac_option_types = ['rac_coc_30', 'rac_del_own', 'rac_del_rent']
        self.tier_option_types = []  # Will be populated dynamically from cost data
        self.all_option_types = self.base_option_types + self.rac_option_types  # Tier options added dynamically
        
        # Load configuration
        self._load_configuration()
        
        # Load country constraint configuration  
        self.country_constraints = self._load_country_constraints()

        logger.info("FuelDepotOptimizerDocplex initialized")

    # ===== HELPER UTILITIES FOR INDICATOR-BASED CONSTRAINTS =====

    def gate_binary_group_with_selector(self, selector_bvar, bin_vars):
        # For binary decision vars, x <= selector is tight and M-free.
        for x in bin_vars:
            self.model.add_constraint(x <= selector_bvar)

    def hard_zero_when(self, trigger_bvar, vars_to_zero):
        # Linear equivalent that works with any Docplex version
        # For binary variables: v <= 1 - trigger_var is equivalent to "if trigger=1 then v=0"
        for v in vars_to_zero:
            self.model.add_constraint(v <= (1 - trigger_bvar))
        if vars_to_zero:
            logger.debug(f"Added {len(vars_to_zero)} linear Big-M equivalent constraints")

    def or_of_binaries(self, binaries, name_prefix):
        # Returns y_any = OR(binaries) with tight linearization:
        if not binaries:
            # Handle empty case - create a constant 0 binary
            y_any = self.model.binary_var(name=f"{name_prefix}_any_empty")
            self.model.add_constraint(y_any == 0)
            return y_any

        y_any = self.model.binary_var(name=f"{name_prefix}_any")
        # y_any >= each s_b
        for b in binaries:
            self.model.add_constraint(y_any >= b)
        # y_any <= sum s_b  (prevents y_any=1 when all zero)
        self.model.add_constraint(y_any <= self.model.sum(binaries))
        return y_any

    def complement(self, bvar, name):
        # Returns c = 1 - bvar as a binary with equality
        c = self.model.binary_var(name=name)
        self.model.add_constraint(bvar + c == 1)
        return c
    
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
    
    def _load_country_constraints(self):
        """Load country allocation constraint configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            country_config = config.get('country_allocation_constraints', {})
            
            if country_config.get('enabled', False):
                logger.info(f"Country allocation constraints enabled")
                restrictions = country_config.get('cross_border_restrictions', {})
                logger.info(f"Loaded cross-border restrictions for {len(restrictions)} countries")
                return country_config
            else:
                logger.info("Country allocation constraints disabled")
                return {'enabled': False}
        except Exception as e:
            logger.warning(f"Could not load country constraints config: {e}")
            return {'enabled': False}
    
    def _get_tiering_regime(self, contract_config) -> str:
        """Get the tiering regime for a contract, defaulting to 'all_units'."""
        return contract_config.get('tiering_regime', 'all_units')
    
    def _band_width(self, band) -> float:
        """Calculate the width of a tier band."""
        min_vol = band.get('min_volume', 0)
        max_vol = band.get('max_volume')
        if max_vol is None:
            # Use a large number for unlimited bands  
            return 1e9
        return max(max_vol - min_vol, 0)
    
    def _option_belongs_to_incremental_contract(self, option_type: str, contract_name: str) -> bool:
        """Check if an option belongs to an incremental contract (base options only)."""
        # For incremental contracts, we only use base options (no tier_ options)
        if 'tier_' in option_type or option_type.startswith('rac_'):
            return False
        
        # Check if option's supplier matches contract
        contract_config = self.contract_configurations.get(contract_name, {})
        regime = self._get_tiering_regime(contract_config)
        
        return regime == 'incremental'
    
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
        
        # Prepare strategic supplier scores
        self._prepare_strategic_scores()
        
        return self
    
    def _prepare_strategic_scores(self):
        """Prepare strategic scores for suppliers used in the optimization."""
        logger.info("Preparing strategic supplier scores...")
        
        # Get mapping from supplier IDs to names
        supplier_id_to_name = {}
        for supplier_depot_data in self.supplier_depots.values():
            supplier_id = supplier_depot_data.get('supplier_id')
            supplier_name = supplier_depot_data.get('supplier_name', f'Supplier {supplier_id}')
            if supplier_id is not None:
                supplier_id_to_name[supplier_id] = supplier_name
        
        # Strategic scores are now included in the cost dictionary from precomputation
        logger.info("Strategic scores available from precomputed cost dictionary")
    
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
        
        # Contract variables: binary[contract_name] for RAC contracts
        # Tier band variables: binary[contract_name, tier_name] for volume tier bands
        tier_band_count = 0
        for contract_name, contract_config in self.contract_configurations.items():
            if contract_config.get('contract_type') == 'rebate_adjustment_clause':
                # RAC contracts use single contract variable
                var_name = f"contract_{contract_name}"
                var = self.model.binary_var(name=var_name)
                self.tier_vars[contract_name] = var
            elif contract_config.get('contract_type') == 'volume_tier_rewards':
                # Volume tier contracts use per-band variables
                regime = self._get_tiering_regime(contract_config)
                tier_bands = self._get_contract_tier_bands(contract_config)
                
                for tier_band in tier_bands:
                    tier_name = tier_band['tier_name']
                    min_vol = tier_band['min_volume']
                    is_incremental_base_band = regime == 'incremental' and min_vol == 0
                    
                    # For incremental contracts, base band does not need a binary selector
                    if not is_incremental_base_band:
                        var_name = f"tier_{contract_name}_{tier_name}"
                        var = self.model.binary_var(name=var_name)
                        self.tier_band_vars[(contract_name, tier_name)] = var
                        tier_band_count += 1
                    
                    # Create regime-specific additional variables
                    if regime == 'all_units':
                        # Create tier selection variables for all_units regime
                        selection_var_name = f"select_{contract_name}_{tier_name}"
                        selection_var = self.model.binary_var(name=selection_var_name)
                        self.tier_selection_vars[(contract_name, tier_name)] = selection_var
                    
                    elif regime == 'incremental':
                        # For incremental regime, create band volume variables s_{o,b} for each base option
                        contract_suppliers = contract_config.get('suppliers', [])
                        transport_modes = contract_config.get('transport_modes', [])
                        
                        # Find all base options that belong to this contract
                        for depot_id in self.cost_matrices:
                            for supplier_depot_id in self.cost_matrices[depot_id]:
                                # Check if this supplier depot belongs to this contract
                                supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                                
                                if (contract_suppliers != ['*'] and supplier_name not in contract_suppliers):
                                    continue
                                
                                for option_type in self.base_option_types:  # Only base options for incremental
                                    if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                                        option_mode = self._get_option_transport_mode(option_type)
                                        
                                        if option_mode in transport_modes:
                                            option_key = (depot_id, supplier_depot_id, option_type)
                                            band_var_name = f"s_{depot_id}_{supplier_depot_id}_{option_type}_{tier_name}"
                                            band_var = self.model.continuous_var(lb=0, name=band_var_name)
                                            self.band_volume_vars[(option_key, tier_name)] = band_var
        
        additional_vars_count = len(self.tier_selection_vars) + len(self.band_volume_vars)
        logger.info(f"Created {allocation_count} allocation variables + {len(self.tier_vars)} RAC variables + {tier_band_count} tier band variables + {additional_vars_count} regime-specific variables")
        return self
    
    def set_objective(self, objective_mode="cost_only", strategic_constraint=None):
        """
        Set objective function supporting multi-objective optimization.
        
        Args:
            objective_mode: "cost_only", "strategic_only", or "epsilon_constraint"
            strategic_constraint: Minimum strategic score constraint for ε-constraint method
        """
        logger.info(f"Setting up objective function (mode: {objective_mode})...")
        
        # Build cost objective (always needed)
        cost_terms = []
        strategic_terms = []
        
        # Identify incremental contracts to exclude from base objective
        incremental_contracts = {}
        for contract_name, contract_config in self.contract_configurations.items():
            if contract_config.get('contract_type') == 'volume_tier_rewards':
                regime = self._get_tiering_regime(contract_config)
                if regime == 'incremental':
                    incremental_contracts[contract_name] = contract_config
        
        for (depot_id, supplier_depot_id, option_type), allocation_var in self.allocation_vars.items():
            # Check if this option belongs to an incremental contract
            is_incremental_base_option = False
            for contract_name, contract_config in incremental_contracts.items():
                contract_suppliers = contract_config.get('suppliers', [])
                transport_modes = contract_config.get('transport_modes', [])
                
                supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                option_mode = self._get_option_transport_mode(option_type)
                
                if (contract_suppliers == ['*'] or supplier_name in contract_suppliers) and \
                   option_mode in transport_modes and \
                   'tier_' not in option_type and not option_type.startswith('rac_'):
                    is_incremental_base_option = True
                    break
            
            # Skip base costs for incremental contract options (they'll be handled by band-split variables)
            if is_incremental_base_option:
                continue
                
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
            
            # Add cost term to objective
            cost_terms.append(total_cost * allocation_var)
            
            # Add strategic score term (for strategic objective)
            supplier_depot_data = self.cost_matrices.get(depot_id, {}).get(supplier_depot_id, {})
            strategic_score = supplier_depot_data.get('strategic_score', 0.0)
            if strategic_score > 0:
                strategic_terms.append(strategic_score * allocation_var)
        
        # Add incremental band-split cost terms
        for contract_name, contract_config in incremental_contracts.items():
            tier_bands = self._get_contract_tier_bands(contract_config)
            
            for tier_band in tier_bands:
                tier_name = tier_band['tier_name']
                
                # Find tier-enhanced costs for this band from precomputed data
                for (option_key, band_tier_name), band_var in self.band_volume_vars.items():
                    if band_tier_name == tier_name:
                        depot_id, supplier_depot_id, option_type = option_key
                        
                        # For base band (0_to_*), use base cost directly since rebate = 0.00
                        if tier_name.startswith('0_to_'):
                            # Base band: use base cost per litre
                            base_cost_per_litre = self.cost_matrices.get(depot_id, {}).get(supplier_depot_id, {}).get(option_type)
                            if base_cost_per_litre is not None and str(base_cost_per_litre).lower() not in ['nan', 'inf', '-inf']:
                                try:
                                    base_cost_per_litre = float(base_cost_per_litre)
                                    # Add base band cost: base_cost_per_litre * s_{o,base}
                                    cost_terms.append(base_cost_per_litre * band_var)
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid base cost for {option_key} base band {tier_name}: {base_cost_per_litre}")
                            else:
                                raise ValueError(f"Missing base cost for {option_type} at depot {depot_id}/supplier_depot {supplier_depot_id}")
                        else:
                            # Non-base band: use tier-enhanced cost
                            tier_option_type = f"{option_type}_tier_{tier_name}"
                            if tier_option_type in self.cost_matrices.get(depot_id, {}).get(supplier_depot_id, {}):
                                tier_cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id][tier_option_type]
                                
                                if tier_cost_per_litre is not None and str(tier_cost_per_litre).lower() not in ['nan', 'inf', '-inf']:
                                    try:
                                        tier_cost_per_litre = float(tier_cost_per_litre)
                                        # Add band cost: cost_per_litre * s_{o,b}
                                        cost_terms.append(tier_cost_per_litre * band_var)
                                    except (ValueError, TypeError):
                                        logger.warning(f"Invalid tier cost for {option_key} band {tier_name}: {tier_cost_per_litre}")
                                else:
                                    raise ValueError(f"Missing tier cost for {tier_option_type} at depot {depot_id}/supplier_depot {supplier_depot_id}")
                            else:
                                raise ValueError(f"Missing tier cost for {tier_option_type} at depot {depot_id}/supplier_depot {supplier_depot_id}")
        
        # Set objective based on mode
        if objective_mode == "cost_only":
            # Minimize cost only
            cost_expr = self.model.sum(cost_terms)
            self.model.minimize(cost_expr)
            logger.info(f"Cost minimization objective set with {len(cost_terms)} cost terms")
            
        elif objective_mode == "strategic_only":
            # Maximize strategic score only
            strategic_expr = self.model.sum(strategic_terms)
            self.model.maximize(strategic_expr)
            logger.info(f"Strategic score maximization objective set with {len(strategic_terms)} strategic terms")
            
        elif objective_mode == "epsilon_constraint":
            # ε-constraint method: minimize cost subject to strategic score constraint
            cost_expr = self.model.sum(cost_terms)
            strategic_expr = self.model.sum(strategic_terms)
            
            self.model.minimize(cost_expr)
            
            if strategic_constraint is not None:
                # Add constraint: strategic score >= strategic_constraint
                self.model.add_constraint(strategic_expr >= strategic_constraint, 
                                        ctname=f"strategic_constraint_{strategic_constraint}")
                logger.info(f"ε-constraint objective set: minimize cost subject to strategic score >= {strategic_constraint}")
            else:
                logger.warning("ε-constraint mode specified but no strategic_constraint provided")
            
            logger.info(f"ε-constraint objective set with {len(cost_terms)} cost terms and strategic constraint")
        
        else:
            valid_modes = ["cost_only", "strategic_only", "epsilon_constraint"]
            raise ValueError(f"Invalid objective_mode: {objective_mode}. Valid modes: {valid_modes}")
        
        return self
    
    def _add_all_units_constraints(self, contract_name: str, contract_config: Dict) -> int:
        """Add constraints for all_units tiering regime."""
        constraint_count = 0
        contract_suppliers = contract_config.get('suppliers', [])
        transport_modes = contract_config.get('transport_modes', [])
        volume_calculation_modes = contract_config.get('volume_calculation_modes', transport_modes)
        tier_bands = self._get_contract_tier_bands(contract_config)
        regime = self._get_tiering_regime(contract_config)
        
        # Calculate total volume for tier eligibility
        volume_contributing_vars = []
        for depot_id in self.cost_matrices:
            depot_volume = self.customer_depots[depot_id]['annual_volume']
            for supplier_depot_id in self.cost_matrices[depot_id]:
                supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                if (contract_suppliers != ['*'] and supplier_name not in contract_suppliers):
                    continue
                
                for option_type in self.all_option_types:
                    if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                        var = self.allocation_vars[(depot_id, supplier_depot_id, option_type)]
                        option_mode = self._get_option_transport_mode(option_type)
                        
                        if option_mode in volume_calculation_modes:
                            # Include base options and tier options for this contract
                            if ('tier_' not in option_type and not option_type.startswith('rac_')) or \
                               ('tier_' in option_type and self._option_belongs_to_contract(option_type, contract_name)):
                                volume_contributing_vars.append(depot_volume * var)
        
        if not volume_contributing_vars:
            return constraint_count
            
        total_volume = self.model.sum(volume_contributing_vars)
        
        # All-units specific constraints
        for tier_band in tier_bands:
            tier_name = tier_band['tier_name']
            min_volume = tier_band['min_volume']
            
            # Skip constraints for base bands in incremental contracts (no binary variable)
            if regime == 'incremental' and min_volume == 0:
                continue
                
            tier_band_var = self.tier_band_vars[(contract_name, tier_name)]
            selection_var = self.tier_selection_vars[(contract_name, tier_name)]
            
            # Selection allowed only if eligible: s_{c,b} <= y_{c,b}
            self.model.add_constraint(
                selection_var <= tier_band_var,
                ctname=f"selection_requires_eligibility_{contract_name}_{tier_name}"
            )
            constraint_count += 1
            
            # Tier band eligibility based on volume
            self.model.add_constraint(
                total_volume >= min_volume * tier_band_var,
                ctname=f"tier_eligibility_{contract_name}_{tier_name}"
            )
            constraint_count += 1
            
            # Gate tier options on selection
            tier_options = []
            for depot_id in self.cost_matrices:
                for supplier_depot_id in self.cost_matrices[depot_id]:
                    supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                    if (contract_suppliers != ['*'] and supplier_name not in contract_suppliers):
                        continue
                        
                    for option_type in self.all_option_types:
                        if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                            if 'tier_' in option_type and self._option_belongs_to_tier_band(option_type, contract_name, tier_name):
                                option_mode = self._get_option_transport_mode(option_type)
                                if option_mode in transport_modes:
                                    tier_options.append(self.allocation_vars[(depot_id, supplier_depot_id, option_type)])
            
            if tier_options:
                # Replace Big-M with indicator constraints - gate tier options when band not selected
                band_off = self.complement(selection_var, name=f"{contract_name}_{tier_name}_off")
                self.hard_zero_when(band_off, tier_options)
                constraint_count += len(tier_options)  # Count indicator constraints
        
        # Pick at most one band constraint
        selection_vars = [self.tier_selection_vars[(contract_name, tier_band['tier_name'])] 
                         for tier_band in tier_bands]
        if selection_vars:
            self.model.add_constraint(
                self.model.sum(selection_vars) <= 1,
                ctname=f"select_at_most_one_band_{contract_name}"
            )
            constraint_count += 1

        # If any band is selected, forbid base options for this contract (true all-units behavior)
        base_vars = []
        for depot_id in self.cost_matrices:
            for supplier_depot_id in self.cost_matrices[depot_id]:
                supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                if (contract_suppliers != ['*'] and supplier_name not in contract_suppliers):
                    continue
                for option_type in self.all_option_types:
                    if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                        if 'tier_' not in option_type and not option_type.startswith('rac_'):
                            option_mode = self._get_option_transport_mode(option_type)
                            if option_mode in transport_modes:
                                base_vars.append(self.allocation_vars[(depot_id, supplier_depot_id, option_type)])
        if base_vars and selection_vars:
            # Replace Big-M with "any tier selected" indicator
            y_any = self.or_of_binaries(selection_vars, name_prefix=f"{contract_name}_tier_any")
            self.hard_zero_when(y_any, base_vars)
            constraint_count += len(base_vars)  # Count indicator constraints
        
        logger.debug(f"Added {constraint_count} all_units constraints for {contract_name}")
        return constraint_count
    
    def _add_incremental_constraints(self, contract_name: str, contract_config: Dict) -> int:
        """Add constraints for incremental tiering regime."""
        constraint_count = 0
        contract_suppliers = contract_config.get('suppliers', [])
        transport_modes = contract_config.get('transport_modes', [])
        volume_calculation_modes = contract_config.get('volume_calculation_modes', transport_modes)
        tier_bands = self._get_contract_tier_bands(contract_config)
        
        # Disable tier options for incremental contracts (they use band-split variables instead)
        for depot_id in self.cost_matrices:
            for supplier_depot_id in self.cost_matrices[depot_id]:
                supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                if (contract_suppliers != ['*'] and supplier_name not in contract_suppliers):
                    continue
                    
                for option_type in self.all_option_types:
                    if (depot_id, supplier_depot_id, option_type) in self.allocation_vars:
                        if 'tier_' in option_type and self._option_belongs_to_contract(option_type, contract_name):
                            # Disable tier options for incremental contracts
                            self.model.add_constraint(
                                self.allocation_vars[(depot_id, supplier_depot_id, option_type)] == 0,
                                ctname=f"disable_tier_option_{contract_name}_{depot_id}_{supplier_depot_id}_{option_type}"
                            )
                            constraint_count += 1
        
        # Flow conservation: Σ_b s_{o,b} = v_o for each option
        for depot_id in self.cost_matrices:
            depot_volume = self.customer_depots[depot_id]['annual_volume']
            for supplier_depot_id in self.cost_matrices[depot_id]:
                supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
                if (contract_suppliers != ['*'] and supplier_name not in contract_suppliers):
                    continue
                
                for option_type in self.base_option_types:
                    option_key = (depot_id, supplier_depot_id, option_type)
                    if option_key in self.allocation_vars:
                        option_mode = self._get_option_transport_mode(option_type)
                        if option_mode in transport_modes:
                            # Flow conservation constraint
                            band_vars = []
                            for tier_band in tier_bands:
                                tier_name = tier_band['tier_name']
                                if (option_key, tier_name) in self.band_volume_vars:
                                    band_vars.append(self.band_volume_vars[(option_key, tier_name)])
                            
                            if band_vars:
                                allocation_var = self.allocation_vars[option_key]
                                self.model.add_constraint(
                                    self.model.sum(band_vars) == depot_volume * allocation_var,
                                    ctname=f"flow_conservation_{contract_name}_{depot_id}_{supplier_depot_id}_{option_type}"
                                )
                                constraint_count += 1
        
        # Band capacity and eligibility constraints
        for tier_band in tier_bands:
            tier_name = tier_band['tier_name']
            min_volume = tier_band['min_volume']
            band_width = self._band_width(tier_band)
            
            # Get band volume variables for this tier
            this_band_vars = [var for (opt_key, t_name), var in self.band_volume_vars.items() 
                             if t_name == tier_name]
            
            if this_band_vars:
                total_band_volume = self.model.sum(this_band_vars)

                # For base bands (min_vol=0): no binary constraint, just width limit
                if min_volume == 0:
                    # Base band constraint: q_base <= band_width (no binary gate)
                    self.model.add_constraint(
                        total_band_volume <= band_width,
                        ctname=f"base_band_width_{contract_name}_{tier_name}"
                    )
                else:
                    # Regular tier band constraint: q_b <= band_width * y_b
                    tier_band_var = self.tier_band_vars[(contract_name, tier_name)]
                    self.model.add_constraint(
                        total_band_volume <= band_width * tier_band_var,
                        ctname=f"band_width_limit_{contract_name}_{tier_name}"
                    )
                constraint_count += 1

                # Limit incremental band volume to available excess volume per allocation option
                if min_volume > 0:
                    for (option_key, t_name), band_var in self.band_volume_vars.items():
                        if t_name != tier_name:
                            continue

                        depot_id, supplier_depot_id, option_type = option_key
                        if option_key not in self.allocation_vars:
                            continue

                        allocation_var = self.allocation_vars[option_key]
                        depot_volume = self.customer_depots[depot_id]['annual_volume']
                        extra_volume = max(depot_volume - min_volume, 0)

                        self.model.add_constraint(
                            band_var <= extra_volume * allocation_var,
                            ctname=(
                                f"band_extra_limit_{contract_name}_{depot_id}_{supplier_depot_id}_"
                                f"{option_type}_{tier_name}"
                            )
                        )
                        constraint_count += 1

                # Band eligibility (cumulative): sum of all bands up to b must exceed min_volume if y_b = 1
                # Only apply for non-base bands (min_volume > 0)
                if min_volume > 0:
                    bands_sorted = sorted(tier_bands, key=lambda x: x['min_volume'])
                    upto_names = [tb['tier_name'] for tb in bands_sorted if tb['min_volume'] <= min_volume]
                    
                    # Build cumulative volume: Q_b = Σ_{k <= b} q_k
                    # Only count volume from modes that contribute to tier calculations
                    cumulative_band_vars = []
                    for upto_tier_name in upto_names:
                        cumulative_band_vars.extend([
                            var for (opt_key, t_name), var in self.band_volume_vars.items()
                            if t_name == upto_tier_name and 
                            self._get_option_transport_mode(opt_key[2]) in volume_calculation_modes
                        ])
                    
                    if cumulative_band_vars:
                        q_cumulative = self.model.sum(cumulative_band_vars)
                        tier_band_var = self.tier_band_vars[(contract_name, tier_name)]
                        self.model.add_constraint(
                            q_cumulative >= min_volume * tier_band_var,
                            ctname=f"band_min_volume_cumulative_{contract_name}_{tier_name}"
                        )
                        constraint_count += 1
        
        # Monotonicity constraint: y_{b+1} <= y_b (higher bands require lower bands)
        # Skip pairs involving base bands (min_volume=0) since they have no binary variables
        sorted_bands = sorted(tier_bands, key=lambda x: x['min_volume'])
        for i in range(len(sorted_bands) - 1):
            current_band = sorted_bands[i]
            next_band = sorted_bands[i + 1]
            current_tier = current_band['tier_name']
            next_tier = next_band['tier_name']
            
            # Skip if either band is a base band (no binary variable)
            if current_band['min_volume'] == 0 or next_band['min_volume'] == 0:
                continue
                
            current_var = self.tier_band_vars[(contract_name, current_tier)]
            next_var = self.tier_band_vars[(contract_name, next_tier)]
            
            self.model.add_constraint(
                next_var <= current_var,
                ctname=f"tier_monotonicity_{contract_name}_{next_tier}_requires_{current_tier}"
            )
            constraint_count += 1
        
        logger.debug(f"Added {constraint_count} incremental constraints for {contract_name}")
        return constraint_count
    
    def _add_country_allocation_constraints(self) -> int:
        """Add country-based allocation constraints."""
        if not self.country_constraints.get('enabled', False):
            return 0
        
        logger.info("Adding country allocation constraints...")
        constraint_count = 0
        blocked_allocations = 0
        
        cross_border_restrictions = self.country_constraints.get('cross_border_restrictions', {})
        
        for (depot_id, supplier_depot_id, option_type), allocation_var in self.allocation_vars.items():
            # Get customer depot country
            customer_country = self.customer_depots.get(depot_id, {}).get('country')
            
            # Get supplier depot country from cost matrix metadata
            supplier_country = self.cost_matrices.get(depot_id, {}).get(supplier_depot_id, {}).get('supplier_depot_country')
            
            # Skip if either country is missing
            if not customer_country or not supplier_country:
                if not customer_country:
                    logger.warning(f"Missing customer depot country for depot {depot_id}")
                if not supplier_country:
                    logger.warning(f"Missing supplier depot country for supplier depot {supplier_depot_id}")
                continue
            
            # Check if this allocation should be blocked
            if customer_country in cross_border_restrictions:
                restrictions = cross_border_restrictions[customer_country]
                
                # Check if supplier country is blocked
                blocked_countries = restrictions.get('blocked_destinations', [])
                allowed_countries = restrictions.get('allowed_destinations', [])
                
                should_block = False
                if blocked_countries and supplier_country in blocked_countries:
                    should_block = True
                elif allowed_countries and supplier_country not in allowed_countries:
                    should_block = True
                
                if should_block:
                    # Add constraint to block this allocation
                    constraint_name = f"country_block_{depot_id}_{supplier_depot_id}_{option_type}"
                    self.model.add_constraint(
                        allocation_var == 0,
                        ctname=constraint_name
                    )
                    constraint_count += 1
                    blocked_allocations += 1
                    
                    logger.debug(f"Blocked allocation: Customer depot {depot_id} ({customer_country}) → "
                               f"Supplier depot {supplier_depot_id} ({supplier_country}) for {option_type}")
        
        logger.info(f"Added {constraint_count} country allocation constraints, "
                   f"blocked {blocked_allocations} cross-border allocations")
        return constraint_count
    
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
        
        # Constraint 2: Volume tier reward contract constraints (Regime-specific)
        for contract_name, contract_config in self.contract_configurations.items():
            # Skip RAC contracts - handled separately
            if contract_config.get('contract_type') == 'rebate_adjustment_clause':
                continue
            
            # Only handle volume tier reward contracts here
            if contract_config.get('contract_type') != 'volume_tier_rewards':
                continue
                
            regime = self._get_tiering_regime(contract_config)
            contract_supplier_depots = contract_config.get('supplier_depots', [])
            contract_suppliers = contract_config.get('suppliers', [])
            transport_modes = contract_config.get('transport_modes', [])
            volume_calculation_modes = contract_config.get('volume_calculation_modes', transport_modes)
            
            logger.debug(f"Processing {contract_name} with regime: {regime}")
            
            if regime == 'all_units':
                constraint_count += self._add_all_units_constraints(contract_name, contract_config)
            elif regime == 'incremental':
                constraint_count += self._add_incremental_constraints(contract_name, contract_config)
        
        # Constraint 3: RAC contract constraints (different logic than volume tier rewards)
        for contract_name, contract_config in self.contract_configurations.items():
            if contract_config.get('contract_type') == 'rebate_adjustment_clause':
                rac_threshold = self._get_contract_threshold(contract_config)
                rac_suppliers = contract_config.get('suppliers', [])
                rac_modes = contract_config.get('transport_modes', [])
                volume_calculation_modes = contract_config.get('volume_calculation_modes', rac_modes)

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
                                            # Use volume_calculation_modes for volume threshold calculation
                                            if option_mode in volume_calculation_modes:
                                                volume_contributing_vars.append(depot_volume * var)
                    
                    if rac_option_vars and base_option_vars and volume_contributing_vars:
                        # RAC contract binary variable
                        contract_var = self.tier_vars[contract_name]

                        # Constraint: Contract is active only if volume threshold is met
                        total_volume = self.model.sum(volume_contributing_vars)
                        self.model.add_constraint(
                            total_volume >= rac_threshold * contract_var,
                            ctname=f"rac_contract_threshold_{contract_name}"
                        )
                        constraint_count += 1

                        # Replace Big-M mutual exclusion with indicators:
                        # If commitment met (contract_var == 1): forbid RAC options
                        rac_off = self.complement(contract_var, name=f"{contract_name}_rac_off")  # 1 when contract_var = 0
                        self.hard_zero_when(contract_var, rac_option_vars)  # If commitment met, forbid RAC
                        self.hard_zero_when(rac_off, base_option_vars)     # If commitment NOT met, forbid base
                        constraint_count += len(rac_option_vars) + len(base_option_vars)  # Count indicator constraints
                        
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
        
        # Constraint 5: Country allocation constraints (cross-border restrictions)
        country_constraint_count = self._add_country_allocation_constraints()
        constraint_count += country_constraint_count
        
        logger.info(f"Added {constraint_count} total constraints "
                   f"({capacity_constraint_count} capacity constraints, "
                   f"{country_constraint_count} country constraints)")
        return self
    
    def _get_contract_threshold(self, contract_config: Dict[str, Any]) -> float:
        """Extract volume threshold from contract configuration (backward compatibility)."""
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
    
    def _get_contract_tier_bands(self, contract_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all tier bands from volume tier reward contract configuration."""
        if contract_config.get('contract_type') != 'volume_tier_rewards':
            return []
        
        reward_bands = contract_config.get('reward_bands', [])
        tier_bands = []
        regime = self._get_tiering_regime(contract_config)
        
        for band in reward_bands:
            min_vol = band.get('min_volume', 0)
            max_vol = band.get('max_volume')
            
            # For incremental contracts, include all bands (including base band with min_vol=0)
            # For all_units contracts, skip base band as before (base pricing separate from tier pricing)
            if regime == 'incremental' or min_vol > 0:
                # Generate tier name based on volume range
                if min_vol == 0:
                    # Special case for base band (0 to first_max)
                    max_str = f"{max_vol//1000000}M" if max_vol and max_vol >= 1000000 else str(max_vol)
                    tier_name = f"0_to_{max_str}"
                else:
                    min_str = f"{min_vol//1000000}M" if min_vol >= 1000000 else str(min_vol)
                    if max_vol:
                        max_str = f"{max_vol//1000000}M" if max_vol >= 1000000 else str(max_vol)
                        tier_name = f"{min_str}_to_{max_str}"
                    else:
                        tier_name = f"{min_str}_plus"
                
                tier_bands.append({
                    'tier_name': tier_name,
                    'min_volume': min_vol,
                    'max_volume': max_vol,
                    'del_rebate': band.get('del_rebate', 0),
                    'coc_rebate': band.get('coc_rebate', 0)
                })
        
        return tier_bands
    
    
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
    
    def _option_belongs_to_tier_band(self, option_type: str, contract_name: str, tier_name: str) -> bool:
        """Check if a tier option belongs to a specific tier band within a contract."""
        if 'tier_' not in option_type:
            return False
        
        tier_part = option_type.split('tier_')[1]  # Get part after 'tier_'
        
        # Direct comparison with tier name
        return tier_name in tier_part


    def _get_incremental_contract_for_option(self, depot_id: int, supplier_depot_id: int, option_type: str) -> Optional[str]:
        """Return incremental contract name if option belongs to one, otherwise None."""
        for contract_name, contract_config in self.contract_configurations.items():
            if contract_config.get('contract_type') != 'volume_tier_rewards':
                continue

            if self._get_tiering_regime(contract_config) != 'incremental':
                continue

            contract_suppliers = contract_config.get('suppliers', [])
            supplier_name = self.supplier_depots.get(supplier_depot_id, {}).get('supplier_name', '')
            if contract_suppliers and contract_suppliers != ['*'] and supplier_name not in contract_suppliers:
                continue

            contract_supplier_depots = contract_config.get('supplier_depots', ['*'])
            if contract_supplier_depots and contract_supplier_depots != ['*'] and str(supplier_depot_id) not in contract_supplier_depots:
                continue

            transport_modes = contract_config.get('transport_modes', [])
            if transport_modes and self._get_option_transport_mode(option_type) not in transport_modes:
                continue

            return contract_name

        return None


    def _compute_incremental_cost(self, option_key: Tuple[int, int, str], base_cost_per_litre: float, solution) -> Tuple[float, Dict[str, float]]:
        """Compute total cost and band volume breakdown for an incremental contract option."""
        depot_id, supplier_depot_id, option_type = option_key
        total_cost = 0.0
        band_breakdown: Dict[str, float] = {}

        for (opt_key, tier_name), band_var in self.band_volume_vars.items():
            if opt_key != option_key:
                continue

            volume = solution.get_value(band_var)
            if abs(volume) < 1e-6:
                continue

            if tier_name.startswith('0_to_'):
                cost_per_litre = base_cost_per_litre
            else:
                tier_option_type = f"{option_type}_tier_{tier_name}"
                cost_per_litre = self.cost_matrices.get(depot_id, {}).get(supplier_depot_id, {}).get(tier_option_type)
                if cost_per_litre is None:
                    logger.warning(
                        "Missing tier cost for incremental option %s band %s; using base cost",
                        option_type,
                        tier_name
                    )
                    cost_per_litre = base_cost_per_litre

            total_cost += cost_per_litre * volume
            band_breakdown[tier_name] = volume

        if not band_breakdown:
            depot_volume = self.customer_depots[depot_id]['annual_volume']
            return depot_volume * base_cost_per_litre, {}

        return total_cost, band_breakdown


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
        band_volume_details: Dict[str, Dict[str, float]] = {}

        # Extract allocations
        for (depot_id, supplier_depot_id, option_type), var in self.allocation_vars.items():
            if solution.get_value(var) > 0.5:  # Variable is selected
                depot_volume = self.customer_depots[depot_id]['annual_volume']

                # Base cost lookups
                base_cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id].get(option_type)
                if base_cost_per_litre is None:
                    logger.warning(
                        "Missing base cost for depot %s, supplier depot %s, option %s", 
                        depot_id,
                        supplier_depot_id,
                        option_type
                    )
                    base_cost_per_litre = 0.0

                actual_cost_per_litre = base_cost_per_litre
                cost_type = "base"
                active_tier = None
                total_depot_cost = depot_volume * base_cost_per_litre

                option_key = (depot_id, supplier_depot_id, option_type)
                incremental_contract = self._get_incremental_contract_for_option(depot_id, supplier_depot_id, option_type)

                if 'tier_' in option_type:
                    cost_type = "tier_enhanced"
                    active_tier = self._extract_tier_from_option(option_type)
                    base_option_type = self._get_base_option_from_tier(option_type)
                    base_option_cost = self.cost_matrices[depot_id][supplier_depot_id].get(base_option_type)
                    if base_option_cost is not None:
                        base_cost_per_litre = base_option_cost
                    actual_cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id][option_type]
                    total_depot_cost = depot_volume * actual_cost_per_litre
                elif option_type.startswith('rac_'):
                    cost_type = "rac_penalty"
                    base_option_type = option_type.replace('rac_', '')
                    base_option_cost = self.cost_matrices[depot_id][supplier_depot_id].get(base_option_type)
                    if base_option_cost is not None:
                        base_cost_per_litre = base_option_cost
                    actual_cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id][option_type]
                    total_depot_cost = depot_volume * actual_cost_per_litre
                elif incremental_contract:
                    total_depot_cost, band_breakdown = self._compute_incremental_cost(
                        option_key,
                        base_cost_per_litre,
                        solution
                    )
                    if depot_volume > 0:
                        actual_cost_per_litre = total_depot_cost / depot_volume
                    else:
                        actual_cost_per_litre = 0.0
                    cost_type = "incremental"
                    if band_breakdown:
                        key_str = f"{depot_id}_{supplier_depot_id}_{option_type}"
                        band_volume_details[key_str] = band_breakdown

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
        
        # Extract active tiers from tier variables (RAC contracts) and tier band variables (volume tier contracts)
        active_tiers = []
        for tier_name, var in self.tier_vars.items():
            if solution.get_value(var) > 0.5:
                active_tiers.append(tier_name)
        
        # Extract active tier bands
        active_tier_bands = []
        for (contract_name, tier_name), var in self.tier_band_vars.items():
            if solution.get_value(var) > 0.5:
                active_tier_bands.append(f"{contract_name}_{tier_name}")
                active_tiers.append(f"{contract_name}_{tier_name}")  # Also add to main active_tiers list for backward compatibility
        
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
        print(f"Active RAC contract variables: {[tier for tier in self.tier_vars.keys() if solution.get_value(self.tier_vars[tier]) > 0.5]}")
        print(f"Active tier band variables: {active_tier_bands}")
        print(f"All active tiers: {active_tiers}")
        
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
            'active_tier_bands': active_tier_bands,  # New field for per-band tracking
            'tier_count': len(active_tiers),
            'supplier_depot_utilization': supplier_depot_utilization,
            'binding_capacity_constraints': binding_constraints,
            'near_capacity_constraints': near_capacity_constraints,
            'capacity_summary': {
                'total_supplier_depots_used': len(supplier_depot_utilization),
                'binding_constraints_count': len(binding_constraints),
                'near_capacity_count': len(near_capacity_constraints)
            },
            'band_volume_details': band_volume_details
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
            self.set_objective(objective_mode="cost_only")  # Default to cost-only optimization
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
