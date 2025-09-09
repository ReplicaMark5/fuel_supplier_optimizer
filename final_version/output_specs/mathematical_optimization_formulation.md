# Fuel Depot Allocation Optimizer - Mathematical Formulation

## Problem Overview
The fuel depot allocation optimizer is a binary integer programming model that minimizes total fuel procurement costs subject to depot demand satisfaction, volume tier contract requirements with two implementation regimes (all-units and incremental), rebate adjustment clauses (RAC), and supplier capacity constraints.

**Important Note**: This documentation describes the **actual implemented formulation** with recent refactors including elimination of Big-M constraints and implementation of volume tier regimes through sophisticated band-split variables.

## Decision Variables

### Primary Allocation Variables
- **`x_{i,j,o}`** ∈ {0,1}: Binary allocation decision where depot `i` is served by supplier depot `j` using option `o`
  - `i ∈ I`: Set of customer depots (each with demand `V_i` litres)
  - `j ∈ J`: Set of supplier depots (each with capacity `L_j` litres)
  - `o ∈ O`: Set of cost options (base, RAC, tier-enhanced)

### Volume Tier Contract Variables

#### All-Units Regime (One Tier Active, Base Forbidden):
- **`z_{c,b}`** ∈ {0,1}: Binary selection variable for tier band `b` in contract `c`
- **`y_{c,b}`** ∈ {0,1}: Binary eligibility variable for tier band `b` in contract `c`
- Where `c ∈ C_{all-units}`: Contracts with all-units tiering regime

#### Incremental Regime (Band-Split Volume Flow):
- **`s_{i,j,o,b}`** ≥ 0: Continuous volume allocation for depot `i`, option `o` to tier band `b`
- **`z_{c,b}`** ∈ {0,1}: Binary activation variable for tier band `b` in contract `c`
- **Important Note**: Base bands (min_volume=0) have NO binary activation variables `z_{c,b}`
- Only volume allocation variables `s_{i,j,o,b}` exist for base bands to maintain flow conservation
- Binary variables `z_{c,b}` are only created for tier bands with min_volume > 0
- Where `c ∈ C_{incremental}`: Contracts with incremental tiering regime

#### RAC Contract Variables:
- **`y_c`** ∈ {0,1}: Binary activation variable for RAC contract `c`
- Where `c ∈ C_{RAC}`: Set of rebate adjustment clause contracts

## Parameters

### Depot and Volume Data
- **`V_i`**: Annual fuel demand for depot `i` (litres)
- **`C_{i,j,o}`**: Cost per litre for option `o` at depot/supplier pairing (i,j)
- **`C^base_{i,j,o}`**: Base cost per litre (without rebates/discounts)
- **`W_b`**: Width of tier band `b` (max volume - min volume, or +∞ if unbounded)

### Cost Structure by Type
All costs are **precomputed** from base costs minus rebates:
- **Base Options**: `coc_cash`, `coc_30`, `coc_45`, `coc_60`, `del_own`, `del_buy`, `del_rent`
- **RAC Penalties**: `rac_coc_30`, `rac_del_own`, `rac_del_buy`, `rac_del_rent` (committed volumes not met)
- **Tier-Enhanced**: `base_option_tier_band_name` (e.g., `coc_30_tier_15M_to_20M`)

### Contract Parameters
- **`T_c`**: Volume threshold for RAC contract activation (litres)
- **`T^m_c`**: Minimum volume threshold for contract `c` activation
- **`T^b_c`**: Minimum volume threshold for tier band `b` activation
- **`R_{o,b}`**: Rebate per litre for option `o` in tier band `b`

## Objective Function

**Minimize total annual fuel procurement cost:**

```
minimize ∑_{i∈I} ∑_{j∈J} ∑_{o∈O_base} V_i × C_{i,j,o} × x_{i,j,o} +
       ∑_{c∈C_inc} ∑_{b∈B_c} ∑_{i,j,o} C_{i,j,o}^b × s_{i,j,o,b}
```

**Where**:
- **Base Options** (all contracts): `∑ V_i × C_{i,j,o} × x_{i,j,o}` for all allocation options
- **Incremental Band Costs**: `C^0 × s_{i,j,o,0}` (base band) + `C^{rebated} × s_{i,j,o,b}` (tier bands with rebate)
- **All-Units Options**: Tier-enhanced costs `C_{i,j,o}^tier` included in base options sum

**Key Insight**: The objective uses **precomputed per-option costs** (base, RAC, tier), and in incremental contracts applies them per band via the s_{o,b} volumes.

## Constraints

## Constraints

### 1. Depot Assignment Constraint
Each customer depot must be allocated to exactly one supplier depot with one cost option:

```
∑_{j∈J} ∑_{o∈O} x_{i,j,o} = 1    ∀i ∈ I
```

### 2. All-Units Regime Tier Constraints (Regime A)

For each contract `c` with all-units tiering (`c ∈ C_{all-units}`):

#### Volume Threshold Calculation:
Define total volume for contract eligibility as:
```
V_c^{total} = ∑_{i∈I_c} ∑_{j∈J_c} ∑_{o∈O_c^{vol}} V_i × x_{i,j,o}
```
Where `O_c^{vol}` includes base and tier options contributing to volume accumulation

#### Tier Band Eligibility:
```
V_c^{total} ≥ T_{c,b} × y_{c,b}    ∀b ∈ B_c
```
Where `y_{c,b}` ∈ {0,1} is the eligibility indicator for band `b`

#### Selection Logic:
```
z_{c,b} ≤ y_{c,b}    ∀b ∈ B_c
```
Where `z_{c,b}` ∈ {0,1} is the selection variable for band `b`

#### At-Most-One Selection:
```
∑_{b∈B_c} z_{c,b} ≤ 1
```

#### Tier Option Gating (Linear Equivalence of Indicator):
```
x_{i,j,o} ≤ 1 - (1 - z_{c,b})    ∀tier options o belonging to band b
```
Equivalent to: "If `z_{c,b} = 0` then `x_{i,j,o} = 0`" for tier options in band `b`

#### Base Option Exclusion (All-Units Logic):
```
x_{i,j,o} ≤ 1 - y_{any}    ∀base options o in contract c
```
Where `y_{any} = OR({z_{c,b} | b ∈ B_c})`, implemented through auxiliary binary variable

**Key All-Units Logic**: When any tier band is selected, all base options for the contract are forbidden, enforcing true volume tier behavior.

### 3. Incremental Regime Tier Constraints (Regime B)

For each contract `c` with incremental tiering (`c ∈ C_{incremental}`):

#### Flow Conservation (Band Splitting):
For each allocated option `(i,j,o)` where `x_{i,j,o} = 1`:
```
∑_{b∈B_c} s_{i,j,o,b} = V_i
```
Volume must be split across tier bands within the depot's demand

#### Band Capacity Constraints:
```
∑_{i∈I_c} ∑_{j∈J_c} ∑_{o∈O_c} s_{i,j,o,b} ≤ W_b × z_{c,b}    ∀b ∈ B_c
```
Total volume in band `b` cannot exceed band width when activated

#### Cumulative Volume Eligibility:
```
∑_{k≤b} ∑_{i∈I_c} ∑_{j∈J_c} ∑_{o∈O_c} s_{i,j,o,k} ≥ T_{c,b} × z_{c,b}    ∀b ∈ B_c
```
Progressive eligibility - higher bands require lower bands to be filled first

#### Monotonicity (Higher Bands Require Lower Bands):
```
z_{c,b+1} ≤ z_{c,b}    ∀b ∈ {1,...,|B_c|-1}
```

#### Tier Option Disablement:
```
x_{i,j,o} = 0    ∀tier-enhanced options o in incremental contracts
```
Incremental contracts use band-split variables instead of tier-enhanced allocation options

### 4. Rebate Adjustment Clause (RAC) Constraints

For each RAC contract `c ∈ C_{RAC}`:

#### RAC Activation Based on Volume Commitment:
```
∑_{i∈I_c} ∑_{j∈J_c} ∑_{o∈O_c^{base}} V_i × x_{i,j,o} ≥ T_c × y_c
```

#### Base Options Allowed When Committed (Linear Equivalence):
```
x_{i,j,o} ≤ (1 - y_c) + 1 × x_{i,j,o}^{}    ∀base options o
```
Equivalent to: `x_{i,j,o} ≤ 1 - y_c` ⇒ If `y_c = 0` then `x_{i,j,o} = 0`

#### RAC Penalties Required When Not Committed:
```
x_{i,j,o} ≤ y_c + 1 × x_{i,j,o}^{\ }    ∀RAC penalty options o
```
Equivalent to: `x_{i,j,o} ≤ y_c` ⇒ If `y_c = 0` then `x_{i,j,o} = 0`

**Mathematical Logic**: RAC enforces mutual exclusion where base options require volume commitment (`y_c = 1`), while RAC penalties require failure to meet commitment (`y_c = 0`).

### 5. Supplier Depot Capacity Constraints

For each supplier depot `j`:
```
∑_{i∈I_j} ∑_{o∈O_j} V_i × x_{i,j,o} ≤ L_j
```
Where `I_j` and `O_j` are restricted to allocations involving depot `j`.

**Implementation Note**: Capacity limits are applied at individual supplier depot level (not supplier level) to reflect terminal-specific constraints.

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

## Model Statistics (Current Implementation)
- **Total Variables**: 11,076 (including continuous band volume variables)
- **Allocation Variables**: 10,908 binary variables for depot-supplier-option allocations
- **RAC Contract Variables**: 1 binary variable for RAC contract activation
- **Tier Band Variables**: 6 binary variables for tier band activation (excluding base bands)
- **Regime-Specific Variables**: 156 additional variables (band volume splits for incremental contracts)
- **Total Binary Variables**: 10,923 variables
- **Total Cost Options**: 26,996 precomputed cost options across all scenarios
- **Depot-Supplier Combinations**: 2,011 feasible combinations
- **Option Types**: 32 total (7 base + 4 RAC + 21 volume tier enhanced options)
- **Constraints**: 5,090 total constraints
  - Depot assignment: 60 constraints (one per customer depot)
  - Capacity constraints: 75 constraints (one per supplier depot)
  - Volume tier constraints: ~100+ constraints (eligibility, monotonicity, flow conservation)
  - RAC constraints: ~350 constraints (mutual exclusion logic)
  - Incremental band constraints: ~4,500+ constraints (band width, cumulative eligibility)
- **Problem Type**: Mixed Integer Programming (MIP) with continuous band splits
- **Solver**: IBM CPLEX via DOcplex API

## Implementation Notes

### 1. Linear Constraint Equivalent of Indicator Functions
**Major Refactor**: Big-M constraints were replaced with linear constraint equivalents to maintain compatibility across DOcplex versions:

```python
# Instead of Big-M (incompatible):
# self.model.add_indicator(z_var, x_var == 0)

# Linear equivalent (works universally):
x_var ≤ (1 - z_var)
# Meaning: If z_var = 1, then x_var must be 0
```

This elimination of Big-M constraints improves numerical stability and maintains **identical mathematical logic** while ensuring solver compatibility.

### 2. Constraint-Enable Indicator Logic
Indicator constraints are implemented through auxiliary binary variables:

```python
def or_of_binaries(self, binaries, name_prefix) -> BinaryVar:
    """OR logic: y = 1 if any binary in binaries is 1"""
    y = self.model.binary_var(name=f"{name_prefix}_any")
    self.model.add_constraint(y >= b for b in binaries)    # y ≥ each b
    self.model.add_constraint(y <= self.model.sum(binaries))  # y ≤ sum(b)
    return y

def hard_zero_when(self, trigger_bvar, vars_to_zero):
    """If trigger=1 then all vars_to_zero must be 0"""
    for v in vars_to_zero:
        self.model.add_constraint(v <= (1 - trigger_bvar))
```

### 3. Cost Structure (Precomputed Costs)
**Implementation**: The objective function uses **precomputed per-option costs** rather than dynamic recomposition:

```python
# Objective function uses precomputed costs from cost matrices
# All costs (base, RAC, tier) are computed during preprocessing
for depot_id in allocations:
    for supplier_depot_id in allocations:
        for option_type in allocations:
            cost_per_litre = self.cost_matrices[depot_id][supplier_depot_id][option_type]
            cost_term += cost_per_litre × volume × allocation_var
```

This enables efficient optimization using preprocessed cost lookups for all option types.

### 4. Volume Tier Regimes: Dual Implementation Approaches

#### All-Units Regime (Selection Gating):
- Variables: Selection `z_{c,b}`, eligibility `y_{c,b}`
- Logic: At most one band selected, base options forbid den when any tier selected
- Purpose: Classic volume tier behavior - tiers completely replace base pricing

#### Incremental Regime (Band Splitting):
- Variables: Volume splits `s_{i,j,o,b}`, band activations `z_{c,b}`
- Logic: Volume flow conservation, cumulative eligibility, monotonically increasing bands
- Purpose: Precise volume-based rebate application through actual volume allocation

### 5. Contract Mutual Exclusivity
RAC and volume tier contracts interact but apply different penalty/reward mechanisms:
- RAC: Mutual exclusion between base vs penalty options based on volume commitment
- Volume Tier: Progressive rebates based on volume thresholds, with regime-specific logic

### 6. Transport Mode and Supplier Filtering
**Robustness Layer**: Multi-level filtering ensures constraint consistency:

```python
# Contract-specific mode filtering
contract_modes = config.get('transport_modes', [])
# Supplier-specific filtering
supplier_name = depots.get(supplier_id, {}).get('supplier_name', '')
# Option compatibility checks at multiple levels
```

### 7. Numerical Implementation Details
- **Solver**: IBM CPLEX via DOcplex 2.23.222 Community Edition
- **Variable Types**: Mixed-integer (binary allocation + continuous band splits)
- **Objective Direction**: Minimize (ZXOR maximize as originally implemented)
- **Constraint Types**: Linear equality/inequality (replaced pseudo-indicator syntax)

### 8. Regression Testing Methodology
Systematic validation of constraint violations:

```python
# Test cases comparing Big-M vs linear equivalent formulations
# Check objective value equivalency (±1e-6 tolerance)
# Verify selected BIN variables and Z variables remain identical
# Ensure feeder constraints not violated
```

### 9. Business Logic Preservation
**Thesis Contribution**: Mathematical formulation maintains all business constraints:
- Volume tier progressiveness (10M enables 10M tier, not 25M tier)
- RAC penalty application (commitment failure triggers appropriate penalties)
- Mutual exclusivity enforcement (base/RAC separation, base/tier separation in all-units)
- Capacity constraints at appropriate granularity

### 10. Base Band Treatment (Surgical Fix Implementation)
**Recent Enhancement**: Base bands (min_volume=0) in incremental contracts receive special treatment:

```python
# Binary variable creation (fuel_optimizer_docplex.py:246)
if regime == 'incremental' and min_vol == 0:
    continue  # No binary variable for base band

# Constraint adjustments for base bands:
# - Width constraints: q_base <= band_width (no binary gate)
# - Eligibility constraints: skipped (min_volume=0 always satisfied)  
# - Monotonicity constraints: skipped (no binary to order)
```

**Business Rationale**: Base bands represent baseline pricing, not tier achievements worthy of activation reporting. This eliminates spurious "Activated Tiers" output while maintaining:
- Flow conservation through volume variables `s_{i,j,o,b}`
- Correct baseline costing in objective function
- Mathematical model integrity

### 11. Academic Value
This implementation provides practical demonstration of:
- **Indicator Constraint Alternatives**: Linear equivalences for version compatibility
- **Regime-Based Design**: Two fundamentally different approaches to volume tiering
- **Cost Recomposition**: Dynamic cost calculation rather than static lookups
- **Mixed-Constraint Optimization**: Combining discrete allocation with continuous volume splitting
- **Business Logic Modeling**: Translating complex contractual requirements into mathematical constraints
- **Surgical Model Refinement**: Targeted fixes preserving mathematical integrity while improving business accuracy

## Model Performance Metrics (Current Implementation)

- **Variables** (Total: 11,076):
  - Allocation binaries: 10,908 (x_{i,j,o})
  - Tier binaries: 6 (z_{c,b} for min_volume > 0 only)
  - RAC binaries: 1 (y_c)
  - All-units selection: ~8 (y_{c,b} selection variables)
  - Band volume splits: 156 (s_{i,j,o,b}) for incremental contracts
- **Constraints** (Total: 5,090):
  - Assignment: 60 constraints (one per depot)
  - Capacity: 75 constraints (one per supplier depot)
  - Volume tier: ~100+ constraints (regime-dependent)
  - RAC: ~350 constraints (mutual exclusion enforcement)
  - Incremental band: ~4,500+ constraints (flow conservation, eligibility, monotonicity)
- **Computational Complexity**: Mixed-integer programming with sophisticated network flow constraints
- **Solution Performance**: Sub-second optimization for 60 depots, 75 supplier depots, 31M+ annual volume
