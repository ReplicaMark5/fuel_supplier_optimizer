

**Equipment**
- [ ] Make sure config defines which suppliers actually have equipment finance and maintenance charges as an option. 
- [ ] Make sure config defines which customer depots already have equipment vs ones that want to buy equipment (for del and coc)
- [ ] make sure that for equipment cost is done per depot for owned or new equipment (either calc or input for each one [cost_pl_on_buy_equip_pv and cost_pl_on_owned_equip_pv]
- [ ] Adjust cost per litre for COC precomputation to include equipment costs as if the collection option is choosen, unitrans still need to pay for equipment themselves this doesnt only apply to the DEL)


**Customer Depot Tank Capacity**
- [ ] Must factor in customer depot tank capcity (UNITRANS PREFERS HAVING FUEL DELIVERED FOR CUSTOMER DEPOTS WITH SMALLER TANK CAPACITY)
  ---> use tank capacity per customer depot 
  ---> add reorder level for these customer tanks
  ---> BASICALLY IF CUSTOMER DEPOT TANK CAPACITY IS LOWER THAN TANKER CAPACITY THEN THIS FORMULA [trans_cost_pl = ((One_Way_Dist)(2)(tanker_cost_per_km))/tanker_cap] MUST USE THE (tank capacity - reorder level)


**Extras**
- [ ] Implement all unit vs incremental volume tiers 
- [ ] Check costs are calculated correctly for international depots
- [ ] Look at implementing (static VS dynamic) and/or (deterministic Vs stochastic) [eg. variable demand volume, variable fuel price etc...][look at stochastic programming and robust optimization]

**Constraints**
- [ ] Max number of customer supplier contracts 
- [ ] Implement, constraints that limit one supplier contract to one payment term(or some sort of constraint that is to do with payment term)
- [ ] Cross-boarder trade constraint or penalty









Could look at adding: 

- Nested `scope_filters`, `operational_rules`, `penalties`                         
- override_value`, `fallback_rebate` 

CHAT GPT RECOMMENDATION 

Modelling take-or-pay and clawbacks precisely

Some contracts don’t switch per-litre price; they charge a deficiency payment on shortfall: deficit = max{0, T_c − realized_volume} with penalty p_c · deficit. You can add a continuous variable d_c ≥ 0, constrain d_c ≥ T_c − Σ volume, and add p_c d_c to the objective. This often matches supplier invoices better than “RAC unit price on all litres.” Keep your RAC pricing path too—enable per-contract contract_type ∈ {clawback, rac_unit_price} so you can do either.