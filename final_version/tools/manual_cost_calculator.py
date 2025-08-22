#!/usr/bin/env python3
"""
Manual Cost Calculator Tool
Cross-check fuel costs with precomputation.py results
"""

def get_input(prompt, data_type=float, default=None):
    """Get user input with type conversion and optional default"""
    while True:
        try:
            if default is not None:
                value = input(f"{prompt} [default: {default}]: ")
                if value.strip() == "":
                    return default
            else:
                value = input(f"{prompt}: ")
            
            if data_type == float:
                return float(value)
            elif data_type == int:
                return int(value)
            else:
                return value
        except ValueError:
            print(f"Invalid input. Please enter a valid {data_type.__name__}")

def calculate_coc_costs():
    """Calculate COC costs based on manual input"""
    print("\n=== COC Cost Calculator ===")
    print("Enter the following values:")
    
    # Get inputs
    rtl_wholesale_sup_dep = get_input("rtl_wholesale_Sup_Dep (cents/litre)")
    wacc_percent = get_input("WACC% (as decimal)", default=0.125)
    tanker_cost_per_km = get_input("tanker_cost_per_km (R/km)", default=15.5)
    tanker_cap = get_input("tanker_cap (litres)", default=30000)
    one_way_dist = get_input("One_Way_Dist (km)")
    
    # Rebate inputs (in Rands)
    coc_reb_pl_cash = get_input("COC_reb_pl_cash (R/litre)")
    coc_reb_pl_30 = get_input("COC_reb_pl_30 (R/litre)")
    coc_reb_pl_45 = get_input("COC_reb_pl_45 (R/litre)")
    coc_reb_pl_60 = get_input("COC_reb_pl_60 (R/litre)")
    
    # Volume tier inputs
    add_volume_tier = get_input("Add volume tier (y/n)", data_type=str, default="n").lower().strip()
    
    vol_tier_reb_30d = 0
    combination_rule = ""
    
    if add_volume_tier == "y":
        combination_rule = get_input("Combination rule (override/add)", data_type=str, default="add").lower().strip()
        vol_tier_reb_30d = get_input("vol_tier_reb_30D (R/litre in 30day terms)")
    
    print("\n=== CALCULATIONS ===")
    
    # Transport cost calculation
    trans_cost_pl = ((one_way_dist * 2 * tanker_cost_per_km) / tanker_cap)
    print(f"trans_cost_pl = {trans_cost_pl:.6f} R/litre")
    
    # Price calculations based on volume tier settings
    if add_volume_tier == "y":
        if combination_rule == "override":
            # Override: Only 30-day term uses volume tier rebate
            coc_cash_price_pl_pv = (rtl_wholesale_sup_dep / 100) - coc_reb_pl_cash
            coc_30_price_pl_pv = ((rtl_wholesale_sup_dep / 100) - vol_tier_reb_30d) / ((1 + wacc_percent / 365) ** 30)
            coc_45_price_pl_pv = ((rtl_wholesale_sup_dep / 100) - coc_reb_pl_45) / ((1 + wacc_percent / 365) ** 45)
            coc_60_price_pl_pv = ((rtl_wholesale_sup_dep / 100) - coc_reb_pl_60) / ((1 + wacc_percent / 365) ** 60)
            print("Using OVERRIDE mode: 30-day term uses volume tier rebate")
        else:  # add
            # Add: 30-day term uses original rebate + volume tier rebate
            coc_cash_price_pl_pv = (rtl_wholesale_sup_dep / 100) - coc_reb_pl_cash
            coc_30_price_pl_pv = ((rtl_wholesale_sup_dep / 100) - (coc_reb_pl_30 + vol_tier_reb_30d)) / ((1 + wacc_percent / 365) ** 30)
            coc_45_price_pl_pv = ((rtl_wholesale_sup_dep / 100) - coc_reb_pl_45) / ((1 + wacc_percent / 365) ** 45)
            coc_60_price_pl_pv = ((rtl_wholesale_sup_dep / 100) - coc_reb_pl_60) / ((1 + wacc_percent / 365) ** 60)
            print("Using ADD mode: 30-day term uses original + volume tier rebate")
    else:
        # No volume tier - standard calculations
        coc_cash_price_pl_pv = (rtl_wholesale_sup_dep / 100) - coc_reb_pl_cash
        coc_30_price_pl_pv = ((rtl_wholesale_sup_dep / 100) - coc_reb_pl_30) / ((1 + wacc_percent / 365) ** 30)
        coc_45_price_pl_pv = ((rtl_wholesale_sup_dep / 100) - coc_reb_pl_45) / ((1 + wacc_percent / 365) ** 45)
        coc_60_price_pl_pv = ((rtl_wholesale_sup_dep / 100) - coc_reb_pl_60) / ((1 + wacc_percent / 365) ** 60)
        print("Using standard calculations (no volume tier)")
    
    print(f"COC_cash_price_pl_pv = {coc_cash_price_pl_pv:.6f} R/litre")
    print(f"COC_30_price_pl_pv = {coc_30_price_pl_pv:.6f} R/litre")
    print(f"COC_45_price_pl_pv = {coc_45_price_pl_pv:.6f} R/litre")
    print(f"COC_60_price_pl_pv = {coc_60_price_pl_pv:.6f} R/litre")
    
    # Total cost calculations
    coc_cash_total_cost_pl_pv = coc_cash_price_pl_pv + trans_cost_pl
    coc_30_total_cost_pl_pv = coc_30_price_pl_pv + trans_cost_pl
    coc_45_total_cost_pl_pv = coc_45_price_pl_pv + trans_cost_pl
    coc_60_total_cost_pl_pv = coc_60_price_pl_pv + trans_cost_pl
    
    print(f"\n=== TOTAL COSTS (R/litre) ===")
    print(f"COC_cash_total_cost_pl_pv = {coc_cash_total_cost_pl_pv:.6f}")
    print(f"COC_30_total_cost_pl_pv = {coc_30_total_cost_pl_pv:.6f}")
    print(f"COC_45_total_cost_pl_pv = {coc_45_total_cost_pl_pv:.6f}")
    print(f"COC_60_total_cost_pl_pv = {coc_60_total_cost_pl_pv:.6f}")
    
    results = {
        'transport_cost': trans_cost_pl,
        'cash_total': coc_cash_total_cost_pl_pv,
        '30_day_total': coc_30_total_cost_pl_pv,
        '45_day_total': coc_45_total_cost_pl_pv,
        '60_day_total': coc_60_total_cost_pl_pv
    }
    
    # Add volume tier info to results
    if add_volume_tier == "y":
        results['volume_tier_applied'] = f"{combination_rule.upper()}: {vol_tier_reb_30d} R/litre"
    else:
        results['volume_tier_applied'] = "None"
    
    return results

def calculate_del_costs():
    """Calculate DEL costs based on manual input"""
    print("\n=== DEL Cost Calculator ===")
    print("Enter the following values:")
    
    # Get shared inputs
    rtl_wholesale_sup_dep = get_input("rtl_wholesale_Sup_Dep (cents/litre)")
    wacc_percent = get_input("WACC% (as decimal)", default=0.125)
    one_way_dist = get_input("One_Way_Dist (km)")
    
    # DEL specific inputs
    cost_pl_on_buy_equip_pv = get_input("cost_pl_on_buy_equip_pv (R/litre)", default=0.08)
    cost_pl_on_owned_equip_pv = get_input("cost_pl_on_owned_equip_pv (R/litre)", default=0.05)
    del_fee_per_ltr_per_km = get_input("del_fee_per_ltr_per_km (R/litre/km)", default=0.0002)
    del_reb_pl_30 = get_input("DEL_reb_pl_30 (R/litre)")
    equip_fin_pl_30 = get_input("equip_fin_pl_30 (R/litre)")
    equip_main_pl_30 = get_input("equip_main_pl_30 (R/litre)")
    
    # Volume tier inputs
    add_volume_tier = get_input("Add DEL volume tier (y/n)", data_type=str, default="n").lower().strip()
    
    vol_tier_reb_30d = 0
    combination_rule = ""
    
    if add_volume_tier == "y":
        combination_rule = get_input("Combination rule (override/add)", data_type=str, default="add").lower().strip()
        vol_tier_reb_30d = get_input("vol_tier_reb_30D (R/litre in 30day terms)")
    
    print("\n=== DEL CALCULATIONS ===")
    
    # Transport cost calculation
    del_transport_cost = del_fee_per_ltr_per_km * one_way_dist
    print(f"del_transport_cost = {del_transport_cost:.6f} R/litre")
    
    # Calculate based on volume tier settings
    if add_volume_tier == "y":
        if combination_rule == "override" or combination_rule == "overide":
            # Override: Use volume tier rebate instead of DEL rebate
            del_own_total_cost_pl_pv = ((rtl_wholesale_sup_dep / 100) - (vol_tier_reb_30d + equip_fin_pl_30 + equip_main_pl_30)) / ((1 + wacc_percent / 365) ** 30) + del_transport_cost + cost_pl_on_owned_equip_pv
            del_buy_total_cost_pl_pv = ((rtl_wholesale_sup_dep / 100) - (vol_tier_reb_30d + equip_fin_pl_30 + equip_main_pl_30)) / ((1 + wacc_percent / 365) ** 30) + del_transport_cost + cost_pl_on_buy_equip_pv
            del_rent_total_cost_pl_pv = ((rtl_wholesale_sup_dep / 100) - vol_tier_reb_30d) / ((1 + wacc_percent / 365) ** 30) + del_transport_cost
            print("Using OVERRIDE mode: volume tier replaces DEL rebate")
        else:  # add
            # Add: Use DEL rebate + volume tier rebate
            del_own_total_cost_pl_pv = ((rtl_wholesale_sup_dep / 100) - (del_reb_pl_30 + vol_tier_reb_30d + equip_fin_pl_30 + equip_main_pl_30)) / ((1 + wacc_percent / 365) ** 30) + del_transport_cost + cost_pl_on_owned_equip_pv
            del_buy_total_cost_pl_pv = ((rtl_wholesale_sup_dep / 100) - (del_reb_pl_30 + vol_tier_reb_30d + equip_fin_pl_30 + equip_main_pl_30)) / ((1 + wacc_percent / 365) ** 30) + del_transport_cost + cost_pl_on_buy_equip_pv
            del_rent_total_cost_pl_pv = ((rtl_wholesale_sup_dep / 100) - (del_reb_pl_30 + vol_tier_reb_30d)) / ((1 + wacc_percent / 365) ** 30) + del_transport_cost
            print("Using ADD mode: volume tier adds to DEL rebate")
    else:
        # Standard DEL calculations (no volume tier) - matching your formulas exactly
        del_own_total_cost_pl_pv = ((rtl_wholesale_sup_dep / 100) - (del_reb_pl_30 + equip_fin_pl_30 + equip_main_pl_30)) / ((1 + wacc_percent / 365) ** 30) + del_transport_cost + cost_pl_on_owned_equip_pv
        del_buy_total_cost_pl_pv = ((rtl_wholesale_sup_dep / 100) - (del_reb_pl_30 + equip_fin_pl_30 + equip_main_pl_30)) / ((1 + wacc_percent / 365) ** 30) + del_transport_cost + cost_pl_on_buy_equip_pv
        del_rent_total_cost_pl_pv = ((rtl_wholesale_sup_dep / 100) - del_reb_pl_30) / ((1 + wacc_percent / 365) ** 30) + del_transport_cost
        print("Using standard DEL calculations (no volume tier)")
    
    print(f"\n=== DEL TOTAL COSTS (R/litre) ===")
    print(f"DEL_own_total_cost_pl_pv = {del_own_total_cost_pl_pv:.6f}")
    print(f"DEL_buy_total_cost_pl_pv = {del_buy_total_cost_pl_pv:.6f}")
    print(f"DEL_rent_total_cost_pl_pv = {del_rent_total_cost_pl_pv:.6f}")
    
    results = {
        'transport_cost': del_transport_cost,
        'own_equipment_total': del_own_total_cost_pl_pv,
        'buy_equipment_total': del_buy_total_cost_pl_pv,
        'rent_equipment_total': del_rent_total_cost_pl_pv
    }
    
    # Add volume tier info to results
    if add_volume_tier == "y":
        results['volume_tier_applied'] = f"{combination_rule.upper()}: {vol_tier_reb_30d} R/litre"
    else:
        results['volume_tier_applied'] = "None"
    
    return results

def main():
    """Main calculator interface"""
    print("Manual Fuel Cost Calculator")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Calculate COC costs")
        print("2. Calculate DEL costs") 
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ")
        
        if choice == "1":
            results = calculate_coc_costs()
            
            print("\n" + "=" * 50)
            print("COC SUMMARY OF RESULTS:")
            print("=" * 50)
            for option, cost in results.items():
                if option == 'volume_tier_applied':
                    print(f"{option}: {cost}")
                else:
                    print(f"{option}: R{cost:.6f}/litre")
                    
        elif choice == "2":
            results = calculate_del_costs()
            
            print("\n" + "=" * 50)
            print("DEL SUMMARY OF RESULTS:")
            print("=" * 50)
            for option, cost in results.items():
                if option == 'volume_tier_applied':
                    print(f"{option}: {cost}")
                else:
                    print(f"{option}: R{cost:.6f}/litre")
                
        elif choice == "3":
            print("Exiting calculator...")
            break
        else:
            print("Invalid choice. Please select 1-3.")

if __name__ == "__main__":
    main()