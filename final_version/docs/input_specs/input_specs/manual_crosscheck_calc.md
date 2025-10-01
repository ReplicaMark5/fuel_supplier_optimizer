
*COC validate*

rtl_wholesale_Sup_Dep = ####
WACC% = default: 0.125
tanker_cost_per_km = default: 15.5
tanker_cap = default: 30000
One_Way_Dist = ####
COC_reb_pl_cash = ####
COC_reb_pl_30 = ####
COC_reb_pl_45 = ####
COC_reb_pl_60 = ####

tankage_size_litres = (from database) \\ customer depot tank capacity in litres 
reorder_level = #### default: 0.30 \\ fraction remaining when refill is triggered (0.30 = 30% remaining)
min_drop_litres = ####default: 0 \\ minimum delivery quantity in litres
allow_multidrop = #### default: false \\ enable multidrop pooling (true/false)
min_expected_fill_ratio = #### default: 1.0 \\ minimum fill ratio when multidrop enabled



**Universal Transport Cost Calculation (applies to all cost types)**
  delivered_litres = min(tanker_cap, max(min_drop_litres, (1 - reorder_level) * tankage_size_litres))
  base_fill_ratio = delivered_litres / tanker_cap  
  fill_ratio = if(allow_multidrop, max(base_fill_ratio, min_expected_fill_ratio), base_fill_ratio)
  effective_litres = tanker_cap * fill_ratio
  trans_cost_pl = ((One_Way_Dist)(2)(tanker_cost_per_km))/effective_litres

  **Fallback:** If tankage_size_litres = NULL then effective_litres = tanker_cap

**Base**


COC_cash_price_pl_pv = (rtl_wholesale_Sup_Dep/100) - COC_reb_pl_cash
COC_30_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - COC_reb_pl_30)/(1+WACC%/365)^30
COC_45_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - COC_reb_pl_45)/(1+WACC%/365)^45
COC_60_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - COC_reb_pl_60)/(1+WACC%/365)^60

COC_cash_total_cost_pl_pv = COC_cash_price_pl_pv + trans_cost_pl + cost_pl_on_owned_equip_pv 
COC_30_total_cost_pl_pv = COC_30_price_pl_pv + trans_cost_pl + cost_pl_on_owned_equip_pv 
COC_45_total_cost_pl_pv = COC_45_price_pl_pv + trans_cost_pl + cost_pl_on_owned_equip_pv 
COC_60_total_cost_pl_pv = COC_60_price_pl_pv + trans_cost_pl + cost_pl_on_owned_equip_pv 

**Volume tier costs - Reward Cost scenario**
Add COC volume tier (y/n) = ####
    Combination rule (overide or add) = ####
    vol_tier_reb_30D = ####       \\R/litre must be in 30day terms

***If Overide***

COC_30_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - vol_tier_reb_30D)/(1+WACC%/365)^30

COC_30_total_cost_pl_pv = COC_30_price_pl_pv + trans_cost_pl cost_pl_on_owned_equip_pv


***If Add***

COC_30_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - (COC_reb_pl_30 + vol_tier_reb_30D))/(1+WACC%/365)^30

COC_30_total_cost_pl_pv = COC_30_price_pl_pv + trans_cost_pl + cost_pl_on_owned_equip_pv


**Rebate_adjustment_clause - Penalty Costs Scenario**

RAC_COC_30_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100))/(1+WACC%/365)^30 + trans_cost_pl + cost_pl_on_owned_equip_pv





*DEL validate*

cost_pl_on_owned_equip_pv = ####  \\(rands per litre) cost of customer owning equipment themselves measured in rands per litre of fuel that goes throught the equipment (eg. pumps and tanks) (this is a company wide calculated average that is used for all fuel depot equipment, whether the company already owns the equipment or will buy more equipment themselves)

DEL_reb_pl_30 = (from database) \\(rands per litre)****
equip_fin_pl_30 = (from database)  \\(rands per litre)
equip_main_pl_30 = (from database) \\(rands per litre)
[TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF] = From delivery_options table in database


**Base**
DEL_own_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) - (DEL_reb_pl_30 + equip_fin_pl_30 + equip_main_pl_30))/(1+WACC%/365)^30 + cost_pl_on_owned_equip_pv   \\Dellivery cost per litre if customer continues to use/buy their own equipment

DEL_rent_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) - DEL_reb_pl_30)/(1+WACC%/365)^30  \\Dellivery cost per litre for if customer wants to rent equipment

**Volume tier costs**
Add DEL volume tier (y/n) = ####
    Combination rule (overide or add) = ####
    vol_tier_reb_30D = ####       \\R/litre must be in 30day terms

***If Overide***
DEL_own_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) - (vol_tier_reb_30D + equip_fin_pl_30 + equip_main_pl_30))/(1+WACC%/365)^30 + cost_pl_on_owned_equip_pv

DEL_rent_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) - vol_tier_reb_30D)/(1+WACC%/365)^30 

***If Add***
DEL_own_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) - (DEL_reb_pl_30 + vol_tier_reb_30D + equip_fin_pl_30 + equip_main_pl_30))/(1+WACC%/365)^30 + cost_pl_on_owned_equip_pv

DEL_rent_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) - (DEL_reb_pl_30 + vol_tier_reb_30D))/(1+WACC%/365)^30

**Rebate_adjustment_clause - Penalty Costs Scenario**

RAC_DEL_own_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) + (TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF))/(1+WACC%/365)^30  + cost_pl_on_owned_equip_pv 
RAC_DEL_rent_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) + (TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF + equip_fin_pl_30 + equip_main_pl_30))/(1+WACC%/365)^30 



