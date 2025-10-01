# ⚡ Quick Start: Generate All Thesis Results

## Two Commands, All Outputs ✨

### Step 1: Navigate to project
```bash
cd /home/blake/projects/demo5/final_version
```

### Step 2: Run baseline optimization
```bash
python scripts/thesis/run_baseline_optimization.py
```
**⏱️ ~10 seconds** → Generates 6 files in `outputs/thesis_results/baseline/`

### Step 3: Run multi-objective analysis
```bash
python scripts/thesis/run_moo_pareto_analysis.py
```
**⏱️ ~40 seconds** → Generates 7 files in `outputs/thesis_results/moo_pareto/`

---

## ✅ What You Get

### 📊 For Your Thesis Tables:
1. `baseline/supplier_utilization_rows.tex` → **Supplier allocation table**
2. `baseline/capacity_summary_rows.tex` → **Capacity constraints table**
3. `moo_pareto/representative_solutions_rows.tex` → **Pareto solutions table** ⭐

### 📈 For Your Thesis Figures:
4. `moo_pareto/pareto_front_fuel_optimization.png` → **Main MOO figure** ⭐

### 🗺️ For Supplementary Material:
5. `baseline/baseline_optimization_map.html` → **Interactive map**

### 📝 For Analysis & Reference:
6. `moo_pareto/tradeoff_summary.txt` → Trade-off narrative
7. `baseline/baseline_results_complete.json` → Full baseline data
8. `moo_pareto/pareto_solutions.json` → Full MOO data

---

## 🎯 Priority Files (Copy to Thesis)

**Must-have for thesis writing:**

```bash
# LaTeX table rows (copy/paste directly)
outputs/thesis_results/baseline/supplier_utilization_rows.tex
outputs/thesis_results/baseline/capacity_summary_rows.tex
outputs/thesis_results/moo_pareto/representative_solutions_rows.tex

# Main figure (copy to thesis figures/ folder)
outputs/thesis_results/moo_pareto/pareto_front_fuel_optimization.png

# Reference material
outputs/thesis_results/moo_pareto/tradeoff_summary.txt
```

---

## 📋 Verification Checklist

After running both commands:

- [ ] Baseline directory has 6 files
- [ ] MOO directory has 7 files
- [ ] PNG image opens correctly
- [ ] LaTeX .tex files contain formatted rows
- [ ] HTML map opens in browser
- [ ] No error messages in console

---

## 🚨 If Something Goes Wrong

**Import errors?**
```bash
# Verify you're in the right directory
pwd  # Should show: .../final_version
```

**CPLEX errors?**
```bash
# Test CPLEX installation
python -c "import docplex.mp.model; print('CPLEX OK')"
```

**Missing files?**
```bash
# Check data files exist
ls -l data/databases/fuel_data.db
ls -l data/config/optimization_config.json
```

---

## 📖 Detailed Documentation

Need more details? See:
- `THESIS_COMMANDS_SUMMARY.md` - Command overview
- `THESIS_OUTPUTS_GUIDE.md` - Complete guide with table formats
- `COMMANDS_RUNBOOK.md` - All commands with troubleshooting
- `docs/LATEX_TABLE_TEMPLATES.md` - LaTeX table templates

---

## 💡 Pro Tips

1. **Run both scripts every time** you make changes to data or config
2. **Keep the JSON files** for validation and cross-checking
3. **Read tradeoff_summary.txt** before writing your analysis section
4. **Backup outputs** before re-running (or use git to track changes)

---

**Questions?** Check `THESIS_OUTPUTS_GUIDE.md` for detailed explanations.

**Last Updated:** 2025-09-30