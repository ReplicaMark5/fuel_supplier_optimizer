#!/usr/bin/env python3
"""
Interactive script to run precomputation and query depot costs.
Usage: python query_costs.py
"""

from precomputation import FuelOptimizationPrecomputation
import json

class CostQueryTool:
    """Tool for querying and analyzing precomputed fuel costs."""
    
    def __init__(self):
        """Initialize with precomputed data."""
        print("🚀 Loading precomputed cost data...")
        self.precomp = FuelOptimizationPrecomputation()
        self.data = self.precomp.run_complete_precomputation()
        self.costs = self.data['costs']
        self.depots = self.data['depots']
        self.suppliers = self.data['suppliers']
        print(f"✅ Data loaded! {len(self.costs)} depots, {sum(len(sd) for sd in self.costs.values())} depot-supplier combinations")
    
    def get_costs_for_depot_supplier(self, depot_id, supplier_depot_id, verbose=True):
        """Get all costs for a specific depot-supplier depot pair."""
        if depot_id not in self.costs:
            print(f"❌ Depot {depot_id} not found")
            return None
            
        if supplier_depot_id not in self.costs[depot_id]:
            print(f"❌ Supplier depot {supplier_depot_id} not available for depot {depot_id}")
            return None
        
        costs = self.costs[depot_id][supplier_depot_id]
        
        if verbose:
            self.print_cost_breakdown(depot_id, supplier_depot_id, costs)
        
        return costs
    
    def print_cost_breakdown(self, depot_id, supplier_depot_id, costs):
        """Print detailed cost breakdown."""
        print("="*80)
        print(f"COST BREAKDOWN: Customer Depot {depot_id} → Supplier Depot {supplier_depot_id}")
        print("="*80)
        
        # Basic info
        depot_info = self.depots[depot_id]
        supplier_name = costs.get('supplier_name', 'Unknown')
        distance_km = costs.get('distance_km', 'N/A')
        
        print(f"\n📋 BASIC INFORMATION:")
        print(f"   Customer Depot: {depot_info['name']} (Annual Volume: {depot_info['annual_volume']:,} L)")
        print(f"   Supplier: {supplier_name}")
        print(f"   Distance: {distance_km} km")
        
        # Separate cost types
        base_costs = {}
        rac_costs = {}
        tier_costs = {}
        
        for option, cost in costs.items():
            if isinstance(cost, (int, float)):  # Only process actual cost values
                if option.startswith('rac_'):
                    rac_costs[option] = cost
                elif 'tier_' in option:
                    tier_costs[option] = cost
                elif option in ['coc_cash', 'coc_30', 'coc_45', 'coc_60', 'del_own', 'del_buy', 'del_rent']:
                    base_costs[option] = cost
        
        # Print base costs
        print(f"\n💰 BASE COSTS ({len(base_costs)} options):")
        if base_costs:
            for option, cost in sorted(base_costs.items()):
                print(f"   {option:15}: R{cost:.6f}/L")
        else:
            print("   No base costs available")
        
        # Print RAC costs
        print(f"\n⚠️  RAC PENALTY COSTS ({len(rac_costs)} options):")
        if rac_costs:
            for option, cost in sorted(rac_costs.items()):
                base_option = option.replace('rac_', '')
                base_cost = base_costs.get(base_option)
                if base_cost:
                    penalty = cost - base_cost
                    print(f"   {option:15}: R{cost:.6f}/L (+R{penalty:.6f} penalty vs base)")
                else:
                    print(f"   {option:15}: R{cost:.6f}/L")
        else:
            print("   No RAC penalty costs available")
        
        # Print tier costs
        print(f"\n🎯 VOLUME TIER ENHANCED COSTS ({len(tier_costs)} options):")
        if tier_costs:
            # Group by tier band
            tier_bands = {}
            for option, cost in tier_costs.items():
                if 'tier_' in option:
                    tier_part = option.split('tier_')[1]
                    if tier_part not in tier_bands:
                        tier_bands[tier_part] = {}
                    base_option = option.split('_tier_')[0]
                    tier_bands[tier_part][base_option] = cost
            
            for band, band_costs in sorted(tier_bands.items()):
                print(f"   Tier Band: {band}")
                for option, cost in sorted(band_costs.items()):
                    base_cost = base_costs.get(option)
                    if base_cost:
                        savings = base_cost - cost
                        print(f"     {option:13}: R{cost:.6f}/L (saves R{savings:.6f} vs base)")
                    else:
                        print(f"     {option:13}: R{cost:.6f}/L")
                print()
        else:
            print("   No volume tier enhanced costs available")
            print("   (This depot-supplier combination doesn't participate in volume tiers)")
        
        # Cost comparison table
        self.print_cost_comparison_table(base_costs, rac_costs, tier_costs)
        
        print("="*80)
    
    def print_cost_comparison_table(self, base_costs, rac_costs, tier_costs):
        """Print a comparison table of all cost types."""
        if not (base_costs or rac_costs or tier_costs):
            return
            
        print(f"\n📊 COST COMPARISON TABLE:")
        print(f"{'Option':<15} {'Base Cost':<12} {'RAC Penalty':<13} {'Best Tier':<12} {'Tier Savings':<12}")
        print("-" * 70)
        
        all_base_options = set(base_costs.keys())
        
        for option in sorted(all_base_options):
            base_cost = base_costs.get(option, 0)
            rac_cost = rac_costs.get(f'rac_{option}', None)
            
            # Find best tier cost for this option
            best_tier_cost = None
            best_tier_name = None
            best_savings = 0
            
            for tier_option, tier_cost in tier_costs.items():
                if tier_option.startswith(f'{option}_tier_'):
                    if best_tier_cost is None or tier_cost < best_tier_cost:
                        best_tier_cost = tier_cost
                        best_tier_name = tier_option.split('tier_')[1]
                        best_savings = base_cost - tier_cost
            
            base_str = f"R{base_cost:.4f}" if base_cost else "N/A"
            rac_str = f"R{rac_cost:.4f}" if rac_cost else "N/A"
            tier_str = f"R{best_tier_cost:.4f}" if best_tier_cost else "N/A"
            savings_str = f"R{best_savings:.4f}" if best_savings > 0 else "None"
            
            print(f"{option:<15} {base_str:<12} {rac_str:<13} {tier_str:<12} {savings_str:<12}")
    
    def interactive_query(self):
        """Run interactive cost querying."""
        available_depots = sorted(list(self.costs.keys()))
        print(f"\n📋 Available depot IDs: {available_depots}")
        
        while True:
            print("\n" + "="*60)
            print("DEPOT COST QUERY OPTIONS")
            print("="*60)
            print("1. Query specific depot-supplier depot pair")
            print("2. List all supplier depots for a customer depot")
            print("3. Search for depots with volume tier costs")
            print("4. Compare costs across suppliers for a depot")
            print("5. Quit")
            
            choice = input("Select option (1-5): ").strip()
            
            if choice == '5' or choice.lower() in ['quit', 'q', 'exit']:
                print("👋 Goodbye!")
                break
            elif choice == '1':
                self.query_depot_supplier_pair()
            elif choice == '2':
                self.list_supplier_depots()
            elif choice == '3':
                self.search_tier_costs()
            elif choice == '4':
                self.compare_suppliers()
            else:
                print("❌ Please select option 1-5")
    
    def query_depot_supplier_pair(self):
        """Query specific depot-supplier depot pair."""
        depot_input = input("Enter customer depot ID: ").strip()
        
        try:
            depot_id = int(depot_input)
        except ValueError:
            print("❌ Please enter a valid depot ID number")
            return
            
        if depot_id not in self.costs:
            print(f"❌ Depot {depot_id} not found. Available: {sorted(list(self.costs.keys()))}")
            return
        
        # Show available supplier depots
        supplier_depots = sorted(list(self.costs[depot_id].keys()))
        print(f"\n📋 Available supplier depot IDs for depot {depot_id}: {supplier_depots}")
        
        supplier_depot_input = input("Enter supplier depot ID: ").strip()
        
        try:
            supplier_depot_id = int(supplier_depot_input)
        except ValueError:
            print("❌ Please enter a valid supplier depot ID number")
            return
            
        if supplier_depot_id not in supplier_depots:
            print(f"❌ Supplier depot {supplier_depot_id} not found for depot {depot_id}. Available: {supplier_depots}")
            return
        
        # Query the costs
        self.get_costs_for_depot_supplier(depot_id, supplier_depot_id)
    
    def list_supplier_depots(self):
        """List all supplier depots for a customer depot."""
        depot_input = input("Enter customer depot ID: ").strip()
        
        try:
            depot_id = int(depot_input)
        except ValueError:
            print("❌ Please enter a valid depot ID number")
            return
            
        if depot_id not in self.costs:
            print(f"❌ Depot {depot_id} not found")
            return
        
        depot_info = self.depots[depot_id]
        supplier_depots = self.costs[depot_id]
        
        print(f"\n🏢 Customer Depot {depot_id}: {depot_info['name']}")
        print(f"   Annual Volume: {depot_info['annual_volume']:,} L")
        print(f"   Available Supplier Depots ({len(supplier_depots)}):")
        
        for sd_id, sd_data in sorted(supplier_depots.items()):
            supplier_name = sd_data.get('supplier_name', 'Unknown')
            distance = sd_data.get('distance_km', 'N/A')
            
            # Count cost options
            cost_count = sum(1 for k, v in sd_data.items() if isinstance(v, (int, float)))
            tier_count = sum(1 for k in sd_data.keys() if 'tier_' in k)
            
            print(f"     {sd_id:3}: {supplier_name} ({distance} km) - {cost_count} options, {tier_count} tier costs")
    
    def search_tier_costs(self):
        """Search for depots with volume tier costs."""
        print("\n🔍 Searching for depots with volume tier enhanced costs...")
        
        tier_depots = []
        for depot_id, supplier_depots in self.costs.items():
            for sd_id, sd_data in supplier_depots.items():
                tier_options = [k for k in sd_data.keys() if 'tier_' in k]
                if tier_options:
                    tier_depots.append((depot_id, sd_id, len(tier_options), sd_data.get('supplier_name', 'Unknown')))
        
        if tier_depots:
            print(f"Found {len(tier_depots)} depot-supplier combinations with volume tier costs:")
            print(f"{'Depot':<6} {'Supplier':<4} {'Supplier Name':<20} {'Tier Options':<12}")
            print("-" * 50)
            
            for depot_id, sd_id, tier_count, supplier_name in sorted(tier_depots)[:20]:  # Show first 20
                print(f"{depot_id:<6} {sd_id:<8} {supplier_name:<20} {tier_count:<12}")
            
            if len(tier_depots) > 20:
                print(f"... and {len(tier_depots) - 20} more combinations")
            
            # Ask if user wants to query one
            query_input = input("\nEnter 'depot_id supplier_depot_id' to query (or press Enter to continue): ").strip()
            if query_input:
                try:
                    depot_id, sd_id = map(int, query_input.split())
                    self.get_costs_for_depot_supplier(depot_id, sd_id)
                except:
                    print("❌ Invalid input format. Use 'depot_id supplier_depot_id'")
        else:
            print("No depots found with volume tier enhanced costs")
    
    def compare_suppliers(self):
        """Compare costs across suppliers for a depot."""
        depot_input = input("Enter customer depot ID: ").strip()
        
        try:
            depot_id = int(depot_input)
        except ValueError:
            print("❌ Please enter a valid depot ID number")
            return
            
        if depot_id not in self.costs:
            print(f"❌ Depot {depot_id} not found")
            return
        
        depot_info = self.depots[depot_id]
        supplier_depots = self.costs[depot_id]
        
        print(f"\n💰 Cost Comparison for Depot {depot_id}: {depot_info['name']}")
        print(f"Annual Volume: {depot_info['annual_volume']:,} L")
        print("\nBest COC_30 costs across suppliers:")
        print(f"{'Supplier':<4} {'Name':<20} {'Distance':<10} {'COC_30 Base':<12} {'Best Tier':<12} {'Savings':<10}")
        print("-" * 80)
        
        comparisons = []
        for sd_id, sd_data in supplier_depots.items():
            supplier_name = sd_data.get('supplier_name', 'Unknown')[:19]
            distance = f"{sd_data.get('distance_km', 'N/A')} km"
            
            base_cost = sd_data.get('coc_30')
            
            # Find best tier cost for coc_30
            best_tier_cost = None
            tier_savings = 0
            
            for option, cost in sd_data.items():
                if option.startswith('coc_30_tier_') and isinstance(cost, (int, float)):
                    if best_tier_cost is None or cost < best_tier_cost:
                        best_tier_cost = cost
                        if base_cost:
                            tier_savings = base_cost - cost
            
            base_str = f"R{base_cost:.4f}" if base_cost else "N/A"
            tier_str = f"R{best_tier_cost:.4f}" if best_tier_cost else "N/A"
            savings_str = f"R{tier_savings:.4f}" if tier_savings > 0 else "None"
            
            comparisons.append((sd_id, supplier_name, distance, base_str, tier_str, savings_str, base_cost or float('inf')))
        
        # Sort by base cost
        for sd_id, name, dist, base, tier, savings, sort_key in sorted(comparisons, key=lambda x: x[6]):
            print(f"{sd_id:<4} {name:<20} {dist:<10} {base:<12} {tier:<12} {savings:<10}")

def main():
    """Main function to run the interactive query tool."""
    try:
        query_tool = CostQueryTool()
        query_tool.interactive_query()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()