> Most Thesis-Useful Artifacts


python comparison_experiment.py --data "/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Demo3.xlsx"



  - Output Data/comparison_summary_20250925T165048Z.json
      - Primary “results bundle”: includes experiment settings, per-run metadata, Pareto-quality indicators
  (hypervolume, IGD, dominance coverage), and aggregated operational KPIs. Use this to cite which method dominates, how
  much spread you get, average supplier usage, etc.
  - Output Data/econstraint_front_20250925T165048Z.csv & nsga_front_20250925T165048Z.csv
      - Clean data tables for analysis/plots. Each row has cost, score, allocations, run identifiers; import these into
  Python/R/Excel to build figures (Pareto overlays, boxplots by KPI) and compute extra stats.
  - Output Data/NSGAII_run_metadata.csv & MOO_e_constraint_run_metadata.csv
      - Chronological log of every run: parameter choices, runtime, feasible counts. Perfect for a methodology table or
  to justify computational effort and feasibility.
  - Output Data/NSGAII_generation_log.csv
      - Convergence history per generation across replications; use for “convergence vs time” or “mean cost/score
  trajectory” plots to discuss GA dynamics.

  Mostly for quick reference / optional

  - nsga-II_selective_na_handling.csv / .png and MOO_e-const_cost_selective_na_pareto.csv / .png are the latest single-
  run exports from the app. They’re fine for sanity-check visuals but the timestamped CSV/JSON pair above is the curated
  output for formal analysis.

  In short: base your thesis evaluation on the timestamped JSON + CSV fronts and supplement with the metadata and
  generation log when you discuss runtime, robustness, and convergence behaviour.