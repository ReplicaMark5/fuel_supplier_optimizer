#!/usr/bin/env python3
"""
Debug script to examine specific depot-supplier cost calculations
"""

import sqlite3
import pandas as pd
from precomputation import FuelOptimizationPrecomputation

def debug_specific_combination(depot_id=1, supplier_depot_id=1):
    """Debug a specific customer depot - supplier depot combination"""
    
    print(f"\n=== DEBUGGING DEPOT {depot_id} - SUPPLIER DEPOT {supplier_depot_id} ===")
    
    # Initialize precomputation
    precomp = FuelOptimizationPrecomputation()
    
    # Load raw data
    df = precomp.load_data_from_database()
    
    # Filter to specific combination
    specific = df[(df['Customer_Depot_FK'] == depot_id) & 
                  (df['Supplier_Depot_FK'] == supplier_depot_id)]
    
    if len(specific) == 0:
        print(f"No data found for Depot {depot_id} - Supplier Depot {supplier_depot_id}")
        return
        
    row = specific.iloc[0]
    
    print("\n--- RAW DATA ---")
    print(f"Customer Depot: {row['Customer_Depot_FK']} ({row['customer_depot_name']})")
    print(f"Supplier Depot: {row['Supplier_Depot_FK']} ({row['Supply_Depot_Name']})")
    print(f"Supplier: {row['Supplier_FK']}")
    print(f"Distance: {row['One_Way_Dist']} km")
    print(f"COC Valid FK: {row['COC_Valid_FK']}")
    print(f"DEL Valid FK: {row['DEL_Valid_FK']}")
    
    print(f"\n--- FUEL PRICING ---")
    print(f"Supplier Fuel Zone: {row['supplier_fuel_zone']}")
    print(f"Retail Wholesale: {row['rtl_wholesale']} cents/litre")
    
    print(f"\n--- REBATE DATA ---") 
    print(f"COC Cash Rebate: {row['COC_reb_pl_cash']} R/litre")
    print(f"COC NET30 Rebate: {row['COC_reb_pl_30']} R/litre")
    print(f"COC NET45 Rebate: {row['COC_reb_pl_45']} R/litre")
    print(f"COC NET60 Rebate: {row['COC_reb_pl_60']} R/litre")
    print(f"DEL NET30 Rebate: {row['DEL_reb_pl_30']} R/litre")
    print(f"DEL Equipment Financing: {row['equip_fin_pl_30']} R/litre")
    print(f"DEL Equipment Maintenance: {row['equip_main_pl_30']} R/litre")
    
    # Apply fuel zone mapping
    df = precomp.apply_fuel_zone_mapping(df)
    specific = df[(df['Customer_Depot_FK'] == depot_id) & 
                  (df['Supplier_Depot_FK'] == supplier_depot_id)]
    row = specific.iloc[0]
    
    print(f"\n--- FUEL ZONE MAPPING ---")
    print(f"Fuel Zone Clean: {row['fuel_zone_clean']}")
    print(f"Is International: {row['is_international']}")
    print(f"Depot Country: {row['depot_country']}")
    print(f"Final Fuel Price: {row['rtl_wholesale_per_litre']} R/litre")
    
    # Calculate transport costs
    df = precomp.calculate_transport_costs(df)
    specific = df[(df['Customer_Depot_FK'] == depot_id) & 
                  (df['Supplier_Depot_FK'] == supplier_depot_id)]
    row = specific.iloc[0]
    
    print(f"\n--- TRANSPORT COSTS ---")
    print(f"Transport Cost: {row['trans_cost_pl']} R/litre")
    
    # Calculate base costs
    df = precomp.calculate_base_costs(df)
    specific = df[(df['Customer_Depot_FK'] == depot_id) & 
                  (df['Supplier_Depot_FK'] == supplier_depot_id)]
    row = specific.iloc[0]
    
    print(f"\n--- CALCULATED COSTS (PV) ---")
    cost_columns = ['coc_cash_cost_pv', 'coc_30_cost_pv', 'coc_45_cost_pv', 'coc_60_cost_pv',
                   'del_own_cost_pv', 'del_buy_cost_pv', 'del_rent_cost_pv']
    
    for col in cost_columns:
        value = row[col]
        if pd.notna(value):
            print(f"{col}: R{value:.4f}/litre")
        else:
            print(f"{col}: NOT AVAILABLE")
    
    # Get PV factors for manual verification
    pv_factors = precomp.calculate_present_value_factors()
    print(f"\n--- PV FACTORS ---")
    for term, factor in pv_factors.items():
        print(f"{term}: {factor:.6f}")
    
    # Manual calculation verification
    print(f"\n--- MANUAL VERIFICATION ---")
    fuel_price = row['rtl_wholesale_per_litre']
    transport_cost = row['trans_cost_pl']
    
    if pd.notna(row['COC_reb_pl_cash']):
        manual_coc_cash = fuel_price - row['COC_reb_pl_cash'] - transport_cost  # rebates are already in R/litre
        print(f"Manual COC Cash: {fuel_price} - {row['COC_reb_pl_cash']} - {transport_cost} = R{manual_coc_cash:.4f}/litre")
        
    if pd.notna(row['COC_reb_pl_30']):
        net_after_rebate = fuel_price - row['COC_reb_pl_30']  # rebates are already in R/litre
        pv_discounted = net_after_rebate / pv_factors['net30']
        manual_coc_30 = pv_discounted - transport_cost
        print(f"Manual COC NET30: ({fuel_price} - {row['COC_reb_pl_30']}) / {pv_factors['net30']:.6f} - {transport_cost} = R{manual_coc_30:.4f}/litre")

if __name__ == "__main__":
    debug_specific_combination(1, 1)