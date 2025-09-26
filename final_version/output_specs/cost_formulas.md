# Fuel Depot Allocation - Cost Calculation Formulas

## Overview
This document details all cost calculation formulas used in the fuel depot allocation optimizer precomputation module. All costs are calculated in South African Rands (R) per litre and include Present Value (PV) discounting for different payment terms.

## Basic Parameters

### Present Value Factors
- **WACC**: Weighted Average Cost of Capital (from config: `wacc_percent`)
- **Annual Rate**: `wacc_decimal = wacc_percent / 100`
- **PV Factors**:
  - `pv_cash = 1.0` (no discounting)
  - `pv_net30 = (1 + wacc_decimal/365) ^ 30`
  - `pv_net45 = (1 + wacc_decimal/365) ^ 45` 
  - `pv_net60 = (1 + wacc_decimal/365) ^ 60`

### Transport Cost (COC Only)
```
transport_cost_per_litre = (distance_km × 2 × tanker_cost_per_km) / tanker_capacity
```
Where:
- `distance_km`: One-way distance from customer depot to supplier depot
- `tanker_cost_per_km`: Cost per kilometer for tanker operation (from config)
- `tanker_capacity`: Tanker capacity in litres (from config)

### Fuel Pricing
- **South African Depots**: `rtl_wholesale_per_litre = rtl_wholesale_cents / 100`
- **International Depots**: `rtl_wholesale_per_litre = country_price` (from config)

## Base Cost Calculations

### COC (Customer Own Collection) Options

#### COC Cash (Immediate Payment)
```
coc_cash_cost_pv = (rtl_wholesale_per_litre - COC_reb_pl_cash) + transport_cost_per_litre + cost_owned_equip_pv
```
- No PV discounting applied to fuel cost
- Includes customer-owned equipment cost (already in PV terms)
- Available only where `COC_Valid_FK IS NOT NULL` and `COC_reb_pl_cash IS NOT NULL`

#### COC NET30 (30-Day Payment)
```
coc_30_cost_pv = ((rtl_wholesale_per_litre - COC_reb_pl_30) / pv_net30) + transport_cost_per_litre + cost_owned_equip_pv
```
- Fuel cost discounted by NET30 PV factor
- Transport cost and equipment cost not discounted (immediate costs)

#### COC NET45 (45-Day Payment)
```
coc_45_cost_pv = ((rtl_wholesale_per_litre - COC_reb_pl_45) / pv_net45) + transport_cost_per_litre + cost_owned_equip_pv
```

#### COC NET60 (60-Day Payment)
```
coc_60_cost_pv = ((rtl_wholesale_per_litre - COC_reb_pl_60) / pv_net60) + transport_cost_per_litre + cost_owned_equip_pv
```

### DEL (Supplier Delivery) Options
All DEL options use NET30 payment terms for fuel costs.

#### DEL Own Equipment
```
del_own_cost_pv = ((rtl_wholesale_per_litre - (DEL_reb_pl_30 + equip_fin_pl_30 + equip_main_pl_30)) / pv_net30) + 
                  cost_owned_equip_pv 
```
Where:
- `DEL_reb_pl_30`: Base delivery rebate (NET30 terms)
- `equip_fin_pl_30`: Equipment financing rebate (NET30 terms)
- `equip_main_pl_30`: Equipment maintenance rebate (NET30 terms)
- `cost_owned_equip_pv`: User-specified owned equipment cost (already in PV terms)

**Note**: No delivery fees are applied in the current implementation.

#### DEL Rent Equipment
```
del_rent_cost_pv = ((rtl_wholesale_per_litre - DEL_reb_pl_30) / pv_net30)
```
- No equipment financing/maintenance rebates for rental option
- No additional equipment costs
- No delivery fees applied in current implementation

## RAC (Rebate Adjustment Clause) Penalty Costs
RAC costs apply when volume commitments are not met. They use wholesale pricing without rebates plus transport/equipment costs.

### RAC COC Options
**Note**: RAC costs are calculated ONLY for NET30 terms as per specifications.

#### RAC COC NET30
```
rac_coc_30_cost_pv = (rtl_wholesale_per_litre / pv_net30) + transport_cost_per_litre + cost_owned_equip_pv
```
- No rebates applied (penalty pricing)
- Includes customer-owned equipment cost
- Only RAC option available - other payment terms not supported for RAC

### RAC DEL Options
RAC DEL uses transport charges from delivery options table and are calculated ONLY for NET30 terms.

#### RAC DEL Own Equipment
```
rac_del_own_cost_pv = ((rtl_wholesale_per_litre + transport_charge_excl_zone) / pv_net30) + cost_owned_equip_pv
```

#### RAC DEL Rent Equipment
```
rac_del_rent_cost_pv = ((rtl_wholesale_per_litre + transport_charge_excl_zone + equip_fin_pl_30 + equip_main_pl_30) / pv_net30)
```

Where:
- `transport_charge_excl_zone`: "TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF" from delivery_options table
- All RAC DEL options use NET30 payment terms only

## Volume Tier Enhanced Costs
Volume tier enhanced costs apply additional rebates when volume commitments are met. These are generated dynamically from `supplier_contract_configurations` where `contract_type` is `"volume_tier_rewards"`.

**Implementation supports both combination rules**:
- **"additive_to_base"**: Volume tier rebate is added to base rebate (Supplier C)
- **"override_base"**: Volume tier rebate replaces base rebate entirely (Supplier I)

**Processing Logic**:
1. Iterate through each contract configuration with `contract_type` = `"volume_tier_rewards"`
2. Filter suppliers by name matching `suppliers` list in config
3. Check transport modes (`COC` and/or `DEL`) from `transport_modes` field
4. Process each reward band with non-zero rebate values
5. Apply appropriate combination rule (`rebate_combination` field)
6. Generate dynamic column names using volume thresholds

### Volume Tier COC Options
**Note**: Volume tier enhanced costs are calculated ONLY for NET30 terms as per specifications.

#### COC NET30 with Volume Tier

**Additive to Base (`"additive_to_base"`)** - Used by Supplier C:
```
coc_30_tier_X = ((rtl_wholesale_per_litre - (COC_reb_pl_30 + coc_tier_rebate)) / pv_net30) + transport_cost_per_litre + cost_owned_equip_pv
```

**Override Base (`"override_base"`)** - Used by Supplier I:
```
coc_30_tier_X = ((rtl_wholesale_per_litre - coc_tier_rebate) / pv_net30) + transport_cost_per_litre + cost_owned_equip_pv
```

Where:
- `coc_tier_rebate`: Volume tier rebate from reward band (R/litre)
- All volume tier enhanced costs use NET30 payment terms only
- Combination rule specified in contract configuration

### Volume Tier DEL Options

#### DEL Own Equipment with Volume Tier

**Additive to Base (`"additive_to_base"`)** - Used by Supplier C:
```
del_own_tier_X = ((rtl_wholesale_per_litre - (DEL_reb_pl_30 + del_tier_rebate + equip_fin_pl_30 + equip_main_pl_30)) / pv_net30) + 
                 cost_owned_equip_pv 
```

**Override Base (`"override_base"`)** - Used by Supplier I:
```
del_own_tier_X = ((rtl_wholesale_per_litre - (del_tier_rebate + equip_fin_pl_30 + equip_main_pl_30)) / pv_net30) + 
                 cost_owned_equip_pv 
```
- Equipment rebates (`equip_fin_pl_30`, `equip_main_pl_30`) are preserved in override mode

#### DEL Rent Equipment with Volume Tier

**Additive to Base (`"additive_to_base"`)** - Used by Supplier C:
```
del_rent_tier_X = ((rtl_wholesale_per_litre - (DEL_reb_pl_30 + del_tier_rebate)) / pv_net30)
```

**Override Base (`"override_base"`)** - Used by Supplier I:
```
del_rent_tier_X = ((rtl_wholesale_per_litre - del_tier_rebate) / pv_net30)
```
- No equipment costs for rental option in either mode

Where:
- `del_tier_rebate`: Volume tier rebate from reward band (R/litre)
- `X`: Tier band identifier (e.g., "15M_to_20M", "20M_plus")
- Combination rule specified in contract configuration 

## Volume Tier Band Naming Convention
Tier options are named using the pattern:
- `{base_option}_tier_{min_volume}M_to_{max_volume}M` (e.g., `coc_30_tier_15M_to_20M`)
- `{base_option}_tier_{min_volume}M_plus` (e.g., `del_own_tier_25M_plus`)

**Implementation Details**:
- Generated dynamically from `reward_bands` in supplier contract configurations
- Volume thresholds divided by 1,000,000 to create "M" (million) suffix
- Band suffix created using: `f"_{min_volume//1000000}M_to_{max_volume//1000000}M"`
- For unlimited tiers: `f"_{min_volume//1000000}M_plus"`

**Current Configuration Examples**:
- **Supplier C**: 15M_to_20M, 20M_to_25M, 25M_plus (additive_to_base)
- **Supplier I**: 10M_to_20M, 20M_to_30M, 30M_plus (override_base, DEL only)

## Availability Rules

### COC Options
- Available only where `COC_Valid_FK IS NOT NULL`
- Requires non-null rebate values for respective payment terms
- Transport cost calculated for all COC options

### DEL Options  
- Available only where `DEL_Valid_FK IS NOT NULL`
- DEL Own requires non-null `equip_fin_pl_30` and `equip_main_pl_30`
- DEL Rent requires only non-null `DEL_reb_pl_30`
- **Equipment Rental Availability**: DEL Rent options are additionally filtered by `supplier_del_capabilities` configuration
  - Only suppliers with `"offers_equipment_rental": true` will have del_rent options generated
  - Suppliers with `"offers_equipment_rental": false` only offer DEL Own Equipment (customer-owned equipment)
  - Default behavior: If supplier not listed in config, rental is assumed to be unavailable (fail-safe)
- **Defensive Filtering**: Cost dictionary building includes additional rental availability checks to ensure business rules are enforced
- No delivery fees currently implemented in the code

### RAC Options
- Only calculated for suppliers with `rebate_adjustment_clause` contracts
- Available for same depot-supplier combinations as base options
- Use penalty pricing (no rebates)
- RAC DEL Rent options additionally filtered by supplier rental availability (same rules as base DEL Rent)

### Volume Tier Options
- Only calculated for suppliers matching `supplier_contract_configurations` where `contract_type` is `"volume_tier_rewards"`
- Filtered by supplier name matching `suppliers` list in contract configuration
- Transport modes filtered by `transport_modes` list (`COC` and/or `DEL`)
- Only reward bands with non-zero rebate values are processed
- Volume tier activation requires meeting minimum volume commitments in optimization
- **DEL Rent Tier Options**: Additionally filtered by supplier rental availability (same rules as base DEL Rent)
- **Current Implementation**: Supports both `"additive_to_base"` and `"override_base"` combination rules
- **Supplier-Specific Rules**:
  - Supplier C: `additive_to_base` for COC and DEL
  - Supplier I: `override_base` for DEL only

## Configuration Dependencies

### From `optimization_config.json`
- `basic_parameters.wacc_percent`: WACC percentage for PV calculations
- `basic_parameters.tanker_cost_per_km`: Transport cost per kilometer
- `basic_parameters.tanker_capacity`: Tanker capacity in litres
- `basic_parameters.cost_owned_equip_pv`: Owned equipment cost (PV terms)
- `international_fuel_prices`: Pricing for international depots
- `supplier_contract_configurations`: Volume tier and RAC contract definitions
- `supplier_del_capabilities`: Equipment rental availability per supplier (boolean `offers_equipment_rental` field)

## Strategic Supplier Scoring Integration

### Multi-Criteria Evaluation Formula
Strategic supplier scores are calculated using a weighted multi-criteria evaluation system:

```
strategic_score_s = ∑_{c∈Criteria} (criterion_value_{s,c} × weight_c)
```

Where:
- `s`: Supplier identifier (not individual depot)
- `c`: Evaluation criteria (6 dimensions)  
- `criterion_value_{s,c}`: Normalized score [0.0, 1.0] for supplier s on criterion c
- `weight_c`: Weight for criterion c from database configuration

**Important**: Strategic scores are calculated at the supplier level. All depots belonging to the same supplier share the same strategic score.

### Strategic Scoring Criteria (6 Dimensions)

#### 1. Current Level (1-8)
- **Definition**: Supplier relationship maturity level on 8-point scale
- **Range**: 1 (new/basic relationship) to 8 (strategic partnership)
- **Business Impact**: Higher levels indicate stronger, more reliable partnerships

#### 2. Product/Service Type
- **Definition**: Alignment of supplier service offerings with operational requirements
- **Assessment**: Compatibility of supplier capabilities with business needs
- **Business Impact**: Better alignment reduces operational risk and improves service quality

#### 3. Geographical Network
- **Definition**: Distribution coverage and logistics capability across service territories
- **Assessment**: Network reach, depot locations, and distribution infrastructure
- **Business Impact**: Broader networks provide better coverage and backup options

#### 4. Method of Sourcing
- **Definition**: Supply chain approach and sourcing methodology employed by supplier
- **Assessment**: Direct sourcing, integrated supply chains, procurement practices
- **Business Impact**: More sophisticated sourcing methods often provide cost and reliability advantages

#### 5. Investment in Refuelling Equipment
- **Definition**: Infrastructure commitment and refuelling capability at supplier facilities
- **Assessment**: Equipment quality, capacity, technological advancement, maintenance standards
- **Business Impact**: Higher investment levels indicate commitment and operational capability

#### 6. Reciprocal Business
- **Definition**: Mutual business relationship strength and bi-directional value creation
- **Assessment**: Joint initiatives, shared investments, collaborative partnerships
- **Business Impact**: Stronger reciprocal relationships provide strategic advantages and risk mitigation

### Strategic Score Properties
- **Score Range**: [0.0, 1.0] normalized scores per supplier (shared by all supplier depots)
- **Aggregation Method**: Linear weighted sum across all criteria
- **Granularity**: Supplier-level scoring (not per individual depot)
- **Data Source**: Multi-criteria weighted evaluation from database tables:
  - `supplier_scores`: Individual criterion scores per supplier
  - `criteria_weights`: Configurable weights per criterion
- **Update Frequency**: Static during optimization run, configurable between runs

### Integration in Multi-Objective Optimization

#### Precomputation Integration
Strategic scores are integrated during the cost calculation pipeline:

```python
# Integration point in precomputation.py
def _add_strategic_scores_to_cost_dict(self, cost_dict: Dict):
    from strategic_supplier_scoring import StrategicSupplierScoring
    scoring = StrategicSupplierScoring(self.db_path)
    
    for depot_id in cost_dict:
        for supplier_depot_id in cost_dict[depot_id]:
            supplier_name = cost_dict[depot_id][supplier_depot_id].get('supplier_name')
            if supplier_name:
                # Same supplier-level score assigned to all depots of this supplier
                strategic_score = scoring.calculate_supplier_strategic_score(supplier_name)
                cost_dict[depot_id][supplier_depot_id]['strategic_score'] = strategic_score
```

**Granularity Consideration**: The current implementation assigns the same strategic score to all depots belonging to the same supplier. This may lose fidelity if depot-specific characteristics (e.g., terminal infrastructure quality, local management effectiveness, geographical advantages) vary significantly within a supplier's network. Future extensions could implement depot-level strategic scoring if such granular data becomes available.

#### Multi-Objective Optimization Modes
Strategic scores enable three distinct optimization approaches:

1. **Cost-Only**: `minimize ∑ cost_terms` (traditional single-objective)
2. **Strategic-Only**: `maximize ∑ strategic_score_terms`  
3. **ε-Constraint**: `minimize cost subject to strategic_score ≥ ε` (preferred for trade-off analysis)

#### Business Applications
- **Trade-off Analysis**: Quantify cost impact of strategic supplier preferences
- **Pareto Front Generation**: Identify efficient cost vs. strategic score solutions
- **Policy Analysis**: Evaluate impact of strategic supplier requirements on total costs
- **Risk Management**: Balance cost optimization with supplier relationship quality

### From Database
- `rtl_wholesale`: Wholesale fuel prices (cents/litre for SA, R/litre for international)
- `COC_reb_pl_*`: COC rebates for different payment terms
- `DEL_reb_pl_30`: Base delivery rebate (NET30 terms)
- `equip_fin_pl_30`, `equip_main_pl_30`: Equipment-related rebates
- `One_Way_Dist`: Distance for transport cost calculations

## Business Rules Summary

1. **Present Value Discounting**: Applied to fuel costs based on payment terms, not to transport/equipment costs
2. **RAC Logic**: Penalty pricing when volume commitments not met (higher costs)
3. **Volume Tier Logic**: Reward pricing when volume commitments met (lower costs)
4. **Payment Terms**: COC supports multiple payment terms, DEL is always NET30
5. **Equipment Options**: DEL has two equipment scenarios (own, rent) with different cost structures
6. **Equipment Rental Availability**: DEL rent options only available for suppliers configured as offering rental equipment
7. **Volume Tier Processing**: Generated dynamically from supplier contract configurations with reward bands
8. **Combination Rules**: Both "additive_to_base" and "override_base" fully implemented and tested
9. **Supplier-Specific Logic**: Different suppliers use different combination rules as configured
10. **Defensive Filtering**: Multiple layers of rental availability checking (calculation, validation, dictionary building)
11. **Currency**: All calculations in South African Rands, input prices converted from cents where needed
12. **Multi-Objective Integration**: Strategic supplier scores integrated during precomputation for multi-objective optimization