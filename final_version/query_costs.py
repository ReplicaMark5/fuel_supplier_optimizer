#!/usr/bin/env python3
"""
Interactive script to run precomputation and query depot costs.
Usage: python query_costs.py
"""

from precomputation import FuelOptimizationPrecomputation
import json

def get_user_input(precomp, results):
    """Interactive function to get user input for querying depots."""
    
    available_depots = sorted(list(results['cost_data']['costs'].keys()))
    print(f"\n📋 Available depot IDs: {available_depots}")
    
    while True:
        print("\n" + "="*60)
        print("DEPOT COST QUERY OPTIONS")
        print("="*60)
        print("1. Query single depot (shows all supplier depots)")
        print("2. Query specific depot-supplier depot pair (VERBOSE DEBUG)")
        print("3. Quit")
        
        choice = input("Select option (1/2/3): ").strip()
        
        if choice == '3' or choice.lower() in ['quit', 'q', 'exit']:
            print("👋 Goodbye!")
            break
        elif choice == '1':
            # Original single depot query
            depot_input = input("Enter depot ID to query: ").strip()
            
            try:
                depot_id = int(depot_input)
            except ValueError:
                print("❌ Please enter a valid depot ID number")
                continue
                
            if depot_id not in available_depots:
                print(f"❌ Depot {depot_id} not found. Available: {available_depots}")
                continue
            
            # Ask for volume filter
            volume_input = input("Enter volume filter in litres (or press Enter for all scenarios): ").strip()
            volume_filter = None
            if volume_input:
                try:
                    volume_filter = int(volume_input)
                except ValueError:
                    print("⚠️ Invalid volume, showing all scenarios")
            
            # Ask for detail level
            detail_input = input("Show detailed costs? (y/n, default=y): ").strip().lower()
            show_details = detail_input != 'n'
            
            # Run the query
            print(f"\n🔍 Querying depot {depot_id}...")
            precomp.query_depot_costs(
                depot_id=depot_id, 
                results=results, 
                volume_filter=volume_filter,
                show_details=show_details
            )
            
        elif choice == '2':
            # New verbose depot-supplier depot pair query
            depot_input = input("Enter customer depot ID: ").strip()
            
            try:
                depot_id = int(depot_input)
            except ValueError:
                print("❌ Please enter a valid depot ID number")
                continue
                
            if depot_id not in available_depots:
                print(f"❌ Depot {depot_id} not found. Available: {available_depots}")
                continue
            
            # Show available supplier depots for this customer depot
            supplier_depots = list(results['cost_data']['costs'][depot_id].keys())
            print(f"\n📋 Available supplier depot IDs for depot {depot_id}: {supplier_depots}")
            
            supplier_depot_input = input("Enter supplier depot ID: ").strip()
            
            try:
                supplier_depot_id = int(supplier_depot_input)
            except ValueError:
                print("❌ Please enter a valid supplier depot ID number")
                continue
                
            if supplier_depot_id not in supplier_depots:
                print(f"❌ Supplier depot {supplier_depot_id} not found for depot {depot_id}. Available: {supplier_depots}")
                continue
            
            # Run verbose query
            print(f"\n🔍 VERBOSE DEBUG: Depot {depot_id} → Supplier Depot {supplier_depot_id}")
            query_depot_supplier_verbose(precomp, results, depot_id, supplier_depot_id)
            
        else:
            print("❌ Please select option 1, 2, or 3")

def query_depot_supplier_verbose(precomp, results, depot_id, supplier_depot_id):
    """
    Verbose debug query showing step-by-step calculations for a specific depot-supplier depot pair.
    """
    print("="*80)
    print(f"VERBOSE DEBUG: Customer Depot {depot_id} → Supplier Depot {supplier_depot_id}")
    print("="*80)
    
    # Get the depot data
    depot_data = results['cost_data']['costs'][depot_id][supplier_depot_id]
    
    # Show basic information
    print(f"\n📋 BASIC INFORMATION:")
    print(f"   Supplier ID: {depot_data.get('supplier_id', 'Unknown')}")
    print(f"   Supplier Name: {depot_data.get('supplier_name', 'Unknown')}")
    print(f"   Supplier Depot Name: {depot_data.get('supplier_depot_name', 'Unknown')}")
    print(f"   Distance: {depot_data.get('distance_km', 'N/A')} km")
    print(f"   Available Options: {depot_data.get('available_options', [])}")
    
    # Show base costs first
    print(f"\n💰 BASE COSTS (Phase 1):")
    base_costs = depot_data.get('base_costs', {})
    for option, cost in base_costs.items():
        if cost is not None:
            print(f"   {option}: R{cost:.6f}/litre")
    
    # Get tier costs
    tier_costs = depot_data.get('tier_costs', {})
    if not tier_costs:
        print("\n💰 TIER COSTS: No volume tier configurations apply")
    else:
        print(f"\n💰 TIER COSTS (Volume Tier Rates):")
        for tier_name, tier_options in tier_costs.items():
            print(f"   {tier_name}:")
            for option, cost in tier_options.items():
                if cost is not None:
                    base_cost = depot_data['base_costs'].get(option)
                    if base_cost is not None:
                        savings = base_cost - cost
                        print(f"      {option}: R{cost:.6f}/litre (saves R{savings:.6f})")
                    else:
                        print(f"      {option}: R{cost:.6f}/litre")
    
    # Show configuration details
    config = precomp.config
    wacc = config['basic_parameters']['wacc_percent']
    print(f"\n⚙️ CONFIGURATION:")
    print(f"   WACC: {wacc}%")
    print(f"   Tanker cost/km: R{config['basic_parameters']['tanker_cost_per_km']}")
    print(f"   Tanker capacity: {config['basic_parameters']['tanker_capacity']} litres")
    
    # Show raw data for calculations - need to get from database
    print(f"\n📊 RAW DATA FROM DATABASE:")
    try:
        # Get raw data for this combination
        raw_data = precomp.raw_data
        if raw_data is not None:
            # Find the row for this combination
            matching_rows = raw_data[
                (raw_data['Customer_Depot_FK'] == depot_id) & 
                (raw_data['Supplier_Depot_FK'] == supplier_depot_id)
            ]
            
            if not matching_rows.empty:
                row = matching_rows.iloc[0]
                print(f"   Wholesale Price (Fuel Zone {row.get('supplier_fuel_zone', 'N/A')}): R{row.get('rtl_wholesale', 'N/A')}")
                print(f"   COC Rebates: cash={row.get('COC_reb_pl_cash', 'N/A')}, 30d={row.get('COC_reb_pl_30', 'N/A')}, 45d={row.get('COC_reb_pl_45', 'N/A')}, 60d={row.get('COC_reb_pl_60', 'N/A')}")
                print(f"   DEL Rebate (30d): {row.get('DEL_reb_pl_30', 'N/A')}")
                print(f"   Equipment Costs: fin={row.get('equip_fin_pl_30', 'N/A')}, main={row.get('equip_main_pl_30', 'N/A')}")
                print(f"   Distance: {row.get('One_Way_Dist', 'N/A')} km")
    except Exception as e:
        print(f"   Could not retrieve raw data: {e}")
    
    # Show volume tier configurations that might apply
    print(f"\n🎯 APPLICABLE VOLUME TIER CONFIGURATIONS:")
    supplier_id = depot_data.get('supplier_id')
    if supplier_id:
        # Check all possible option types to find applicable volume tiers
        all_applicable_tiers = set()
        test_options = ['coc_cash', 'coc_30', 'coc_45', 'coc_60', 'del_own', 'del_buy', 'del_rent']
        
        for option in test_options:
            tiers = precomp.get_applicable_volume_tiers(supplier_id, supplier_depot_id, option)
            all_applicable_tiers.update(tiers)
        
        if all_applicable_tiers:
            for tier_name in sorted(all_applicable_tiers):
                tier_config = config['volume_tier_configurations'][tier_name]
                print(f"   {tier_name}:")
                print(f"     Suppliers: {tier_config.get('suppliers', [])}")
                print(f"     Combination Rule: {tier_config.get('combination_rule', 'Unknown')}")
                print(f"     Bands: {tier_config.get('bands', [])}")
        else:
            print("   No volume tier configurations apply")
    
    print("\n" + "="*80)
    print("🎯 SUMMARY FOR OPTIMIZER:")
    print("="*80)
    print("✅ Base costs: Use for volume below tier thresholds")
    print("✅ Tier costs: Use for volume above tier thresholds") 
    print("✅ Optimizer handles incremental volume allocation")
    print("="*80)

def main():
    print("🚀 Starting fuel optimization precomputation...")
    
    # Run full precomputation
    precomp = FuelOptimizationPrecomputation()
    results = precomp.run_complete_precomputation_with_validation()
    
    print(f"✅ Precomputation complete! Status: {results['status']}")
    print(f"📊 Total depots available: {len(results['cost_data']['costs'])}")
    
    # Interactive querying
    get_user_input(precomp, results)

if __name__ == "__main__":
    main()