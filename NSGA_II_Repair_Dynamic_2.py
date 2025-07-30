from deap import base, creator, tools, algorithms
import pandas as pd
import random
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import os

# CRITICAL: Set random seeds for reproducibility
random.seed(42)
np.random.seed(42)

class FixedFlexibleSupplyChainOptimizer:
    def __init__(self, file_path, sheet_names=None):
        """
        Initialize the optimizer with flexible data loading
        FIXED to match static version exactly + Selective NA handling
        """
        if sheet_names is None:
            sheet_names = {
                'obj1': 'Obj1_Coeff',
                'obj2': 'Obj2_Coeff', 
                'volumes': 'Annual Volumes'
            }
        
        self.file_path = file_path
        self.sheet_names = sheet_names
        self.load_data()
        self.setup_deap()
    
    def load_data(self):
        """Load and parse data from Excel file - FIXED with selective NA handling"""
        try:
            # Load data sheets
            self.df_data = pd.read_excel(self.file_path, sheet_name=self.sheet_names['obj1'])
            self.df_scores = pd.read_excel(self.file_path, sheet_name=self.sheet_names['obj2'])
            self.df_volume = pd.read_excel(self.file_path, sheet_name=self.sheet_names['volumes'])
            
            print("Original data shape:", self.df_data.shape)
            
            # Parse depot-supplier pairs from ALL rows (don't filter yet)
            self.df_data['Key'] = list(zip(self.df_data['Depot'], self.df_data['Supplier']))
            self.all_pairs = self.df_data['Key'].tolist()
            self.depots = sorted(set(i for i, _ in self.all_pairs))
            self.suppliers = sorted(set(j for _, j in self.all_pairs))
            
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
            
            # FIXED: Build feasible choices considering valid operations only
            from collections import defaultdict
            self.feasible_choices = defaultdict(list)
            self.suppliers_per_depot = defaultdict(set)
            
            for (i, j) in self.all_pairs:
                if j in self.suppliers:
                    supplier_idx = self.suppliers.index(j)
                    
                    # Only add Collection option if valid
                    if self.valid_collection[(i, j)]:
                        self.feasible_choices[i].append(2 * supplier_idx)     # Collection
                        self.suppliers_per_depot[i].add(j)
                    
                    # Only add Delivery option if valid
                    if self.valid_delivery[(i, j)]:
                        self.feasible_choices[i].append(2 * supplier_idx + 1) # Delivery  
                        self.suppliers_per_depot[i].add(j)
            
            # Check if any depot has no feasible choices
            empty_depots = [depot for depot, choices in self.feasible_choices.items() if len(choices) == 0]
            if empty_depots:
                raise ValueError(f"Depots {empty_depots} have no feasible operations after filtering NA values!")
            
            self.n_depots = len(self.depots)
            self.n_suppliers = len(self.suppliers)
            
            # Calculate choices per depot
            self.choices_per_depot = {}
            for depot in self.depots:
                self.choices_per_depot[depot] = len(self.feasible_choices[depot])
            
            # For display purposes, show the range
            min_choices = min(self.choices_per_depot.values())
            max_choices = max(self.choices_per_depot.values())
            self.choices_range = f"{min_choices}-{max_choices}" if min_choices != max_choices else str(min_choices)
            
            print(f"Data loaded: Depots={self.depots}, Suppliers={self.suppliers}")
            print(f"Feasible choices per depot: {dict(self.choices_per_depot)}")
            
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
            
            # Load volumes and scores (same as before)
            self.V = dict(zip(
                self.df_volume["Site Names"].str.extract(r"Depot (\d+)").astype(int)[0],
                self.df_volume["Annual Volume(Litres)"]
            ))
            self.V = {k: v for k, v in self.V.items() if pd.notna(k)}
            
            score_row = self.df_scores.iloc[6]
            score_row.index = score_row.index.str.strip()
            score_row = score_row.drop(labels=["Scoring Element", "Criteria Weighting"], errors="ignore")
            self.S = score_row.to_dict()
            
            self.DP = 23.0
            
            print(f"Volume data: {self.V}")
            print(f"Score data: {self.S}")
            
            # Print operation availability summary
            print("\nOperation availability summary:")
            for depot in self.depots:
                print(f"Depot {depot}:")
                for supplier in sorted(self.suppliers_per_depot[depot]):
                    operations = []
                    if self.valid_collection.get((depot, supplier), False):
                        operations.append("Collection")
                    if self.valid_delivery.get((depot, supplier), False):
                        operations.append("Delivery")
                    print(f"  Supplier {supplier}: {', '.join(operations) if operations else 'No valid operations'}")
            
        except Exception as e:
            print(f"Error loading data: {e}")
            raise
    
    def convert_allocations_dict_to_individual(self, alloc_dict):
        """
        Convert MOO decoded allocations {'C': {...}, 'D': {...}} to NSGA-II individual.
        """
        individual = []
        
        for depot in self.depots:
            gene_found = False

            # Check for Collection
            for (d, supplier) in alloc_dict.get('C', {}).keys():
                if d == depot and alloc_dict['C'][(d, supplier)] == 1:
                    if supplier in self.suppliers:
                        supplier_idx = self.suppliers.index(supplier)
                        gene = 2 * supplier_idx
                        individual.append(gene)
                        gene_found = True
                        break

            # If no collection found, check for Delivery
            if not gene_found:
                for (d, supplier) in alloc_dict.get('D', {}).keys():
                    if d == depot and alloc_dict['D'][(d, supplier)] == 1:
                        if supplier in self.suppliers:
                            supplier_idx = self.suppliers.index(supplier)
                            gene = 2 * supplier_idx + 1
                            individual.append(gene)
                            gene_found = True
                            break

            # If still not found, use random fallback
            if not gene_found:
                individual.append(random.choice(self.feasible_choices[depot]))

        return creator.Individual(individual)

    def setup_deap(self, indpb=0.2):
        """Setup DEAP framework - FIXED to match static version"""
        # Clear existing classes if they exist
        if hasattr(creator, 'FitnessMulti'):
            del creator.FitnessMulti
        if hasattr(creator, 'Individual'):
            del creator.Individual
        
        creator.create("FitnessMulti", base.Fitness, weights=(-1.0, 1.0))  # Min cost, Max score
        creator.create("Individual", list, fitness=creator.FitnessMulti)
        
        self.toolbox = base.Toolbox()
        
        def make_individual():
            return creator.Individual([
                random.choice(self.feasible_choices[depot]) for depot in self.depots
            ])

        self.toolbox.register("individual", make_individual)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("evaluate", self.evaluate)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", self.mutate_individual, indpb=indpb)  # Use dynamic indpb
        self.toolbox.register("select", tools.selNSGA2)
    
    # def make_low_cost_individual(self):
    #     individual = []
    #     for depot in self.depots:
    #         min_cost = float('inf')
    #         best_gene = None
    #         for gene in self.feasible_choices[depot]:
    #             supplier_idx = gene // 2
    #             is_collection = gene % 2 == 0
    #             supplier = self.suppliers[supplier_idx]
    #             key = (depot, supplier)
    #             cost_val = self.COST.get(key, 0) if is_collection else self.DEL.get(key, 0)
    #             if isinstance(cost_val, (int, float)) and cost_val < min_cost:
    #                 min_cost = cost_val
    #                 best_gene = gene
    #         individual.append(best_gene if best_gene is not None else random.choice(self.feasible_choices[depot]))
    #     return creator.Individual(individual)

    # def make_high_score_individual(self):
    #     individual = []
    #     for depot in self.depots:
    #         max_score = float('-inf')
    #         best_gene = None
    #         for gene in self.feasible_choices[depot]:
    #             supplier_idx = gene // 2
    #             supplier = self.suppliers[supplier_idx]
    #             score = self.S.get(f"Supplier {supplier}", 0)
    #             if score > max_score:
    #                 max_score = score
    #                 best_gene = gene
    #         individual.append(best_gene if best_gene is not None else random.choice(self.feasible_choices[depot]))
    #     return creator.Individual(individual)

    def decode_individual(self, ind):
        """
        Decode individual to C and D matrices with operation validity checking
        """
        C = {}
        D = {}
        
        # Initialize ALL pairs to 0 first
        for (i, j) in self.all_pairs:
            C[(i, j)] = 0
            D[(i, j)] = 0
        
        for depot_idx, gene_value in enumerate(ind):
            depot = self.depots[depot_idx]
            
            # Convert gene_value back to supplier and operation type
            supplier_idx = gene_value // 2
            is_collection = gene_value % 2 == 0
            
            if supplier_idx < len(self.suppliers):
                supplier = self.suppliers[supplier_idx]
                
                # Only set if this depot-supplier pair exists
                if (depot, supplier) in self.all_pairs:
                    if is_collection and self.valid_collection.get((depot, supplier), False):
                        C[(depot, supplier)] = 1
                    elif not is_collection and self.valid_delivery.get((depot, supplier), False):
                        D[(depot, supplier)] = 1
                    # If operation is invalid for this pair, it stays 0 (no operation)
        
        return C, D
    
    def evaluate(self, ind):
        """Evaluate individual fitness with selective coefficient usage"""
        C, D = self.decode_individual(ind)
        
        # Cost calculation with operation-specific coefficient checking (Objective Function: Cost)
        cost = 0
        for (i, j) in self.all_pairs:
            if i in self.V:  # Only include depots with volume data
                pair_cost = self.DP + self.ZD.get((i, j), 0)
                
                # Only subtract collection benefit if collection is valid and selected
                if C[i, j] == 1 and self.valid_collection.get((i, j), False):
                    coc_val = self.COC.get((i, j), 0)
                    cost_val = self.COST.get((i, j), 0)
                    # Only apply if both values are numeric and not NA
                    if isinstance(coc_val, (int, float)) and isinstance(cost_val, (int, float)):
                        pair_cost -= (coc_val - cost_val)
                
                # Only subtract delivery benefit if delivery is valid and selected
                if D[i, j] == 1 and self.valid_delivery.get((i, j), False):
                    del_val = self.DEL.get((i, j), 0)
                    # Only apply if value is numeric and not NA
                    if isinstance(del_val, (int, float)):
                        pair_cost -= del_val
                
                cost += self.V[i] * pair_cost
        
        # Score calculation (same as before) (Objective Function: Supplier Score)
        score = sum(
            self.S[f"Supplier {j}"] * (C[i, j] + D[i, j])
            for (i, j) in self.all_pairs
            if f"Supplier {j}" in self.S
        )
        
        return cost, score
    
    def mutate_individual(self, ind, indpb):
        """Mutate individual with depot-specific feasible choices"""
        for idx in range(len(ind)):
            if random.random() < indpb:
                depot = self.depots[idx]
                ind[idx] = random.choice(self.feasible_choices[depot])
        return ind,
    
    def repair_individual(self, ind):
        """Repair individual to ensure valid gene values for each depot"""
        for i in range(len(ind)):
            depot = self.depots[i]
            if ind[i] not in self.feasible_choices[depot]:
                # If invalid choice, select random valid choice for this depot
                ind[i] = random.choice(self.feasible_choices[depot])
        return ind
    
    def decode_solution_string(self, ind):
        """Convert individual to readable solution string"""
        C, D = self.decode_individual(ind)
        solution_parts = []
        
        for depot in self.depots:
            for supplier in self.suppliers:
                if (depot, supplier) in self.all_pairs:
                    if C.get((depot, supplier), 0) == 1:
                        solution_parts.append(f"C({depot},{supplier})")
                    elif D.get((depot, supplier), 0) == 1:
                        solution_parts.append(f"D({depot},{supplier})")
        
        return " ".join(solution_parts)
    
    def optimize(self, ngen=50, mu=100, lambda_=200, cxpb=0.7, mutpb=0.2, indpb=0.2, seed_individuals=None):
        """Run the optimization - EXACTLY like static version"""
        print(f"Starting optimization with {ngen} generations...")
        print(f"Population size: {mu}, Offspring: {lambda_}, Individual Mutation Rate: {indpb}")
        
        # Setup DEAP with the provided indpb
        self.setup_deap(indpb=indpb)


        # Initialize population
        if seed_individuals is not None:
            n_seeds = len(seed_individuals)
            pop = self.toolbox.population(n=mu - n_seeds)
            pop.extend(seed_individuals)
        else:
            pop = self.toolbox.population(n=mu)



        # Initialize population
       # pop = self.toolbox.population(n=mu)   
       
        
        # Evaluate initial population
        invalid_ind = [ind for ind in pop if not ind.fitness.valid]
        fitnesses = map(self.toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
        
        # Evolution loop
        for gen in range(ngen):
            print(f"Generation {gen + 1}/{ngen}")
            
            # Generate offspring
            offspring = algorithms.varAnd(pop, self.toolbox, cxpb=cxpb, mutpb=mutpb)

            
            # Repair offspring
            for ind in offspring:
                self.repair_individual(ind)
            
            # Evaluate offspring
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
            
            # Select next generation
            pop = self.toolbox.select(pop + offspring, k=mu)
            
            # Track progress
            pareto_solutions = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
            print(f"  Pareto optimal solutions: {len(pareto_solutions)}")
        
            print("Evolution completed!")
        return pop
    
    def extract_pareto_front(self, population):
        """Extract and format Pareto front solutions"""
        pareto_front = tools.sortNondominated(population, len(population), first_front_only=True)[0]
        
        results = []
        for ind in pareto_front:
            results.append({
                "cost": ind.fitness.values[0],
                "score": ind.fitness.values[1],
                "allocations": self.decode_solution_string(ind)
            })
        
        return pd.DataFrame(results)
    
    def run_full_optimization(self, **kwargs):
        """Run complete optimization with results export"""
        print("="*60)
        print("SELECTIVE NA HANDLING SUPPLY CHAIN OPTIMIZATION")
        print("="*60)
        print(f"Problem size: {self.n_depots} depots × {self.n_suppliers} suppliers")
        print(f"Total depot-supplier pairs: {len(self.all_pairs)}")
        print(f"Encoding: {self.n_depots} genes (compound encoding: supplier + operation per depot)")
        print(f"Choices per depot range: {self.choices_range}")
        
        # Show depot-specific information
        print("\nDepot-specific supplier availability:")
        for depot in self.depots:
            available_suppliers = sorted(self.suppliers_per_depot[depot])
            print(f"  Depot {depot}: Suppliers {available_suppliers} ({self.choices_per_depot[depot]} choices)")
        
        print("="*60)
        
        # Run optimization
        final_population = self.optimize(**kwargs)
        
        # Extract results
        df_pareto = self.extract_pareto_front(final_population)
        
        # Save results
        output_path = "Output Data/"
        os.makedirs(output_path, exist_ok=True)
        df_pareto.to_csv(f"{output_path}nsga-II_selective_na_handling.csv", index=False)
        
        # Print summary
        print("\nOptimization Results:")
        print(f"Pareto optimal solutions found: {len(df_pareto)}")
        print(f"Cost range: {df_pareto['cost'].min():.2f} - {df_pareto['cost'].max():.2f}")
        print(f"Score range: {df_pareto['score'].min():.2f} - {df_pareto['score'].max():.2f}")
        
        # Show sample solutions
        print("\nSample Pareto optimal solutions:")
        print(df_pareto.head())
        
        # Create visualizations
        self.create_plots(df_pareto, output_path)
        
        return df_pareto
    
    def create_plots(self, df_pareto, save_path):
        """Create plots"""
        # Matplotlib plot
        plt.figure(figsize=(8, 6))
        plt.scatter(df_pareto["cost"], df_pareto["score"], c='blue', alpha=0.7)
        plt.xlabel("Cost (Objective 1) - Minimize")
        plt.ylabel("Supplier Score (Objective 2) - Maximize")
        plt.title("NSGA-II Pareto Front: Selective NA Handling")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f"{save_path}nsga-II_selective_na_handling_plot.png")
       # plt.show()
        
        # Interactive plotly plot
        fig = px.scatter(df_pareto, x="cost", y="score", hover_data=["allocations"])
        fig.update_layout(
            title="NSGA-II Pareto Front (Interactive) - Selective NA Handling",
            xaxis_title="Cost (Minimize)",
            yaxis_title="Supplier Score (Maximize)"
        )
        #fig.show()
        
        # Print statistics
        unique_allocs = set(df_pareto["allocations"])
        print(f"\nUnique solutions found: {len(unique_allocs)}")
        print(f"Total Pareto optimal solutions: {len(df_pareto)}")


# Usage example
# if __name__ == "__main__":
#     # Set consistent random seed
#     random.seed(42)
#     np.random.seed(42)
    
#     file_path = r"C:\Users\blake\OneDrive - Stellenbosch University\SUN 2\2025\Skripsie\Demo Data\Demo3.xlsx"
    
#     try:
#         # Initialize optimizer with selective NA handling
#         optimizer = FixedFlexibleSupplyChainOptimizer(file_path)
        
#         # Run optimization
#         results = optimizer.run_full_optimization(
#             ngen=50,      
#             mu=100,       
#             lambda_=200,  
#             cxpb=0.7,     
#             mutpb=0.2     
#         )
        
#         print("\nOptimization with selective NA handling completed successfully!")
        
#     except Exception as e:
#         print(f"Error during optimization: {e}")
#         import traceback
#         traceback.print_exc()