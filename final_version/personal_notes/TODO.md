

Equipment 
- Make sure config defines which suppliers actually have equipment finance and maintenance charges as an option. 
- Make sure config defines which customer depots already have equipment vs ones that want to buy equipment 
- make sure that for equipment cost is done per depot for owned or new equipment (either calc or input for each one)


- Must factor in customer depot tank capcity (UNITRANS PREFERS HAVING FUEL DELIVERED FOR CUSTOMER DEPOTS WITH SMALLER TANK CAPACITY)
  ---> use tank capacity per customer depot 
  ---> add reorder level for these customer tanks
  ---> BASICALLY IF CUSTOMER DEPOT TANK CAPACITY IS LOWER THAN TANKER CAPACITY THEN THIS FORMULA [trans_cost_pl = ((One_Way_Dist)(2)(tanker_cost_per_km))/tanker_cap] MUST USE THE (tank capacity - reorder level)

- Add equipment availability in the config for each customer depot... (for DEL options and might have to adjust to include COC options as well)


-Look at implementing (static VS dynamic) and/or (deterministic Vs stochastic) [eg. variable demand volume, variable fuel price etc...][look at stochastic programming and robust optimization]

- Implement all unit vs incremental volume tiers 


Could look at adding: 

- Nested `scope_filters`, `operational_rules`, `penalties`                         
- override_value`, `fallback_rebate` 



**Check costs are calculated correctly for international depots


CONSTRAINTS

- Max number of customer supplier contracts 
- Implement, constraints that limit one supplier contract to one payment term(or some sort of constraint that is to do with payment term)

- Cross-boarder trade constraint or penalty



CHAT GPT RECOMMENDATION 

Modelling take-or-pay and clawbacks precisely

Some contracts don’t switch per-litre price; they charge a deficiency payment on shortfall: deficit = max{0, T_c − realized_volume} with penalty p_c · deficit. You can add a continuous variable d_c ≥ 0, constrain d_c ≥ T_c − Σ volume, and add p_c d_c to the objective. This often matches supplier invoices better than “RAC unit price on all litres.” Keep your RAC pricing path too—enable per-contract contract_type ∈ {clawback, rac_unit_price} so you can do either.