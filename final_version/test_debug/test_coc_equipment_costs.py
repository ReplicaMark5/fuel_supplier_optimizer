#!/usr/bin/env python3
"""
Test script to validate that COC calculations now include equipment costs.
"""

import sys
sys.path.append('/home/blake/projects/demo5/final_version')

from precomputation import FuelOptimizationPrecomputation
import pandas as pd
import numpy as np

def test_coc_equipment_costs():
    """Test that COC calculations now include equipment costs."""
    
    print("=== Testing COC Equipment Cost Integration ===\n")
    
    # Initialize precomputation engine
    precomp = FuelOptimizationPrecomputation(
        config_path='/home/blake/projects/demo5/final_version/optimization_config.json',
        db_path='/home/blake/projects/demo5/final_version/fuel_data.db'
    )
    
    # Get equipment cost from config
    equipment_cost = precomp.config['basic_parameters']['cost_owned_equip_pv']
    print(f"Equipment cost per litre: R{equipment_cost:.3f}")
    print()
    
    # Load and process data
    print("Loading and processing data...")
    df = precomp.load_data_from_database()
    df = precomp.apply_fuel_zone_mapping(df)
    df = precomp.calculate_transport_costs(df)
    df = precomp.calculate_base_costs(df)
    df = precomp.calculate_rac_costs(df)
    df = precomp.calculate_volume_tier_enhanced_costs(df)
    
    # Test 1: Base COC calculations
    print("=== Test 1: Base COC Calculations ===")
    coc_sample = df[df['coc_30_cost_pv'].notna()].head(3)
    
    for _, row in coc_sample.iterrows():
        depot_name = row['customer_depot_name']
        
        # Manual calculation to verify equipment cost inclusion
        wholesale = row['rtl_wholesale_per_litre']
        rebate = row['COC_reb_pl_30']
        transport = row['trans_cost_pl']
        pv_factor = (1 + 0.125/365) ** 30  # NET30 PV factor
        
        manual_calc = ((wholesale - rebate) / pv_factor) + transport + equipment_cost
        actual_calc = row['coc_30_cost_pv']
        
        print(f"Depot: {depot_name}")
        print(f"  Manual calc: R{manual_calc:.4f}")
        print(f"  System calc: R{actual_calc:.4f}")
        print(f"  Difference:  R{abs(manual_calc - actual_calc):.6f}")
        print()
    
    # Test 2: RAC COC calculations  
    print("=== Test 2: RAC COC Calculations ===")
    rac_sample = df[df['rac_coc_30_cost_pv'].notna()].head(2)
    
    for _, row in rac_sample.iterrows():
        depot_name = row['customer_depot_name']
        
        # Manual RAC calculation
        wholesale = row['rtl_wholesale_per_litre']
        transport = row['trans_cost_pl']
        pv_factor = (1 + 0.125/365) ** 30  # NET30 PV factor
        
        manual_calc = (wholesale / pv_factor) + transport + equipment_cost
        actual_calc = row['rac_coc_30_cost_pv']
        
        print(f"RAC Depot: {depot_name}")
        print(f"  Manual calc: R{manual_calc:.4f}")
        print(f"  System calc: R{actual_calc:.4f}")
        print(f"  Difference:  R{abs(manual_calc - actual_calc):.6f}")
        print()
    
    # Test 3: Volume Tier COC calculations
    print("=== Test 3: Volume Tier COC Calculations ===")
    tier_columns = [col for col in df.columns if 'coc_30_tier' in col]
    
    if tier_columns:
        tier_col = tier_columns[0]
        tier_sample = df[df[tier_col].notna()].head(2)
        
        print(f"Testing tier column: {tier_col}")
        
        for _, row in tier_sample.iterrows():
            depot_name = row['customer_depot_name']
            
            print(f"Tier Depot: {depot_name}")
            print(f"  System tier cost: R{row[tier_col]:.4f}")
            print(f"  (Manual verification would require tier config details)")
            print()
    else:
        print("No volume tier COC data found in sample.")
    
    # Test 4: Compare with DEL calculations (should be similar structure)
    print("=== Test 4: COC vs DEL Equipment Cost Comparison ===")
    comparison_sample = df[
        (df['coc_30_cost_pv'].notna()) & 
        (df['del_own_cost_pv'].notna())
    ].head(3)
    
    for _, row in comparison_sample.iterrows():
        depot_name = row['customer_depot_name']
        coc_cost = row['coc_30_cost_pv']
        del_cost = row['del_own_cost_pv']
        
        print(f"Depot: {depot_name}")
        print(f"  COC 30 cost:   R{coc_cost:.4f}")
        print(f"  DEL own cost:  R{del_cost:.4f}")
        print(f"  Difference:    R{coc_cost - del_cost:.4f}")
        print()

if __name__ == "__main__":
    test_coc_equipment_costs()