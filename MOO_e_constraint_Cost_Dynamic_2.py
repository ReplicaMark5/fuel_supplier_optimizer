from docplex.mp.model import Model
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import os
import time
from datetime import datetime
from collections import defaultdict

class SelectiveNAFlexibleEConstraintOptimizer:
    def __init__(self, file_path, sheet_names=None, max_suppliers=None):
        """
        Initialize the e-constraint optimizer with selective NA handling
        """
        if sheet_names is None:
            sheet_names = {
                'obj1': 'Obj1_Coeff',
                'obj2': 'Obj2_Coeff', 
                'volumes': 'Annual Volumes'
            }
        
        self.file_path = file_path
        self.sheet_names = sheet_names
        self.max_suppliers = max_suppliers  # Maximum number of unique suppliers allowed
        self.load_data()
    
    def load_data(self):
        """Load and parse data from Excel file with selective NA handling"""
        try:
            # Load data sheets
            self.df_data = pd.read_excel(self.file_path, sheet_name=self.sheet_names['obj1'])
            self.df_scores = pd.read_excel(self.file_path, sheet_name=self.sheet_names['obj2'])
            self.df_volume = pd.read_excel(self.file_path, sheet_name=self.sheet_names['volumes'])
            
            print("Original data shape:", self.df_data.shape)
            print("Columns in df_data:", self.df_data.columns.tolist())
            
            # Parse depot-supplier pairs EXACTLY like the original
            self.df_data['Key'] = list(zip(self.df_data['Depot'], self.df_data['Supplier']))
            self.all_pairs = self.df_data['Key'].tolist()
            self.depots = sorted(set(i for i, _ in self.all_pairs))
            self.suppliers = sorted(set(j for _, j in self.all_pairs))
            
            self.n_depots = len(self.depots)
            self.n_suppliers = len(self.suppliers)
            
            # SELECTIVE NA HANDLING: Check which operations are valid for each pair
            self.valid_collection = {}  # (depot, supplier) -> bool
            self.valid_delivery = {}    # (depot, supplier) -> bool
            
            for idx, row in self.df_data.iterrows():
                key = (row['Depot'], row['Supplier'])
                
                # Check if Collection is valid (needs COC Rebate and Cost of Collection)
                coc_valid = not (pd.isna(row['COC Rebate(R/L)']) or row['COC Rebate(R/L)'] == 'NA')
                cost_valid = not (pd.isna(row['Cost of Collection (R/L)']) or row['Cost of Collection (R/L)'] == 'NA')
                self.valid_collection[key] = coc_valid and cost_valid
                
                # Check if Delivery is valid (needs DEL Rebate)
                del_valid = not (pd.isna(row['DEL Rebate(R/L)']) or row['DEL Rebate(R/L)'] == 'NA')
                self.valid_delivery[key] = del_valid
                
                # Report invalid operations
                if not self.valid_collection[key]:
                    print(f"Collection DISABLED for Depot {key[0]} - Supplier {key[1]} (COC or Cost NA)")
                if not self.valid_delivery[key]:
                    print(f"Delivery DISABLED for Depot {key[0]} - Supplier {key[1]} (DEL NA)")
            
            # Check if any depot has no valid operations at all
            depot_has_valid_operation = defaultdict(bool)
            for (depot, supplier) in self.all_pairs:
                if self.valid_collection.get((depot, supplier), False) or self.valid_delivery.get((depot, supplier), False):
                    depot_has_valid_operation[depot] = True
            
            empty_depots = [depot for depot in self.depots if not depot_has_valid_operation[depot]]
            if empty_depots:
                raise ValueError(f"Depots {empty_depots} have no feasible operations after filtering NA values!")
            
            print(f"Data loaded: Depots={self.depots}, Suppliers={self.suppliers}")
            print(f"Available depot-supplier pairs: {len(self.all_pairs)}")
            
            # Create coefficient dictionaries for ALL pairs (we'll handle NA during evaluation)
            self.COC = dict(zip(self.df_data['Key'], self.df_data['COC Rebate(R/L)']))
            self.DEL = dict(zip(self.df_data['Key'], self.df_data['DEL Rebate(R/L)']))
            self.COST = dict(zip(self.df_data['Key'], self.df_data['Cost of Collection (R/L)']))
            self.ZD = dict(zip(self.df_data['Key'], self.df_data['Zone Differentials']))
            
            # Convert to numeric where possible, keep NA as is for now
            for key in self.all_pairs:
                # Only convert if not NA
                if not (pd.isna(self.COC[key]) or self.COC[key] == 'NA'):
                    self.COC[key] = pd.to_numeric(self.COC[key], errors='coerce')
                if not (pd.isna(self.DEL[key]) or self.DEL[key] == 'NA'):
                    self.DEL[key] = pd.to_numeric(self.DEL[key], errors='coerce')
                if not (pd.isna(self.COST[key]) or self.COST[key] == 'NA'):
                    self.COST[key] = pd.to_numeric(self.COST[key], errors='coerce')
                # Zone differentials should always be numeric
                self.ZD[key] = pd.to_numeric(self.ZD[key], errors='coerce')
            
            # Check if Distance column exists (from original but not used in calculations)
            if 'Distance(Km)' in self.df_data.columns:
                self.DIST = dict(zip(self.df_data['Key'], self.df_data['Distance(Km)']))
            
            # Parse volume data - handle different possible formats
            if "Site Names" in self.df_volume.columns:
                # Extract depot number from 'Depot 1', 'Depot 2', etc.
                depot_numbers = self.df_volume["Site Names"].str.extract(r"Depot (\d+)").astype(int)[0]
                self.V = dict(zip(depot_numbers, self.df_volume["Annual Volume(Litres)"]))
            elif "Depot" in self.df_volume.columns:
                # Direct depot column
                self.V = dict(zip(self.df_volume["Depot"], self.df_volume["Annual Volume(Litres)"]))
            else:
                raise ValueError("Cannot find depot information in volume data")
            
            # Remove NaN keys from volume data
            self.V = {k: v for k, v in self.V.items() if pd.notna(k)}
            
            # Parse score data EXACTLY like original
            score_row = self.df_scores.iloc[6]  # Row 6 contains the total scores
            score_row.index = score_row.index.str.strip()
            score_row = score_row.drop(labels=["Scoring Element", "Criteria Weighting"], errors="ignore")
            self.S = score_row.to_dict()
            
            # Same diesel price as original
            self.DP = 23.0
            
            print(f"Volume data: {self.V}")
            print(f"Score data: {self.S}")
            
            # Identify which depots have suppliers available for valid operations
            self.depot_suppliers = defaultdict(set)
            for (i, j) in self.all_pairs:
                # Only include supplier for depot if at least one operation is valid
                if self.valid_collection.get((i, j), False) or self.valid_delivery.get((i, j), False):
                    self.depot_suppliers[i].add(j)
            
            print("Depot-supplier availability (with valid operations):")
            for depot in self.depots:
                available_suppliers = sorted(self.depot_suppliers[depot])
                print(f"  Depot {depot}: Suppliers {available_suppliers}")
            
            # Print operation availability summary
            print("\nOperation availability summary:")
            for depot in self.depots:
                print(f"Depot {depot}:")
                for supplier in sorted(self.depot_suppliers[depot]):
                    operations = []
                    if self.valid_collection.get((depot, supplier), False):
                        operations.append("Collection")
                    if self.valid_delivery.get((depot, supplier), False):
                        operations.append("Delivery")
                    print(f"  Supplier {supplier}: {', '.join(operations) if operations else 'No valid operations'}")
            
        except Exception as e:
            print(f"Error loading data: {e}")
            raise
    
    def create_model(self, epsilon, constraint_type="cost"):
        """
        Create optimization model with e-constraint and selective operation constraints
        constraint_type: "cost" or "score" - which objective to constrain
        """
        model_name = f"E_Constraint_SelectiveNA_{constraint_type}≤{epsilon:.0f}"
        mdl = Model(name=model_name)
        
        # Decision variables for all available depot-supplier pairs
        C = mdl.binary_var_dict(self.all_pairs, name="C")  # Collection
        D = mdl.binary_var_dict(self.all_pairs, name="D")  # Delivery
        
        # Binary variables for whether each supplier is used (for max suppliers constraint)
        if self.max_suppliers is not None:
            Y = mdl.binary_var_dict(self.suppliers, name="Y")  # 1 if supplier is used, 0 otherwise
        
        # Constraint: Exactly one valid allocation per depot
        for depot in self.depots:
            available_suppliers = list(self.depot_suppliers[depot])
            if available_suppliers:  # Only add constraint if depot has suppliers with valid operations
                valid_operations = []
                for supplier in available_suppliers:
                    if self.valid_collection.get((depot, supplier), False):
                        valid_operations.append(C[depot, supplier])
                    if self.valid_delivery.get((depot, supplier), False):
                        valid_operations.append(D[depot, supplier])
                
                if valid_operations:  # Only add constraint if there are valid operations
                    mdl.add_constraint(
                        mdl.sum(valid_operations) == 1,
                        ctname=f"one_valid_allocation_depot_{depot}"
                    )
        
        # Constraint: Disable invalid operations explicitly
        for (depot, supplier) in self.all_pairs:
            if not self.valid_collection.get((depot, supplier), False):
                mdl.add_constraint(C[depot, supplier] == 0, ctname=f"disable_collection_{depot}_{supplier}")
            if not self.valid_delivery.get((depot, supplier), False):
                mdl.add_constraint(D[depot, supplier] == 0, ctname=f"disable_delivery_{depot}_{supplier}")
        
        # Max suppliers constraint (if enabled)
        if self.max_suppliers is not None:
            # Link supplier usage variables to allocation variables
            for supplier in self.suppliers:
                supplier_operations = []
                for depot in self.depots:
                    if (depot, supplier) in self.all_pairs:
                        supplier_operations.extend([C[depot, supplier], D[depot, supplier]])
                
                if supplier_operations:
                    # Y[supplier] = 1 if any operation uses this supplier
                    mdl.add_constraint(
                        Y[supplier] >= (1.0 / len(supplier_operations)) * mdl.sum(supplier_operations),
                        ctname=f"link_supplier_usage_{supplier}"
                    )
                    # Y[supplier] <= sum of all operations for this supplier
                    mdl.add_constraint(
                        Y[supplier] <= mdl.sum(supplier_operations),
                        ctname=f"limit_supplier_usage_{supplier}"
                    )
            
            # Limit total number of suppliers used
            mdl.add_constraint(
                mdl.sum(Y[supplier] for supplier in self.suppliers) <= self.max_suppliers,
                ctname="max_suppliers_constraint"
            )
        
        # Define objectives with selective coefficient usage
        # Cost objective (to minimize) - only apply coefficients for valid operations
        cost_terms = []
        for (i, j) in self.all_pairs:
            if i in self.V:  # Only include depots with volume data
                base_cost = self.DP + self.ZD.get((i, j), 0)
                
                # Collection cost reduction - only if valid and coefficients are numeric
                collection_benefit = 0
                if self.valid_collection.get((i, j), False):
                    coc_val = self.COC.get((i, j), 0)
                    cost_val = self.COST.get((i, j), 0)
                    if isinstance(coc_val, (int, float)) and isinstance(cost_val, (int, float)):
                        collection_benefit = C[i, j] * (coc_val - cost_val)
                
                # Delivery cost reduction - only if valid and coefficient is numeric
                delivery_benefit = 0
                if self.valid_delivery.get((i, j), False):
                    del_val = self.DEL.get((i, j), 0)
                    if isinstance(del_val, (int, float)):
                        delivery_benefit = D[i, j] * del_val
                
                cost_terms.append(self.V[i] * (base_cost - collection_benefit - delivery_benefit))
        
        cost_obj = mdl.sum(cost_terms) if cost_terms else 0
        
        # Score objective (to maximize) - only for valid operations
        score_terms = []
        for (i, j) in self.all_pairs:
            if f"Supplier {j}" in self.S:  # Only include suppliers with score data
                # Only count operations that are valid
                valid_ops = []
                if self.valid_collection.get((i, j), False):
                    valid_ops.append(C[i, j])
                if self.valid_delivery.get((i, j), False):
                    valid_ops.append(D[i, j])
                
                if valid_ops:
                    score_terms.append(self.S[f"Supplier {j}"] * mdl.sum(valid_ops))
        
        score_obj = mdl.sum(score_terms) if score_terms else 0
        
        # Apply e-constraint based on constraint type
        if constraint_type == "cost":
            # Constrain cost, maximize score
            mdl.add_constraint(cost_obj <= epsilon, ctname="epsilon_constraint")
            mdl.maximize(score_obj)
            primary_obj = score_obj
            constrained_obj = cost_obj
        else:  # constraint_type == "score"
            # Constrain score, minimize cost
            mdl.add_constraint(score_obj >= epsilon, ctname="epsilon_constraint")
            mdl.minimize(cost_obj)
            primary_obj = cost_obj
            constrained_obj = score_obj
        
        return mdl, C, D, cost_obj, score_obj, primary_obj, constrained_obj
    
    def solve_single_epsilon(self, epsilon, constraint_type="cost"):
        """Solve optimization for a single epsilon value"""
        mdl, C, D, cost_obj, score_obj, primary_obj, constrained_obj = self.create_model(epsilon, constraint_type)
        
        # Solve the model
        solution = mdl.solve()
        
        if solution:
            # Extract allocations - only show valid operations
            allocations = []
            for (i, j) in self.all_pairs:
                if C[i, j].solution_value == 1 and self.valid_collection.get((i, j), False):
                    allocations.append(f"C({i},{j})")
                elif D[i, j].solution_value == 1 and self.valid_delivery.get((i, j), False):
                    allocations.append(f"D({i},{j})")
            
            result = {
                "epsilon": epsilon,
                "cost": cost_obj.solution_value,
                "score": score_obj.solution_value,
                "allocations": " ".join(allocations),
                "status": "Optimal"
            }

        else:
            result = {
                "epsilon": epsilon,
                "cost": None,
                "score": None,
                "allocations": "No solution",
                "status": "Infeasible"
            }
        
        # Clean up model to free memory
        mdl.end()
        
        return result
    
    def optimize_epsilon_constraint(self, epsilon_range=None, n_points=21, constraint_type="cost"):
        """
        Run e-constraint optimization across epsilon range
        
        Args:
            epsilon_range: tuple (min, max) or None for auto-detection
            n_points: number of epsilon points to test
            constraint_type: "cost" or "score" - which objective to constrain
        """
        print(f"Starting e-constraint optimization with {constraint_type} constraint and selective NA handling...")
        
        # Auto-detect epsilon range if not provided
        if epsilon_range is None:
            epsilon_range = self.detect_epsilon_range(constraint_type)
        
        self.last_epsilon_range = (float(epsilon_range[0]), float(epsilon_range[1])) if epsilon_range else None
        epsilons = np.linspace(epsilon_range[0], epsilon_range[1], n_points)
        print(f"Testing {n_points} epsilon values from {epsilon_range[0]:.2e} to {epsilon_range[1]:.2e}")

        results = []
        for i, eps in enumerate(epsilons):
            print(f"Solving epsilon {i+1}/{n_points}: {eps:.2e}")
            epsilon_start = time.time()
            result = self.solve_single_epsilon(eps, constraint_type)
            result["epsilon_index"] = i
            result["solve_time_seconds"] = time.time() - epsilon_start
            results.append(result)

        return pd.DataFrame(results)
    
    def detect_epsilon_range(self, constraint_type="cost"):
        """
        Detect reasonable epsilon range by solving extreme cases with selective NA handling
        """
        print("Detecting epsilon range with selective NA handling...")
        
        # Solve for minimum cost (ignore score)
        mdl_min_cost, C, D, cost_obj, score_obj, _, _ = self.create_model(float('inf'), "cost")
        mdl_min_cost.minimize(cost_obj)
        sol_min_cost = mdl_min_cost.solve()
        
        # Solve for maximum score (ignore cost)  
        mdl_max_score, C2, D2, cost_obj2, score_obj2, _, _ = self.create_model(0, "score")
        mdl_max_score.maximize(score_obj2)
        sol_max_score = mdl_max_score.solve()
        
        if constraint_type == "cost":
            if sol_min_cost and sol_max_score:
                min_cost = cost_obj.solution_value
                max_cost = cost_obj2.solution_value
                epsilon_range = (min_cost, max_cost)
                print(f"Detected cost range: {min_cost:.2e} to {max_cost:.2e}")
            else:
                print("Warning: Could not detect range, using default")
                epsilon_range = (2.280e+08, 2.295e+08)  # Default from original
        else:  # score constraint
            if sol_min_cost and sol_max_score:
                min_score = score_obj.solution_value
                max_score = score_obj2.solution_value
                epsilon_range = (min_score, max_score)
                print(f"Detected score range: {min_score:.2e} to {max_score:.2e}")
            else:
                print("Warning: Could not detect range, using default")
                epsilon_range = (50, 200)  # Reasonable default for scores
        
        # Clean up models
        mdl_min_cost.end()
        mdl_max_score.end()
        
        return epsilon_range
    
    def run_full_optimization(self, epsilon_range=None, n_points=21, constraint_type="cost", show_plots: bool = True, **kwargs):


        """Run complete e-constraint optimization with results export"""
        start_time = time.time()
        run_timestamp = datetime.utcnow().isoformat()
        print("="*60)
        print("SELECTIVE NA HANDLING E-CONSTRAINT OPTIMIZATION")
        print("="*60)
        print(f"Problem size: {self.n_depots} depots × {self.n_suppliers} suppliers")
        print(f"Total depot-supplier pairs: {len(self.all_pairs)}")
        print(f"Constraint type: {constraint_type.upper()}")
        
        # Show depot-specific information
        print("\nDepot-supplier availability (with valid operations):")
        for depot in self.depots:
            available_suppliers = sorted(self.depot_suppliers[depot])
            print(f"  Depot {depot}: Suppliers {available_suppliers}")
        
        # Show operation validity summary
        valid_collection_count = sum(1 for key in self.all_pairs if self.valid_collection.get(key, False))
        valid_delivery_count = sum(1 for key in self.all_pairs if self.valid_delivery.get(key, False))
        print(f"\nOperation validity:")
        print(f"  Valid collection operations: {valid_collection_count}/{len(self.all_pairs)}")
        print(f"  Valid delivery operations: {valid_delivery_count}/{len(self.all_pairs)}")
        
        print("="*60)
        
        # Run optimization
        df_pareto = self.optimize_epsilon_constraint(epsilon_range, n_points, constraint_type)

        # Filter out infeasible solutions
        df_feasible = df_pareto[df_pareto['status'] == 'Optimal'].copy()

        run_duration = time.time() - start_time
        epsilon_range_used = getattr(self, "last_epsilon_range", None)
        output_path = "Output Data/"
        os.makedirs(output_path, exist_ok=True)

        metadata = {
            "run_timestamp": run_timestamp,
            "constraint_type": constraint_type,
            "n_points": n_points,
            "epsilon_range_min": epsilon_range_used[0] if epsilon_range_used else None,
            "epsilon_range_max": epsilon_range_used[1] if epsilon_range_used else None,
            "max_suppliers": self.max_suppliers,
            "total_points": int(len(df_pareto)),
            "feasible_points": int(len(df_feasible)),
            "feasible_ratio": float(len(df_feasible) / len(df_pareto)) if len(df_pareto) > 0 else 0.0,
            "runtime_seconds": run_duration,
            "solve_time_mean_seconds": None,
            "solve_time_std_seconds": None,
            "cost_min": float(df_feasible['cost'].min()) if len(df_feasible) > 0 else None,
            "cost_max": float(df_feasible['cost'].max()) if len(df_feasible) > 0 else None,
            "score_min": float(df_feasible['score'].min()) if len(df_feasible) > 0 else None,
            "score_max": float(df_feasible['score'].max()) if len(df_feasible) > 0 else None,
        }

        if 'solve_time_seconds' in df_pareto.columns and len(df_pareto) > 0:
            solve_times = df_pareto['solve_time_seconds'].dropna()
            if not solve_times.empty:
                metadata["solve_time_mean_seconds"] = float(solve_times.mean())
                metadata["solve_time_std_seconds"] = float(solve_times.std(ddof=0))

        metadata_path = os.path.join(output_path, "MOO_e_constraint_run_metadata.csv")
        metadata_df = pd.DataFrame([metadata])
        metadata_df.to_csv(metadata_path, mode='a', header=not os.path.exists(metadata_path), index=False)
        self.last_run_metadata = metadata
        self.last_run_results = df_pareto.copy()

        # Save results
        df_pareto.to_csv(f"{output_path}MOO_e-const_{constraint_type}_selective_na_pareto.csv", index=False)

        if len(df_feasible) == 0:
            print("No feasible solutions found!")
            return df_pareto

        # Print summary
        print(f"\nOptimization Results ({constraint_type} constraint with selective NA handling):")
        print(f"Total epsilon points tested: {len(df_pareto)}")
        print(f"Feasible solutions found: {len(df_feasible)}")
        if len(df_feasible) > 0:
            print(f"Cost range: {df_feasible['cost'].min():.2f} - {df_feasible['cost'].max():.2f}")
            print(f"Score range: {df_feasible['score'].min():.2f} - {df_feasible['score'].max():.2f}")
        
        # Show sample solutions
        print(f"\nSample Pareto optimal solutions:")
        print(df_feasible.head())
        
        # Create visualizations (optional for headless/sandboxed runs)
        if show_plots:
            self.create_plots(df_feasible, output_path, constraint_type)
        
        return df_pareto
    
    def create_plots(self, df_pareto, save_path, constraint_type):
        """Create plots for e-constraint results"""
        if len(df_pareto) == 0:
            print("No data to plot")
            return
            
        # Matplotlib plot
        plt.figure(figsize=(8, 6))
        plt.plot(df_pareto["score"], df_pareto["cost"], marker='o', linestyle='-', alpha=0.7)
        plt.xlabel("Supplier Score (↑)")
        plt.ylabel("Total Cost (↓)")
        plt.title(f"Pareto Front: Cost vs Supplier Score (E-Constraint: {constraint_type}, Selective NA)")
        plt.grid(True)
        plt.gca().invert_yaxis()  # Lower cost is better
        plt.tight_layout()
        plt.savefig(f"{save_path}MOO_e-const_{constraint_type}_selective_na_pareto_plot.png")
        plt.show()
        
        # Interactive plotly plot
        fig = px.scatter(
            df_pareto,
            x="cost",
            y="score", 
            color="epsilon",
            hover_data=["epsilon", "allocations"],
            title=f"Interactive Pareto Front: E-Constraint Selective NA ({constraint_type} constraint)"
        )
        fig.update_layout(
            xaxis_title="Cost (Minimize)",
            yaxis_title="Supplier Score (Maximize)"
        )
        fig.show()
        
        # Print additional statistics
        unique_allocs = set(df_pareto["allocations"])
        print(f"\nUnique allocation patterns found: {len(unique_allocs)}")
        print(f"Total Pareto optimal solutions: {len(df_pareto)}")

    def get_feasible_allocations(self, n_points=10, constraint_type="cost"):
        """
        Run MOO and extract decoded allocation dicts (C, D) for each feasible solution.
        """
        df = self.optimize_epsilon_constraint(n_points=n_points, constraint_type=constraint_type)
        df_feasible = df[df['status'] == 'Optimal'].copy()

        allocations_list = []
        for row in df_feasible.itertuples():
            allocation_str = getattr(row, "allocations")
            C = {}
            D = {}
            for item in allocation_str.split():
                if item.startswith("C("):
                    i, j = map(int, item[2:-1].split(','))
                    C[(i, j)] = 1
                elif item.startswith("D("):
                    i, j = map(int, item[2:-1].split(','))
                    D[(i, j)] = 1
            allocations_list.append({"C": C, "D": D})
        
        return allocations_list


# # Usage example
# if __name__ == "__main__":
#     # Example file path - update this to match your file
#     file_path = r"C:\Users\blake\OneDrive - Stellenbosch University\SUN 2\2025\Skripsie\Demo Data\Demo3.xlsx"
    
#     try:
#         # Initialize optimizer with selective NA handling
#         optimizer = SelectiveNAFlexibleEConstraintOptimizer(file_path)
        
#         # Run optimization with cost constraint (like original)
#         print("Running with COST constraint (maximize score, limit cost) with selective NA handling:")
#         results_cost = optimizer.run_full_optimization(
#             n_points=21,
#             constraint_type="cost"
#         )
        
#         print("\n" + "="*60 + "\n")
        
#         # Run optimization with score constraint (alternative approach)
#         print("Running with SCORE constraint (minimize cost, require minimum score) with selective NA handling:")
#         results_score = optimizer.run_full_optimization(
#             n_points=21,
#             constraint_type="score"
#         )
        
#         print("\nSelective NA handling e-constraint optimization completed successfully!")
        
#     except Exception as e:
#         print(f"Error during optimization: {e}")
#         import traceback
#         traceback.print_exc()
