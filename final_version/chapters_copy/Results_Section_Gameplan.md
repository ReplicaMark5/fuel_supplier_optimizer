# Model Results Section Gameplan (Updated)

## Strategic Framing: Confidentiality as Strength

Core message: Use adjusted/synthetic data to demonstrate generalizability and protect proprietary terms. Focus on optimization patterns, trade-offs, and business logic—not absolute commercial figures. Include the sanitized optimization configuration in the appendix for reproducibility.

## Section Structure (with concrete deliverables)

### 1) Research Context and Data Confidentiality (~200 words)
- Opening paragraph (ready to paste in LaTeX) clarifying synthetic/augmented dataset while preserving structure, logic, and constraints.
- One sentence linking to sanitized config in the appendix.

LaTeX snippet to paste:
\textbf{Research Context and Data Confidentiality}: To protect proprietary supplier pricing and contract terms while demonstrating model capabilities, this analysis employs a realistic but adjusted dataset that preserves the complexity and business logic of real-world fuel procurement scenarios. This approach enables validation of the optimization framework's effectiveness across diverse market conditions while maintaining commercial confidentiality. The results emphasize optimization patterns, decision trade-offs, and business logic validation rather than company-specific cost figures, demonstrating the model's generalizability and practical applicability. A sanitized configuration listing is provided in the appendix to support reproducibility on the adjusted dataset.

### 2) Baseline (Cost-Only) Optimization Results (~500–700 words)
- Deliverables to insert:
  - Figure: Optimized allocation map (static snapshot).
  - Table: Supplier utilization summary (Supplier, Allocations, Volume, Total Cost, Avg R/L).
  - Table: Tier/RAC activations (contract, regime, selected band(s), notes).
  - Table: Capacity constraints summary (binding and near-capacity depots).
- Sources: `fuel_optimizer_docplex.py` solution extraction + `final_version/optimization_allocation_map.html` (export PNG before compiling LaTeX).
- LaTeX stubs provided in `final_version/chapters_copy/results_insert_stubs.tex`.

Notes:
- If absolute R values are undesirable in main text, keep the table in an appendix and report relative deltas in the chapter.

### 3) Multi-Objective (ε-Constraint) Results and Trade-offs (~500 words)
- Deliverables to insert:
  - Figure: Pareto front plot (cost vs strategic score).
  - Table: Representative solutions (Min Cost, Knee, Max Score) with ΔCost/ΔScore vs Min Cost.
- Source: Latest run artifacts in `Output Data/econstraint_front_*.csv` and Pareto plot.
- Status: Representative table is pre-filled with exact values from latest run (see `results_insert_stubs.tex`).

### 4) Operational Insights Across the Front (~300–400 words)
- Discuss supplier share evolution, capacity utilization, and contract mechanics (tiers/RAC) across the three representative points.
- Optional: Add stacked bars for supplier shares (requires extracting shares at each point).

### 5) Algorithm Comparison: NSGA-II vs ε-Constraint (~300–400 words)
- Deliverables to insert:
  - Figure: Front overlay (`Output Data/pareto_front_comparison.png`).
  - Table: Pareto indicators (Hypervolume, IGD, Spacing, Points) + pairwise dominance coverage.
- Source: `Output Data/comparison_summary_*.json`, `econstraint_front_*.csv`, `nsga_front_*.csv`.
- Status: Indicators table is pre-filled with exact values from latest run (see `results_insert_stubs.tex`).

### 6) Verification & Performance (~150–250 words)
- Tie back to verification framework (manual calculator, coverage over contract types, constraint checks).
- Report model stats (variables, constraints) and solve times; reference reproducibility.

### 7) Limitations and NDA Compliance (~150 words)
- Reiterate adjusted dataset, structural fidelity, and focus on patterns/mechanisms.

## Implementation Guide (Do/Don’t)

Do:
- Use percentage improvements and relative performance metrics where appropriate.
- Emphasize pattern recognition and optimization logic.
- Highlight constraint management sophistication and operational feasibility.
- Connect claims to verification evidence and provided tables/figures.

Avoid:
- Disclosing proprietary prices or contract specifics beyond the sanitized appendix.
- Apologetic/defensive framing around synthetic data.
- Unverifiable claims—prefer citing the provided tables/figures.

## Deliverables Added in Repo

- `final_version/chapters_copy/results_insert_stubs.tex`
  - Figure stubs: Pareto front, Algorithm front overlay, Allocation map (PNG placeholder).
  - Table (filled): Representative ε-constraint solutions (Min Cost, Knee, Max Score) with exact values.
  - Table (filled): Pareto indicators and pairwise coverage from latest run artifacts.
  - Table stubs (placeholders): Supplier utilization summary; Capacity constraints summary.

- `final_version/chapters_copy/appendix_config_schema.tex`
  - One-paragraph schema description for the configuration.
  - `\lstinputlisting` for `final_version/chapters_copy/optimization_config_sanitized.json`.

- `final_version/chapters_copy/optimization_config_sanitized.json`
  - Sanitized copy (anonymized supplier labels retained; values reflect adjusted dataset). Use this in Appendix B.

Integration Notes:
- Ensure LaTeX preamble includes `listings` (or `minted`) for JSON listings and `graphicx` for figures.
- Export a PNG snapshot of `final_version/optimization_allocation_map.html` to `final_version/chapters_copy/optimization_allocation_map.png` before compiling.
