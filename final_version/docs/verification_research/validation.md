1. Face Validation (Expert or Literature-Based Logic Check)

Compare your model’s outputs against what domain knowledge or literature says is reasonable.

Example: If Supplier A has the lowest cost and high reliability, the optimizer should allocate them significantly unless a constraint (e.g., emissions cap or supply limit) prevents it.

You can reference published procurement strategies, industry reports, or academic case studies as the "benchmark."


2. Extreme Condition Tests

Change parameters to unrealistic extremes and check if the model reacts logically.

Example:

Set one supplier’s price extremely high → optimizer should stop selecting it.

Remove emissions caps → optimizer should choose the cheapest mix regardless of emissions.

These checks validate that the formulation behaves logically under stress.



4. Scenario-Based Validation

Build a few stylized “toy scenarios” with small, hypothetical data where the optimal solution can be worked out manually.

Example: With 2 suppliers (one cheap, one clean), you can reason about the trade-offs.

If the optimizer’s output matches your manual expectations, it validates correctness.


5. Qualitative Business Logic Validation

Yes, this works. Document the decision logic companies should follow and compare your optimizer’s results to those expectations.

Example: “Industry practice suggests diversifying suppliers to mitigate risk. The optimizer also produces diversified portfolios under most scenarios, which aligns with best practice.”

This keeps the validation academically credible even without raw company data.



## Results granularity


You do **not** need to show every granular result table. The expectation in a thesis is to *demonstrate* that you performed the check and that the model behaved logically. How you present it depends on how much space and depth you want:

---

### Options for Presenting Extreme Condition Tests

**1. Concise Narrative (minimal data shown)**

* Describe the test, explain the expected outcome, and confirm the result.
* Example (paragraph style):

> When Supplier A’s price was increased by 500%, the optimizer consistently eliminated Supplier A from the solution set, confirming that the cost-minimization logic functions correctly. Similarly, when emissions caps were removed, the optimizer selected only the cheapest suppliers, which aligns with expected behavior.

This works if you want to keep the section short and clean.

---

**2. Small Summary Table (optional, illustrative only)**

* A simple before/after or expected vs observed results table.
* Example:

| Test Scenario         | Expected Outcome                  | Observed Outcome                  | Pass/Fail |
| --------------------- | --------------------------------- | --------------------------------- | --------- |
| Supplier A price ×5   | Supplier A excluded               | Supplier A excluded               | Pass      |
| Emission caps removed | Cheapest suppliers fully selected | Cheapest suppliers fully selected | Pass      |

This avoids overwhelming detail but shows clarity and systematic verification.

---

**3. Detailed Tables (not recommended unless examiner demands evidence)**

* Full optimizer outputs for each extreme scenario.
* Only worth including in an **appendix** if needed.

---

### Recommendation for Your Case

* In the **main thesis body**: use **paragraph explanations** and, if you want extra clarity, a **short summary table**.
* If you feel pressured to show evidence: move the detailed optimizer results into an **appendix** and reference it (“see Appendix B for raw outputs”).

---

This way you keep the narrative flowing, prove you tested, but don’t drown the reader in unnecessary numbers.

Do you want me to draft you a **sample write-up (paragraph + optional table)** for one of your extreme condition tests so you can see the right level of detail?
