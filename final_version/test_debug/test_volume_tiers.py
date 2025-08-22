#!/usr/bin/env python3
"""
Test volume tier application to specific depot-supplier combinations
"""

from precomputation import FuelOptimizationPrecomputation

def test_volume_tier_filtering():
    """Test volume tier filtering logic"""
    
    precomp = FuelOptimizationPrecomputation()
    
    print("=== TESTING VOLUME TIER FILTERING ===")
    
    # Test cases for different depot-supplier-option combinations
    test_cases = [
        (1, 1, 'coc_cash'),   # Depot 1, Supplier 1, COC Cash
        (1, 1, 'coc_30'),     # Depot 1, Supplier 1, COC NET30
        (1, 1, 'del_own'),    # Depot 1, Supplier 1, DEL Own (if available)
    ]
    
    for depot_id, supplier_id, option in test_cases:
        applicable_tiers = precomp.get_applicable_volume_tiers(supplier_id, depot_id, option)
        print(f"\nDepot {depot_id}, Supplier {supplier_id}, Option {option}:")
        print(f"  Applicable tiers: {applicable_tiers}")
        
        if applicable_tiers:
            for tier_name in applicable_tiers:
                tier_config = precomp.config['volume_tier_configurations'][tier_name]
                scope = tier_config['scope_filters']
                print(f"    {tier_name}:")
                print(f"      Suppliers: {scope.get('suppliers', ['*'])}")
                print(f"      Modes: {scope.get('modes', ['*'])}")  
                print(f"      Terms: {scope.get('terms', ['*'])}")

def test_enhanced_costs_with_specific_volume():
    """Test enhanced costs for a specific volume scenario"""
    
    precomp = FuelOptimizationPrecomputation()
    
    print("\n=== TESTING ENHANCED COSTS WITH VOLUME TIERS ===")
    
    # Get base costs first
    base_data = precomp.run_base_precomputation()
    
    # Test with a specific volume that should trigger tier rebates
    test_volume = 15000000  # 15M litres
    enhanced_data = precomp.calculate_volume_enhanced_costs(base_data, [test_volume])
    
    # Examine first depot that has COC options
    for depot_id, supplier_depots in enhanced_data['costs'].items():
        print(f"\nDepot {depot_id}:")
        
        for supplier_depot_id, data in list(supplier_depots.items())[:2]:
            if 'coc_30' in data['available_options']:
                base_cost = data['base_costs']['coc_30'] 
                enhanced_cost = data['volume_scenarios'][test_volume]['coc_30']
                volume_rebate = data['volume_scenarios'][test_volume].get('volume_tier_rebate', 0)
                
                print(f"  Supplier Depot {supplier_depot_id} - COC NET30:")
                print(f"    Base cost: R{base_cost:.4f}/litre")
                print(f"    Enhanced cost: R{enhanced_cost:.4f}/litre")
                print(f"    Volume tier rebate: R{volume_rebate:.6f}/litre")
                print(f"    Savings: R{base_cost - enhanced_cost:.6f}/litre")
                
                if 'applicable_tiers' in data['volume_scenarios'][test_volume]:
                    print(f"    Applied tiers: {[t['tier_name'] for t in data['volume_scenarios'][test_volume]['applicable_tiers']]}")
                
                break
        break

if __name__ == "__main__":
    test_volume_tier_filtering()
    test_enhanced_costs_with_specific_volume()