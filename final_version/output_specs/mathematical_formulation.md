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
- **`y_c`** ∈ {0,1}: Binary variable indicating if contract `c` is activated
  - `c` ∈ C: Set of contracts (volume tier rewards and RAC contracts)

## Parameters

### Depot and Volume Data
- **`V_i`**: Annual fuel volume demand for customer depot `i` (litres)
- **`C_{i,j,o}`**: Cost per litre for allocating depot `i` to supplier depot `j` with option `o` (Rands/litre)

### Contract Parameters
- **`T_c`**: Volume threshold for contract `c` (litres)
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

### 2. Volume Tier Reward Contract Constraints

For each volume tier reward contract `c`:

**2a. Contract Activation Based on Volume Threshold:**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_vol^c} V_i × x_{i,j,o} ≥ T_c × y_c
```
Where `O_vol^c` = volume-contributing options for contract `c` (base options + tier options belonging to this contract)

**2b. Tier Options Require Contract Activation:**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_tier^c} x_{i,j,o} ≤ M × y_c
```
Where:
- `O_tier^c` = tier-enhanced options belonging to contract `c`
- `M` = big-M constant (maximum number of tier options)

### 3. Rebate Adjustment Clause (RAC) Contract Constraints

For each RAC contract `c`:

**3a. RAC Contract Activation Based on Volume Commitment:**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_base^c} V_i × x_{i,j,o} ≥ T_c × y_c
```
Where `O_base^c` = base options in relevant transport modes for contract `c`

**3b. RAC Penalty Application (Volume Commitment Not Met):**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_RAC^c} x_{i,j,o} ≤ M × (1 - y_c)
```

**3c. Base Options Forbidden When RAC Applies (Mutual Exclusion):**
```
Σ_{i∈I} Σ_{j∈S_c} Σ_{o∈O_base^c} x_{i,j,o} ≤ M × y_c
```
Where:
- `O_RAC^c` = RAC penalty options for contract `c`
- `O_base^c` = base options for contract `c`
- If volume commitment is met (`y_c = 1`): base options allowed, RAC options forbidden
- If volume commitment is not met (`y_c = 0`): base options forbidden, RAC options allowed
- **Ensures mutual exclusion**: prevents using cheaper base options when RAC penalties should apply

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
- **RAC Penalties**: `rac_coc_cash`, `rac_coc_30`, `rac_coc_45`, `rac_coc_60`, `rac_del_own`, `rac_del_buy`, `rac_del_rent`

### Volume Tier Enhanced Options
- **Tier Options**: e.g., `coc_30_tier_15M_to_20M`, `del_own_tier_20M_to_25M`
- Include base cost + volume tier rebate/discount

## Contract Logic Summary

### Volume Tier Rewards
- **Purpose**: Provide discounts when volume commitments are met
- **Logic**: If total volume (base + tier) ≥ threshold → tier options become available
- **Cost Effect**: Tier options typically have lower costs than base options
- **Volume Calculation**: Includes both base options and tier options to avoid circular dependency

### Rebate Adjustment Clause (RAC)  
- **Purpose**: Penalize failure to meet volume commitments
- **Logic**: If total base volume < threshold → RAC penalty options must be used (mutual exclusion enforced)
- **Cost Effect**: RAC options typically have higher costs than base options
- **Mutual Exclusion**: Base and RAC options cannot be used simultaneously for the same supplier contract

## Model Statistics
- **Variables**: ~8,833 allocation variables + contract variables
- **Constraints**: ~2,011 depot assignment + contract constraints + supplier depot capacity constraints
- **Problem Type**: Binary Integer Programming (BIP)
- **Solver**: IBM CPLEX via DOcplex API

## Implementation Notes

1. **Cost Precomputation**: All costs are calculated in `precomputation.py` including volume tier calculations and Present Value discounting

2. **Contract Mutual Exclusivity**: RAC and volume tier contracts can coexist but apply different logic for the same supplier relationships

3. **Big-M Constraints**: Used to model conditional logic where tier options are only available when volume commitments are met

4. **Volume Calculation Fix**: Volume tier contracts now count both base and tier allocations to prevent circular dependency where using tier options would disable tier eligibility

5. **RAC Mutual Exclusion**: Added constraint 3c to prevent simultaneous use of base and RAC options, ensuring proper penalty application when volume commitments are not met

6. **Granular Capacity Constraints**: Capacity limits applied at supplier depot level rather than supplier level to reflect real terminal throughput constraints

7. **Currency**: All costs in South African Rands (R), volumes in litres

8. **Optimization Goal**: Minimize total annual fuel procurement cost while satisfying all operational and contractual constraints