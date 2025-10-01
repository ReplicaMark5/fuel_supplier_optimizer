# Thesis Results Generation - Quick Command Summary

## Two Commands for Complete Thesis Results

### 1️⃣ Baseline Single-Objective (Cost Only)

```bash
python scripts/thesis/run_baseline_optimization.py
```

**Generates:** 6 files in `outputs/thesis_results/baseline/`
- ✅ Supplier utilization (CSV + LaTeX)
- ✅ Capacity summary (CSV + LaTeX)
- ✅ Optimization map (HTML)
- ✅ Complete results (JSON)

**Runtime:** ~5-10 seconds

---

### 2️⃣ Multi-Objective Pareto Front Analysis

```bash
python scripts/thesis/run_moo_pareto_analysis.py
```

**Generates:** 7 files in `outputs/thesis_results/moo_pareto/`
- ✅ Pareto front plot (PNG)
- ✅ All solutions (CSV + JSON)
- ✅ Representative solutions table (CSV + LaTeX)
- ✅ Trade-off analysis (JSON + TXT)

**Runtime:** ~30-40 seconds

---

## What You Get for Your Thesis

### From Baseline Script:
1. **supplier_utilization_rows.tex** → Copy/paste into thesis table
2. **capacity_summary_rows.tex** → Copy/paste into thesis table
3. **baseline_optimization_map.html** → Include as supplementary material

### From MOO Script:
1. **pareto_front_fuel_optimization.png** → Main MOO results figure
2. **representative_solutions_rows.tex** → Copy/paste into thesis table (Min/Knee/Max)
3. **tradeoff_summary.txt** → Reference for writing trade-off analysis

---

## Representative Solutions Table Format

The MOO script generates LaTeX rows for this table structure:

| Point | Cost (R) | Strategic Score | ΔCost (%) | ΔScore (%) |
|-------|----------|-----------------|-----------|------------|
| Min Cost | 1,290,475,652.50 | 4047 | 0.0000 | 0.00 |
| Knee | 1,290,481,476.39 | 4249 | 0.0005 | 4.99 |
| Max Score | 1,290,970,044.28 | 4550 | 0.0383 | 12.43 |

**Where:**
- **Min Cost** = Pure cost optimization (baseline)
- **Knee** = Best trade-off point (recommended)
- **Max Score** = Maximum strategic supplier score
- **ΔCost (%)** = Percentage increase in cost vs baseline
- **ΔScore (%)** = Percentage increase in score vs baseline

---

## File Locations

```
outputs/thesis_results/
├── baseline/
│   ├── supplier_utilization_rows.tex        ← COPY TO THESIS
│   ├── capacity_summary_rows.tex            ← COPY TO THESIS
│   └── baseline_optimization_map.html       ← SUPPLEMENTARY
│
└── moo_pareto/
    ├── pareto_front_fuel_optimization.png   ← MAIN FIGURE
    ├── representative_solutions_rows.tex    ← COPY TO THESIS
    └── tradeoff_summary.txt                 ← REFERENCE
```

---

## Quick Verification

After running both scripts, verify outputs exist:

```bash
# Check baseline outputs
ls -lh outputs/thesis_results/baseline/

# Check MOO outputs
ls -lh outputs/thesis_results/moo_pareto/

# View trade-off summary
cat outputs/thesis_results/moo_pareto/tradeoff_summary.txt
```

---

## Detailed Documentation

- **COMMANDS_RUNBOOK.md** - Complete command reference with all options
- **THESIS_OUTPUTS_GUIDE.md** - Detailed guide with table formats and troubleshooting
- **PROJECT_STRUCTURE.md** - Project organization and file locations

---

**Last Updated:** 2025-09-30