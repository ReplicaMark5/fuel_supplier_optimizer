#!/usr/bin/env python3
"""
Test script to check what tier columns exist after del_buy removal.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.precomputation import FuelOptimizationPrecomputation
import pandas as pd

def test_tier_columns():
    """Check what tier columns are generated and included in cost dictionary."""
    
    print("=== Testing Volume Tier Column Generation ===\n")
    
    # Initialize and run precomputation
    precomp = FuelOptimizationPrecomputation(
        config_path=str(Path(__file__).resolve().parents[2] / 'data/config/optimization_config.json'),
        db_path=str(Path(__file__).resolve().parents[2] / 'data/databases/fuel_data.db')
    )
    
    # Run full precomputation to get tier columns
    df = precomp.load_data_from_database()
    df = precomp.apply_fuel_zone_mapping(df)
    df = precomp.calculate_transport_costs(df)
    df = precomp.calculate_base_costs(df)
    df = precomp.calculate_rac_costs(df)
    df = precomp.calculate_volume_tier_enhanced_costs(df)
    
    # Check all tier columns
    all_tier_columns = [col for col in df.columns if 'tier_' in col]
    del_tier_columns = [col for col in all_tier_columns if col.startswith('del_')]
    coc_tier_columns = [col for col in all_tier_columns if col.startswith('coc_')]
    
    print(f"All tier columns found: {len(all_tier_columns)}")
    print(f"COC tier columns: {len(coc_tier_columns)}")
    print(f"DEL tier columns: {len(del_tier_columns)}")
    print()
    
    # Check for del_buy_tier specifically
    del_buy_tier_columns = [col for col in all_tier_columns if 'del_buy_tier' in col]
    del_own_tier_columns = [col for col in all_tier_columns if 'del_own_tier' in col]
    del_rent_tier_columns = [col for col in all_tier_columns if 'del_rent_tier' in col]
    
    print("DEL tier breakdown:")
    print(f"  del_buy_tier columns: {len(del_buy_tier_columns)} (should be 0)")
    print(f"  del_own_tier columns: {len(del_own_tier_columns)}")  
    print(f"  del_rent_tier columns: {len(del_rent_tier_columns)}")
    print()
    
    if del_buy_tier_columns:
        print("❌ Found del_buy_tier columns:")
        for col in del_buy_tier_columns:
            print(f"    {col}")
        print()
    else:
        print("✅ No del_buy_tier columns found")
        print()
    
    # Test the tier_cost_columns dictionary building logic
    print("Testing tier_cost_columns dictionary logic:")
    tier_cost_columns = {}
    for col in df.columns:
        if ('tier_' in col and 
            ('coc_' in col or 'del_' in col) and 
            not col.endswith('_cost_pv')):  # Already in right format
            tier_cost_columns[col] = col
    
    print(f"Total tier cost columns in dictionary: {len(tier_cost_columns)}")
    
    # Show breakdown by type
    dict_del_buy = [col for col in tier_cost_columns.keys() if 'del_buy_tier' in col]
    dict_del_own = [col for col in tier_cost_columns.keys() if 'del_own_tier' in col]
    dict_del_rent = [col for col in tier_cost_columns.keys() if 'del_rent_tier' in col]
    dict_coc = [col for col in tier_cost_columns.keys() if col.startswith('coc_')]
    
    print(f"  Dictionary del_buy_tier: {len(dict_del_buy)} (should be 0)")
    print(f"  Dictionary del_own_tier: {len(dict_del_own)}")
    print(f"  Dictionary del_rent_tier: {len(dict_del_rent)}")
    print(f"  Dictionary coc_tier: {len(dict_coc)}")
    
    if dict_del_buy:
        print(f"\n❌ del_buy_tier columns in cost dictionary:")
        for col in dict_del_buy:
            print(f"    {col}")
    else:
        print(f"\n✅ No del_buy_tier columns in cost dictionary")
        
    # Show sample tier columns
    print(f"\nSample tier columns:")
    sample_cols = list(tier_cost_columns.keys())[:10]
    for col in sample_cols:
        print(f"  {col}")

if __name__ == "__main__":
    test_tier_columns()
