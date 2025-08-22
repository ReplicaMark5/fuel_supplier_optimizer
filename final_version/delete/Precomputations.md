**Binary decision variables(0 or 1):**


C_cash_bin   \\collection with cash payment 
C_30_bin      \\collection with 30days payment
C_45_bin    
C_60_bin      

D_own_bin    \\Delivery with using own fuelling equipment 
D_buy_bin  
D_rent_bin


**Precomputations:**
#### = User Input in UI 

***COC options***
rtl_wholesale_Sup_Dep = Fuel Zone match with supplier    \\zone differential for each supplier depot 


WACC% = #### 

   
tanker_cost_per_km = ####     \\how much it costs to drive tanker in (R/km)
tanker_cap = ####      \\the capacity of a tanker (litres)
trans_cost_pl = ((One_Way_Dist)(2)(tanker_cost_per_km))/tanker_cap  \\Transport cost per litre based on dist from customer depot to supplier depot and back (R/ltr)

COC_cash_price_pl_pv = (rtl_wholesale_Sup_Dep/100) - COC_reb_pl_cash
COC_30_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - COC_reb_pl_30)/(1+WACC%/365)^30
COC_45_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - COC_reb_pl_45)/(1+WACC%/365)^45
COC_60_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - COC_reb_pl_60)/(1+WACC%/365)^60

COC_cash_total_cost_pl_pv = COC_cash_price_pl_pv + trans_cost_pl
COC_30_total_cost_pl_pv = COC_30_price_pl_pv + trans_cost_pl
COC_45_total_cost_pl_pv = COC_45_price_pl_pv + trans_cost_pl
COC_60_total_cost_pl_pv = COC_60_price_pl_pv + trans_cost_pl

***DEL & Already own equipment***
cost_pl_on_owned_equip_pv = #### OR CALC
DEL_own_reb_pl_30 = DEL_reb_pl_30 + equip_fin_pl_30 + equip_main_pl_30   

DEL_own_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - DEL_own_reb_pl_30)/(1+WACC%/365)^30

DEL_own_total_cost_pl_pv = DEL_own_price_pl_pv + cost_pl_on_owned_equip_pv


***DEL & Buy Equipmemt***
cost_pl_on_buy_equip_pv = #### OR CALC
DEL_buy_reb_pl_30 = DEL_reb_pl_30 + equip_fin_pl_30 + equip_main_pl_30

DEL_buy_price_pl_pv = ((rtl_wholesale_Sup_Dep/100) - DEL_buy_reb_pl_30)/(1+WACC%/365)^30

DEL_buy_total_cost_pl_pv = DEL_buy_price_pl_pv + cost_pl_on_buy_equip_pv


***DEL & Rent equipment***
DEL_rent_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) - DEL_reb_pl_30)/(1+WACC%/365)^30


