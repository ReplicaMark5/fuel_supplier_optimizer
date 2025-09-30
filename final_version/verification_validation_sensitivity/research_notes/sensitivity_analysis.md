If you place **Sensitivity Analysis** inside **Validation**, you treat it as one of the ways to show the model is realistic and useful (robust under uncertainty). That’s common in theses when you don’t want a whole standalone chapter.

Here’s what you’d include:

---

## **Validation** (main section)

* **Face validation** – compare results to expected business logic.
* **Extreme condition tests** – stress test with unrealistic values.
* **Scenario validation** – check realistic stylized datasets.
* **Sensitivity analysis** (subsection) – test robustness to input variation.

---

### **Sensitivity Analysis Subsection**

Purpose: show the optimizer’s results are not fragile to small changes in input data, and identify parameters that strongly influence outcomes.

**Steps to include:**

1. **Select key parameters**

   * Supplier costs
   * Fuel demand levels
   * Emission caps / carbon tax rates
   * Supplier reliability or availability (if modeled)

2. **Define variation ranges**

   * ±10%, ±20% changes for costs/demand.
   * Tight vs relaxed emission limits.
   * “Best-case” vs “worst-case” scenarios.

3. **Run experiments**

   * Re-run the optimizer with each variation.
   * Observe how supplier allocation, cost, and emissions change.

4. **Summarize results**

   * Show whether solutions shift dramatically or remain stable.
   * Highlight which parameters the model is *most sensitive* to.

**How to present:**

* A **few concise graphs or tables** are better than walls of numbers.

  * Bar charts: supplier allocation under cost ±20%.
  * Pareto plots: baseline vs altered emission caps.
* If you need to save space, put raw numbers in an appendix and describe results in text.

**Example paragraph style:**

> When supplier costs were increased by ±20%, the optimizer’s allocation shifted only slightly, with Supplier B’s share rising from 30% to 35%. This indicates robustness to moderate cost changes. However, tightening the emissions cap by 50% significantly altered the solution set, forcing greater reliance on Supplier C. This shows that emissions constraints are a highly sensitive parameter in the model.

---

✅ By embedding sensitivity analysis as a subsection of validation, you strengthen the **“realism and robustness”** argument without needing a separate chapter.

---

Do you want me to draft you a **ready-to-use subsection template (with headings, text blocks, and example figure/table placeholders)** for your thesis Validation → Sensitivity Analysis?
