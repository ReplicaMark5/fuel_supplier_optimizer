# Depot Supplier Allocation Optimizer Project

## Project Context
This is a thesis project developing a depot supplier allocation optimizer using CPLEX to minimize fuel supply costs. The project involves binary integer programming optimization with volume tier constraints. 


## Key Files

### Core Algorithm Files
- **`fuel_optimizer_docplex.py`**: **CPLEX Optimization Engine** - DOcplex-based binary integer programming solver
  - **Purpose**: Minimizes total fuel supply costs across all customer depot allocations
  - **Logic**: Binary variables for each customer→supplier_depot→option combination with assignment constraints
  - **Features**: Volume tier activation constraints, supplier depot capacity limits, RAC penalty enforcement
  - **Output**: Optimal allocation decisions with cost breakdown and capacity utilization analysis
  
- **`precomputation.py`**: **Cost Calculation System** - High-performance pandas-based cost computation engine  
  - **Purpose**: Calculates all possible cost options in Present Value terms for optimization consumption
  - **Logic**: Multi-table database joins → fuel zone mapping → PV discounting → volume tier calculations
  - **Features**: Base costs (COC/DEL options), RAC penalty costs, volume tier enhanced costs, coordinate integration
  - **Output**: Comprehensive cost dictionary with 31,079+ cost options across 2,011 depot-supplier_depot pairs

### Supporting System Files  
- **`optimization_map.py`**: Enhanced visualization system - Interactive mapping with layer controls
- **`optimization_config.json`**: Simplified volume tier configurations and PV settings  
- **`fuel_data.db`**: Production SQLite database (reorganized structure)
- **`query_costs.py`**: Interactive cost analysis and debugging tool
- **`thesis_notes.md`**: **CRITICAL** - Methodology documentation for thesis writing
- **`manual_crosscheck_calc.md`**: Formula specifications for COC and DEL calculations

## Project Structure
```
├── fuel_optimizer_docplex.py  # CPLEX optimization engine (Phase 4 complete)
├── precomputation.py          # Cost calculation system (Phases 1-3 complete)
├── optimization_map.py        # Enhanced visualization mapper (Phase 4 complete)
├── optimization_config.json   # All configuration and volume tier definitions
├── fuel_data.db              # Reorganized database with clean schema
├── query_costs.py            # Interactive cost analysis and debugging tool
├── thesis_notes.md           # Methodology documentation for thesis writing
├── manual_crosscheck_calc.md  # Formula specifications for validation
├── test_debug/               # Testing and debugging scripts
│   ├── debug_costs.py
│   ├── debug_validation_stats.py
│   └── test_volume_tiers.py
```

## Important Instructions for Future Claude Instances

### Thesis Documentation Protocol
**ALWAYS update `thesis_notes.md` after ANY significant progress, changes, or methods are applied to the project.**

The thesis_notes.md file serves as:
- Methodology section documentation
- Step-by-step process tracking
- Technical implementation notes
- Data processing decisions

### SOUTH AFRICAN CURRENCY
- the financials of this optimizer and calculator uses Rands, the only value in cents is from the diesel_prices table when the rtl_wholesale values are used
- All rebate values etc are given in rands and all outputs must be in rands
- In south africa 1R (Rand) = 100c (Cents)

### What to Document
- Data processing steps and decisions
- Model structure changes
- Constraint modifications
- Algorithm implementations
- Validation procedures
- Technical challenges and solutions

### Format for Updates
Add new entries under appropriate sections:
- Use bullet points for concise documentation
- Include technical details relevant for methodology
- Document rationale for design decisions
- Note any data transformations or cleaning steps

## Current Project Status (Latest Update: 2025-08-26)

### ✅ Complete Optimization System Implementation
- **Phase 1**: Base cost calculations for COC and DEL options with Present Value discounting ✅
- **Phase 2**: Volume tier system with supplier depot-specific tier structures ✅
- **Phase 3**: Configuration simplification and formula validation ✅
- **Phase 4**: CPLEX integration and enhanced visualization system ✅

### 🎯 Technical Achievements
- **CPLEX Integration**: Complete binary integer programming optimization with 31,079 decision variables
- **Capacity Management**: Supplier depot capacity constraints with utilization tracking
- **Enhanced Visualization**: Interactive mapping with layer controls and detailed cost analysis
- **Volume Tier System**: Incremental/stacked bands with individual cost calculations
- **Formula Validation**: All calculations match manual crosscheck specifications exactly
- **Performance Excellence**: Sub-second execution across all system components

### 📁 Active Core Files
- **`fuel_optimizer_docplex.py`**: CPLEX optimization engine - Complete mathematical model implementation
- **`precomputation.py`**: Cost calculation system - base_costs + tier_costs structure
- **`optimization_map.py`**: Enhanced visualization mapper - Layer-based interactive mapping
- **`optimization_config.json`**: Clean volume tier configurations (4 tiers defined)
- **`fuel_data.db`**: Production database (2,011 depot-supplier_depot combinations)

### 🏗️ Algorithm Architecture and Logic

#### Precomputation Engine (`precomputation.py`)
**Data Processing Pipeline**:
1. **Database Integration**: Multi-table joins across 6 tables (od_pair, collection_options, delivery_options, supplier_depots, customer_depots, diesel_prices)
2. **Fuel Zone Mapping**: SA zones (09A→9A format) + international country pricing integration
3. **Present Value Calculations**: WACC-based discounting for different payment terms (0, 30, 45, 60 days)
4. **Base Cost Calculations**: 
   - **COC Options**: `(wholesale_price - rebate) / pv_factor + transport_cost`
   - **DEL Options**: `(wholesale_price - rebate - equipment_rebates) / pv_factor + equipment_cost`
5. **RAC Penalty Calculations**: Wholesale pricing without rebates for volume commitment failures
6. **Volume Tier Enhancements**: Additional rebates when volume commitments are met
   - **"add" rule**: `base_rebate + tier_rebate`  
   - **"override" rule**: `tier_rebate` (replaces base rebate)

**Output Structure**: `costs[customer_depot_id][supplier_depot_id][option_type]` with 31,079+ total cost options

#### CPLEX Optimization Engine (`fuel_optimizer_docplex.py`)
**Mathematical Model Structure**:
- **Decision Variables**: `x[customer_depot_id][supplier_depot_id][option_type]` (binary)
- **Objective Function**: `minimize Σ(annual_volume × cost_per_litre × x[c][s][o])`
- **Assignment Constraint**: `Σ(x[c][s][o]) = 1 for each customer_depot_c` (exactly one allocation per depot)
- **Volume Tier Constraints**: Binary activation logic for tier eligibility based on aggregate volumes
- **Capacity Constraints**: `Σ(volume × x[c][s][o]) ≤ capacity_limit[s]` for each supplier_depot

**Solution Extraction**:
1. Identify selected variables (`x[c][s][o] > 0.5`)
2. Calculate capacity utilization and binding constraints
3. Determine cost type (base, tier_enhanced, rac_penalty)
4. Generate comprehensive results with allocation details and tier activation status

#### Integration Flow
**Complete Pipeline**: `FuelOptimizationPrecomputation.run_complete_precomputation()` → `FuelDepotOptimizerDocplex.run_optimization()` → `OptimizationMapper.create_enhanced_allocation_map()`

### 🔧 Business Logic Implementation

#### Cost Option Types (precomputation.py)
- **Base Options**: Standard pricing without special conditions
  - **COC (Customer Own Collection)**: Customer arranges transport, pays transport costs
  - **DEL (Supplier Delivery)**: Supplier delivers, customer pays for equipment (own/buy/rent)
- **RAC Penalty Options**: Higher costs when volume commitments are not met (removes all rebates)
- **Volume Tier Options**: Lower costs when volume commitments are achieved (additional rebates)

#### Constraint Logic (fuel_optimizer_docplex.py)
- **Assignment Constraints**: Each customer depot must select exactly one supply option
- **Volume Tier Activation**: Tiers activate only when aggregate volume across supplier depot group meets minimum threshold
- **Capacity Enforcement**: Supplier depot throughput limits prevent over-allocation
- **Option Availability**: NULL database values prevent unavailable options from being selected

#### Decision Optimization Process
1. **Data Preparation**: Extract cost matrices and availability from precomputed dictionary
2. **Variable Creation**: Generate binary variables for all available depot-supplier-option combinations
3. **Constraint Setup**: Enforce assignment, volume tier, and capacity business rules
4. **CPLEX Solution**: Mathematical solver finds minimum-cost feasible allocation
5. **Result Processing**: Extract allocations, calculate utilization, identify binding constraints
6. **Visualization**: Generate interactive map with layer controls and detailed cost popups

### 📊 Production System Scale
- **Decision Variables**: 31,079 binary variables across optimization space
- **Depot Combinations**: 2,011 customer-supplier_depot pairs
- **Cost Options**: 8,833 total (base + volume tier options)
- **Volume Tiers Active**: 4 tier configurations across suppliers
- **Performance**: Complete optimization pipeline <2 seconds end-to-end

### 🎨 Visualization Features
- **Interactive Layer Control**: Right-side panel with supplier-specific toggles
- **Advanced Markers**: BeautifyIcon supplier depots with custom hex colors
- **Route Detail Popups**: Comprehensive cost option display with color-coded categories
- **MarkerCluster Integration**: Automatic clustering/splitting of overlapping depots
- **Color Consistency**: Unified hex color scheme across markers and route lines
- **Professional Theme**: CartoDB positron white theme for enhanced visibility

### 🚀 Complete Optimization System Ready
- **End-to-End Functionality**: Data processing → Optimization → Interactive visualization
- **Mathematical Accuracy**: All calculations validated against manual specifications
- **Business Logic Compliance**: Full alignment with South African fuel supply chain practices
- **Production Ready**: Scalable architecture supporting real-world deployment
- **Interactive Analysis**: Comprehensive cost exploration and optimization result visualization


## Database Structure (Current)
- **6 main tables**: od_pair, collection_options, delivery_options, supplier_depots, customer_depots, diesel_prices, suppliers
- **Clean separation**: COC vs DEL options with proper availability flags (NULL = not available)
- **Volume tiers**: Moved from database to JSON configuration for flexibility
- **Performance**: Optimized joins and indexing for <750ms total processing time


Remember: This project documentation is for thesis writing purposes - maintain detailed, methodical records of all development steps.