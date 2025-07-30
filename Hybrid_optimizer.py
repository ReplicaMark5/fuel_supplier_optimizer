from MOO_e_constraint_Cost_Dynamic_2 import SelectiveNAFlexibleEConstraintOptimizer
from NSGA_II_Repair_Dynamic_2 import FixedFlexibleSupplyChainOptimizer

# hybrid_optimizer.py
def run_hybrid(file_path):
    moo = SelectiveNAFlexibleEConstraintOptimizer(file_path)
    allocations = moo.get_feasible_allocations(n_points=10)

    nsga = FixedFlexibleSupplyChainOptimizer(file_path)
    seeds = nsga.convert_allocations_dict_to_individual(allocations)

    return nsga.run_full_optimization(
        ngen=50, mu=100, lambda_=200, seed_individuals=seeds
    )


# Test Code 

#if __name__ == "__main__":
#    file_path = r"C:\Users\blake\OneDrive - Stellenbosch University\SUN 2\2025\Skripsie\Demo Data\Demo3.xlsx"  # <- Update this path
#    results = run_hybrid(file_path)
#    print(results.head())  # or display however you'd like
