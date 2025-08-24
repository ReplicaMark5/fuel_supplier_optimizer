#!/usr/bin/env python3
"""Quick test to validate RAC cost fix"""

import json
from precomputation import FuelOptimizationPrecomputation

def test_rac_costs():
    # Load configuration
    with open('optimization_config.json', 'r') as f:
        config = json.load(f)
    
    # Run precomputation
    precomp = FuelOptimizationPrecomputation('optimization_config.json')
    cost_data = precomp.run_complete_precomputation()
    
    print("=== RAC COST VALIDATION TEST ===")
    
    # Test a few depot combinations
    test_cases = [
        (1, 21, "Depot 1 → Supplier Depot 21"),
        (5, 22, "Depot 5 → Supplier Depot 22"),
    ]
    
    for depot_id, supplier_depot_id, description in test_cases:
        if depot_id in cost_data and supplier_depot_id in cost_data[depot_id]:
            costs = cost_data[depot_id][supplier_depot_id]
            base_costs = costs['base_costs']
            
            print(f"\n--- {description} ---")
            print(f"Supplier: {costs.get('supplier_name', 'N/A')}")
            print(f"Distance: {costs.get('distance', 'N/A')} km")
            
            # Check DEL costs
            if 'del_own' in base_costs:
                base_del = base_costs['del_own']
                rac_del = costs.get('rac_del_own_cost_pv')
                if rac_del:
                    diff = rac_del - base_del
                    status = "✅ PENALTY" if diff > 0 else "❌ NOT PENALTY"
                    print(f"DEL Own: Base R{base_del:.4f}/L vs RAC R{rac_del:.4f}/L (diff: +R{diff:.4f}/L) {status}")
            
            if 'del_rent' in base_costs:
                base_del = base_costs['del_rent']
                rac_del = costs.get('rac_del_rent_cost_pv')
                if rac_del:
                    diff = rac_del - base_del
                    status = "✅ PENALTY" if diff > 0 else "❌ NOT PENALTY"
                    print(f"DEL Rent: Base R{base_del:.4f}/L vs RAC R{rac_del:.4f}/L (diff: +R{diff:.4f}/L) {status}")
                    
            # Check COC costs
            if 'coc_30' in base_costs:
                base_coc = base_costs['coc_30']
                rac_coc = costs.get('rac_coc_30_cost_pv')
                if rac_coc:
                    diff = rac_coc - base_coc
                    status = "✅ PENALTY" if diff > 0 else "❌ NOT PENALTY"
                    print(f"COC 30: Base R{base_coc:.4f}/L vs RAC R{rac_coc:.4f}/L (diff: +R{diff:.4f}/L) {status}")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    test_rac_costs()