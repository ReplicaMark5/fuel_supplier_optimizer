


**Constraints**
- [ ] Max number of customer supplier contracts 
- [ ] Implement, constraints that limit one supplier contract to one payment term(or some sort of constraint that is to do with payment term) --todo
- [ ] Cross-boarder trade constraint or penalty --todo
- [ ] Make sure config defines which customer depots have forced constraints for using their own equipment vs ones that want to buy equipment for del and coc (optional, force rent, force buy) 

**Multi-Objective Optimization**
- [ ] Add in qualitative supplier selection data into database --todo
- [ ] Add in e-constaint method --todo


**Extras**
- [x] Implement all unit vs incremental volume tiers 
- [ ] Check costs are calculated correctly for international depots
- [ ] Look at implementing (static VS dynamic) and/or (deterministic Vs stochastic) [eg. variable demand volume, variable fuel price etc...][look at stochastic programming and robust optimization]


**Equipment**
- [x] Make sure config defines which suppliers actually have equipment rental as an option (as some of the DEL data could include 0s for equipment finance and miantenance charge which would be ambiguos as a supplier could either be offering equipment for free or it could not be offering equipment rental). 
- [ ] make sure that for equipment cost is done per depot for owned equipment (either calc or input for each one [cost_pl_on_owned_equip_pv]
- [x] Adjust cost per litre for COC precomputation to include equipment costs as if the collection option is choosen, customer still needs to pay for equipment themselves this doesnt only apply to the DEL)   -----> SOLUTION: used (+ cost_pl_on_owned_equip_pv) in all coc calcs



**Customer Depot Tank Capacity**
- [x] Must factor in customer depot tank capcity (UNITRANS PREFERS HAVING FUEL DELIVERED FOR CUSTOMER DEPOTS WITH SMALLER TANK CAPACITY)
  ---> use tank capacity per customer depot 
  ---> add reorder level for these customer tanks (config as a percentage)
  ---> BASICALLY IF CUSTOMER DEPOT TANK CAPACITY IS LOWER THAN TANKER CAPACITY THEN THIS FORMULA [trans_cost_pl = ((One_Way_Dist)(2)(tanker_cost_per_km))/tanker_cap] MUST USE THE (tank capacity - reorder level)

      reorder_level is the fraction remaining when a refill is triggered (0.30 = refill at 30% remaining → deliver 70% of tank, capped by tanker capacity).
      min_drop_litres avoids unrealistically tiny deliveries (keep 0 if not needed).
      allow_multidrop = true assumes realistic pooling across multiple depots.
      If allow_multidrop = true, enforce fill_ratio >= min_expected_fill_ratio (e.g., 0.8).





Could look at adding: 

- Nested `scope_filters`, `operational_rules`, `penalties`                         
- override_value`, `fallback_rebate` 

CHAT GPT RECOMMENDATION 

Modelling take-or-pay and clawbacks precisely

Some contracts don’t switch per-litre price; they charge a deficiency payment on shortfall: deficit = max{0, T_c − realized_volume} with penalty p_c · deficit. You can add a continuous variable d_c ≥ 0, constrain d_c ≥ T_c − Σ volume, and add p_c d_c to the objective. This often matches supplier invoices better than “RAC unit price on all litres.” Keep your RAC pricing path too—enable per-contract contract_type ∈ {clawback, rac_unit_price} so you can do either.