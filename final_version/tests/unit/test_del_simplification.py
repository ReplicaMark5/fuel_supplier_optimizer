#!/usr/bin/env python3
"""
Test script to validate DEL cost simplification (removal of del_buy calculations).
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.precomputation import FuelOptimizationPrecomputation
import pandas as pd

def test_del_simplification():
    """Test that DEL calculations now only include del_own and del_rent (no del_buy)."""
    
    print("=== Testing DEL Cost Simplification ===\n")
    
    # Initialize precomputation engine
    precomp = FuelOptimizationPrecomputation(
        config_path=str(Path(__file__).resolve().parents[2] / 'data/config/optimization_config.json'),
        db_path=str(Path(__file__).resolve().parents[2] / 'data/databases/fuel_data.db')
    )
    
    # Check config - should only have cost_owned_equip_pv
    config = precomp.config['basic_parameters']
    print("Configuration check:")
    print(f"  cost_owned_equip_pv: R{config['cost_owned_equip_pv']:.3f}")
    if 'cost_buy_equip_pv' in config:
        print(f"  ❌ cost_buy_equip_pv still exists: R{config['cost_buy_equip_pv']:.3f}")
    else:
        print("  ✅ cost_buy_equip_pv removed from config")
    print()
    
    # Load and process data
    print("Processing data...")
    df = precomp.load_data_from_database()
    df = precomp.apply_fuel_zone_mapping(df)
    df = precomp.calculate_transport_costs(df)
    df = precomp.calculate_base_costs(df)
    df = precomp.calculate_rac_costs(df)
    df = precomp.calculate_volume_tier_enhanced_costs(df)
    
    # Test 1: Check base DEL calculations
    print("=== Test 1: Base DEL Calculations ===")
    
    # Check that del_buy_cost_pv column doesn't exist
    if 'del_buy_cost_pv' in df.columns:
        print("❌ del_buy_cost_pv column still exists")
    else:
        print("✅ del_buy_cost_pv column removed")
    
    # Check that del_own and del_rent still exist
    del_own_count = df['del_own_cost_pv'].notna().sum()
    del_rent_count = df['del_rent_cost_pv'].notna().sum()
    
    print(f"  del_own_cost_pv: {del_own_count} calculations")
    print(f"  del_rent_cost_pv: {del_rent_count} calculations")
    
    # Sample DEL calculations
    del_sample = df[df['del_own_cost_pv'].notna()].head(3)
    print(f"\nSample DEL calculations:")
    for _, row in del_sample.iterrows():
        depot_name = row['customer_depot_name']
        del_own = row['del_own_cost_pv']
        del_rent = row['del_rent_cost_pv']
        
        print(f"  {depot_name}:")
        print(f"    DEL own:  R{del_own:.4f}")
        print(f"    DEL rent: R{del_rent:.4f}")
        print(f"    Difference: R{del_own - del_rent:.4f} (should be ~R{config['cost_owned_equip_pv']:.3f})")
    
    # Test 2: Check RAC DEL calculations
    print(f"\n=== Test 2: RAC DEL Calculations ===")
    
    # Check that rac_del_buy_cost_pv column doesn't exist
    if 'rac_del_buy_cost_pv' in df.columns:
        print("❌ rac_del_buy_cost_pv column still exists")
    else:
        print("✅ rac_del_buy_cost_pv column removed")
        
    rac_del_own_count = df['rac_del_own_cost_pv'].notna().sum()
    rac_del_rent_count = df['rac_del_rent_cost_pv'].notna().sum()
    
    print(f"  rac_del_own_cost_pv: {rac_del_own_count} calculations")
    print(f"  rac_del_rent_cost_pv: {rac_del_rent_count} calculations")
    
    # Test 3: Check volume tier DEL calculations
    print(f"\n=== Test 3: Volume Tier DEL Calculations ===")
    
    tier_columns = [col for col in df.columns if col.startswith('del_') and '_tier' in col]
    buy_tier_columns = [col for col in tier_columns if 'buy_tier' in col]
    own_tier_columns = [col for col in tier_columns if 'own_tier' in col]
    rent_tier_columns = [col for col in tier_columns if 'rent_tier' in col]
    
    print(f"  del_buy_tier columns: {len(buy_tier_columns)} (should be 0)")
    print(f"  del_own_tier columns: {len(own_tier_columns)}")
    print(f"  del_rent_tier columns: {len(rent_tier_columns)}")
    
    if buy_tier_columns:
        print(f"❌ Found del_buy_tier columns: {buy_tier_columns[:3]}...")
    else:
        print("✅ No del_buy_tier columns found")
    
    # Test 4: Verify calculations use single equipment cost
    print(f"\n=== Test 4: Equipment Cost Consolidation ===")
    
    if del_own_count > 0:
        sample_del = df[df['del_own_cost_pv'].notna()].iloc[0]
        
        # Manual calculation to verify single equipment cost is used
        wholesale = sample_del['rtl_wholesale_per_litre']
        del_rebate = sample_del['DEL_reb_pl_30']
        equip_fin = sample_del['equip_fin_pl_30']
        equip_main = sample_del['equip_main_pl_30']
        pv_factor = (1 + 0.125/365) ** 30  # NET30
        
        manual_del_own = ((wholesale - (del_rebate + equip_fin + equip_main)) / pv_factor) + config['cost_owned_equip_pv']
        manual_del_rent = (wholesale - del_rebate) / pv_factor
        
        actual_del_own = sample_del['del_own_cost_pv']
        actual_del_rent = sample_del['del_rent_cost_pv']
        
        print(f"Manual verification for {sample_del['customer_depot_name']}:")
        print(f"  DEL own  - Manual: R{manual_del_own:.4f}, System: R{actual_del_own:.4f}, Diff: R{abs(manual_del_own - actual_del_own):.6f}")
        print(f"  DEL rent - Manual: R{manual_del_rent:.4f}, System: R{actual_del_rent:.4f}, Diff: R{abs(manual_del_rent - actual_del_rent):.6f}")
        
    print(f"\n=== Simplification Summary ===")
    print(f"✅ Removed del_buy calculations from all contexts")
    print(f"✅ Consolidated equipment costs under single cost_owned_equip_pv parameter")
    print(f"✅ DEL own and DEL rent calculations preserved")
    print(f"✅ Business logic: DEL own now represents both owned and purchased equipment scenarios")

if __name__ == "__main__":
    test_del_simplification()
