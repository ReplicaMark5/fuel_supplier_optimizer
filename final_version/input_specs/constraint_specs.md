# Constraint Specifications (Natural Language)

This document explains, in structured natural language, the constraints implemented by the optimizer in `final_version/fuel_optimizer_docplex.py`, excluding the detailed mechanics of volume‑tier and rebate contracts (those appear in `input_specs/volume_tier_specs.md`). This document   is the ground truth and references tier/RAC logic where relevant.

## Scope and Entities

- Customer depots `i ∈ I` with annual demand `V_i` (litres)
- Supplier depots `j ∈ J` with capacity limit `L_j` (litres) where configured
- Cost options `o ∈ O`: base (`coc_cash`, `coc_30`, `coc_45`, `coc_60`, `del_own`, `del_rent`), RAC penalty (`rac_*`), and tier‑enhanced (`*_tier_*`)
- Contracts and tier bands exist and drive pricing/gating; their detailed business rules and thresholds are specified in `input_specs/volume_tier_specs.md` and not repeated here.

## Modeling Notes

- The model creates binary allocation variables only for feasible customer–supplier–option triplets present in the cost dictionary. Unavailable services are simply absent from the decision space.
- “Transport modes” are inferred from option names: options containing `coc` are mode `COC`; options containing `del` are mode `DEL`.
- Indicator‐style gating is implemented without Big‑M: by constraints of the form `x ≤ 1 − b` (if `b = 1` then `x = 0`).

Note: Contracts also apply supplier/mode filters and may use `volume_calculation_modes`; see `volume_tier_specs.md` for those mode‑specific business rules.

## 1) Depot Assignment (Exactly One)

Business rule: Every customer depot must be served by exactly one supplier depot and one cost option.

- For each customer depot `i`, the sum of all allocation binaries across all supplier depots `j` and all cost options `o` equals 1.
- Effect: Guarantees a unique allocation decision per depot.

## 2) Contract‑Driven Pricing and Gating (Reference Only)

The optimizer enforces several contract‑driven constraints (all‑units tiers, incremental tiers, and RAC mutual exclusion). Their business rules—thresholds, band widths, mode logic, and rebate semantics—are specified in `input_specs/volume_tier_specs.md` and are not repeated here.

At a high level:
- All‑units tiers: Selecting a tier band for a contract forbids base options for that contract; tier options are gated by the selected band.
- Incremental tiers: Volume is split across bands; band capacities/eligibility apply; tier options are disabled (pricing occurs via band splits).
- RAC: Base options are allowed only when commitment is met; RAC penalty options are allowed only when it is not.

Please consult `volume_tier_specs.md` for the authoritative tier/RAC business specification.

## 3) Supplier Depot Capacity Limits

## 4) Country (Cross‑Border) Allocation Constraints

Purpose: Respect individual supplier depot throughput limits where configured.

Constraint implemented: For each supplier depot `j` with a capacity limit, the sum of `V_i` over all selected allocations to that depot (across all options) must not exceed the capacity `L_j`.

Outcome: Prevents over‑allocation beyond terminal capacity.

## 5) Service Availability

Purpose: Enforce cross‑border business rules driven by configuration.

Constraints implemented:

- For each allocation `(i,j,o)`, if the customer depot’s country and supplier depot’s country form a blocked pair under the policy, that allocation is forbidden (`x_{i,j,o} = 0`).
- Policy precedence: When both `allowed_destinations` and `blocked_destinations` are provided for a country, the blocked list takes precedence.
- The constraint set is generated dynamically from `optimization_config.json`. Missing country metadata results in warnings and the allocation is left unconstrained for cross‑border logic (other constraints still apply).

Outcome: Allocations adhere to configured regulatory and operational cross‑border policies.

## 6) Contract Scoping Filters (Supplier/Mode)

Purpose: Apply contract logic only to relevant suppliers, specific supplier depots (if listed), and transport modes.

Filters applied before building constraint terms:

- Supplier scoping: If a contract lists specific suppliers, allocations from other suppliers are ignored for that contract’s counting and gating.
- Supplier depot scoping: If a contract lists specific supplier depots, only those depots are included.
- Mode scoping: Contract logic only affects options whose inferred transport mode is included in `transport_modes`. Threshold tallies additionally use `volume_calculation_modes` when provided.

Outcome: Contracts affect only the intended subset of allocations.

## 7) Variable Domains and Integrity

- Allocation variables are binary (0/1).
- Tier band activation binaries are created only when needed (no binary for base band in incremental regime).
- RAC activation variables are binary.
- Band split variables `s_{i,j,o,b}` are continuous and non‑negative.

## 8) Implicit Service Availability

- If a particular combination `(i,j,o)` is not available or not present in the cost dictionary, no decision variable is created for it and it cannot be selected. This implicitly enforces service availability constraints from the data layer in the optimization layer.

## 9) Data and Numerical Safeguards (Implementation Notes)

- The objective ignores entries with non‑finite costs or volumes (e.g., NaN) and logs warnings; constraints remain valid for the rest of the model.
- No Big‑M constants are used. Logical gating is enforced with tight linear constraints (e.g., `v ≤ 1 − b`) and per‑contract OR variables.

---

If a business rule needs to be refined or extended (e.g., different mode sets for threshold vs pricing, supplier‑level capacity instead of depot‑level), it can usually be added by adjusting configuration and the corresponding filter in the constraint assembly without changing the core model structure.
