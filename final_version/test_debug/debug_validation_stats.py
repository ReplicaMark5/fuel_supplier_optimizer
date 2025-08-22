#!/usr/bin/env python3
"""
Debug validation statistics to identify the rebate calculation error
"""

from precomputation import FuelOptimizationPrecomputation

def debug_validation_statistics():
    """Debug the validation statistics calculation"""
    
    precomp = FuelOptimizationPrecomputation()
    
    # Run complete precomputation
    complete_results = precomp.run_complete_precomputation_with_validation()
    enhanced_cost_data = complete_results['cost_data']
    validation_results = complete_results['validation']
    
    print("=== DEBUGGING VALIDATION STATISTICS ===")
    print(f"Reported Average Volume Tier Rebate: R{validation_results['statistics']['average_volume_tier_rebate']:.6f}/litre")
    print(f"Reported Maximum Volume Tier Rebate: R{validation_results['statistics']['max_volume_tier_rebate']:.6f}/litre")
    
    # Manual calculation to verify
    all_rebates = []
    combinations_with_tiers = 0
    max_rebate = 0.0
    
    for depot_id, supplier_depots in enhanced_cost_data['costs'].items():
        for supplier_depot_id, data in supplier_depots.items():
            volume_scenarios = data.get('volume_scenarios', {})
            has_volume_tiers = False
            
            for volume, scenario_data in volume_scenarios.items():
                if 'volume_tier_rebate' in scenario_data and scenario_data['volume_tier_rebate'] > 0:
                    has_volume_tiers = True
                    rebate = scenario_data['volume_tier_rebate']
                    all_rebates.append(rebate)
                    max_rebate = max(max_rebate, rebate)
                    
            if has_volume_tiers:
                combinations_with_tiers += 1
    
    # Calculate correct statistics
    manual_average = sum(all_rebates) / len(all_rebates) if all_rebates else 0
    manual_max = max_rebate
    
    print(f"\n=== MANUAL VERIFICATION ===")
    print(f"Total rebate entries found: {len(all_rebates)}")
    print(f"Combinations with volume tiers: {combinations_with_tiers}")
    print(f"Manual Average Rebate: R{manual_average:.6f}/litre")
    print(f"Manual Maximum Rebate: R{manual_max:.6f}/litre")
    
    # Show sample rebates
    print(f"\n=== SAMPLE REBATES (first 10) ===")
    for i, rebate in enumerate(all_rebates[:10]):
        print(f"  {i+1}: R{rebate:.6f}/litre")
    
    print(f"\n=== REBATE DISTRIBUTION ===")
    if all_rebates:
        all_rebates_sorted = sorted(all_rebates, reverse=True)
        print(f"Highest 5 rebates: {[f'R{r:.6f}' for r in all_rebates_sorted[:5]]}")
        print(f"Lowest 5 rebates: {[f'R{r:.6f}' for r in all_rebates_sorted[-5:]]}")
        
        # Check if there are any suspiciously high rebates
        high_rebates = [r for r in all_rebates if r > 0.01]  # More than 1 cent
        if high_rebates:
            print(f"\nWARNING: Found {len(high_rebates)} rebates > 1 cent/litre:")
            for rebate in high_rebates[:3]:
                print(f"  R{rebate:.6f}/litre")

if __name__ == "__main__":
    debug_validation_statistics()