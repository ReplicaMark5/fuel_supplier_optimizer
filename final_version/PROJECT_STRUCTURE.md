# Final Version - Project Structure

**Last Updated:** 2025-09-30
**Status:** ✅ Fully Restructured and Operational

---

## Quick Navigation

```
final_version/
├── src/                    # Core library code (import from here)
├── scripts/                # Executable scripts (run these)
├── tests/                  # All testing & verification
├── tools/                  # Interactive utilities
├── data/                   # Config & databases (gitignored)
├── outputs/                # Generated files (gitignored)
├── docs/                   # Documentation & thesis
└── archive/                # Deprecated code
```

---

## Directory Guide

### 📦 `src/` - Core Library Code
**Purpose:** Reusable optimization engine (import, don't run directly)

```
src/
├── fuel_optimizer_docplex.py       # Main CPLEX optimizer
├── precomputation.py               # Cost calculation engine
├── pareto_front_generator.py       # Multi-objective analysis
├── strategic_supplier_scoring.py   # Supplier scoring
└── visualization/
    └── optimization_map.py         # HTML map generator
```

**Usage:**
```python
from src.precomputation import FuelOptimizationPrecomputation
from src.fuel_optimizer_docplex import FuelDepotOptimizerDocplex
```

**Defaults:** All modules auto-resolve paths to `data/config/` and `data/databases/`

---

### 🚀 `scripts/` - Executable Scripts
**Purpose:** Run these to perform operations

```
scripts/
├── data_preparation/
│   ├── create_supplier_tables.py          # Setup strategic scoring tables
│   └── extractors/
│       ├── diesel_price_extractor.py      # Extract diesel prices
│       └── excel_to_sqlite.py             # Import Excel to DB
├── export/
│   ├── export_costs.py                    # Export cost data
│   └── export_baseline_summaries.py       # Generate thesis tables
└── (future: visualization/ for map generation scripts)
```

**Usage:**
```bash
python scripts/export/export_baseline_summaries.py
python scripts/data_preparation/create_supplier_tables.py
```

**Output:** Scripts write to `outputs/` directory

---

### 🧪 `tests/` - Testing & Verification
**Purpose:** Unit tests, debugging scripts, verification suite

```
tests/
├── unit/                              # Unit tests
│   ├── test_volume_tiers.py
│   ├── test_transport_costs.py
│   ├── test_coc_equipment_costs.py
│   ├── test_del_simplification.py
│   └── ...
├── debug/                             # Debugging utilities
│   ├── debug_costs.py
│   ├── debug_validation_stats.py
│   └── transport_cost_comparison.py
└── verification/                      # Formal verification
    ├── optimizer_verification_suite.py
    ├── test_data_generator.py
    ├── test_scenarios/                # Test configs & DBs
    └── verification_results/
```

**Usage:**
```bash
python tests/unit/test_del_simplification.py
python tests/verification/optimizer_verification_suite.py
```

---

### 🛠️ `tools/` - Interactive Utilities
**Purpose:** Interactive CLI tools for exploration

```
tools/
├── query_costs.py              # Interactive cost query tool
└── manual_cost_calculator.py   # Manual calculation utility
```

**Usage:**
```bash
python tools/query_costs.py
```

---

### 💾 `data/` - Data Files (Gitignored)
**Purpose:** Configuration and databases

```
data/
├── config/
│   └── optimization_config.json    # Volume tiers, PV settings, weights
└── databases/
    ├── fuel_data.db                # Production database
    └── fuel_data_backup.db         # Backup
```

**Gitignore:** `*.db` files are ignored, `*.json` config is tracked

---

### 📊 `outputs/` - Generated Files (Gitignored)
**Purpose:** All generated outputs go here

```
outputs/
├── optimization_results/           # CSV/JSON optimization results
│   ├── pareto_fuel_solutions.csv
│   ├── pareto_fuel_solutions.json
│   ├── complete_export.json
│   └── ...
├── visualizations/                 # PNG/HTML visualizations
│   ├── pareto_front_fuel_optimization.png
│   └── optimization_allocation_map.html
└── thesis_exports/                 # LaTeX-ready thesis files
    ├── supplier_utilization_rows.tex
    ├── capacity_summary_rows.tex
    └── ...
```

**Gitignore:** Entire `outputs/` directory is ignored

---

### 📚 `docs/` - Documentation
**Purpose:** Thesis materials, specs, notes

```
docs/
├── chapters_copy/              # Thesis LaTeX files
├── input_specs/                # Constraint & tier specifications
├── output_specs/               # Mathematical formulation docs
├── personal_notes/             # Development notes & thesis_notes.md
└── verification_research/      # V&V methodology notes
```

---

### 🗄️ `archive/` - Deprecated Code
**Purpose:** Old/broken code for reference

```
archive/
└── delete/                     # Deprecated implementations
```

---

## Common Workflows

### Run a Complete Optimization
```python
from src.precomputation import FuelOptimizationPrecomputation
from src.fuel_optimizer_docplex import FuelDepotOptimizerDocplex

# Precompute all costs
precomp = FuelOptimizationPrecomputation()
data = precomp.run_complete_precomputation()

# Run optimization
optimizer = FuelDepotOptimizerDocplex(data)
results = optimizer.run_optimization()

print(f"Status: {results['status']}")
print(f"Cost: R{results['objective_value']:,.2f}")
```

### Generate Pareto Front
```python
from src.pareto_front_generator import ParetoFrontGenerator

generator = ParetoFrontGenerator()
pareto_results = generator.generate_pareto_front(num_points=10)
```

### Export Thesis Data
```bash
python scripts/export/export_baseline_summaries.py
# Output: outputs/thesis_exports/*.csv, *.tex
```

### Query Costs Interactively
```bash
python tools/query_costs.py
```

---

## Import Patterns

### Within `src/` (package-relative)
```python
# In src/fuel_optimizer_docplex.py
from .precomputation import FuelOptimizationPrecomputation
from .visualization.optimization_map import OptimizationMapper
```

### Outside `src/` (absolute from src)
```python
# In scripts/, tests/, tools/
from src.precomputation import FuelOptimizationPrecomputation
from src.fuel_optimizer_docplex import FuelDepotOptimizerDocplex
```

---

## Path Resolution

All core modules use **project-root-relative paths**:

```python
# Automatically resolves to:
# /path/to/final_version/data/config/optimization_config.json
# /path/to/final_version/data/databases/fuel_data.db

precomp = FuelOptimizationPrecomputation()  # No paths needed!
```

**How it works:**
```python
config_path = str(Path(__file__).resolve().parents[1] / "data/config/optimization_config.json")
db_path = str(Path(__file__).resolve().parents[1] / "data/databases/fuel_data.db")
```

---

## Migration Notes

**Backup Location:** `backup_before_restructure_20250930_101233/`

**Migration Report:** `migration_report.json`

**Key Changes:**
- ✅ 68 files moved
- ✅ 35 files updated (imports/paths)
- ✅ 0 errors
- ✅ All tests updated
- ✅ All data-prep scripts updated
- ✅ Core defaults updated

---

## Git Workflow

### Ignored Patterns
```gitignore
outputs/                    # All generated files
data/databases/*.db         # Databases
__pycache__/               # Python cache
backup_before_restructure_*/
```

### Tracked Files
```
src/                       # All source code
scripts/                   # All scripts
tests/                     # All tests
data/config/*.json         # Configuration only
docs/                      # Documentation
```

---

## Next Steps

1. **Test your scripts:**
   ```bash
   python scripts/export/export_costs.py
   python tests/verification/optimizer_verification_suite.py
   ```

2. **Update documentation** if you add new scripts/modules

3. **Delete backup** once you've verified everything works:
   ```bash
   rm -rf backup_before_restructure_*
   ```

4. **Commit the restructure:**
   ```bash
   git add .
   git commit -m "refactor: restructure project with src/scripts/tests/data/outputs separation"
   ```

---

## Support Files

- `restructure_migration.py` - Migration script (can be archived)
- `fix_test_and_dataprep_paths.py` - Post-migration fixes (can be archived)
- `migration_report.json` - Detailed migration log (reference)

---

**Last Migration:** 2025-09-30 10:12:33
**Migration Scripts:** Completed successfully
**Status:** ✅ Production Ready