#!/usr/bin/env python3
"""
Test script to validate the new partial tanker load transport cost calculations.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.precomputation import FuelOptimizationPrecomputation
import pandas as pd
import numpy as np

def test_transport_costs():
    """Test the new transport cost calculations with different scenarios."""
    
    print("=== Testing Partial Tanker Load Transport Cost Calculations ===\n")
    
    # Initialize precomputation engine
    precomp = FuelOptimizationPrecomputation(
        config_path=str(Path(__file__).resolve().parents[2] / 'data/config/optimization_config.json'),
        db_path=str(Path(__file__).resolve().parents[2] / 'data/databases/fuel_data.db')
    )
    
    # Load data
    print("Loading data...")
    df = precomp.load_data_from_database()
    
    # Apply fuel zone mapping
    df = precomp.apply_fuel_zone_mapping(df)
    
    # Test 1: Default configuration (allow_multidrop=false)
    print("\n--- Test 1: Single-drop scenario (allow_multidrop=false) ---")
    df_test1 = precomp.calculate_transport_costs(df.copy())
    
    # Show sample results for different tank sizes
    test_depots = df_test1[df_test1['trans_cost_pl'] > 0].copy()
    if len(test_depots) > 0:
        # Sort by tank size and show variety
        test_depots = test_depots.sort_values('tankage_size_litres', na_position='last')
        sample_depots = test_depots.iloc[::max(1, len(test_depots)//8)][:8]  # Sample 8 depots
        
        print(f"Sample results (from {len(test_depots)} COC records):")
        print("Depot Name".ljust(25), "Tank Size (L)".ljust(15), "Distance (km)".ljust(15), "Transport Cost/L".ljust(18))
        print("-" * 80)
        
        for _, row in sample_depots.iterrows():
            depot_name = str(row.get('customer_depot_name', 'Unknown'))[:24]
            tank_size = f"{row.get('tankage_size_litres', 'N/A'):,}" if pd.notna(row.get('tankage_size_litres')) else "N/A"
            distance = f"{row.get('One_Way_Dist', 'N/A'):.1f}" if pd.notna(row.get('One_Way_Dist')) else "N/A"
            cost = f"R {row['trans_cost_pl']:.4f}"
            
            print(depot_name.ljust(25), tank_size.ljust(15), distance.ljust(15), cost.ljust(18))
    
    # Test 2: Multidrop scenario (allow_multidrop=true, min_expected_fill_ratio=0.8)
    print("\n--- Test 2: Multidrop scenario (allow_multidrop=true, min_expected_fill_ratio=0.8) ---")
    
    # Update config for multidrop test
    original_multidrop = precomp.config['basic_parameters']['allow_multidrop']
    original_min_fill = precomp.config['basic_parameters']['min_expected_fill_ratio']
    
    precomp.config['basic_parameters']['allow_multidrop'] = True
    precomp.config['basic_parameters']['min_expected_fill_ratio'] = 0.8
    
    df_test2 = precomp.calculate_transport_costs(df.copy())
    
    # Show comparison
    if len(test_depots) > 0:
        comparison_depots = test_depots.head(5)  # Show top 5 for comparison
        
        print("Comparison: Single-drop vs Multidrop for same depots:")
        print("Depot Name".ljust(25), "Tank Size (L)".ljust(15), "Single-drop Cost".ljust(18), "Multidrop Cost".ljust(18), "Difference".ljust(15))
        print("-" * 95)
        
        for _, row in comparison_depots.iterrows():
            depot_id = row['Customer_Depot_FK']
            supplier_depot_id = row['Supplier_Depot_FK']
            
            # Find corresponding row in test2
            test2_row = df_test2[
                (df_test2['Customer_Depot_FK'] == depot_id) & 
                (df_test2['Supplier_Depot_FK'] == supplier_depot_id)
            ]
            
            if len(test2_row) > 0:
                depot_name = str(row.get('customer_depot_name', 'Unknown'))[:24]
                tank_size = f"{row.get('tankage_size_litres', 'N/A'):,}" if pd.notna(row.get('tankage_size_litres')) else "N/A"
                cost1 = f"R {row['trans_cost_pl']:.4f}"
                cost2 = f"R {test2_row.iloc[0]['trans_cost_pl']:.4f}"
                diff_pct = ((test2_row.iloc[0]['trans_cost_pl'] - row['trans_cost_pl']) / row['trans_cost_pl'] * 100)
                diff = f"{diff_pct:+.1f}%"
                
                print(depot_name.ljust(25), tank_size.ljust(15), cost1.ljust(18), cost2.ljust(18), diff.ljust(15))
    
    # Restore original config
    precomp.config['basic_parameters']['allow_multidrop'] = original_multidrop
    precomp.config['basic_parameters']['min_expected_fill_ratio'] = original_min_fill
    
    # Test 3: Validation against expected calculations
    print("\n--- Test 3: Manual Validation Examples ---")
    
    # Example calculations based on your specifications
    C = precomp.config['basic_parameters']['tanker_capacity']  # 30,000L
    r = precomp.config['basic_parameters']['reorder_level']     # 0.30
    k = precomp.config['basic_parameters']['tanker_cost_per_km'] # 15.5
    
    print(f"Configuration: C={C:,}L, r={r:.2f}, k=R{k}/km")
    print()
    
    test_cases = [
        ("Small Tank", 21275, 100),   # 21,275L tank, 100km distance  
        ("Medium Tank", 42550, 100),  # 42,550L tank, 100km distance
        ("Large Tank", 60000, 100),   # 60,000L tank, 100km distance (>57,143 threshold)
    ]
    
    for case_name, T, D in test_cases:
        # Manual calculation
        delivered = min(C, max(0, (1.0 - r) * T))
        fill_ratio = delivered / C
        effective_litres = C * fill_ratio
        manual_cost = (2 * D * k) / effective_litres
        old_cost = (2 * D * k) / C  # Old full-load formula
        multiplier = manual_cost / old_cost
        
        print(f"{case_name}:")
        print(f"  Tank size: {T:,}L")
        print(f"  Delivered: {delivered:,.1f}L")
        print(f"  Fill ratio: {fill_ratio:.4f}")
        print(f"  Transport cost: R{manual_cost:.4f}/L")
        print(f"  Old cost: R{old_cost:.4f}/L")
        print(f"  Multiplier: {multiplier:.2f}x")
        print()

if __name__ == "__main__":
    test_transport_costs()
