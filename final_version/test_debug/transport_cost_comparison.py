#!/usr/bin/env python3
"""
Generate detailed comparison showing old vs new transport cost calculations.
"""

import sys
sys.path.append('/home/blake/projects/demo5/final_version')

from precomputation import FuelOptimizationPrecomputation
import pandas as pd
import numpy as np

def generate_comparison():
    """Generate detailed comparison table of old vs new transport costs."""
    
    print("=== Transport Cost Implementation: Old vs New Comparison ===\n")
    
    # Initialize precomputation engine
    precomp = FuelOptimizationPrecomputation(
        config_path='/home/blake/projects/demo5/final_version/optimization_config.json',
        db_path='/home/blake/projects/demo5/final_version/fuel_data.db'
    )
    
    # Load configuration
    C = precomp.config['basic_parameters']['tanker_capacity']  # 30,000L
    r = precomp.config['basic_parameters']['reorder_level']     # 0.30
    k = precomp.config['basic_parameters']['tanker_cost_per_km'] # 15.5
    
    print(f"Configuration: Tanker capacity={C:,}L, Reorder level={r:.0%}, Cost per km=R{k}")
    print()
    
    # Load data
    df = precomp.load_data_from_database()
    df = precomp.apply_fuel_zone_mapping(df)
    
    # Get COC records with tank sizes
    coc_data = df[
        (df['COC_Valid_FK'].notna()) & 
        (df['One_Way_Dist'].notna()) & 
        (df['tankage_size_litres'].notna())
    ].copy()
    
    if len(coc_data) == 0:
        print("No valid COC data found with tank sizes!")
        return
    
    # Calculate old-style costs manually
    coc_data['old_trans_cost_pl'] = (2 * coc_data['One_Way_Dist'] * k) / C
    
    # Calculate new-style costs
    precomp.config['basic_parameters']['allow_multidrop'] = False
    coc_data = precomp._compute_trans_cost_per_litre(coc_data, precomp.config)
    coc_data['new_single_drop'] = coc_data['trans_cost_pl'].copy()
    
    # Calculate multidrop costs
    precomp.config['basic_parameters']['allow_multidrop'] = True
    precomp.config['basic_parameters']['min_expected_fill_ratio'] = 0.8
    coc_data = precomp._compute_trans_cost_per_litre(coc_data, precomp.config)
    coc_data['new_multidrop'] = coc_data['trans_cost_pl'].copy()
    
    # Sort by tank size for better visualization
    coc_data = coc_data.sort_values('tankage_size_litres')
    
    # Select diverse sample (small, medium, large tanks)
    small_tanks = coc_data[coc_data['tankage_size_litres'] <= 25000]
    medium_tanks = coc_data[(coc_data['tankage_size_litres'] > 25000) & (coc_data['tankage_size_litres'] <= 50000)]
    large_tanks = coc_data[coc_data['tankage_size_litres'] > 50000]
    
    sample_data = pd.concat([
        small_tanks.head(4),
        medium_tanks.head(3), 
        large_tanks.head(3)
    ])
    
    print("Detailed Comparison: Transport Cost per Litre")
    print("=" * 120)
    print("Depot Name".ljust(20), "Tank Size (L)".ljust(12), "Dist (km)".ljust(10), 
          "Old Cost".ljust(12), "New Single".ljust(12), "New Multi".ljust(12), 
          "Single Δ".ljust(10), "Multi Δ".ljust(10))
    print("-" * 120)
    
    for _, row in sample_data.iterrows():
        name = str(row['customer_depot_name'])[:19]
        tank = f"{row['tankage_size_litres']:,.0f}"
        dist = f"{row['One_Way_Dist']:.1f}"
        old_cost = f"R{row['old_trans_cost_pl']:.4f}"
        new_single = f"R{row['new_single_drop']:.4f}" 
        new_multi = f"R{row['new_multidrop']:.4f}"
        single_delta = f"{((row['new_single_drop'] / row['old_trans_cost_pl']) - 1) * 100:+.0f}%"
        multi_delta = f"{((row['new_multidrop'] / row['old_trans_cost_pl']) - 1) * 100:+.0f}%"
        
        print(name.ljust(20), tank.ljust(12), dist.ljust(10), 
              old_cost.ljust(12), new_single.ljust(12), new_multi.ljust(12),
              single_delta.ljust(10), multi_delta.ljust(10))
    
    # Summary statistics
    print("\nSummary Statistics:")
    print("=" * 50)
    
    avg_old = coc_data['old_trans_cost_pl'].mean()
    avg_new_single = coc_data['new_single_drop'].mean()
    avg_new_multi = coc_data['new_multidrop'].mean()
    
    print(f"Average transport cost per litre:")
    print(f"  Old formula:     R{avg_old:.4f}")
    print(f"  New single-drop: R{avg_new_single:.4f} ({((avg_new_single/avg_old)-1)*100:+.1f}%)")
    print(f"  New multidrop:   R{avg_new_multi:.4f} ({((avg_new_multi/avg_old)-1)*100:+.1f}%)")
    
    # Tank size impact analysis
    print(f"\nTank Size Impact Analysis:")
    print("=" * 50)
    
    size_ranges = [
        ("Very Small", 0, 15000),
        ("Small", 15000, 30000), 
        ("Medium", 30000, 50000),
        ("Large", 50000, 100000),
        ("Very Large", 100000, float('inf'))
    ]
    
    for label, min_size, max_size in size_ranges:
        subset = coc_data[
            (coc_data['tankage_size_litres'] >= min_size) & 
            (coc_data['tankage_size_litres'] < max_size)
        ]
        
        if len(subset) > 0:
            avg_multiplier_single = (subset['new_single_drop'] / subset['old_trans_cost_pl']).mean()
            avg_multiplier_multi = (subset['new_multidrop'] / subset['old_trans_cost_pl']).mean()
            
            print(f"{label:12} ({len(subset):3d} depots): {avg_multiplier_single:.2f}x single, {avg_multiplier_multi:.2f}x multi")

if __name__ == "__main__":
    generate_comparison()