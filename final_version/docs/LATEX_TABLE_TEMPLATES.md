# LaTeX Table Templates for Thesis

This document provides the exact LaTeX table templates you'll use in your thesis, with instructions on where to paste the generated `.tex` files.

---

## 1. Baseline Supplier Utilization Table

**Generated file:** `outputs/thesis_results/baseline/supplier_utilization_rows.tex`

**LaTeX template:**

```latex
\FloatBarrier
\begin{table}[!htbp]
  \centering
  \renewcommand{\arraystretch}{1.2}
  \caption{Baseline supplier utilization summary (cost-only optimization).}
  \label{tab:baseline_supplier_util}
  \begin{tabular}{lrrrr}
    \topline
    \headcol
    \textbf{Supplier} & \textbf{Allocations} & \textbf{Total Volume (L)} & \textbf{Total Cost (R)} & \textbf{Avg Cost/L (R)} \\
    \midline
    % PASTE supplier_utilization_rows.tex CONTENT HERE
    \bottomline
  \end{tabular}
\end{table}
\FloatBarrier
```

**Expected row format:**
```latex
Supplier A & 12 & 15,234,567 & 245,678,912.34 & 16.1234 \\
```

---

## 2. Baseline Capacity Summary Table

**Generated file:** `outputs/thesis_results/baseline/capacity_summary_rows.tex`

**LaTeX template:**

```latex
\FloatBarrier
\begin{table}[!htbp]
  \centering
  \renewcommand{\arraystretch}{1.2}
  \caption{Supplier depot capacity utilization (top binding/near-capacity constraints).}
  \label{tab:baseline_capacity}
  \begin{tabular}{lrrr}
    \topline
    \headcol
    \textbf{Supplier Depot} & \textbf{Used Volume (L)} & \textbf{Capacity Limit (L)} & \textbf{Utilisation (\%)} \\
    \midline
    % PASTE capacity_summary_rows.tex CONTENT HERE
    \bottomline
  \end{tabular}
\end{table}
\FloatBarrier
```

**Expected row format:**
```latex
123 (Supplier A) & 12,345,678 & 15,000,000 & 82.3 \\
```

---

## 3. Representative Pareto Solutions Table

**Generated file:** `outputs/thesis_results/moo_pareto/representative_solutions_rows.tex`

**LaTeX template:**

```latex
\FloatBarrier
\begin{table}[!htbp]
  \centering
  \renewcommand{\arraystretch}{1.2}
  \caption{Representative Pareto solutions ($\epsilon$-constraint). Costs in Rands; deltas vs minimum cost.}
  \label{tab:rep_solutions}
  \begin{tabular}{p{2.5cm}rrrr}
    \topline
    \headcol
    \textbf{Point} & \textbf{Cost (R)} & \textbf{Strategic Score} & \textbf{$\Delta$Cost (\%)} & \textbf{$\Delta$Score (\%)} \\
    \midline
    % PASTE representative_solutions_rows.tex CONTENT HERE
    \bottomline
  \end{tabular}
\end{table}
\FloatBarrier
```

**Expected row format:**
```latex
Min Cost & 1,290,475,652.50 & 4047 & 0.0000 & 0.00 \\
\midlinecbw
\rowcol
Knee & 1,290,481,476.39 & 4249 & 0.0005 & 4.99 \\
\midlinecbw
Max Score & 1,290,970,044.28 & 4550 & 0.0383 & 12.43 \\
```

**Note:** The generated file will have simple `\\` line endings. If you want alternating row colors (`\rowcol`) and colored midlines (`\midlinecbw`), you'll need to add those manually or adjust the script.

---

## 4. Pareto Front Figure

**Generated file:** `outputs/thesis_results/moo_pareto/pareto_front_fuel_optimization.png`

**LaTeX template:**

```latex
\begin{figure}[!htbp]
  \centering
  \includegraphics[width=0.85\textwidth]{figures/pareto_front_fuel_optimization.png}
  \caption{Pareto front showing trade-off between total annual cost and strategic supplier score. Generated using $\epsilon$-constraint method with 20 points.}
  \label{fig:pareto_front}
\end{figure}
```

**Instructions:**
1. Copy `pareto_front_fuel_optimization.png` to your thesis `figures/` directory
2. Paste the LaTeX above in your results section
3. Reference in text as `Figure~\ref{fig:pareto_front}`

---

## 5. Optimization Map (Supplementary Material)

**Generated file:** `outputs/thesis_results/baseline/baseline_optimization_map.html`

**Not included directly in LaTeX**, but can be:
- Included in appendix with a reference
- Hosted online and linked
- Submitted as supplementary material

**Reference in thesis:**

```latex
An interactive visualization of the optimized allocation network is provided as supplementary material (see Appendix~\ref{app:interactive_maps}).
```

---

## Quick Copy/Paste Workflow

1. **Run both scripts:**
   ```bash
   python scripts/thesis/run_baseline_optimization.py
   python scripts/thesis/run_moo_pareto_analysis.py
   ```

2. **For each table in your thesis:**
   - Open the corresponding `.tex` file
   - Copy all content
   - Paste in the designated spot in the LaTeX template above
   - Compile thesis to verify formatting

3. **For the figure:**
   - Copy PNG to thesis `figures/` directory
   - Use the figure LaTeX template above

---

## Expected Table Sizes

| Table | Approx. Rows | Description |
|-------|--------------|-------------|
| Supplier Utilization | ~9 rows | One per supplier used |
| Capacity Summary | ~10-15 rows | Top binding/near-capacity depots |
| Representative Solutions | 3 rows | Min/Knee/Max points |

---

## Customization Notes

If you need to modify the generated LaTeX formatting:

1. **Number formatting:** Edit `_format_int()` and `_format_currency()` functions in the scripts
2. **Row styling:** Modify the `writer.write()` sections to add `\rowcol` or other commands
3. **Column alignment:** Already set to reasonable defaults (`l` for text, `r` for numbers)
4. **Caption text:** Provided in templates above, customize as needed

---

## Verification

After pasting, compile your thesis and check:
- ✓ Numbers are properly formatted with thousand separators
- ✓ Decimal places are appropriate (2 for currency, 4 for per-litre costs)
- ✓ Table fits within page margins
- ✓ Caption and label are correct
- ✓ Cross-references work (`\ref{tab:...}`)

---

**Last Updated:** 2025-09-30