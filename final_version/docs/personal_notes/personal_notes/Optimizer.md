**Binary decision variables(0 or 1):**

C_cash_bin   \\collection with cash payment 
C_30_bin      \\collection with 30days payment
C_45_bin    
C_60_bin      

D_own_bin    \\Delivery with using own fuelling equipment 
D_buy_bin  
D_rent_bin

**Coefficients**


**Objective functions:**

min z = (Debot_1_vol)((C_cash_bin)(COC_cash_total_cost_pl_pv) + (C_30_bin)(COC_30_total_cost_pl_pv) + (C_45_bin)(COC_45_total_cost_pl_pv) + (C_60_bin)(COC_60_total_cost_pl_pv) + (D_own_bin)(DEL_own_total_cost_pl_pv) + (D_buy_bin)(DEL_buy_total_cost_pl_pv) + (D_rent_bin)(DEL_rent_total_cost_pl_pv))


**Constraints:**

C_cash_bin[i, j, k] + C_30_bin[i, j, k] + C_45_bin[i, j, k] + C_60_bin[i, j, k] + D_own_bin[i, j, k] + D_buy_bin[i, j, k] + D_rent_bin[i, j, k] = 1


***Supplier A volume constraint -- supply depot: ALL Fuel Zone: 09C***

IF ((Debot_vol[1])(C_cash_bin[1, 1] + C_30_bin[1, 1] + C_45_bin[1, 1] + C_60_bin[1, 1]) + (Debot_vol[2])(C_cash_bin[2, 1] + C_30_bin[2, 1] + C_45_bin[2, 1] + C_60_bin[2, 1]) + #### ... < ####) = TRUE {



}  j = 1:57



**UI Constraints:**

-Forced allocation for transport option out of the 7 options---> constrains to 1 
-Forced one payment term constraint across all depots 

**Output**