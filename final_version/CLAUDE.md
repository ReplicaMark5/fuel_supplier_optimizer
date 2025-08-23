# Depot Supplier Allocation Optimizer Project

## Project Context
This is a thesis project developing a depot supplier allocation optimizer using CPLEX to minimize fuel supply costs. The project involves binary integer programming optimization with volume tier constraints. 


## Key Files
- **`precomputation.py`**: Main implementation - Complete volume tier system (base costs + tier costs)
- **`optimization_config.json`**: Simplified volume tier configurations and PV settings  
- **`fuel_data.db`**: Production SQLite database (reorganized structure)
- **`query_costs.py`**: Interactive cost analysis and debugging tool
- **`thesis_notes.md`**: **CRITICAL** - Methodology documentation for thesis writing
- **`manual_crosscheck_calc.md`**: Formula specifications for COC and DEL calculations

## Project Structure
```
├── precomputation.py          # Main implementation (Phases 1+2 complete)
├── optimization_config.json   # All configuration and volume tier definitions
├── fuel_data.db              # Reorganized database with clean schema
├── query_costs.py            # Interactive cost analysis and debugging tool
├── thesis_notes.md           # Methodology documentation for thesis writing
├── extractors/               # Data processing utilities
│   ├── diesel_price_extractor.py
│   └── excel_to_sqlite.py
├── test_debug/               # Testing and debugging scripts
│   ├── debug_costs.py
│   ├── debug_validation_stats.py
│   └── test_volume_tiers.py
├── tools/                    # Additional utilities
│   └── manual_cost_calculator.py
├── personal_notes/           # Development planning and technical design docs
│   ├── manual_crosscheck_calc.md
│   ├── vol_tier_logic.txt
│   ├── volume_tier_specs.txt
│   ├── Optimizer.md
│   ├── TODO.txt
│   └── commands.txt
└── delete/                   # Archived/backup files
    ├── memory_log.md
    ├── Precomputations.md
    ├── precomputation_broken_backup.py
    └── [various backup files]
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

## Current Project Status (Latest Update: 2025-01-22)

### ✅ Volume Tier Implementation Complete
- **Phase 1**: Base cost calculations for COC and DEL options with Present Value discounting
- **Phase 2**: Volume tier system with supplier depot-specific tier structures
- **Phase 3**: Configuration simplification and formula validation complete

### 🎯 Technical Achievements
- **COC Volume Tiers**: NET30 calculations with override/add combination rules
- **DEL Volume Tiers**: Complete implementation including delivery costs and equipment costs
- **Multiple Tier Bands**: Individual tier calculations (15M-20M, 20M-25M, 25M+ etc.)
- **Formula Validation**: All calculations match manual crosscheck specifications exactly
- **Simplified Configuration**: Removed legacy fields, clean JSON structure

### 📁 Active Core Files
- **`precomputation.py`**: Main implementation (904 lines) - base_costs + tier_costs structure
- **`optimization_config.json`**: Clean volume tier configurations (4 tiers defined)
- **`query_costs.py`**: Interactive testing with verbose debugging capability
- **`fuel_data.db`**: Production database (2,011 depot-supplier_depot combinations)

### 🏗️ System Architecture
- **Cost Dictionary Structure**: `costs[depot_id][supplier_depot_id]`
  - `base_costs`: {coc_cash, coc_30, coc_45, coc_60, del_own, del_buy, del_rent}
  - `tier_costs`: {tier_name: {option_tier_bands...}}
- **Volume Tier Logic**: Incremental/stacked bands with individual cost calculations
- **Business Rules**: Supplier depot-specific tier groupings (not customer depots)
- **Combination Rules**: "add" (base + tier rebates) or "override" (tier replaces base)

### 📊 Production Data Scale
- **Total Combinations**: 2,011 depot-supplier_depot pairs
- **Cost Options**: 8,833 total (base + volume tier options)
- **Volume Tiers Active**: 4 tier configurations across suppliers
- **Performance**: <1 second complete precomputation including volume tiers

### 🔧 Recent Critical Fixes
- **DEL Cost Formula**: Added missing delivery cost component `(del_fee_per_ltr_per_km * distance)`
- **Volume Tier Structure**: Multiple tier bands per supplier (not just highest tier)
- **Configuration Cleanup**: Removed unnecessary `precomputation_settings.volume_scenarios`
- **Manual Formula Alignment**: Both COC and DEL now match manual calculation specs

### 🚀 Ready For Next Phase: CPLEX Integration
- Volume tier system architecturally complete
- Dictionary structure optimized for binary integer programming
- Individual supplier depot tier structures preserved
- All cost calculations validated against manual formulas
- Configuration system simplified and production-ready


## Database Structure (Current)
- **6 main tables**: od_pair, collection_options, delivery_options, supplier_depots, customer_depots, diesel_prices, suppliers
- **Clean separation**: COC vs DEL options with proper availability flags (NULL = not available)
- **Volume tiers**: Moved from database to JSON configuration for flexibility
- **Performance**: Optimized joins and indexing for <750ms total processing time

Remember: This project documentation is for thesis writing purposes - maintain detailed, methodical records of all development steps.