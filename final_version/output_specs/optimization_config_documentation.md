# Optimization Configuration Documentation

## Overview
The `optimization_config.json` file serves as the central configuration hub for the multi-objective depot supplier allocation optimizer. This file enables researchers and practitioners to model different business logic scenarios, contract structures, and operational constraints without modifying the underlying code. The configuration system supports complex real-world supply chain scenarios including volume tier rewards, rebate adjustment clauses, capacity constraints, and strategic supplier scoring.

## Configuration Structure

### 1. Basic Parameters (`basic_parameters`)

Core operational parameters that define the fundamental economics of the fuel supply system.

```json
"basic_parameters": {
    "fuel_type": "Diesel 0.005% sulfur",
    "wacc_percent": 12.5,
    "tanker_cost_per_km": 15.5,
    "tanker_capacity": 30000,
    "cost_owned_equip_pv": 0.05,
    "reorder_level": 0.30,
    "min_drop_litres": 0,
    "allow_multidrop": false,
    "min_expected_fill_ratio": 1.0
}
```

**Parameters:**
- **`fuel_type`**: Specification of fuel grade (used for database filtering)
- **`wacc_percent`**: Weighted Average Cost of Capital for present value calculations (percentage)
- **`tanker_cost_per_km`**: Transportation cost per kilometer for COC options (Rands)
- **`tanker_capacity`**: Maximum tanker capacity in litres (affects transport efficiency)
- **`cost_owned_equip_pv`**: Present value factor for owned equipment depreciation
- **`reorder_level`**: Inventory reorder threshold (0.30 = 30% of tank capacity)
- **`min_drop_litres`**: Minimum delivery volume per drop (0 = no minimum)
- **`allow_multidrop`**: Enable multiple customer deliveries per tanker trip
- **`min_expected_fill_ratio`**: Minimum tank fill ratio expected (1.0 = always fill to capacity)

**Business Impact:** These parameters directly affect cost calculations and operational feasibility. Adjusting `wacc_percent` changes present value discounting, while `tanker_cost_per_km` affects COC option competitiveness.

### 2. Present Value Settings (`present_value_settings`)

Defines payment terms for different cost components, crucial for accurate present value calculations in the South African fuel industry.

#### Base Rebate Terms
```json
"base_rebate_terms": {
    "COC_cash": 0,
    "COC_30": 30,
    "COC_45": 45,
    "COC_60": 60,
    "DEL_30": 30
}
```

**Configuration Options:**
- **`COC_cash`**: Cash payment terms for COC options (0 days)
- **`COC_30/45/60`**: Net payment terms for different COC contracts
- **`DEL_30`**: Standard NET30 terms for delivery options

#### Volume Tier Rebate Terms
```json
"volume_tier_rebate_terms": {
    "payment_days": 30
}
```

**Purpose:** Volume tier rewards typically follow NET30 payment terms regardless of base contract terms.

#### Delivery Option Terms
```json
"delivery_option_terms": {
    "del_rebate_terms": "NET30",
    "equipment_financing_terms": "NET30",
    "equipment_maintenance_terms": "NET30"
}
```

**Business Logic:** All delivery-related costs follow standardized NET30 terms to simplify supplier cash flow management.

### 3. International Fuel Prices (`international_fuel_prices`)

Cross-border pricing for regional operations (prices in Rands per litre).

```json
"international_fuel_prices": {
    "Botswana": 22,
    "Namibia": 20.09,
    "Mozambique": 22,
    "Eswatini": 20.29
}
```

**Application:** Used when customer depots are located outside South Africa. Enables modeling of regional fuel supply networks.

### 4. Supplier Contract Configurations (`supplier_contract_configurations`)

The most complex section, enabling modeling of different contract types and business relationships.

#### Contract Types

##### A. Rebate Adjustment Clause (RAC)
```json
"supplier_A_RAC": {
    "contract_type": "rebate_adjustment_clause",
    "suppliers": ["Supplier A"],
    "supplier_depots": ["*"],
    "transport_modes": ["COC", "DEL"],
    "commitment_threshold": 20000000,
    "coc_rebate": null,
    "del_rebate": null
}
```

**Parameters:**
- **`contract_type`**: Must be `"rebate_adjustment_clause"`
- **`suppliers`**: Array of supplier names affected
- **`supplier_depots`**: Specific depots or `["*"]` for all depots
- **`transport_modes`**: Which delivery modes are subject to RAC
- **`commitment_threshold`**: Minimum annual volume commitment (litres)
- **`coc_rebate/del_rebate`**: Set to `null` (rebates removed if commitment not met)

**Business Logic:** If total allocated volume falls below threshold, all rebates are removed, reverting to wholesale pricing.

##### B. Volume Tier Rewards
```json
"supplier_C_tiers": {
    "contract_type": "volume_tier_rewards",
    "suppliers": ["Supplier C"],
    "supplier_depots": ["*"],
    "transport_modes": ["COC", "DEL"],
    "volume_calculation_modes": ["COC", "DEL"],
    "tiering_regime": "all_units",
    "rebate_combination": "additive_to_base",
    "reward_bands": [...]
}
```

**Key Parameters:**
- **`volume_calculation_modes`**: Which transport modes count toward volume thresholds
- **`tiering_regime`**: 
  - `"all_units"`: All volume gets tier rebate once threshold reached
  - `"incremental"`: Only volume above threshold gets enhanced rebate
- **`rebate_combination`**: 
  - `"additive_to_base"`: `final_rebate = base_rebate + tier_rebate`
  - `"override_base"`: `final_rebate = tier_rebate` (replaces base rebate)

##### Reward Band Structure
```json
"reward_bands": [
    {
        "min_volume": 0,
        "max_volume": 15000000,
        "del_rebate": 0.00,
        "coc_rebate": 0.00
    },
    {
        "min_volume": 15000000,
        "max_volume": 20000000,
        "del_rebate": 0.50,
        "coc_rebate": 0.59
    }
]
```

**Band Configuration:**
- **`min_volume/max_volume`**: Volume thresholds (litres per annum)
- **`max_volume`**: Use `null` for unlimited upper band
- **`del_rebate/coc_rebate`**: Additional rebate in Rands per litre
- **`null` values**: Indicate unavailable options for that transport mode

### 5. Supplier Delivery Capabilities (`supplier_del_capabilities`)

Controls equipment rental availability for delivery options.

```json
"supplier_del_capabilities": {
    "Supplier A": {"offers_equipment_rental": false},
    "Supplier C": {"offers_equipment_rental": true}
}
```

**Impact:** Suppliers with `"offers_equipment_rental": false` cannot provide DEL options with rental equipment, limiting customer flexibility but reducing supplier capital requirements.

### 6. Country Allocation Constraints (`country_allocation_constraints`)

Defines cross-border supply restrictions for compliance and operational reasons.

```json
"country_allocation_constraints": {
    "enabled": true,
    "cross_border_restrictions": {
        "South Africa": {
            "allowed_destinations": ["South Africa", "Mozambique", "Botswana", "Namibia", "Eswatini"],
            "blocked_destinations": []
        }
    }
}
```

**Configuration Options:**
- **`enabled`**: Toggle constraint enforcement on/off
- **`allowed_destinations`**: Countries that can be supplied from this origin
- **`blocked_destinations`**: Explicit prohibition list (takes precedence)

**Business Logic:** Models regulatory restrictions, tax implications, and operational constraints in cross-border fuel supply.

### 7. Supplier Depot Capacity Limits (`supplier_depot_capacity_limits`)

Individual depot throughput constraints reflecting real-world terminal limitations.

```json
"supplier_depot_capacity_limits": {
    "1": 5250000,
    "2": 4200000,
    "61": 30000000
}
```

**Parameters:**
- **Key**: Supplier depot ID (as string)
- **Value**: Maximum annual capacity in litres

**Strategic Importance:** Prevents unrealistic allocations to high-capacity depots while forcing distribution across the supply network.

## Strategic Supplier Scoring Configuration

Strategic supplier scoring weights are stored in the database `criteria_weights` table and can be modified to reflect different strategic priorities.

**Current Criteria Weights:**
- **Current Level (1-8)**: 20% - Existing business relationship strength
- **Product/Service Type**: 15% - Compatibility of supplier offerings
- **Geographical Network**: 15% - Supplier's geographic coverage
- **Method of Sourcing**: 15% - Sourcing approach alignment
- **Investment in Refuelling Equipment**: 10% - Capital investment commitment
- **Reciprocal Business**: 25% - Mutual business relationship value

**Modification:** Update weights in database to reflect different strategic priorities for multi-objective optimization.

## Configuration Use Cases

### Scenario 1: Cost-Only Optimization
- Set all volume tier configurations to minimal rewards
- Disable strategic scoring weights (set all to 0)
- Focus purely on cost minimization

### Scenario 2: Strategic Partnership Emphasis
- Increase "Reciprocal Business" and "Current Level" weights
- Add aggressive volume tier rewards for preferred suppliers
- Enable cross-border restrictions to favor domestic suppliers

### Scenario 3: Capacity Stress Testing
- Reduce `supplier_depot_capacity_limits` by 50%
- Increase `commitment_threshold` values
- Test network resilience under capacity constraints

### Scenario 4: Regional Network Optimization
- Enable `country_allocation_constraints`
- Set different `international_fuel_prices`
- Model regional supply chain efficiency

## Mathematical Integration

The configuration directly influences the optimization model:

**Cost Calculation:**
```
total_cost = Σ(volume × cost_per_litre × binary_variable)
```

Where `cost_per_litre` incorporates:
- Base wholesale price with rebates
- Present value adjustments based on payment terms
- Volume tier enhancements or RAC penalties
- Transportation and equipment costs

**Strategic Score Integration:**
```
strategic_objective = Σ(strategic_score × binary_variable)
```

**Multi-Objective Formulation:**
- **Cost-only**: `minimize total_cost`
- **Strategic-only**: `maximize strategic_objective`
- **Weighted**: `minimize (1-w) × total_cost - w × strategic_objective`
- **ε-constraint**: `minimize total_cost subject to strategic_objective ≥ ε`

## Validation and Testing

**Configuration Validation:**
- JSON schema compliance
- Supplier name consistency with database
- Volume threshold logical ordering
- Rebate value non-negativity

**Business Rule Testing:**
- Volume tier activation logic
- RAC penalty application
- Capacity constraint binding
- Cross-border allocation compliance

## Best Practices for Thesis Research

1. **Document Configuration Changes**: Record all parameter modifications for methodology transparency
2. **Sensitivity Analysis**: Test key parameters across reasonable ranges
3. **Business Logic Validation**: Ensure configurations reflect realistic industry practices
4. **Scenario Comparison**: Use different configurations to demonstrate model flexibility
5. **Performance Monitoring**: Track solution times across different configuration complexities

This configuration system enables comprehensive modeling of South African fuel supply chain dynamics while maintaining academic rigor and practical applicability.