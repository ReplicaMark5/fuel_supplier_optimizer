Here’s a clean separation for your **fuel supplier optimizer** thesis work.

---

## **Verification** – “Did we build the model right?”

Prove the formulation and code are internally correct.

**Tasks:**

1. **Formulation check:** Ensure every mathematical constraint and objective in your thesis is implemented exactly in code.
2. **Toy problem tests:**

   * Build 1–2 very small datasets (e.g., 2 suppliers, 1 demand node).
   * Manually compute the optimal solution.
   * Confirm the optimizer matches it exactly.
3. **Constraint satisfaction:** Verify all outputs obey demand balance, capacity, emissions, and other constraints.
4. **Objective sanity:** If costs increase, objective value should increase. If emissions penalties are removed, solutions should revert to cost-optimal.
5. **Algorithm consistency:**

   * MILP: confirm solver reaches consistent optimal values.
   * NSGA-II: run multiple times and check Pareto fronts are stable in shape and range.
6. **Cross-tool check (optional):** Solve one small case with Excel Solver or another MILP package to confirm equivalence.

**Write-up:** Present at least one toy example and a summary table confirming all constraints/objectives behaved as intended. Keep raw solver logs in an appendix if needed.

---

## **Validation** – “Did we build the right model?”

Prove the optimizer produces outputs that make sense for its intended business purpose.

**Tasks:**

1. **Face validation:** Compare optimizer behavior to expected business logic (e.g., cheapest supplier dominates unless capped, diversification under risk).
2. **Extreme condition tests:**

   * Inflate a supplier’s cost massively → should be excluded.
   * Remove emission limits → should fully favor cheapest suppliers.
3. **Scenario validation:** Create stylized realistic datasets (e.g., mix of cheap/high-emission vs expensive/clean suppliers). See if the optimizer chooses sensible trade-offs.
4. **Consistency validation:** Run model on slightly different input sets (e.g., ±10% demand) and check results are stable and logical.
5. **Qualitative validation:** If no real company data is available, compare your outputs with literature or general procurement principles (e.g., supplier diversification, robustness to price shocks).

**Write-up:** Describe each test, expected logic, and whether results matched. Use short summary tables (Expected vs Observed vs Pass/Fail) or just paragraphs.

---

## **Sensitivity Analysis** – “How robust are the results under uncertainty?”

Systematically vary key inputs to test robustness and provide managerial insight.

**Tasks:**

1. **Parameter variation:** Adjust fuel demand, supplier costs, or emission caps within plausible ranges.
2. **Impact analysis:** Show how allocations, costs, or emissions change.
3. **Pareto sensitivity:** For NSGA-II, see how the Pareto front shifts under different assumptions (e.g., cost inflation, carbon tax).
4. **Scenario comparison:** Define best-case, worst-case, and average scenarios. Compare results to highlight robustness.

**Write-up:**

* Include graphs (Pareto fronts under different assumptions, bar charts of supplier shares under varying costs).
* Emphasize interpretation: *which parameters the solution is sensitive to, and which ones it is robust against.*

---

### ✅ Summary

* **Verification:** internal correctness → toy cases, constraint checks.
* **Validation:** external realism → business logic, extreme cases, stylized scenarios.
* **Sensitivity analysis:** robustness → vary parameters and show effect on results.

---

Do you want me to now draft a **chapter outline (with suggested headings and subsections)** showing how these three fit sequentially in your thesis?
