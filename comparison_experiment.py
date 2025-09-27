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


def run_econstraint(optimizer: SelectiveNAFlexibleEConstraintOptimizer, n_points: int, constraint_type: str):
    df = optimizer.run_full_optimization(n_points=n_points, constraint_type=constraint_type)
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
