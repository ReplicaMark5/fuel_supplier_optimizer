# Fuel Depot Allocation Optimizer - Mathematical Formulation

## Problem Overview
The fuel depot allocation optimizer is a binary integer programming problem that minimizes total fuel supply costs while satisfying depot demand, volume tier contract requirements, rebate adjustment clauses, and supplier capacity constraints.

## Decision Variables

### Primary Allocation Variables
- **`x_{i,j,o}`** ∈ {0,1}: Binary variable indicating if customer depot `i` is allocated to supplier depot `j` using option `o`
  - `i` ∈ I: Set of customer depots
  - `j` ∈ J: Set of supplier depots  
  - `o` ∈ O: Set of cost options (base, RAC, and volume tier enhanced options)

### Contract Activation Variables
- **`y_c`** ∈ {0,1}: Binary variable indicating if RAC contract `c` is activated
  - `c` ∈ C_RAC: Set of RAC contracts
- **`z_{c,b}`** ∈ {0,1}: Binary variable indicating if tier band `b` in volume tier contract `c` is activated
  - `c` ∈ C_VTR: Set of volume tier reward contracts
  - `b` ∈ B_c: Set of tier bands for contract `c`

## Parameters

### Depot and Volume Data
- **`V_i`**: Annual fuel volume demand for customer depot `i` (litres)
- **`C_{i,j,o}`**: Cost per litre for allocating depot `i` to supplier depot `j` with option `o` (Rands/litre)

### Contract Parameters
- **`T_c`**: Volume threshold for RAC contract `c` (litres)
- **`T_{c,b}`**: Minimum volume threshold for tier band `b` in volume tier contract `c` (litres)
- **`T^{max}_{c,b}`**: Maximum volume threshold for tier band `b` in volume tier contract `c` (litres, optional)
- **`L_j`**: Capacity limit for supplier depot `j` (litres)

### Sets and Mappings
- **`S_c`**: Set of supplier depots participating in contract `c`
- **`M_c`**: Set of transport modes covered by contract `c`
- **`σ(j)`**: Supplier associated with supplier depot `j`
- **`μ(o)`**: Transport mode of option `o` (COC or DEL)

## Objective Function

**Minimize total annual fuel cost:**

```
min Σ_{i∈I} Σ_{j∈J} Σ_{o∈O} V_i × C_{i,j,o} × x_{i,j,o}
```

Where:
- All costs `C_{i,j,o}` are precomputed and include:
  - Base costs (COC: cash, NET30, NET45, NET60; DEL: own, buy, rent)
  - RAC penalty costs (when volume commitments not met)
  - Volume tier enhanced costs (base + tier rebates)

## Constraints

### 1. Depot Assignment Constraint
Each customer depot must be allocated to exactly one supplier depot with one cost option:

```
Σ_{j∈J} Σ_{o∈O} x_{i,j,o} = 1    ∀i ∈ I
```

### 2. Volume Tier Reward Contract Constraints (Multi-Band Tier Gating)

For each volume tier reward contract `c` and each tier band `b`:

**2a. Tier Band Activation Based on Volume Threshold:**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_vol^c} V_i × x_{i,j,o} ≥ T_{c,b} × z_{c,b}
```
Where:
- `O_vol^c` = volume-contributing options for contract `c` (base options excluding RAC + tier options belonging to this contract)
- `T_{c,b}` = minimum volume threshold for tier band `b`
- Includes both base and tier allocations to prevent circular dependency

**2b. Tier Band Options Require Band Activation:**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_tier^{c,b}} x_{i,j,o} ≤ M_b × z_{c,b}
```
Where:
- `O_tier^{c,b}` = tier-enhanced options belonging specifically to tier band `b` of contract `c`
- `M_b` = big-M constant (number of tier options in band `b`)
- **Key Difference**: Each tier band can only be used if its specific volume threshold is met

### 3. Rebate Adjustment Clause (RAC) Contract Constraints

For each RAC contract `c`:

**3a. RAC Contract Activation Based on Volume Commitment:**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_base^c} V_i × x_{i,j,o} ≥ T_c × y_c
```
Where `O_base^c` = base options (excluding RAC and tier options) in relevant transport modes for contract `c`

**3b. RAC Penalty Enforcement (Volume Commitment Not Met):**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_RAC^c} x_{i,j,o} ≤ M × (1 - y_c)
```

**3c. Base Options Require Contract Fulfillment (Mutual Exclusion):**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_base^c} x_{i,j,o} ≤ M × y_c
```
Where:
- `O_RAC^c` = RAC penalty options for contract `c` (NET30 terms only)
- `O_base^c` = base options for contract `c` in RAC transport modes
- `M` = big-M constant (implementation: `len(rac_option_vars + base_option_vars)`)
- **Mutual Exclusion Logic**:
  - If `y_c = 1` (commitment met): base options allowed, RAC options forbidden
  - If `y_c = 0` (commitment not met): base options forbidden, RAC options required

### 4. Supplier Depot Capacity Constraints

For each supplier depot `j`:

```
Σ_{i∈I} Σ_{o∈O} V_i × x_{i,j,o} ≤ L_j
```

Total volume allocated to supplier depot `j` cannot exceed its individual capacity limit. This reflects real-world terminal constraints such as:
- Storage tank capacity limits
- Loading bay throughput constraints  
- Pipeline/rail delivery capacity limits
- Operational hour restrictions

## Option Types and Cost Structure

### Base Options
- **COC (Customer Own Collection)**: `coc_cash`, `coc_30`, `coc_45`, `coc_60`
- **DEL (Supplier Delivery)**: `del_own`, `del_buy`, `del_rent`

### RAC Options  
- **RAC Penalties**: `rac_coc_30`, `rac_del_own`, `rac_del_buy`, `rac_del_rent` (NET30 terms only)

### Volume Tier Enhanced Options
- **Tier Options**: e.g., `coc_30_tier_15M_to_20M`, `del_own_tier_20M_to_25M`
- Include base cost + volume tier rebate/discount

## Contract Logic Summary

### Volume Tier Rewards (Multi-Band Gating)
- **Purpose**: Provide progressive discounts based on volume bands
- **Logic**: Each tier band has independent activation based on its specific volume threshold
  - Example: 15M volume activates only 15M-20M tier, not 25M+ tier
- **Cost Effect**: Higher tier bands typically have better rebates/lower costs than lower bands
- **Volume Calculation**: Shared volume calculation across all bands to prevent gaming
- **Multi-Band Logic**: Prevents premature access to higher-tier benefits

### Rebate Adjustment Clause (RAC)  
- **Purpose**: Penalize failure to meet volume commitments
- **Logic**: If total base volume < threshold → RAC penalty options must be used (mutual exclusion enforced)
- **Cost Effect**: RAC options typically have higher costs than base options
- **Mutual Exclusion**: Base and RAC options cannot be used simultaneously for the same supplier contract

## Model Statistics (Updated for Multi-Band Gating)
- **Allocation Variables**: 10,908 binary variables for depot-supplier-option allocations
- **RAC Contract Variables**: 1 binary variable for RAC contract activation
- **Tier Band Variables**: 6 binary variables for individual tier band activation (3 bands × 2 contracts)
- **Total Binary Variables**: 10,915 variables
- **Total Cost Options**: 26,996 precomputed cost options across all scenarios
- **Depot-Supplier Combinations**: 2,011 feasible combinations
- **Option Types**: 32 total (7 base + 4 RAC + 21 volume tier enhanced options)
- **Constraints**: ~60 depot assignment + 18 tier band constraints + 6 RAC constraints + 75 capacity constraints = 159 total
- **Problem Type**: Binary Integer Programming (BIP)
- **Solver**: IBM CPLEX via DOcplex API

## Implementation Notes

1. **Cost Precomputation**: All costs are calculated in `precomputation.py` including volume tier calculations and Present Value discounting

2. **Contract Mutual Exclusivity**: RAC and volume tier contracts can coexist but apply different logic for the same supplier relationships

3. **Big-M Constraints**: Used to model conditional logic where tier options are only available when volume commitments are met

4. **Volume Calculation Fix**: Volume tier contracts count both base and tier allocations to prevent circular dependency where using tier options would disable tier eligibility

5. **Multi-Band Tier Gating**: **CRITICAL FIX** - Replaced single contract variables with per-band variables to prevent premature access to higher tiers:
   - Each tier band (15M-20M, 20M-25M, 25M+) has its own binary activation variable
   - 15M volume can only activate 15M-20M tier options, not 25M+ tier options
   - Prevents optimizer from accessing unrealistic cost savings
   - Maintains business logic compliance with progressive volume tier requirements

6. **RAC Mutual Exclusion**: Added constraint 3c to prevent simultaneous use of base and RAC options, ensuring proper penalty application when volume commitments are not met

6. **Granular Capacity Constraints**: Capacity limits applied at supplier depot level rather than supplier level to reflect real terminal throughput constraints

7. **Currency**: All costs in South African Rands (R), volumes in litres

8. **Optimization Goal**: Minimize total annual fuel procurement cost while satisfying all operational and contractual constraints