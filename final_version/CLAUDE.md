# Multi-Objective Depot Supplier Allocation Optimizer Project

## Project Context
This is a thesis project developing a multi-objective depot supplier allocation optimizer using CPLEX to simultaneously minimize fuel supply costs and maximize strategic supplier scores. The project implements binary integer programming optimization with volume tier constraints and ε-constraint method for Pareto front generation.

## Key Files

### Core Algorithm Files
- **`fuel_optimizer_docplex.py`**: **Multi-Objective CPLEX Optimization Engine** - DOcplex-based binary integer programming solver
  - **Purpose**: Minimizes costs while maximizing strategic supplier scores through multiple objective modes
  - **Objective Modes**: "cost_only", "strategic_only", "weighted", "epsilon_constraint"
  - **Logic**: Binary variables for each customer→supplier_depot→option combination with assignment constraints
  - **Features**: Volume tier activation constraints, supplier depot capacity limits, RAC penalty enforcement, strategic score integration
  - **Output**: Optimal allocation decisions with cost breakdown, capacity utilization, and strategic score analysis
  
- **`precomputation.py`**: **Cost & Strategic Score Calculation System** - High-performance pandas-based computation engine  
  - **Purpose**: Calculates all possible cost options in Present Value terms AND integrates strategic supplier scores
  - **Logic**: Multi-table database joins → fuel zone mapping → PV discounting → volume tier calculations → strategic score integration
  - **Features**: Base costs (COC/DEL options), RAC penalty costs, volume tier enhanced costs, strategic supplier scores, coordinate integration
  - **Strategic Integration**: Calls `strategic_supplier_scoring.py` to add weighted strategic scores to cost dictionary
  - **Output**: Comprehensive cost dictionary with 31,079+ cost options and strategic scores across 2,011 depot-supplier_depot pairs

- **`pareto_front_generator.py`**: **Multi-Objective Analysis Controller** - ε-constraint method implementation
  - **Purpose**: Generates Pareto-optimal solutions for cost vs strategic supplier score trade-offs
  - **Method**: ε-constraint approach minimizing cost subject to strategic score constraints
  - **Logic**: Calculate strategic bounds → Generate ε values → Solve constrained optimizations → Analyze trade-offs
  - **Features**: Theoretical bound calculation, adaptive ε spacing, feasibility checking, comprehensive trade-off analysis
  - **Output**: Pareto front solutions, trade-off analysis, visualization plots, CSV/JSON exports

### Supporting System Files  
- **`strategic_supplier_scoring.py`**: **Strategic Supplier Score Calculator** - Weighted multi-criteria supplier evaluation
  - **Purpose**: Calculate weighted strategic scores for suppliers based on multiple business criteria
  - **Criteria**: Current Level, Product/Service Type, Geographical Network, Method of Sourcing, Investment in Equipment, Reciprocal Business
  - **Logic**: Database loading → criteria weight application → weighted score calculation → supplier ranking
  - **Output**: Strategic scores (0.0-1.0) for each supplier, used in multi-objective optimization

- **`optimization_map.py`**: Enhanced visualization system - Interactive mapping with layer controls
- **`optimization_config.json`**: Simplified volume tier configurations, PV settings, and strategic scoring weights  
- **`fuel_data.db`**: Production SQLite database (reorganized structure with supplier_scores and criteria_weights tables)
- **`query_costs.py`**: Interactive cost analysis and debugging tool
- **`thesis_notes.md`**: **CRITICAL** - Methodology documentation for thesis writing
- **`manual_crosscheck_calc.md`**: Formula specifications for COC and DEL calculations
- **`test_multi_objective.py`**: Multi-objective optimization testing and validation

## Project Structure
```
├── fuel_optimizer_docplex.py          # Multi-objective CPLEX optimization engine
├── precomputation.py                # Cost & strategic score calculation system
├── pareto_front_generator.py         # Multi-objective analysis controller
├── strategic_supplier_scoring.py    # Strategic supplier score calculator
├── optimization_map.py              # Enhanced visualization mapper
├── optimization_config.json         # Volume tiers, PV settings, strategic weights
├── fuel_data.db                    # Production database with strategic scoring tables
├── query_costs.py                  # Interactive cost analysis tool
├── thesis_notes.md                 # Methodology documentation
├── manual_crosscheck_calc.md       # Formula specifications
├── test_multi_objective.py         # Multi-objective testing
└── test_debug/                     # Testing and debugging scripts
    ├── debug_costs.py
    ├── debug_validation_stats.py
    └── test_volume_tiers.py
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

## Current Project Status (Latest Update: 2025-09-10)

### ✅ Complete Multi-Objective Optimization System Implementation
- **Phase 1**: Base cost calculations for COC and DEL options with Present Value discounting ✅
- **Phase 2**: Volume tier system with supplier depot-specific tier structures ✅
- **Phase 3**: Configuration simplification and formula validation ✅
- **Phase 4**: CPLEX integration and enhanced visualization system ✅
- **Phase 5**: Strategic supplier scoring system integration ✅
- **Phase 6**: Multi-objective optimization with ε-constraint method ✅
- **Phase 7**: Pareto front generation and trade-off analysis ✅

### 🎯 Technical Achievements
- **Multi-Objective CPLEX Integration**: Complete binary integer programming with cost and strategic objectives (31,079 variables)
- **ε-Constraint Method Implementation**: Systematic Pareto front generation for cost vs strategic score trade-offs
- **Strategic Supplier Scoring**: Multi-criteria weighted evaluation system with database integration
- **Capacity Management**: Supplier depot capacity constraints with utilization tracking
- **Enhanced Visualization**: Interactive mapping with layer controls and detailed cost analysis
- **Volume Tier System**: Incremental/stacked bands with individual cost calculations
- **Formula Validation**: All calculations match manual crosscheck specifications exactly
- **Performance Excellence**: Sub-second execution for single optimizations, ~30 seconds for full Pareto fronts

### 📁 Active Core Files
- **`fuel_optimizer_docplex.py`**: Multi-objective CPLEX optimization engine - Supports cost_only, strategic_only, weighted, and epsilon_constraint modes
- **`precomputation.py`**: Cost & strategic score calculation system - Integrates strategic scores from supplier scoring module
- **`pareto_front_generator.py`**: Multi-objective analysis controller - Generates Pareto fronts using ε-constraint method
- **`strategic_supplier_scoring.py`**: Strategic supplier score calculator - Multi-criteria weighted evaluation
- **`optimization_map.py`**: Enhanced visualization mapper - Layer-based interactive mapping
- **`optimization_config.json`**: Volume tiers, PV settings, and strategic scoring weights (6 criteria defined)
- **`fuel_data.db`**: Production database with supplier_scores and criteria_weights tables (2,011 depot-supplier_depot combinations)

### 🏗️ Algorithm Architecture and Logic

#### Precomputation Engine (`precomputation.py`)
**Data Processing Pipeline**:
1. **Database Integration**: Multi-table joins across 8 tables (od_pair, collection_options, delivery_options, supplier_depots, customer_depots, diesel_prices, supplier_scores, criteria_weights)
2. **Fuel Zone Mapping**: SA zones (09A→9A format) + international country pricing integration
3. **Present Value Calculations**: WACC-based discounting for different payment terms (0, 30, 45, 60 days)
4. **Base Cost Calculations**: 
   - **COC Options**: `(wholesale_price - rebate) / pv_factor + transport_cost`
   - **DEL Options**: `(wholesale_price - rebate - equipment_rebates) / pv_factor + equipment_cost`
5. **RAC Penalty Calculations**: Wholesale pricing without rebates for volume commitment failures
6. **Volume Tier Enhancements**: Additional rebates when volume commitments are met
   - **"add" rule**: `base_rebate + tier_rebate`  
   - **"override" rule**: `tier_rebate` (replaces base rebate)
7. **Strategic Score Integration**: Dynamic import and calculation of strategic supplier scores
   - **Call Flow**: `precomputation.py` → `strategic_supplier_scoring.py` → database tables
   - **Scoring Logic**: Weighted multi-criteria evaluation (6 criteria)
   - **Integration**: Strategic scores added to cost dictionary for each supplier depot

**Output Structure**: `costs[customer_depot_id][supplier_depot_id][option_type]` with strategic scores included
- **Total Cost Options**: 31,079+ across 2,011 depot-supplier_depot pairs
- **Strategic Scores**: 0.0-1.0 range for each supplier depot combination

#### CPLEX Optimization Engine (`fuel_optimizer_docplex.py`)
**Multi-Objective Mathematical Model Structure**:
- **Decision Variables**: `x[customer_depot_id][supplier_depot_id][option_type]` (binary)
- **Objective Modes**:
  - **Cost Only**: `minimize Σ(annual_volume × cost_per_litre × x[c][s][o])`
  - **Strategic Only**: `maximize Σ(strategic_score × x[c][s][o])`
  - **Weighted**: `minimize (1-w) × cost - w × strategic_score`
  - **ε-Constraint**: `minimize cost subject to Σ(strategic_score × x[c][s][o]) ≥ ε`
- **Assignment Constraint**: `Σ(x[c][s][o]) = 1 for each customer_depot_c` (exactly one allocation per depot)
- **Volume Tier Constraints**: Binary activation logic for tier eligibility based on aggregate volumes
- **Capacity Constraints**: `Σ(volume × x[c][s][o]) ≤ capacity_limit[s]` for each supplier_depot
- **Strategic Score Integration**: Strategic scores accessed from precomputed cost dictionary

**Multi-Objective Solution Extraction**:
1. Identify selected variables (`x[c][s][o] > 0.5`)
2. Calculate capacity utilization and binding constraints
3. Determine cost type (base, tier_enhanced, rac_penalty)
4. Calculate achieved strategic score for the solution
5. Generate comprehensive results with allocation details, costs, and strategic analysis

#### Multi-Objective Integration Flow
**Complete Pipeline**: 
1. `FuelOptimizationPrecomputation.run_complete_precomputation()` (with strategic scores)
2. `ParetoFrontGenerator.generate_pareto_front()` (ε-constraint method)
3. `FuelDepotOptimizerDocplex.run_optimization()` (multi-objective solver)
4. `OptimizationMapper.create_enhanced_allocation_map()` (visualization)

#### Strategic Supplier Scoring System (`strategic_supplier_scoring.py`)
**Multi-Criteria Evaluation Framework**:
- **Database Tables**: supplier_scores, criteria_weights
- **Evaluation Criteria**: 
  - Current Level (1-8 scale)
  - Product/Service Type
  - Geographical Network
  - Method of Sourcing
  - Investment in Refuelling Equipment
  - Reciprocal Business
- **Scoring Logic**: `strategic_score = Σ(criterion_value × criterion_weight)`
- **Output Range**: 0.0-1.0 for each supplier
- **Integration**: Called dynamically by precomputation engine

#### Pareto Front Generator (`pareto_front_generator.py`)
**ε-Constraint Method Implementation**:
1. **Bound Calculation**: Theoretical min/max strategic scores across all depots
2. **ε Generation**: Linear spacing of strategic constraint values
3. **Constrained Optimization**: For each ε, solve: minimize cost subject to strategic_score ≥ ε
4. **Solution Collection**: Store cost, strategic_score, and allocation details for each feasible solution
5. **Trade-off Analysis**: Calculate cost variations, strategic improvements, and extreme points
6. **Visualization**: Generate Pareto front plots and comprehensive analysis reports

### 🔧 Business Logic Implementation

#### Cost Option Types (precomputation.py)
- **Base Options**: Standard pricing without special conditions
  - **COC (Customer Own Collection)**: Customer arranges transport, pays transport costs
  - **DEL (Supplier Delivery)**: Supplier delivers, customer pays for equipment (own/buy/rent)
- **RAC Penalty Options**: Higher costs when volume commitments are not met (removes all rebates)
- **Volume Tier Options**: Lower costs when volume commitments are achieved (additional rebates)
- **Strategic Score Integration**: Each option includes strategic score for multi-objective optimization

#### Multi-Objective Constraint Logic (fuel_optimizer_docplex.py)
- **Assignment Constraints**: Each customer depot must select exactly one supply option
- **Volume Tier Activation**: Tiers activate only when aggregate volume across supplier depot group meets minimum threshold
- **Capacity Enforcement**: Supplier depot throughput limits prevent over-allocation
- **Option Availability**: NULL database values prevent unavailable options from being selected
- **Strategic Score Constraints**: ε-constraint method enforces minimum strategic score requirements

#### Multi-Objective Decision Optimization Process
1. **Data Preparation**: Extract cost matrices and strategic scores from precomputed dictionary
2. **Variable Creation**: Generate binary variables for all available depot-supplier-option combinations
3. **Objective Setup**: Configure optimization mode (cost_only, strategic_only, weighted, epsilon_constraint)
4. **Constraint Setup**: Enforce assignment, volume tier, capacity, and strategic score business rules
5. **CPLEX Solution**: Mathematical solver finds optimal allocation based on selected objective mode
6. **Multi-Objective Analysis**: For ε-constraint, generate multiple solutions across strategic score range
7. **Result Processing**: Extract allocations, calculate utilization, identify binding constraints
8. **Trade-off Analysis**: Analyze cost vs strategic score trade-offs across Pareto front
9. **Visualization**: Generate interactive map with layer controls and detailed cost/strategic popups

#### ε-Constraint Method Workflow
1. **Primary Objective**: Minimize total cost (driving objective in all iterations)
2. **Secondary Objective**: Maximize strategic score (handled as constraint)
3. **Constraint Generation**: Create strategic score constraints (ε values) from theoretical bounds
4. **Iterative Solution**: For each ε, solve: minimize cost subject to strategic_score ≥ ε
5. **Pareto Front Construction**: Collect all feasible (cost, strategic_score) pairs
6. **Trade-off Analysis**: Calculate marginal costs of strategic score improvements

### 📊 Production System Scale
- **Decision Variables**: 31,079 binary variables across optimization space
- **Depot Combinations**: 2,011 customer-supplier_depot pairs
- **Cost Options**: 8,833 total (base + volume tier options)
- **Strategic Scores**: Multi-criteria evaluation for 9 suppliers across 6 criteria
- **Volume Tiers Active**: 4 tier configurations across suppliers
- **Multi-Objective Performance**: 
  - Single optimization: <2 seconds end-to-end
  - Full Pareto front (20 points): ~30 seconds
  - Strategic score calculation: <1 second
- **Database Tables**: 8 core tables with strategic scoring integration

### 🎨 Visualization Features
- **Interactive Layer Control**: Right-side panel with supplier-specific toggles
- **Advanced Markers**: BeautifyIcon supplier depots with custom hex colors
- **Route Detail Popups**: Comprehensive cost option display with color-coded categories
- **Strategic Score Integration**: Popups include strategic supplier scores and multi-objective analysis
- **MarkerCluster Integration**: Automatic clustering/splitting of overlapping depots
- **Color Consistency**: Unified hex color scheme across markers and route lines
- **Professional Theme**: CartoDB positron white theme for enhanced visibility

### 🚀 Complete Multi-Objective Optimization System Ready
- **End-to-End Functionality**: Strategic scoring → Data processing → Multi-objective optimization → Interactive visualization
- **Mathematical Accuracy**: All calculations validated against manual specifications
- **Multi-Objective Capabilities**: ε-constraint method, weighted objectives, Pareto front generation
- **Business Logic Compliance**: Full alignment with South African fuel supply chain practices
- **Thesis Ready**: Comprehensive methodology documentation and academic analysis framework
- **Production Ready**: Scalable architecture supporting real-world deployment
- **Interactive Analysis**: Comprehensive cost and strategic score exploration with trade-off analysis

## Database Structure (Current)
- **8 main tables**: od_pair, collection_options, delivery_options, supplier_depots, customer_depots, diesel_prices, suppliers, supplier_scores, criteria_weights
- **Strategic Scoring Integration**: supplier_scores table stores multi-criteria evaluations
- **Configuration Management**: criteria_weights table stores strategic scoring weights
- **Clean Separation**: COC vs DEL options with proper availability flags (NULL = not available)
- **Volume Tiers**: Moved from database to JSON configuration for flexibility
- **Performance**: Optimized joins and indexing for <750ms total processing time

## Architecture Overview
The system follows a modular, thesis-friendly architecture with clear separation of concerns:

### Information Flow
```
pareto_front_generator.py (Multi-Objective Controller)
    ↓
precomputation.py (Data Processing Hub)
    ↓
strategic_supplier_scoring.py (Strategic Score Calculator)
    ↓
fuel_data.db (Database with Strategic Tables)
    ↓
fuel_optimizer_docplex.py (Multi-Objective Optimization Engine)
    ↓
optimization_map.py (Visualization Layer)
```

### Key Design Principles
- **Modularity**: Each component has a single, well-defined responsibility
- **Thesis-Friendly**: Clear documentation and methodology tracking
- **Extensibility**: Easy to add new objectives, constraints, or visualization methods
- **Performance**: Optimized for both single optimizations and Pareto front generation
- **Debugging**: Transparent data flow and error handling for academic research


Remember: This project documentation is for thesis writing purposes - maintain detailed, methodical records of all development steps.