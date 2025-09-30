"""Command-line utility to run optimization methods and report comparison metrics."""

import argparse
import json
import os
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd

from MOO_e_constraint_Cost_Dynamic_2 import SelectiveNAFlexibleEConstraintOptimizer
from NSGA_II_Repair_Dynamic_2 import FixedFlexibleSupplyChainOptimizer
from pareto_metrics import (
    aggregate_operational_metrics,
    apply_normalisation,
    compare_fronts,
    compute_normalisation_bounds,
    summarise_operational_metrics,
)


def _normalise_series(series: pd.Series, lower: float, upper: float) -> pd.Series:
    span = (upper - lower) if (pd.notna(lower) and pd.notna(upper)) else None
    if span is None or span == 0:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (pd.to_numeric(series, errors="coerce") - lower) / span


def _strict_nondominated_and_dedup(df: pd.DataFrame, bounds: Dict[str, float], tol: float = 1e-6) -> pd.DataFrame:
    """Return strict nondominated and de-duplicated DataFrame.

    - Works in normalised space to use a consistent tolerance across magnitudes.
    - Assumes cost is minimised and score is maximised.
    - Drops near-duplicates by rounding normalised points.
    """
    if df is None or df.empty:
        return df

    if not {"cost", "score"}.issubset(df.columns):
        return df

    df = df.copy()
    c_norm = _normalise_series(df["cost"], bounds.get("cost_min"), bounds.get("cost_max"))
    s_norm = _normalise_series(df["score"], bounds.get("score_min"), bounds.get("score_max"))

    data = np.column_stack([c_norm.to_numpy(dtype=float), s_norm.to_numpy(dtype=float)])
    n = data.shape[0]
    keep = np.ones(n, dtype=bool)

    for i in range(n):
        if not keep[i]:
            continue
        ci, si = data[i]
        # A point j dominates i if it is no worse within tol and strictly better beyond tol in at least one objective
        for j in range(n):
            if i == j or not keep[j]:
                continue
            cj, sj = data[j]
            no_worse = (cj <= ci + tol) and (sj >= si - tol)
            strictly_better = (cj < ci - tol) or (sj > si + tol)
            if no_worse and strictly_better:
                keep[i] = False
                break

    filtered = df.loc[keep].copy()

    # De-duplicate near-identical points (grid-based using normalised rounding)
    c_round = np.round(_normalise_series(filtered["cost"], bounds.get("cost_min"), bounds.get("cost_max")), 6)
    s_round = np.round(_normalise_series(filtered["score"], bounds.get("score_min"), bounds.get("score_max")), 6)
    filtered["_c_key"] = c_round
    filtered["_s_key"] = s_round
    filtered = filtered.drop_duplicates(subset=["_c_key", "_s_key"]).drop(columns=["_c_key", "_s_key"]) 

    return filtered


def _diagnose_removed(
    original: pd.DataFrame,
    filtered: pd.DataFrame,
    bounds: Dict[str, float],
    tol: float = 1e-6,
    round_decimals: int = 6,
) -> pd.DataFrame:
    """Return a table of removed points with reason and (if dominated) a dominating point.

    Reasons:
    - 'dominated': strictly dominated (with tolerance) by another original point
    - 'duplicate': near-duplicate merged by rounding in normalised space
    - 'unknown': fallback when neither condition is detected (should be rare)
    """
    if original is None or original.empty:
        return pd.DataFrame()

    needed = {"cost", "score"}
    if not needed.issubset(original.columns):
        return pd.DataFrame()

    orig = original.copy()
    kept = filtered.copy()

    # normalised columns for both sets
    for df in (orig, kept):
        df["_c_norm"] = _normalise_series(df["cost"], bounds.get("cost_min"), bounds.get("cost_max"))
        df["_s_norm"] = _normalise_series(df["score"], bounds.get("score_min"), bounds.get("score_max"))

    # Identify removed rows by exact (cost, score) mismatch; complement with tolerance check below
    key_cols = ["cost", "score"]
    merged = orig.merge(kept[key_cols], on=key_cols, how="left", indicator=True)
    removed = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"]).copy()
    if removed.empty:
        return pd.DataFrame()

    # Build normalised arrays for dominance check
    P = orig[["_c_norm", "_s_norm"]].to_numpy(float)

    def dominates(j, i):
        cj, sj = P[j]
        ci, si = P[i]
        no_worse = (cj <= ci + tol) and (sj >= si - tol)
        strictly_better = (cj < ci - tol) or (sj > si + tol)
        return no_worse and strictly_better

    # Index map from cost,score to original index (may have duplicates; take first)
    idx_map = {}
    for k, row in orig.reset_index().iterrows():
        idx_map.setdefault((row["cost"], row["score"]), row["index"])  # preserve original index

    reasons = []
    dom_costs = []
    dom_scores = []

    # Precompute rounded keys for de-dup reasoning
    orig_round_keys = list(zip(orig["_c_norm"].round(round_decimals), orig["_s_norm"].round(round_decimals)))
    kept_round_keys = set(zip(kept["_c_norm"].round(round_decimals), kept["_s_norm"].round(round_decimals)))

    for r in removed.itertuples():
        i = idx_map.get((getattr(r, "cost"), getattr(r, "score")))
        reason = "unknown"
        dcost = np.nan
        dscore = np.nan

        # Check duplicate by rounded key
        r_key = orig_round_keys[i]
        if r_key in kept_round_keys:
            reason = "duplicate"
        else:
            # Find a dominator in original set
            found = False
            for j in range(len(P)):
                if j == i:
                    continue
                if dominates(j, i):
                    reason = "dominated"
                    dcost = orig.iloc[j]["cost"]
                    dscore = orig.iloc[j]["score"]
                    found = True
                    break
            if not found and reason == "unknown":
                # As a fallback, try domination by kept set only (should be redundant but helpful for diagnostics)
                K = kept[["_c_norm", "_s_norm"]].to_numpy(float)
                ci, si = P[i]
                for (cj, sj), kr in zip(K, kept.itertuples()):
                    no_worse = (cj <= ci + tol) and (sj >= si - tol)
                    strictly_better = (cj < ci - tol) or (sj > si + tol)
                    if no_worse and strictly_better:
                        reason = "dominated"
                        dcost = getattr(kr, "cost")
                        dscore = getattr(kr, "score")
                        break

        reasons.append(reason)
        dom_costs.append(dcost)
        dom_scores.append(dscore)

    removed["reason"] = reasons
    removed["dominator_cost"] = dom_costs
    removed["dominator_score"] = dom_scores
    return removed


def run_econstraint(optimizer: SelectiveNAFlexibleEConstraintOptimizer, n_points: int, constraint_type: str):
    df = optimizer.run_full_optimization(n_points=n_points, constraint_type=constraint_type, show_plots=False)
    df_feasible = df[df['status'] == 'Optimal'].copy()
    df_feasible['method'] = 'ε-Constraint'
    metadata = getattr(optimizer, 'last_run_metadata', {})
    return df_feasible, metadata


def run_nsga(
    optimizer: FixedFlexibleSupplyChainOptimizer,
    ngen: int,
    mu: int,
    lambda_: int,
    cxpb: float,
    mutpb: float,
    indpb: float,
    runs: int,
    seed: int,
) -> (pd.DataFrame, List[Dict]):
    dfs = []
    metadata_list: List[Dict] = []
    for rep in range(runs):
        seed_value = seed + rep if seed is not None else None
        df = optimizer.run_full_optimization(
            ngen=ngen,
            mu=mu,
            lambda_=lambda_,
            cxpb=cxpb,
            mutpb=mutpb,
            indpb=indpb,
            seed=seed_value,
        )
        run_id = getattr(optimizer, 'last_run_metadata', {}).get('run_id', f'nsga_run_{rep+1}')
        df = df.assign(method='NSGA-II', run_id=run_id, replication=rep + 1)
        dfs.append(df)
        metadata = getattr(optimizer, 'last_run_metadata', {}).copy()
        metadata['replication'] = rep + 1
        metadata_list.append(metadata)
    combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return combined, metadata_list


def main():
    parser = argparse.ArgumentParser(description="Run comparative optimization experiments.")
    parser.add_argument('--data', required=True, help='Path to Excel workbook with model inputs.')
    parser.add_argument('--nsga-runs', type=int, default=7, help='Number of NSGA-II replications to execute.')
    parser.add_argument('--ngen', type=int, default=200, help='NSGA-II generations.')
    parser.add_argument('--mu', type=int, default=500, help='NSGA-II population size.')
    parser.add_argument('--lambda_', type=int, default=250, help='NSGA-II offspring size.')
    parser.add_argument('--cxpb', type=float, default=0.75, help='NSGA-II crossover probability.')
    parser.add_argument('--mutpb', type=float, default=0.8, help='NSGA-II mutation probability.')
    parser.add_argument('--indpb', type=float, default=0.05, help='NSGA-II per-gene mutation probability.')
    parser.add_argument('--epsilon-points', type=int, default=300, help='Number of epsilon points for ε-constraint.')
    parser.add_argument('--constraint-type', choices=['cost', 'score'], default='cost', help='ε-constraint objective to bound.')
    parser.add_argument('--max-suppliers', type=int, default=None, help='Optional cap on unique suppliers.')
    parser.add_argument('--seed', type=int, default=42, help='Base random seed.')
    parser.add_argument('--obj1-sheet', default='Obj1_Coeff')
    parser.add_argument('--obj2-sheet', default='Obj2_Coeff')
    parser.add_argument('--volumes-sheet', default='Annual Volumes')
    args = parser.parse_args()

    sheet_names = {
        'obj1': args.obj1_sheet,
        'obj2': args.obj2_sheet,
        'volumes': args.volumes_sheet,
    }

    print('Initializing optimizers...')
    nsga_optimizer = FixedFlexibleSupplyChainOptimizer(args.data, sheet_names, args.max_suppliers)
    econst_optimizer = SelectiveNAFlexibleEConstraintOptimizer(args.data, sheet_names, args.max_suppliers)

    print('Running ε-constraint search...')
    df_econst, econst_metadata = run_econstraint(
        econst_optimizer,
        n_points=args.epsilon_points,
        constraint_type=args.constraint_type,
    )

    print('Running NSGA-II replicates...')
    df_nsga, nsga_metadata = run_nsga(
        nsga_optimizer,
        ngen=args.ngen,
        mu=args.mu,
        lambda_=args.lambda_,
        cxpb=args.cxpb,
        mutpb=args.mutpb,
        indpb=args.indpb,
        runs=args.nsga_runs,
        seed=args.seed,
    )

    # Post-filter: strict nondomination + de-duplication (fair comparison)
    prelim_bounds = compute_normalisation_bounds([df_econst, df_nsga])
    before_counts = (len(df_econst), len(df_nsga))

    # Keep originals for diagnostics
    df_econst_raw = df_econst.copy()
    df_nsga_raw = df_nsga.copy()

    df_econst = _strict_nondominated_and_dedup(df_econst, prelim_bounds)
    df_nsga = _strict_nondominated_and_dedup(df_nsga, prelim_bounds)
    after_counts = (len(df_econst), len(df_nsga))
    print(f"Filtered to strict nondomination + de-dup (ε-Constraint {before_counts[0]} -> {after_counts[0]}, NSGA-II {before_counts[1]} -> {after_counts[1]})")

    # Normalise for reporting convenience
    bounds = compute_normalisation_bounds([df_econst, df_nsga])
    df_econst = apply_normalisation(df_econst, bounds)
    df_nsga = apply_normalisation(df_nsga, bounds)

    print('Computing comparison metrics...')
    metrics = compare_fronts(df_econst, df_nsga, method_a='ε-Constraint', method_b='NSGA-II')

    op_econst = aggregate_operational_metrics(df_econst, econst_optimizer)
    op_nsga = aggregate_operational_metrics(df_nsga, nsga_optimizer)

    op_summary = {
        'ε-Constraint': summarise_operational_metrics(op_econst),
        'NSGA-II': summarise_operational_metrics(op_nsga),
    }

    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    output_dir = 'Output Data'
    os.makedirs(output_dir, exist_ok=True)

    df_econst.to_csv(os.path.join(output_dir, f'econstraint_front_{timestamp}.csv'), index=False)
    df_nsga.to_csv(os.path.join(output_dir, f'nsga_front_{timestamp}.csv'), index=False)

    # Diagnostics: record removed points and their reason
    removed_econst = _diagnose_removed(df_econst_raw, df_econst, prelim_bounds)
    removed_nsga = _diagnose_removed(df_nsga_raw, df_nsga, prelim_bounds)
    if not removed_econst.empty:
        removed_econst.to_csv(os.path.join(output_dir, f'econstraint_removed_{timestamp}.csv'), index=False)
    if not removed_nsga.empty:
        removed_nsga.to_csv(os.path.join(output_dir, f'nsga_removed_{timestamp}.csv'), index=False)

    summary_payload = {
        'timestamp': timestamp,
        'data_path': args.data,
        'nsga_runs': args.nsga_runs,
        'nsga_metadata': nsga_metadata,
        'econstraint_metadata': econst_metadata,
        'pareto_metrics': metrics,
        'normalisation_bounds': bounds,
        'operational_metrics': op_summary,
    }

    with open(os.path.join(output_dir, f'comparison_summary_{timestamp}.json'), 'w', encoding='utf-8') as fh:
        json.dump(summary_payload, fh, indent=2)

    print(f'Summary written to comparison_summary_{timestamp}.json')

    metrics_table = pd.DataFrame([
        {
            'method': method,
            'hypervolume': details.get('hypervolume'),
            'igd': details.get('igd'),
            'spacing': details.get('spacing'),
            'points': details.get('points'),
        }
        for method, details in metrics['methods'].items()
    ])
    print('\nPareto indicators:')
    print(metrics_table)

    coverage = metrics['pairwise']
    print('\nDominance coverage:')
    print(pd.Series(coverage))

    print('\nOperational KPIs (mean ± std where applicable):')
    print(pd.DataFrame(op_summary).T)


if __name__ == '__main__':
    main()
