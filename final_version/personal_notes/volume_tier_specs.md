

*Payment Terms*
All volume tier rebates are 30 day terms rebates. other payment terms are not available at these tiers only 30 

*Volume Congigurations*

**Supplier A**
Supplier 1 has 20 000 000 volume tier on all supply depots with Rebate_adjustment_clause = True (this means that the base costs are used if volume tier is met and if it is not then the TOP costs must be used), this supplier has combination rule = null (as this is a Rebate_adjustment_clause volume tier so overide and add is no use). This suppliers volume tier is applicable across all transport modes (COC and DEL),  ["coc_rebate": null,"del_rebate": null] (this is the case as it is a Rebate_adjustment_clause agreement)


****Rebate_adjustment_clause****   <---- these calculations must be added to the computations and included in the dictionary so that the Rebate_adjustment_clause contract option can be modelled
RAC_COC_cash_total_cost_pl_pv  = (rtl_wholesale_Sup_Dep/100) + trans_cost_pl
RAC_COC_30_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100))/(1+WACC%/365)^30 + trans_cost_pl
RAC_COC_45_total_cost_pl_pv= ((rtl_wholesale_Sup_Dep/100))/(1+WACC%/365)^45 + trans_cost_pl
RAC_COC_60_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100))/(1+WACC%/365)^60 + trans_cost_pl

RAC_DEL_own_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) + (TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF))/(1+WACC%/365)^30  + cost_pl_on_owned_equip_pv 
RAC_DEL_buy_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) + (TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF))/(1+WACC%/365)^30  + cost_pl_on_buy_equip_pv 
RAC_DEL_rent_total_cost_pl_pv = ((rtl_wholesale_Sup_Dep/100) + (TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF + equip_fin_pl_30 + equip_main_pl_30))/(1+WACC%/365)^30 

[TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF <----- find in the delivery_options table in the database]

**Supplier C**

Supplier 2 has 15 000 000, 20 000 000, and 25 000 000 volume tiers on all supplier depots with Rebate_adjustment_clause = False (this means that the supplier still keeps the base rebate and then the volume tier rebate is either added or overides it), this supplier has combination rule = add (because this is not a Rebate_adjustment_clause agreement, the del_rebate and or coc_rebate per volume tier is added to the base rebate if the supplier meets the required volume for that volume tier). This suppliers volume tiers are applicable across all transport modes (COC and DEL),  [          "min_volume": 0,
          "max_volume": 15000000,
          "del_rebate": 0.00,
          "coc_rebate": 0.00
        },
        {
          "min_volume": 15000000,
          "max_volume": 20000000,
          "del_rebate": 0.50,
          "coc_rebate": 0.59
        },
        {
          "min_volume": 20000000,
          "max_volume": 25000000,
          "del_rebate": 0.51,
          "coc_rebate": 0.60
        },
        {
          "min_volume": 25000000,
          "max_volume": null,
          "del_rebate": 0.53,
          "coc_rebate": 0.62 ] (this is the case as it is not a Rebate_adjustment_clause agreement and the volume tiers correspond to COC and DEL for this supplier so essentially if the volume is met for the contract as a whole then del_rebate is use for del options allocated and coc_rebate is used for COC options allocated)

**Supplier 3** 
No volume tier

**Supplier 4** 
No volume tier

**Supplier 5** 
No volume tier

**Supplier 6** 
No volume tier

**Supplier I**

Supplier 7 has 10 000 000, 20 000 000, 30 000 000 volume tiers on all supply depots with Rebate_adjustment_clause = False, this supplier has combination rule = add (because this is not a Rebate_adjustment_clause agreement, the del_rebate and or coc_rebate per volume tier is added to the base rebate if the supplier meets the required volume for that volume tier). This suppliers volume tiers are applicable across only transport mode DEL(so basically for this supplier all the volume uplifted using del options will determine if the volume tier is met and the coc options used wont determine if volume is met or not, for this supplier base rebates for coc will be used but for the del options base rebates or the volume tier rebates can be used depending on if the volume tier is met,  [         {
          "min_volume": 0,
          "max_volume": 10000000,
          "del_rebate": 0.00,
          "coc_rebate": null
        },
        {
          "min_volume": 10000000,
          "max_volume": 20000000,
          "del_rebate": 0.51,
          "coc_rebate": null
        },
        {
          "min_volume": 20000000,
          "max_volume": 30000000,
          "del_rebate": 0.54,
          "coc_rebate": null
        },
        {
          "min_volume": 30000000,
          "max_volume": null,
          "del_rebate": 0.56,
          "coc_rebate": null
        } ] (this is the case as it is not a Rebate_adjustment_clause agreement and the volume tiers correspond to COC and DEL for this supplier so essentially if the volume is met using del allocations then del_rebate is used and if other allocations used coc from this supplier then the base costs must be used)



**Supplier 8** 
No volume tier

**Supplier 9** 
No volume tier




