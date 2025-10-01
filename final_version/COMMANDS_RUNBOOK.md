Commands Runbook

Purpose: a concise, copy‑pasteable list of commands to produce thesis outputs, with descriptions and where to find results. Run all commands from the project root:

  cd /home/blake/projects/demo5/final_version

Prerequisites
- Python deps: `pip install -r requirements.txt`
- Data present:
  - `data/databases/fuel_data.db`
  - `data/config/optimization_config.json`
- Optimizer uses DOcplex/CPLEX. Ensure IBM CPLEX is installed/licensed and visible to `docplex`.


## PRIMARY THESIS COMMANDS

### 1) Complete Baseline (Single-Objective) Analysis
**Command:** `python scripts/thesis/run_baseline_optimization.py`

**What it does:** Runs cost-only optimization and generates ALL baseline thesis outputs including:
- Supplier utilization summary (CSV + LaTeX rows)
- Capacity summary (CSV + LaTeX rows)
- Interactive HTML optimization map
- Comprehensive JSON results

**Outputs (in `outputs/thesis_results/baseline/`):**
- `supplier_utilization_baseline.csv` - Supplier allocation summary
- `supplier_utilization_rows.tex` - LaTeX table rows for thesis
- `capacity_summary_baseline.csv` - Capacity utilization summary
- `capacity_summary_rows.tex` - LaTeX table rows for thesis
- `baseline_optimization_map.html` - Interactive map visualization
- `baseline_results_complete.json` - Full optimization results

**Use for:** Baseline single-objective cost minimization results section


### 2) Complete Multi-Objective (MOO) Pareto Analysis
**Command:** `python scripts/thesis/run_moo_pareto_analysis.py`

**What it does:** Runs ε-constraint multi-objective optimization to generate Pareto front trading off cost vs strategic supplier score. Generates ALL MOO thesis outputs including:
- Pareto front visualization
- Representative solutions table (Min Cost, Knee, Max Score)
- Trade-off analysis with marginal rates
- Complete solution data

**Configuration:** Settings controlled via `data/config/optimization_config.json` under `pareto_front_settings`:
- `num_epsilon_points`: Number of ε-constraint points (default: 50)
- `duplicate_tolerance`: Precision for filtering duplicates
- `plotting`: Visualization settings (colors, markers, figure size, DPI)

**Outputs (in `outputs/thesis_results/moo_pareto/`):**
- `pareto_front_fuel_optimization.png` - Pareto front visualization
- `pareto_solutions.csv` - All Pareto solutions data
- `pareto_solutions.json` - Full solutions with metadata
- `representative_solutions.csv` - Min/Knee/Max solutions
- `representative_solutions_rows.tex` - LaTeX table rows for thesis
- `tradeoff_analysis.json` - Statistical trade-off analysis
- `tradeoff_summary.txt` - Human-readable summary

**Use for:** Multi-objective optimization and Pareto analysis results section


## LEGACY/ALTERNATIVE COMMANDS

1) Baseline (single optimization) → Thesis tables (LEGACY)
- Command: `python scripts/export/export_baseline_summaries.py`
- What it does: Runs cost‑only optimization and writes baseline supplier utilization and capacity summaries.
- Outputs:
  - `outputs/thesis_exports/supplier_utilization_baseline.csv`
  - `outputs/thesis_exports/capacity_summary_baseline.csv`
  - `outputs/thesis_exports/supplier_utilization_rows.tex`
  - `outputs/thesis_exports/capacity_summary_rows.tex`
- **Note:** Use `run_baseline_optimization.py` instead for complete outputs including map

3) Run a single optimization (programmatic, quick summary)
- Command:
  - `python - << 'PY'
from src.precomputation import FuelOptimizationPrecomputation
from src.fuel_optimizer_docplex import FuelDepotOptimizerDocplex
pre = FuelOptimizationPrecomputation()
data = pre.run_complete_precomputation()
opt = FuelDepotOptimizerDocplex(data)
results = opt.run_optimization()
print('Status:', results.get('status'))
print('Total Annual Cost (R):', results.get('total_annual_cost'))
print('Allocations:', len(results.get('allocations', [])))
PY`
- Outputs: summary printed to console (no files written by this snippet).

4) Pareto front generation (ε‑constraint) → JSON/CSV
- Command:
  - `python - << 'PY'
from pathlib import Path
from src.pareto_front_generator import ParetoFrontGenerator
import json, csv
out_dir = Path('outputs/optimization_results'); out_dir.mkdir(parents=True, exist_ok=True)
pg = ParetoFrontGenerator()
points = pg.generate_pareto_front(num_points=20)
json_path = out_dir / 'pareto_fuel_solutions.json'
csv_path = out_dir / 'pareto_fuel_solutions.csv'
json.dump(points, open(json_path, 'w'), indent=2)
with open(csv_path, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=sorted(points[0].keys()))
    w.writeheader(); w.writerows(points)
print('Wrote:', json_path, csv_path)
PY`
- Outputs:
  - `outputs/optimization_results/pareto_fuel_solutions.json`
  - `outputs/optimization_results/pareto_fuel_solutions.csv`

5) Pareto front plot (PNG)
- Command:
  - `python - << 'PY'
from pathlib import Path
from src.pareto_front_generator import ParetoFrontGenerator
pg = ParetoFrontGenerator()
pg.generate_pareto_front(num_points=20)
Path('outputs/visualizations').mkdir(parents=True, exist_ok=True)
pg.plot_pareto_front(save_path='outputs/visualizations/pareto_front_fuel_optimization.png')
print('Saved plot to outputs/visualizations/pareto_front_fuel_optimization.png')
PY`
- Output:
  - `outputs/visualizations/pareto_front_fuel_optimization.png`


## Other Commands

2) Cost dictionary exports (JSON/CSV/Excel)
- JSON only:
  - `python scripts/export/export_costs.py --format json --output outputs/optimization_results/fuel_costs`
  - Output: `outputs/optimization_results/fuel_costs.json`
- CSV only:
  - `python scripts/export/export_costs.py --format csv --output outputs/optimization_results/fuel_costs`
  - Output: `outputs/optimization_results/fuel_costs_flattened.csv`
- Excel only:
  - `python scripts/export/export_costs.py --format excel --output outputs/optimization_results/fuel_costs`
  - Output: `outputs/optimization_results/fuel_costs.xlsx`
- All formats:
  - `python scripts/export/export_costs.py --format all --output outputs/optimization_results/fuel_costs`
  - Outputs in `outputs/optimization_results/` (JSON, CSV, Excel)

6) Interactive cost query (manual inspection)
- Command: `python tools/query_costs.py`
- What it does: Loads the full precomputed cost dictionary and lets you query per depot→supplier_depot.
- Outputs: Console output only (no files written).

7) Verification suite (validation appendix)
- Command: `python tests/verification/optimizer_verification_suite.py`
- What it does: Runs automated verification over scenarios.
- Inputs: `tests/verification/test_scenarios/*.json` and `*.db`
- Output: `tests/verification/verification_results/verification_report.json`

8) Data preparation (only if rebuilding the database)
- Convert Excel → SQLite (set the Excel path inside the script if needed):
  - `python scripts/data_preparation/extractors/excel_to_sqlite.py`
  - Output DB: `data/databases/fuel_data.db` (overwrites existing)
- Extract diesel prices from PDF (set PDF path inside the script):
  - `python scripts/data_preparation/extractors/diesel_price_extractor.py`
  - Writes/updates table: `diesel_prices` in `data/databases/fuel_data.db`
- Create/import strategic scoring tables (update the Excel path at top):
  - `python scripts/data_preparation/create_supplier_tables.py`
  - Writes/updates tables: `criteria_weights`, `supplier_scores` in `data/databases/fuel_data.db`

Notes / Troubleshooting
- Default paths: all core modules/scripts default to `data/config/optimization_config.json` and `data/databases/fuel_data.db`.
- CPLEX: If the optimizer fails to solve, verify your IBM CPLEX installation and license; `docplex` must be able to find the solver.
- Performance: single optimization < 2s; full 20‑point Pareto ≈ 30s (machine‑dependent).

