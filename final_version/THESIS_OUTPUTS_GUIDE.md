# Thesis Outputs Quick Reference Guide

This guide explains the two main commands you need to generate all thesis results.

## Setup

Ensure you're in the project directory:
```bash
cd /home/blake/projects/demo5/final_version
```

## Command 1: Baseline Single-Objective Optimization

**Purpose:** Generate all baseline cost minimization results for your thesis

**Command:**
```bash
python scripts/thesis/run_baseline_optimization.py
```

**What it generates:**

| Output File | Description | Use In Thesis |
|------------|-------------|---------------|
| `supplier_utilization_baseline.csv` | Supplier allocation summary with volumes and costs | Reference data |
| `supplier_utilization_rows.tex` | LaTeX table rows ready to paste | Supplier utilization table |
| `capacity_summary_baseline.csv` | Depot capacity utilization summary | Reference data |
| `capacity_summary_rows.tex` | LaTeX table rows ready to paste | Capacity constraints table |
| `baseline_optimization_map.html` | Interactive map of optimized allocations | Visual in appendix |
| `baseline_results_complete.json` | Full optimization results | Reference/validation |

**Output location:** `outputs/thesis_results/baseline/`

**Expected runtime:** ~5-10 seconds

**Key metrics provided:**
- Total annual cost (R)
- Number of allocations (60 customer depots)
- Supplier utilization breakdown
- Capacity constraint analysis
- Binding capacity constraints

---

## Command 2: Multi-Objective Pareto Front Analysis

**Purpose:** Generate Pareto front and trade-off analysis between cost and strategic supplier score

**Command:**
```bash
python scripts/thesis/run_moo_pareto_analysis.py
```

**What it generates:**

| Output File | Description | Use In Thesis |
|------------|-------------|---------------|
| `pareto_front_fuel_optimization.png` | Pareto front visualization (cost vs score) | Main MOO results figure |
| `pareto_solutions.csv` | All 20 Pareto-optimal solutions | Reference data |
| `pareto_solutions.json` | Full solutions with metadata | Reference/validation |
| `representative_solutions.csv` | Min Cost, Knee, Max Score points | Reference data |
| `representative_solutions_rows.tex` | LaTeX table rows ready to paste | **Main results table** |
| `tradeoff_analysis.json` | Statistical trade-off analysis (MRS, etc.) | Analysis section |
| `tradeoff_summary.txt` | Human-readable summary | Quick reference |

**Output location:** `outputs/thesis_results/moo_pareto/`

**Expected runtime:** ~30-40 seconds (20 optimization runs)

**Key metrics provided:**
- Pareto front with 20 solutions
- Min cost solution (baseline equivalent)
- Knee point solution (recommended trade-off)
- Max strategic score solution
- Cost range and variation (%)
- Strategic score range and variation (%)
- Marginal rates of substitution (R per score point)

---

## Representative Solutions Table

The `representative_solutions_rows.tex` file provides LaTeX rows for this table format:

```latex
\begin{table}[!htbp]
  \centering
  \caption{Representative Pareto solutions (ε-constraint). Costs in Rands; deltas vs minimum cost.}
  \label{tab:rep_solutions}
  \begin{tabular}{p{2.5cm}rrrr}
    \toprule
    \textbf{Point} & \textbf{Cost (R)} & \textbf{Strategic Score} & \textbf{ΔCost (\%)} & \textbf{ΔScore (\%)} \\
    \midrule
    % PASTE representative_solutions_rows.tex CONTENT HERE
    \bottomrule
  \end{tabular}
\end{table}
```

**The table shows:**
- **Min Cost**: Pure cost optimization (baseline)
- **Knee**: Recommended balanced solution with best cost/score trade-off
- **Max Score**: Maximum strategic supplier score
- **ΔCost (%)**: Percentage cost increase vs baseline
- **ΔScore (%)**: Percentage strategic score improvement vs baseline

---

## Quick Workflow

1. **For baseline results section:**
   ```bash
   python scripts/thesis/run_baseline_optimization.py
   ```
   - Copy LaTeX rows from `supplier_utilization_rows.tex` → thesis table
   - Copy LaTeX rows from `capacity_summary_rows.tex` → thesis table
   - Include `baseline_optimization_map.html` as supplementary material

2. **For multi-objective results section:**
   ```bash
   python scripts/thesis/run_moo_pareto_analysis.py
   ```
   - Include `pareto_front_fuel_optimization.png` as main figure
   - Copy LaTeX rows from `representative_solutions_rows.tex` → thesis table
   - Reference `tradeoff_summary.txt` for analysis narrative

---

## Troubleshooting

**Import errors:**
- Ensure you're running from `final_version/` directory
- Check that `src/` contains all required modules

**CPLEX errors:**
- Verify IBM CPLEX is installed and licensed
- Test with: `python -c "import docplex.mp.model; print('OK')"`

**Missing data files:**
- Ensure `data/databases/fuel_data.db` exists
- Ensure `data/config/optimization_config.json` exists

**Performance issues:**
- Baseline should complete in <10 seconds
- MOO should complete in <60 seconds
- If slower, check CPLEX configuration

---

## Output Directory Structure

```
outputs/thesis_results/
├── baseline/
│   ├── supplier_utilization_baseline.csv
│   ├── supplier_utilization_rows.tex        ← PASTE IN THESIS
│   ├── capacity_summary_baseline.csv
│   ├── capacity_summary_rows.tex            ← PASTE IN THESIS
│   ├── baseline_optimization_map.html       ← INCLUDE AS SUPPLEMENTARY
│   └── baseline_results_complete.json
│
└── moo_pareto/
    ├── pareto_front_fuel_optimization.png   ← MAIN FIGURE
    ├── pareto_solutions.csv
    ├── pareto_solutions.json
    ├── representative_solutions.csv
    ├── representative_solutions_rows.tex    ← PASTE IN THESIS
    ├── tradeoff_analysis.json
    └── tradeoff_summary.txt                 ← REFERENCE FOR NARRATIVE
```

---

## Key Differences from Previous Commands

**OLD:** Multiple fragmented commands, manual assembly required
- Separate baseline export script
- Separate Pareto generation
- Manual map creation
- No integrated LaTeX output

**NEW:** Two comprehensive commands
- ✓ Complete baseline analysis in one command
- ✓ Complete MOO analysis in one command
- ✓ All LaTeX rows pre-formatted
- ✓ All visualizations generated
- ✓ Organized output structure

---

## Notes

- Both scripts use the same underlying optimization engine (`fuel_optimizer_docplex.py`)
- Data is consistent between baseline and MOO runs
- Representative solutions table format matches your thesis LaTeX template
- All costs are in South African Rands (R)
- Strategic scores are normalized weighted scores (0-1 scale, multiplied by 60 depots)