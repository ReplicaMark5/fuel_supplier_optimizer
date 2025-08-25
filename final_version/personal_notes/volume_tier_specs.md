

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


**Supplier C**

Supplier 2 has 15 000 000, 20 000 000, and 25 000 000 volume tiers on all supplier depots with Rebate_adjustment_clause = False (this means that the cost per litre of fuel for this supplier is the base costs for if below the volume tiers and then for within volume tiers then the volume tier costs are used depending on whcih volume tier is used which are calculated in `precomputation.py`), this supplier has combination rule = add (because this is not a Rebate_adjustment_clause agreement, the del_rebate and or coc_rebate per volume tier is added to the base rebate if the supplier meets the required volume for that volume tier off which the costs for these scnarios are calculated in `precomputation.py` and then stored in the dictionary for the optimizer to use). This suppliers volume tiers are applicable across all transport modes (COC and DEL),  [          "min_volume": 0,
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
          "coc_rebate": 0.62 ] (this is the case as it is not a Rebate_adjustment_clause agreement and the volume tiers correspond to COC and DEL for this supplier so essentially if the volume is met for the contract as a whole then del_rebate is use for del options allocated and coc_rebate is used for COC options allocated. these rebate values are/must be used in the present value formulas in the `precomputation.py` to calcualte the base costs per litre for if volume tier is met for these scenarios. For example if a volume tier is met for supplier C then the optimizer must use that volume tiers costs per litre from the dictionary for the customer depot-supplier depot allocations, some can be the del costs per litre for that tier or some can be coc cost per litre for other allocations within that supplier, essentially the optimizer must just use the costs from the dictionary and the precomputations calculate the costs per litre for the difference scenarios)

**Supplier 3** 
No volume tier

**Supplier 4** 
No volume tier

**Supplier 5** 
No volume tier

**Supplier 6** 
No volume tier

**Supplier I**

Supplier 7 has 10 000 000, 20 000 000, 30 000 000 volume tiers on all supply depots with Rebate_adjustment_clause = False, this supplier has combination rule = override (because this is not a Rebate_adjustment_clause agreement, the del_rebate and or coc_rebate per volume tier override base rebate if the supplier meets the required volume for that volume tier, the formulas to calculate these cost per litre values for scenarious are done in `precomputation.py`). This suppliers volume tiers are applicable across only transport mode DEL (so basically for this supplier all the volume uplifted using del options will determine if the volume tier is met and the coc options used wont determine if volume is met or not, for this supplier base rebates for coc allocations will be used but for the del options base rebates or the volume tier rebates can be used depending on if the volume tier is met, essentially only del allocations from this supplier will be used to calculate volume uplifted to trigger volume tier but for coc options it will just be the base coc options available),  [         {
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
        } ] (this is the case as it is not a Rebate_adjustment_clause agreement and the volume tiers correspond to COC and DEL for this supplier so essentially if the volume is met using del allocations then del_rebate is used for volume tier cost per litre calculations in `precomputation.py` and if other allocations use coc from this supplier then the base costs must be used)



**Supplier 8** 
No volume tier

**Supplier 9** 
No volume tier




