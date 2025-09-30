<!-- Edit ONLY this file (CONTEXT.md). Targets like CLAUDE.md / AGENTS.md / GEMINI.md are read only and generated. (after edits to the CONTEXT.MD run .context-sync/manual_sync_context.sh to make the changes sync across to the target files) -->

# Project Context

**Name:** Multi-Objective Depot Supplier Allocation Optimizer
**One-liner:** Thesis project developing multi-objective optimization using CPLEX to minimize fuel supply costs while maximizing strategic supplier scores
**Stack:** Python, CPLEX/DOcplex, SQLite, Pandas, Matplotlib, Streamlit
**Owners:** Blake (Thesis Project)

## Quick Start
1. `pip install -r requirements.txt`
2. `python final_version/fuel_optimizer_docplex.py` (core optimization)
3. `python final_version/pareto_front_generator.py` (multi-objective analysis)
4. Key files: fuel_optimizer_docplex.py, precomputation.py, pareto_front_generator.py, strategic_supplier_scoring.py

## Commands
**Common:**
- `pip install -r requirements.txt` (install dependencies)
- `python final_version/fuel_optimizer_docplex.py` (run single optimization)
- `python final_version/pareto_front_generator.py` (generate Pareto fronts)
- `python final_version/query_costs.py` (interactive cost analysis)
- `python final_version/optimization_map.py` (create visualizations)

## Architecture Notes
- **Binary Integer Programming**: CPLEX-based optimization with 31,079+ decision variables
- **Multi-Objective Framework**: ε-constraint method for Pareto front generation
- **Strategic Scoring Integration**: Multi-criteria weighted supplier evaluation (6 criteria)
- **South African Currency**: All financials in Rands (R), diesel prices in cents converted appropriately
- **Volume Tier System**: Incremental rebate structure with supplier depot-specific configurations
- **Present Value Calculations**: WACC-based discounting for different payment terms

## Project Structure
```
├── final_version/                           # Active core implementation
│   ├── fuel_optimizer_docplex.py          # Multi-objective CPLEX optimization engine
│   ├── precomputation.py                  # Cost & strategic score calculation system
│   ├── pareto_front_generator.py          # Multi-objective analysis controller
│   ├── strategic_supplier_scoring.py      # Strategic supplier score calculator
│   ├── optimization_map.py                # Enhanced visualization mapper
│   ├── optimization_config.json           # Volume tiers, PV settings, strategic weights
│   ├── fuel_data.db                      # Production database with strategic scoring
│   ├── query_costs.py                     # Interactive cost analysis tool
│   ├── thesis_notes.md                    # Methodology documentation
│   └── test_debug/                        # Testing and debugging scripts
├── NSGA_II_Repair_Dynamic_2.py           # NSGA-II implementation for comparison
├── MOO_e_constraint_Cost_Dynamic_2.py     # Alternative ε-constraint implementation
├── Comparison_App.py                      # Streamlit comparison interface
├── comparison_experiment.py               # Algorithm comparison experiments
├── pareto_metrics.py                      # Pareto front quality metrics
└── requirements.txt                       # Python dependencies
```

## Standards
- Format and lint before PR
- Prefer types where available
- Small, focused functions
- Tests for new behavior

## Agent Guide
**Before coding:** read this file + README, locate existing patterns, plan minimal change.
**When coding:** follow conventions, add tests, update docs if API changes.
**Before submitting:** run format, lint, types, unit tests. Provide minimal diff.
**Don't:** edit generated targets, add deps without reason, break public APIs.

## Install Policy
- **Default: no sudo**. Use user-space installs (venv, pipx, nvm)
- **sudo only** for OS packages (`apt install git`)
- **Never** `sudo pip` or `sudo npm`
- Agents must ask before using sudo

## Current Focus
**Complete Multi-Objective Optimization System** - System is production-ready with full ε-constraint method implementation for Pareto front generation, strategic supplier scoring integration, and comprehensive visualization capabilities. Current focus on algorithm comparison experiments and thesis documentation.

## Important Instructions for Future Claude Instances

### Thesis Documentation Protocol
**ALWAYS update `final_version/thesis_notes.md` after ANY significant progress, changes, or methods are applied to the project.**

The thesis_notes.md file serves as:
- Methodology section documentation
- Step-by-step process tracking
- Technical implementation notes
- Data processing decisions

### SOUTH AFRICAN CURRENCY
- The financials of this optimizer use Rands; only values in cents are from diesel_prices table (rtl_wholesale)
- All rebate values are in Rands and all outputs must be in Rands
- In South Africa: 1R (Rand) = 100c (Cents)

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

## Core Algorithm Implementation

### Multi-Objective CPLEX Optimization Engine (`fuel_optimizer_docplex.py`)
**Purpose**: Minimizes costs while maximizing strategic supplier scores through multiple objective modes
- **Objective Modes**: "cost_only", "strategic_only", "weighted", "epsilon_constraint"
- **Logic**: Binary variables for each customer→supplier_depot→option combination with assignment constraints
- **Features**: Volume tier activation constraints, supplier depot capacity limits, RAC penalty enforcement, strategic score integration
- **Output**: Optimal allocation decisions with cost breakdown, capacity utilization, and strategic score analysis

### Cost & Strategic Score Calculation System (`precomputation.py`)
**Purpose**: Calculates all possible cost options in Present Value terms AND integrates strategic supplier scores
- **Logic**: Multi-table database joins → fuel zone mapping → PV discounting → volume tier calculations → strategic score integration
- **Features**: Base costs (COC/DEL options), RAC penalty costs, volume tier enhanced costs, strategic supplier scores, coordinate integration
- **Strategic Integration**: Calls `strategic_supplier_scoring.py` to add weighted strategic scores to cost dictionary
- **Output**: Comprehensive cost dictionary with 31,079+ cost options and strategic scores across 2,011 depot-supplier_depot pairs

### Multi-Objective Analysis Controller (`pareto_front_generator.py`)
**Purpose**: Generates Pareto-optimal solutions for cost vs strategic supplier score trade-offs
- **Method**: ε-constraint approach minimizing cost subject to strategic score constraints
- **Logic**: Calculate strategic bounds → Generate ε values → Solve constrained optimizations → Analyze trade-offs
- **Features**: Theoretical bound calculation, adaptive ε spacing, feasibility checking, comprehensive trade-off analysis
- **Output**: Pareto front solutions, trade-off analysis, visualization plots, CSV/JSON exports

### Strategic Supplier Score Calculator (`strategic_supplier_scoring.py`)
**Purpose**: Calculate weighted strategic scores for suppliers based on multiple business criteria
- **Criteria**: Current Level, Product/Service Type, Geographical Network, Method of Sourcing, Investment in Equipment, Reciprocal Business
- **Logic**: Database loading → criteria weight application → weighted score calculation → supplier ranking
- **Output**: Strategic scores (0.0-1.0) for each supplier, used in multi-objective optimization

## System Performance & Scale
- **Decision Variables**: 31,079 binary variables across optimization space
- **Depot Combinations**: 2,011 customer-supplier_depot pairs
- **Cost Options**: 8,833 total (base + volume tier options)
- **Strategic Scores**: Multi-criteria evaluation for 9 suppliers across 6 criteria
- **Performance**: Single optimization <2 seconds, Full Pareto front ~30 seconds
- **Database Tables**: 8 core tables with strategic scoring integration

---
_Generated on 20250928T003021_

Remember: This project documentation is for thesis writing purposes - maintain detailed, methodical records of all development steps.
