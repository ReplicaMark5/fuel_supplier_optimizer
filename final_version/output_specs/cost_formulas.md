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
coc_cash_cost_pv = (rtl_wholesale_per_litre - COC_reb_pl_cash) + transport_cost_per_litre
```
- No PV discounting applied
- Available only where `COC_Valid_FK IS NOT NULL` and `COC_reb_pl_cash IS NOT NULL`

#### COC NET30 (30-Day Payment)
```
coc_30_cost_pv = ((rtl_wholesale_per_litre - COC_reb_pl_30) / pv_net30) + transport_cost_per_litre
```
- Fuel cost discounted by NET30 PV factor
- Transport cost not discounted (immediate cost)

#### COC NET45 (45-Day Payment)
```
coc_45_cost_pv = ((rtl_wholesale_per_litre - COC_reb_pl_45) / pv_net45) + transport_cost_per_litre
```

#### COC NET60 (60-Day Payment)
```
coc_60_cost_pv = ((rtl_wholesale_per_litre - COC_reb_pl_60) / pv_net60) + transport_cost_per_litre
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

#### DEL Buy Equipment  
```
del_buy_cost_pv = ((rtl_wholesale_per_litre - (DEL_reb_pl_30 + equip_fin_pl_30 + equip_main_pl_30)) / pv_net30) + 
                  cost_buy_equip_pv 
```

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
rac_coc_30_cost_pv = (rtl_wholesale_per_litre / pv_net30) + transport_cost_per_litre
```
- No rebates applied (penalty pricing)
- Only RAC option available - other payment terms not supported for RAC

### RAC DEL Options
RAC DEL uses transport charges from delivery options table and are calculated ONLY for NET30 terms.

#### RAC DEL Own Equipment
```
rac_del_own_cost_pv = ((rtl_wholesale_per_litre + transport_charge_excl_zone) / pv_net30) + cost_owned_equip_pv
```

#### RAC DEL Buy Equipment
```
rac_del_buy_cost_pv = ((rtl_wholesale_per_litre + transport_charge_excl_zone) / pv_net30) + cost_buy_equip_pv
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
coc_30_tier_X = ((rtl_wholesale_per_litre - (COC_reb_pl_30 + coc_tier_rebate)) / pv_net30) + transport_cost_per_litre 
```

**Override Base (`"override_base"`)** - Used by Supplier I:
```
coc_30_tier_X = ((rtl_wholesale_per_litre - coc_tier_rebate) / pv_net30) + transport_cost_per_litre 
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

#### DEL Buy Equipment with Volume Tier

**Additive to Base (`"additive_to_base"`)** - Used by Supplier C:
```
del_buy_tier_X = ((rtl_wholesale_per_litre - (DEL_reb_pl_30 + del_tier_rebate + equip_fin_pl_30 + equip_main_pl_30)) / pv_net30) + 
                 cost_buy_equip_pv 
```

**Override Base (`"override_base"`)** - Used by Supplier I:
```
del_buy_tier_X = ((rtl_wholesale_per_litre - (del_tier_rebate + equip_fin_pl_30 + equip_main_pl_30)) / pv_net30) + 
                 cost_buy_equip_pv 
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
- DEL Own/Buy require non-null `equip_fin_pl_30` and `equip_main_pl_30`
- DEL Rent requires only non-null `DEL_reb_pl_30`
- No delivery fees currently implemented in the code

### RAC Options
- Only calculated for suppliers with `rebate_adjustment_clause` contracts
- Available for same depot-supplier combinations as base options
- Use penalty pricing (no rebates)

### Volume Tier Options
- Only calculated for suppliers matching `supplier_contract_configurations` where `contract_type` is `"volume_tier_rewards"`
- Filtered by supplier name matching `suppliers` list in contract configuration
- Transport modes filtered by `transport_modes` list (`COC` and/or `DEL`)
- Only reward bands with non-zero rebate values are processed
- Volume tier activation requires meeting minimum volume commitments in optimization
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
- `basic_parameters.cost_buy_equip_pv`: Buy equipment cost (PV terms)
- `international_fuel_prices`: Pricing for international depots
- `supplier_contract_configurations`: Volume tier and RAC contract definitions

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
5. **Equipment Options**: DEL has three equipment scenarios (own, buy, rent) with different cost structures
6. **Volume Tier Processing**: Generated dynamically from supplier contract configurations with reward bands
7. **Combination Rules**: Both "additive_to_base" and "override_base" fully implemented and tested
8. **Supplier-Specific Logic**: Different suppliers use different combination rules as configured
9. **Currency**: All calculations in South African Rands, input prices converted from cents where needed