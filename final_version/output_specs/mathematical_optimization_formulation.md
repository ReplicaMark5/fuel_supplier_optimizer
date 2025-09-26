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
- **Base Options**: `coc_cash`, `coc_30`, `coc_45`, `coc_60`, `del_own`, `del_rent`
- **RAC Penalties**: `rac_coc_30`, `rac_del_own`, `rac_del_rent` (committed volumes not met)
- **Tier-Enhanced**: `base_option_tier_band_name` (e.g., `coc_30_tier_15M_to_20M`)

### Contract Parameters
- **`T_c`**: Volume threshold for RAC contract activation (litres)
- **`T^m_c`**: Minimum volume threshold for contract `c` activation
- **`T^b_c`**: Minimum volume threshold for tier band `b` activation
- **`R_{o,b}`**: Rebate per litre for option `o` in tier band `b`

## Objective Functions

### Single-Objective Formulation

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

### Multi-Objective Formulation

The system supports **three distinct optimization modes** for multi-objective analysis:

#### Mode 1: Cost-Only Optimization (Default Single-Objective)
```
minimize ∑_{i∈I} ∑_{j∈J} ∑_{o∈O} V_i × C_{i,j,o} × x_{i,j,o}
```
Standard cost minimization without strategic considerations.

#### Mode 2: Strategic-Only Optimization
```
maximize ∑_{i∈I} ∑_{j∈J} ∑_{o∈O} S_s(j) × x_{i,j,o}
```
Where `S_s(j)` is the strategic score for supplier `s` that owns supplier depot `j`.

**Note**: Strategic scores are calculated at the supplier level, not per individual depot. All depots belonging to the same supplier share the same strategic score.

#### Mode 3: ε-Constraint Method (Pareto Front Generation)
**Primary Objective** (Cost Minimization):
```
minimize ∑_{i∈I} ∑_{j∈J} ∑_{o∈O} V_i × C_{i,j,o} × x_{i,j,o}
```

**Subject to Strategic Score Constraint**:
```
∑_{i∈I} ∑_{j∈J} ∑_{o∈O} S_s(j) × x_{i,j,o} ≥ ε
```

Where `ε` is the minimum required total strategic score across all depot allocations, and `S_s(j)` is the supplier-level strategic score.

### Strategic Supplier Score Definition

**Strategic Score Calculation**:
```
S_s = ∑_{c∈Criteria} (criterion_value_{s,c} × weight_c)
```

Where `s` represents the supplier (not individual depot), and the same score `S_s` applies to all depots `j` owned by supplier `s`.

**Multi-Criteria Evaluation Framework**:
- **Current Level (1-8)**: Supplier relationship maturity level
- **Product/Service Type**: Alignment of service offerings with requirements  
- **Geographical Network**: Distribution coverage and logistics capability
- **Method of Sourcing**: Supply chain approach and sourcing methodology
- **Investment in Refuelling Equipment**: Infrastructure commitment and capability
- **Reciprocal Business**: Mutual business relationship strength

**Score Properties**:
- Range: [0.0, 1.0] normalized scores per supplier (shared by all depots of that supplier)
- Source: Multi-criteria weighted evaluation from database (`supplier_scores` table)  
- Granularity: Supplier-level scoring (not per individual depot)
- Integration: Precomputed during cost calculation and embedded in cost dictionary

**Implementation Note**: The current system assigns the same strategic score to all depots belonging to the same supplier. This simplifies the multi-criteria evaluation but may lose fidelity if depot-specific strategic characteristics vary significantly within a supplier's network.

### Pareto Front Generation Methodology

**ε-Constraint Implementation**:
1. **Bound Calculation**: 
   - `ε_min = min(S_s) × |I|` (all depots use lowest-scoring supplier)
   - `ε_max = max(S_s) × |I|` (all depots use highest-scoring supplier)

2. **ε Value Generation**:
   - Linear spacing: `ε_k = ε_min + k × (ε_max - ε_min)/(n-1)` for `k = 0,1,...,n-1`
   - Default: 15-20 points for comprehensive Pareto front coverage

3. **Systematic Optimization**:
   - For each `ε_k`: Solve cost minimization subject to `∑S_s(j) × x_{i,j,o} ≥ ε_k`
   - Collect feasible solutions forming Pareto-optimal front

4. **Trade-off Analysis**:
   - Cost range quantification across strategic score improvements
   - Marginal cost per strategic score point calculation
   - Extreme point identification (minimum cost vs. maximum strategic score)

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

#### Volume Commitment Link:
```
∑_{i∈I_c} ∑_{j∈J_c} ∑_{o∈O_c^{base}} V_i × x_{i,j,o} ≥ T_c × y_c
```

#### RAC Gating Constraints (Linear Equivalence):
**Base Options Allowed Only When Committed** (`y_c = 1`):
```
x_{i,j,o}^{base} ≤ y_c    ∀base options o
```

**RAC Options Allowed Only When Not Committed** (`y_c = 0`):
```
x_{i,j,o}^{rac} ≤ 1 - y_c    ∀RAC penalty options o
```

**Mathematical Logic**: RAC enforces mutual exclusion where base options require volume commitment (`y_c = 1`), while RAC penalties require failure to meet commitment (`y_c = 0`).

### 5. Supplier Depot Capacity Constraints

For each supplier depot `j`:
```
∑_{i∈I_j} ∑_{o∈O_j} V_i × x_{i,j,o} ≤ L_j
```
Where `I_j` and `O_j` are restricted to allocations involving depot `j`.

**Implementation Note**: Capacity limits are applied at individual supplier depot level (not supplier level) to reflect terminal-specific constraints.

### 6. Country Allocation Constraints (Cross-Border Restrictions)

For each customer depot `i` located in country `k_i` and supplier depot `j` located in country `k_j`:

```
x_{i,j,o} = 0    ∀(i,j,o) where (k_i, k_j) ∉ P
```

Where `P` is the set of permitted country pairs defined by cross-border policy configuration.

**Alternative Formulation** (Policy-Based):
For each customer depot country `k_i` with cross-border restrictions:

```
x_{i,j,o} = 0    ∀i ∈ I_{k_i}, j ∈ J_{k_j}, o ∈ O where k_j ∈ B_{k_i}
```

Where:
- `I_{k_i}`: Set of customer depots in country `k_i`
- `J_{k_j}`: Set of supplier depots in country `k_j`  
- `B_{k_i}`: Set of blocked destination countries for customer country `k_i`

**Configuration Structure**:
```json
"country_allocation_constraints": {
  "enabled": true,
  "cross_border_restrictions": {
    "South Africa": {
      "allowed_destinations": ["South Africa", "Mozambique"],
      "blocked_destinations": ["Botswana", "Namibia", "Eswatini"]
    },
    "Botswana": {
      "allowed_destinations": ["Botswana", "South Africa"],
      "blocked_destinations": ["Mozambique", "Namibia", "Eswatini"]
    }
  }
}
```

**Implementation Notes**:
- Constraints are generated dynamically based on configuration
- Each blocked country pair results in one binary constraint per allocation variable
- Country information is extracted from depot database tables (`customer_depots.Country`, `supplier_depots.Country`)
- Provides flexible control over cross-border fuel supply policies
- Can model scenarios from same-country-only to selective cross-border permissions

## Option Types and Cost Structure

### Base Options
- **COC (Customer Own Collection)**: `coc_cash`, `coc_30`, `coc_45`, `coc_60`
- **DEL (Supplier Delivery)**: `del_own`, `del_rent`

**Note**: The `del_buy` option was removed from the implementation as it was redundant with `del_own` (customer purchases equipment vs. customer already owns equipment). The current implementation covers the essential DEL scenarios: customer-owned equipment (`del_own`) and supplier-rental equipment (`del_rent`).

### RAC Options  
- **RAC Penalties**: `rac_coc_30`, `rac_del_own`, `rac_del_rent` (NET30 terms only)

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

### Single-Objective Model Scale
- **Total Variables**: 10,452 (including continuous band volume variables)
- **Allocation Variables**: 10,335 binary variables for depot-supplier-option allocations
- **RAC Contract Variables**: 1 binary variable for RAC contract activation
- **Tier Band Variables**: 6 binary variables for tier band activation (excluding base bands)
- **Regime-Specific Variables**: 105 additional variables (band volume splits for incremental contracts)
- **Total Binary Variables**: 10,350 variables
- **Total Cost Options**: 26,423+ precomputed cost options across all scenarios
- **Depot-Supplier Combinations**: 2,011 feasible combinations
- **Option Types**: 19+ total (6 base + 3 RAC + 10+ volume tier enhanced options)
- **Constraints**: 4,734+ total constraints (varies with country constraint configuration)
  - Depot assignment: 60 constraints (one per customer depot)
  - Capacity constraints: 68 constraints (one per supplier depot with defined limits)
  - Volume tier constraints: ~3,300+ constraints (eligibility, monotonicity, flow conservation)
  - RAC constraints: ~580+ constraints (mutual exclusion logic)
  - Country allocation constraints: 0-1,302+ constraints (dynamic based on cross-border policy)
- **Problem Type**: Mixed Integer Programming (MIP) with continuous band splits
- **Solver**: IBM CPLEX via DOcplex API

### Multi-Objective Model Extensions
- **Strategic Score Variables**: Embedded in allocation variables (no additional variables)
- **Strategic Score Constraints**: 1 additional constraint per ε-constraint problem
- **Optimization Modes**: 3 distinct formulations (cost_only, strategic_only, epsilon_constraint)
- **Pareto Front Generation**: 15-20 ε-constraint problems per analysis
- **Strategic Score Range**: [0.0, 1.0] per supplier depot, aggregated across 60 depots
- **Multi-Objective Performance**:
  - Single optimization: ~2 seconds per mode
  - Full Pareto front (15 points): ~30 seconds
  - Strategic score integration: <1 second overhead
- **Trade-off Analysis**: Cost range typically 3-4% across strategic score improvements

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

### 11. Country-Based Allocation Constraints (Geographic Policy Control)
**Implementation Strategy**: Dynamic constraint generation based on configuration-driven cross-border policies:

```python
# Constraint generation logic
for (depot_id, supplier_depot_id, option_type), allocation_var in self.allocation_vars.items():
    customer_country = self.customer_depots[depot_id]['country']
    supplier_country = self.cost_matrices[depot_id][supplier_depot_id]['supplier_depot_country']
    
    if self._is_blocked_country_pair(customer_country, supplier_country):
        self.model.add_constraint(allocation_var == 0)
```

**Business Applications**:
- **Trade Policy Modeling**: Implement government cross-border trade restrictions
- **Operational Constraints**: Model logistical difficulties of cross-border fuel transport
- **Regulatory Compliance**: Ensure allocations comply with international fuel trade agreements
- **Scenario Analysis**: Compare same-country vs cross-border optimization strategies

**Configuration Flexibility**:
```json
// Restrictive policy (Botswana depots can only source from Botswana suppliers)
"Botswana": {"allowed_destinations": ["Botswana"]}

// Permissive policy (South African depots can source from any supplier)  
"South Africa": {"allowed_destinations": ["South Africa", "Mozambique", "Botswana", "Namibia", "Eswatini"]}
```

**Mathematical Properties**:
- **Linear Constraints**: Simple binary constraints `x_{i,j,o} = 0` for blocked pairs
- **Dynamic Generation**: Constraint count varies from 0 (no restrictions) to thousands (strict restrictions)
- **Policy Consistency**: Configuration validation ensures allowed/blocked lists are mutually exclusive
- **Performance Impact**: Minimal solve time increase (<5%) due to constraint sparsity

### 12. Multi-Objective Optimization Implementation

**Strategic Score Integration Architecture**:
```python
# Cost dictionary enhanced with strategic scores during precomputation
cost_dict[depot_id][supplier_depot_id]['strategic_score'] = strategic_score

# Multi-objective optimization modes supported
optimizer.set_objective(
    objective_mode="epsilon_constraint",
    strategic_constraint=epsilon_value
)
```

**ε-Constraint Method Implementation**:
- **Pareto Front Generator**: `pareto_front_generator.py` orchestrates systematic ε-constraint solving
- **Strategic Bound Calculation**: Theoretical min/max based on available supplier strategic scores
- **Linear Spacing Strategy**: Even distribution of ε values across feasible strategic score range
- **Solution Collection**: Pareto-optimal points with cost, strategic score, and allocation details

**Performance Optimizations**:
- **Data Reuse**: Single precomputation run shared across all ε problems
- **Efficient Constraint Addition**: Strategic constraints added without model rebuilding
- **Parallel Potential**: Independent ε problems suitable for parallel solving

### 13. Academic Value
This implementation provides practical demonstration of:
- **Multi-Objective Optimization**: Complete ε-constraint method with Pareto front generation
- **Strategic Supplier Evaluation**: Multi-criteria decision analysis integration in optimization
- **Indicator Constraint Alternatives**: Linear equivalences for version compatibility
- **Regime-Based Design**: Two fundamentally different approaches to volume tiering
- **Cost Recomposition**: Dynamic cost calculation rather than static lookups
- **Mixed-Constraint Optimization**: Combining discrete allocation with continuous volume splitting
- **Business Logic Modeling**: Translating complex contractual requirements into mathematical constraints
- **Surgical Model Refinement**: Targeted fixes preserving mathematical integrity while improving business accuracy
- **Geographic Policy Constraints**: Flexible implementation of location-based allocation restrictions
- **Trade-off Analysis**: Quantitative assessment of cost vs. strategic score relationships

## Model Performance Metrics (Current Implementation)

- **Variables** (Total: 10,452):
  - Allocation binaries: 10,335 (x_{i,j,o})
  - Tier binaries: 6 (z_{c,b} for min_volume > 0 only)  
  - RAC binaries: 1 (y_c)
  - All-units selection: ~5 (y_{c,b} selection variables)
  - Band volume splits: 105 (s_{i,j,o,b}) for incremental contracts
- **Constraints** (Total: 4,734+ dynamic):
  - Assignment: 60 constraints (one per depot)
  - Capacity: 68 constraints (one per supplier depot with capacity limits)
  - Volume tier: ~3,300+ constraints (regime-dependent)
  - RAC: ~580+ constraints (mutual exclusion enforcement)  
  - Country allocation: 0-1,302+ constraints (dynamic based on cross-border policy)
- **Computational Complexity**: Mixed-integer programming with sophisticated network flow and policy constraints
- **Solution Performance**: ~2 second optimization for 60 depots, 75 supplier depots, 70M+ annual volume
- **Cross-Border Policy**: Flexible country-based allocation constraints supporting:
  - Same-country-only restrictions
  - Selective cross-border permissions (e.g., South Africa ↔ Mozambique allowed)
  - Dynamic policy configuration without model rebuilding
