import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from NSGA_II_Repair_Dynamic_2 import FixedFlexibleSupplyChainOptimizer
import importlib
MOO_e_constraint = importlib.import_module("MOO_e_constraint_Cost_Dynamic_2")
SelectiveNAFlexibleEConstraintOptimizer = MOO_e_constraint.SelectiveNAFlexibleEConstraintOptimizer
import numpy as np
import random
import optuna
from scipy.spatial.distance import cdist  # For distance between Pareto points
from Hybrid_optimizer import run_hybrid

def generate_supplier_ranking(allocations_str, optimizer_instance):
    """
    Generate supplier ranking for each depot based on the selected solution.
    
    Args:
        allocations_str: String containing allocations like "C(1,2) D(3,1)"
        optimizer_instance: The optimizer instance with cost and score data
    
    Returns:
        dict: Depot -> list of suppliers ranked by cost (lowest to highest)
    """
    if not allocations_str or allocations_str.lower() in ["no solution", "none", ""]:
        return {}
    
    # Parse allocations
    allocations = allocations_str.split()
    depot_allocations = {}
    
    for alloc in allocations:
        if '(' in alloc and ')' in alloc:
            operation = alloc[0]
            params = alloc[2:-1]
            if ',' in params:
                depot, supplier = params.split(',')
                depot = int(depot)
                supplier = int(supplier)
                
                if depot not in depot_allocations:
                    depot_allocations[depot] = []
                depot_allocations[depot].append({
                    'supplier': supplier,
                    'operation': operation,
                    'score': optimizer_instance.S.get(f"Supplier {supplier}", 0)
                })
    
    # Generate ranking for each depot
    depot_rankings = {}
    for depot in optimizer_instance.depots:
        if depot in depot_allocations:
            # Get the selected supplier for this depot
            selected_suppliers = depot_allocations[depot]
            
            # Get all available suppliers for this depot with their costs
            available_suppliers = []
            for supplier in optimizer_instance.suppliers:
                # Check if this supplier is available for this depot
                if (depot, supplier) in optimizer_instance.all_pairs:
                    score = optimizer_instance.S.get(f"Supplier {supplier}", 0)
                    is_selected = any(s['supplier'] == supplier for s in selected_suppliers)
                    
                    # Calculate cost for this depot-supplier pair
                    base_cost = optimizer_instance.DP + optimizer_instance.ZD.get((depot, supplier), 0)
                    
                    # Calculate cost reductions for valid operations
                    collection_reduction = 0
                    delivery_reduction = 0
                    
                    # Collection cost reduction (if valid)
                    if optimizer_instance.valid_collection.get((depot, supplier), False):
                        coc_val = optimizer_instance.COC.get((depot, supplier), 0)
                        cost_val = optimizer_instance.COST.get((depot, supplier), 0)
                        if isinstance(coc_val, (int, float)) and isinstance(cost_val, (int, float)):
                            collection_reduction = coc_val - cost_val
                    
                    # Delivery cost reduction (if valid)
                    if optimizer_instance.valid_delivery.get((depot, supplier), False):
                        del_val = optimizer_instance.DEL.get((depot, supplier), 0)
                        if isinstance(del_val, (int, float)):
                            delivery_reduction = del_val
                    
                    # Calculate total cost (base cost minus best possible reduction)
                    total_cost = base_cost - max(collection_reduction, delivery_reduction)
                    
                    available_suppliers.append({
                        'supplier': supplier,
                        'score': score,
                        'cost': total_cost,
                        'is_selected': is_selected,
                        'operation': next((s['operation'] for s in selected_suppliers if s['supplier'] == supplier), None)
                    })
            
            # Sort by cost (ascending - lowest cost first) and add ranking
            available_suppliers.sort(key=lambda x: x['cost'])
            for i, supplier_info in enumerate(available_suppliers):
                supplier_info['rank'] = i + 1
            
            depot_rankings[depot] = available_suppliers
    
    return depot_rankings

# Configure page
st.set_page_config(
    page_title="Multi-Objective Optimizer Comparison (NSGA-II vs ε-Constraint vs Hybrid)",
    page_icon="🏭",
    layout="wide"
)# Side

st.title("Multi-Objective Optimizer Comparison (NSGA-II vs ε-Constraint vs Hybrid)")
st.markdown("*Compare multi-objective optimization methods with selective NA handling*")

# Initialize session state for file path
if 'file_path' not in st.session_state:
    st.session_state.file_path = "/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Demo3.xlsx"

# Sidebar controls
with st.sidebar:
    st.header("📁 Data Configuration")
    
    # File path input
    file_path = st.text_input(
        "Excel File Path", 
        value=st.session_state.file_path,
        help="Path to your Excel file containing optimization data"
    )
    st.session_state.file_path = file_path
    
    # Sheet name configuration
    st.subheader("📋 Sheet Names")
    obj1_sheet = st.text_input("Objective 1 Coefficients", value="Obj1_Coeff")
    obj2_sheet = st.text_input("Objective 2 Coefficients", value="Obj2_Coeff") 
    volumes_sheet = st.text_input("Annual Volumes", value="Annual Volumes")
    
    sheet_names = {
        'obj1': obj1_sheet,
        'obj2': obj2_sheet,
        'volumes': volumes_sheet
    }
    
    st.divider()
    
    optimization_method = st.selectbox(
        "Select Method",
        ["NSGA-II", "ε-Constraint", "Hybrid"],
        help="Choose which optimization method to run"
    )

    
    st.header("⚙️ Algorithm Parameters")
    
    # NSGA-II Parameters
    if optimization_method in ["NSGA-II", "Hybrid"]:
        st.subheader("NSGA-II Parameters")
        # Runtime controls 
        st.markdown("Runtime controls")
        n_gen = st.slider("Number of Generations", 10, 200, 200, help="How many iterations the algorithm runs")
        pop_size = st.slider("Population Size", 50, 500, 500, help="Number of individuals per generation")
        offspring_size = st.slider("Offspring Size", 50, 500, 250, help="Number of new individuals per generation")
        crossover_prob = st.slider("Crossover Probability", 0.0, 1.0, 0.75, help="Probability that two selected parents will undergo crossover")
        mutation_prob = st.slider("Mutation Probability", 0.0, 1.0, 0.80, help="Probability that an individual will undergo mutation")
        # Operator Definitions 
        st.markdown("Operator Definitions")
        indpb = st.slider("Mutation Rate per Gene", 0.0, 1.0, 0.05, help="Probability of mutation per gene in an individual")
    

    # ε-Constraint Parameters
    if optimization_method in ["ε-Constraint", "Hybrid"]:
        st.subheader("ε-Constraint Parameters")
        n_points = st.slider("Number of Epsilon Points", 5, 400, 21, help="Number of points to test in the Pareto front")
        constraint_type = st.selectbox("Constraint Type", ["cost", "score"], help="Which objective to constrain")

    st.divider()
    
    # Maximum Suppliers Constraint (applies to all methods)
    st.markdown("**Supply Chain Constraints**")
    enable_max_suppliers = st.checkbox("Enable Maximum Suppliers Constraint", value=False, help="Limit the total number of unique suppliers that can be allocated across all depots")
    
    max_suppliers = None
    if enable_max_suppliers:
        max_suppliers = st.slider("Maximum Number of Suppliers", min_value=1, max_value=20, value=3, help="Maximum number of unique suppliers allowed to serve all depots")
        st.info(f"🏢 Constraint: At most {max_suppliers} unique suppliers can be selected to serve all depots")

    
    random_seed = st.number_input("Random Seed", value=42, help="For reproducible results")
    
    st.divider()
    
    st.header("📋 Instructions")
    st.markdown("""
    1. Configure data file path and sheet names
    2. Select optimization method(s)
    3. Adjust algorithm parameters
    4. Click **Initialize & Analyze Data**
    5. Click **Run Optimization**
    6. **Click any point** on the Pareto front to view details
    """)
    
    # Initialize optimizer button
    if st.button("🔍 Initialize & Analyze Data", type="secondary"):
        if os.path.exists(file_path):
            try:
                with st.spinner("Loading and analyzing data..."):
                    # Set random seeds
                    random.seed(random_seed)
                    np.random.seed(random_seed)
                    
                    if optimization_method == "NSGA-II":
                        nsga_optimizer = FixedFlexibleSupplyChainOptimizer(file_path, sheet_names, max_suppliers)
                        st.session_state.nsga_optimizer = nsga_optimizer
                        st.session_state.optimizer_instance = nsga_optimizer
                    elif optimization_method == "ε-Constraint":
                        econst_optimizer = SelectiveNAFlexibleEConstraintOptimizer(file_path, sheet_names, max_suppliers)
                        st.session_state.econst_optimizer = econst_optimizer
                        st.session_state.optimizer_instance = econst_optimizer
                    elif optimization_method == "Hybrid":
                        # For hybrid, we need both optimizers
                        nsga_optimizer = FixedFlexibleSupplyChainOptimizer(file_path, sheet_names, max_suppliers)
                        econst_optimizer = SelectiveNAFlexibleEConstraintOptimizer(file_path, sheet_names, max_suppliers)
                        st.session_state.nsga_optimizer = nsga_optimizer
                        st.session_state.econst_optimizer = econst_optimizer
                        st.session_state.optimizer_instance = nsga_optimizer  # Use NSGA as primary for display
                    st.session_state.data_loaded = True
                    
                st.success("✅ Data loaded and analyzed successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error loading data: {str(e)}")
        else:
            st.error("❌ File path does not exist!") 

# Run optimization only if optimizers are initialized
if st.session_state.get('data_loaded', False):
    if st.button("🚀 Run Optimization", type="primary"):
        try:
            with st.spinner("Running optimization..."):
                if optimization_method == "NSGA-II":
                    if 'nsga_optimizer' in st.session_state:
                        nsga_optimizer = st.session_state.nsga_optimizer
                        final_population = nsga_optimizer.optimize(
                            ngen=n_gen,
                            mu=pop_size,
                            lambda_=offspring_size,
                            cxpb=crossover_prob,
                            mutpb=mutation_prob,
                            indpb=indpb
                        )
                        df_nsga = nsga_optimizer.extract_pareto_front(final_population)
                        df_nsga['method'] = 'NSGA-II'
                        st.session_state.results_nsga = df_nsga

                        
                        # Compute evaluation metrics for NSGA-II
                        objectives = df_nsga[['cost', 'score']].values

                        # Hypervolume
                        ref_point = [df_nsga['cost'].max() + 1, df_nsga['score'].max() + 1]
                        def compute_hv(points, ref):
                            hv = 0.0
                            sorted_points = sorted(points, key=lambda x: x[0])
                            prev_score = ref[1]
                            for cost, score in sorted_points:
                                width = ref[0] - cost
                                height = prev_score - score
                                hv += width * height
                                prev_score = score
                            return hv

                        # Spread
                        def compute_spread(points):
                            points = sorted(points, key=lambda x: x[0])
                            distances = [np.linalg.norm(np.array(points[i]) - np.array(points[i-1])) for i in range(1, len(points))]
                            avg_d = np.mean(distances)
                            spread = sum(abs(d - avg_d) for d in distances) / (len(distances) * avg_d) if avg_d != 0 else 0
                            return spread

                        hv = compute_hv(objectives, ref_point)
                        spread = compute_spread(objectives)
                        num_nd = len(objectives)

                        st.session_state.hv = hv
                        st.session_state.spread = spread
                        st.session_state.num_nd = num_nd

                    else:
                        st.error("❌ NSGA-II optimizer not initialized. Please click 'Initialize & Analyze Data' first.")
                
                elif optimization_method == "ε-Constraint":
                    if 'econst_optimizer' in st.session_state:
                        econst_optimizer = st.session_state.econst_optimizer
                        df_econst = econst_optimizer.optimize_epsilon_constraint(
                            n_points=n_points,
                            constraint_type=constraint_type
                        )
                        df_econst = df_econst[df_econst['status'] == 'Optimal']
                        df_econst['method'] = 'ε-Constraint'
                        st.session_state.results_econst = df_econst
                    else:
                        st.error("❌ ε-Constraint optimizer not initialized. Please click 'Initialize & Analyze Data' first.")
                
                elif optimization_method == "Hybrid":
                    if 'nsga_optimizer' in st.session_state and 'econst_optimizer' in st.session_state:
                        with st.spinner("Running Hybrid Optimization..."):
                            # Get feasible allocations from ε-constraint
                            econst_optimizer = st.session_state.econst_optimizer
                            feasible_allocations = econst_optimizer.get_feasible_allocations(n_points=10)
                            
                            # Convert to seed individuals for NSGA-II
                            nsga_optimizer = st.session_state.nsga_optimizer
                            seed_individuals = [
                                nsga_optimizer.convert_allocations_dict_to_individual(alloc)
                                for alloc in feasible_allocations
                            ]
                            
                            # Run NSGA-II with seeds
                            df_hybrid = nsga_optimizer.run_full_optimization(
                                ngen=n_gen,
                                mu=pop_size,
                                lambda_=offspring_size,
                                seed_individuals=seed_individuals
                            )
                            df_hybrid['method'] = 'Hybrid'
                            st.session_state.results_hybrid = df_hybrid
                    else:
                        st.error("❌ Hybrid optimizer not properly initialized. Please click 'Initialize & Analyze Data' first.")

                # Store an optimizer instance for data analysis display
                st.session_state.optimizer_instance = (
                    st.session_state.nsga_optimizer
                    if 'nsga_optimizer' in st.session_state
                    else st.session_state.econst_optimizer
                )
                
                st.success("✅ Optimization completed!")
                st.rerun()
            
        except Exception as e:
            st.error(f"❌ Optimization failed: {str(e)}")
            st.exception(e)

# Main content area
if st.session_state.get('data_loaded', False):
    optimizer = st.session_state.optimizer_instance
    
    # Display data analysis
    st.subheader("📊 Data Analysis")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏭 Depots", len(optimizer.depots))
    with col2:
        st.metric("🚛 Suppliers", len(optimizer.suppliers))
    with col3:
        st.metric("🔗 Total Pairs", len(optimizer.all_pairs))
    with col4:
        if optimizer.max_suppliers is not None:
            st.metric("🏢 Max Suppliers", f"{optimizer.max_suppliers}/{len(optimizer.suppliers)}")
        else:
            st.metric("🏢 Max Suppliers", "Unlimited")

# Show depot-supplier availability
    with st.expander("🔍 Depot-Supplier Availability Analysis", expanded=False):
        availability_data = []
        for depot in optimizer.depots:
            for supplier in optimizer.suppliers:
                if (depot, supplier) in optimizer.all_pairs:
                    collection_valid = optimizer.valid_collection.get((depot, supplier), False)
                    delivery_valid = optimizer.valid_delivery.get((depot, supplier), False)
                    
                    operations = []
                    if collection_valid:
                        operations.append("Collection")
                    if delivery_valid:
                        operations.append("Delivery")
                    
                    availability_data.append({
                        "🏭 Depot": depot,
                        "🏢 Supplier": supplier,
                        "Available Operations": ", ".join(operations) if operations else "None",
                        "Collection": "✅" if collection_valid else "❌",
                        "Delivery": "✅" if delivery_valid else "❌"
                    })
        
        availability_df = pd.DataFrame(availability_data)
        st.dataframe(availability_df, use_container_width=True)
        
        # Summary statistics
        total_pairs = len(availability_data)
        collection_available = sum(1 for row in availability_data if "Collection" in row["Available Operations"])
        delivery_available = sum(1 for row in availability_data if "Delivery" in row["Available Operations"])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Pairs", total_pairs)
        with col2:
            st.metric("Collection Available", f"{collection_available} ({collection_available/total_pairs*100:.1f}%)")
        with col3:
            st.metric("Delivery Available", f"{delivery_available} ({delivery_available/total_pairs*100:.1f}%)")

# Results section
if any(key in st.session_state for key in ['results_nsga', 'results_econst', 'results_hybrid']):
    df_nsga = st.session_state.get('results_nsga', pd.DataFrame())
    df_econst = st.session_state.get('results_econst', pd.DataFrame())
    df_hybrid = st.session_state.get('results_hybrid', pd.DataFrame())
    
    # Combine all available results for plotting with proper indexing
    results_list = []
    combined_index_map = {}  # Maps (method, original_index) -> combined_index
    combined_idx = 0
    
    if not df_nsga.empty:
        results_list.append(df_nsga)
        for orig_idx in df_nsga.index:
            combined_index_map[('NSGA-II', orig_idx)] = combined_idx
            combined_idx += 1
    if not df_econst.empty:
        results_list.append(df_econst)
        for orig_idx in df_econst.index:
            combined_index_map[('ε-Constraint', orig_idx)] = combined_idx
            combined_idx += 1
    if not df_hybrid.empty:
        results_list.append(df_hybrid)
        for orig_idx in df_hybrid.index:
            combined_index_map[('Hybrid', orig_idx)] = combined_idx
            combined_idx += 1
    
    if results_list:
        df_combined = pd.concat(results_list, ignore_index=True)
    else:
        df_combined = pd.DataFrame()
    
    st.divider()
    
    # Interactive Pareto Front Plot (full width)
    st.subheader("📈 Interactive Pareto Front Comparison")
    
    # Create the interactive plot
    fig = go.Figure()
    
    if not df_nsga.empty:
        # Create customdata that maps to correct combined index
        nsga_combined_indices = [combined_index_map[('NSGA-II', idx)] for idx in df_nsga.index]
        fig.add_trace(go.Scatter(
            x=df_nsga["cost"],
            y=df_nsga["score"],
            mode='markers',
            name='NSGA-II',
            marker=dict(color='blue', size=10),
            text=df_nsga.index,
            customdata=nsga_combined_indices,
            hovertemplate=
            '<b>NSGA-II Solution %{text}</b><br>' +
            'Cost: R%{x:,.0f}<br>' +
            'Score: %{y:.2f}<br>' +
            '<b>👆 Click to see details</b><br>' +
            '<extra></extra>'
        ))
    
    if not df_econst.empty:
        # Create customdata that maps to correct combined index
        econst_combined_indices = [combined_index_map[('ε-Constraint', idx)] for idx in df_econst.index]
        fig.add_trace(go.Scatter(
            x=df_econst["cost"],
            y=df_econst["score"],
            mode='markers',
            name='ε-Constraint',
            marker=dict(color='red', size=10),
            text=df_econst.index,
            customdata=econst_combined_indices,
            hovertemplate=
            '<b>ε-Constraint Solution %{text}</b><br>' +
            'Cost: R%{x:,.0f}<br>' +
            'Score: %{y:.2f}<br>' +
            '<b>👆 Click to see details</b><br>' +
            '<extra></extra>'
        ))
        
    if not df_hybrid.empty:
        # Create customdata that maps to correct combined index
        hybrid_combined_indices = [combined_index_map[('Hybrid', idx)] for idx in df_hybrid.index]
        fig.add_trace(go.Scatter(
            x=df_hybrid["cost"],
            y=df_hybrid["score"],
            mode='markers',
            name='Hybrid',
            marker=dict(color='green', size=10),
            text=df_hybrid.index,
            customdata=hybrid_combined_indices,
            hovertemplate=
            '<b>Hybrid Solution %{text}</b><br>' +
            'Cost: R%{x:,.0f}<br>' +
            'Score: %{y:.2f}<br>' +
            '<b>👆 Click to see details</b><br>' +
            '<extra></extra>'
        ))
    
    fig.update_layout(
        title="Multi-Method Pareto Front Comparison",
        xaxis_title="Total Cost (R)",
        yaxis_title="Supplier Score",
        legend_title="Method",
        hovermode='closest',
        height=500
    )
    
    # Display the plot and capture click events
    clicked_data = st.plotly_chart(fig, use_container_width=True, key="pareto_plot", on_select="rerun")
    
    # Handle click events
    if clicked_data and 'selection' in clicked_data and clicked_data['selection']['points']:
        clicked_point = clicked_data['selection']['points'][0]
        selected_idx = clicked_point['customdata']
        st.session_state.selected_solution = selected_idx
        st.session_state.selected_method = df_combined.iloc[selected_idx]['method']
    
    # Solution Overview below the plot
    st.subheader("📊 Solution Overview")
    
    # Create columns for metrics and distribution chart
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if not df_nsga.empty:
            st.metric("NSGA-II Solutions", len(df_nsga))
        if not df_econst.empty:
            st.metric("ε-Constraint Solutions", len(df_econst))
        if not df_hybrid.empty:
            st.metric("Hybrid Solutions", len(df_hybrid))
    
    with col2:
        # Distribution chart
        st.markdown("**📈 Cost Distribution:**")
        fig_dist = go.Figure()
        if not df_nsga.empty:
            fig_dist.add_trace(go.Histogram(
                x=df_nsga['cost'],
                name='NSGA-II',
                opacity=0.7,
                marker_color='blue'
            ))
        if not df_econst.empty:
            fig_dist.add_trace(go.Histogram(
                x=df_econst['cost'],
                name='ε-Constraint',
                opacity=0.7,
                marker_color='red'
            ))
        if not df_hybrid.empty:
            fig_dist.add_trace(go.Histogram(
                x=df_hybrid['cost'],
                name='Hybrid',
                opacity=0.7,
                marker_color='green'
            ))
        fig_dist.update_layout(
            title="Cost Distribution",
            xaxis_title="Cost",
            yaxis_title="Frequency",
            height=300,
            barmode='overlay'
        )
        st.plotly_chart(fig_dist, use_container_width=True)
    
    # Display selected solution details
    if 'selected_solution' in st.session_state and st.session_state.selected_solution is not None:
        selected_idx = st.session_state.selected_solution
        selected_method = st.session_state.selected_method
        solution = df_combined.iloc[selected_idx]
        
        with st.expander(f"🔍 **{selected_method} Solution {selected_idx} Details**", expanded=True):
            col_header1, col_header2 = st.columns(2)
            with col_header1:
                st.metric("💰 Total Cost", f"{solution['cost']:,.0f}")
            with col_header2:
                st.metric("⭐ Score", f"{solution['score']:.2f}")
            
            st.divider()
            
            # ✅ Safely get and validate allocations
            allocations_str = solution.get("allocations", "").strip()
            if allocations_str.lower() in ["no solution", "none", ""]:
                st.warning("⚠️ No allocation data available for this solution.")
                st.stop()
            
            allocations = allocations_str.split()

            # Generate supplier rankings
            optimizer = st.session_state.optimizer_instance
            depot_rankings = generate_supplier_ranking(allocations_str, optimizer)
            
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["🏭 Allocations", "🏆 Supplier Rankings", "📊 Summary"])
            
            with tab1:
                col_detail1, col_detail2 = st.columns([1, 1])
                
                with col_detail1:
                    st.markdown("**🏭 Detailed Allocations:**")
                    
                    if allocations and allocations_str:
                        allocations_data = []
                        for alloc in allocations:
                            if '(' in alloc and ')' in alloc:
                                operation = alloc[0]
                                params = alloc[2:-1]
                                if ',' in params:
                                    depot, supplier = params.split(',')
                                    allocations_data.append({
                                        "🏭 Depot": f"Depot {depot}",
                                        "🏢 Supplier": f"Supplier {supplier}",
                                        "📋 Operation": "Collection" if operation == 'C' else "Delivery",
                                        "🔧 Code": alloc
                                    })
                        
                        if allocations_data:
                            allocation_df = pd.DataFrame(allocations_data)
                            st.dataframe(allocation_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No valid allocations parsed")
                    else:
                        st.info("No allocations found for this solution")
                
                with col_detail2:
                    st.markdown("**📈 Allocation Summary:**")
                    
                    if allocations and allocations_str:
                        supplier_operations = {}
                        operation_counts = {"Collection": 0, "Delivery": 0}
                        
                        for alloc in allocations:
                            if '(' in alloc and ')' in alloc:
                                operation = alloc[0]
                                params = alloc[2:-1]
                                if ',' in params:
                                    depot, supplier = params.split(',')
                                    supplier_key = f"Supplier {supplier}"
                                    
                                    if supplier_key not in supplier_operations:
                                        supplier_operations[supplier_key] = {"Collection": 0, "Delivery": 0}
                                    
                                    if operation == 'C':
                                        supplier_operations[supplier_key]["Collection"] += 1
                                        operation_counts["Collection"] += 1
                                    elif operation == 'D':
                                        supplier_operations[supplier_key]["Delivery"] += 1
                                        operation_counts["Delivery"] += 1
                        
                        for supplier_id, operations in supplier_operations.items():
                            total_ops = operations['Collection'] + operations['Delivery']
                            if total_ops > 0:
                                st.markdown(f"**{supplier_id}:** {total_ops} operations")
                                if operations['Collection'] > 0:
                                    st.markdown(f"  - Collection: {operations['Collection']}")
                                if operations['Delivery'] > 0:
                                    st.markdown(f"  - Delivery: {operations['Delivery']}")
                        
                        st.markdown("---")
                        st.markdown(f"**Total Operations:** {sum(operation_counts.values())}")
                    else:
                        st.info("No allocation summary available")
            
            with tab2:
                st.markdown("**🏆 Supplier Rankings by Depot**")
                st.markdown("*Suppliers ranked by cost (lowest to highest). Selected suppliers are highlighted.*")
                
                if depot_rankings:
                    for depot in sorted(depot_rankings.keys()):
                        with st.expander(f"🏭 Depot {depot} Rankings", expanded=True):
                            suppliers = depot_rankings[depot]
                            
                            # Create ranking table
                            ranking_data = []
                            for supplier_info in suppliers:
                                rank_emoji = "🥇" if supplier_info['rank'] == 1 else "🥈" if supplier_info['rank'] == 2 else "🥉" if supplier_info['rank'] == 3 else f"#{supplier_info['rank']}"
                                status = "✅ SELECTED" if supplier_info['is_selected'] else ""
                                operation = f"({supplier_info['operation']})" if supplier_info['operation'] else ""
                                
                                ranking_data.append({
                                    "🏆 Rank": rank_emoji,
                                    "🏢 Supplier": f"Supplier {supplier_info['supplier']}",
                                    "💰 Cost": f"R{supplier_info['cost']:.2f}",
                                    "⭐ Score": f"{supplier_info['score']:.2f}",
                                    "📋 Status": f"{status} {operation}".strip()
                                })
                            
                            ranking_df = pd.DataFrame(ranking_data)
                            st.dataframe(ranking_df, use_container_width=True, hide_index=True)
                            
                            # Show why this supplier was selected
                            selected_supplier = next((s for s in suppliers if s['is_selected']), None)
                            if selected_supplier:
                                st.markdown(f"**Why Supplier {selected_supplier['supplier']} was selected:**")
                                if selected_supplier['rank'] == 1:
                                    st.success(f"✅ **Lowest Cost**: Supplier {selected_supplier['supplier']} has the lowest cost (R{selected_supplier['cost']:.2f}) for Depot {depot}")
                                else:
                                    # Find the best supplier
                                    best_supplier = suppliers[0]
                                    st.info(f"📊 **Trade-off Decision**: Supplier {selected_supplier['supplier']} (cost: R{selected_supplier['cost']:.2f}) was chosen over Supplier {best_supplier['supplier']} (lowest cost: R{best_supplier['cost']:.2f}) to optimize overall cost-score balance")
                else:
                    st.info("No supplier rankings available for this solution")
            
            with tab3:
                st.markdown("**📊 Solution Analysis**")
                
                # Summary statistics
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                
                with col_sum1:
                    if depot_rankings:
                        total_depots = len(depot_rankings)
                        selected_best_ranked = sum(1 for depot, suppliers in depot_rankings.items() 
                                                 if any(s['is_selected'] and s['rank'] == 1 for s in suppliers))
                        st.metric("🏭 Total Depots", total_depots)
                        st.metric("🥇 Lowest Cost Selected", f"{selected_best_ranked}/{total_depots}")
                
                with col_sum2:
                    if allocations and allocations_str:
                        collection_count = sum(1 for alloc in allocations if alloc.startswith('C'))
                        delivery_count = sum(1 for alloc in allocations if alloc.startswith('D'))
                        st.metric("📦 Collection Operations", collection_count)
                        st.metric("🚚 Delivery Operations", delivery_count)
                
                with col_sum3:
                    if depot_rankings:
                        avg_rank = np.mean([next(s['rank'] for s in suppliers if s['is_selected']) 
                                          for suppliers in depot_rankings.values()])
                        st.metric("📊 Average Cost Rank", f"{avg_rank:.1f}")
                
                # Visual summary
                st.markdown("**📈 Cost Efficiency Analysis:**")
                
                if depot_rankings:
                    # Create bar chart of selected supplier ranks
                    depot_names = [f"Depot {depot}" for depot in sorted(depot_rankings.keys())]
                    selected_ranks = [next(s['rank'] for s in suppliers if s['is_selected']) 
                                    for suppliers in depot_rankings.values()]
                    
                    fig_ranks = go.Figure(data=[
                        go.Bar(
                            x=depot_names,
                            y=selected_ranks,
                            marker_color=['green' if rank == 1 else 'orange' if rank == 2 else 'red' for rank in selected_ranks],
                            text=[f"Rank {rank}" for rank in selected_ranks],
                            textposition='auto'
                        )
                    ])
                    fig_ranks.update_layout(
                        title="Selected Supplier Cost Ranks by Depot",
                        xaxis_title="Depot",
                        yaxis_title="Cost Rank (1 = Lowest Cost)",
                        yaxis=dict(autorange='reversed'),  # Lower rank is better
                        height=400
                    )
                    st.plotly_chart(fig_ranks, use_container_width=True)
            
            st.divider()
            st.markdown("**🔤 Raw Allocation String:**")
            st.code(allocations_str if allocations_str else "No allocation data", language="text")
            
            if st.button("❌ Close Details", key="close_details"):
                st.session_state.selected_solution = None
                st.session_state.selected_method = None
                st.rerun()
    
    # Export results section
    st.divider()
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        if st.button("💾 Export Results to CSV"):
            try:
                output_dir = "Output Data"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, "optimizer_comparison_results.csv")
                df_combined.to_csv(output_path, index=False)
                st.success(f"✅ Results exported to {output_path}")
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
    
    with col_export2:
        csv_data = df_combined.to_csv(index=False)
        st.download_button(
            label="📥 Download Results CSV",
            data=csv_data,
            file_name="optimizer_comparison_results.csv",
            mime="text/csv"
        )
    
    # Full results table
    st.subheader("📋 All Solutions")
    with st.expander("View All Pareto Solutions", expanded=False):
        display_df = df_combined[['cost', 'score', 'method', 'allocations']].copy()
        display_df.columns = ['Total Cost', 'Score', 'Method', 'Allocation']
        st.dataframe(display_df, use_container_width=True)

    if all(k in st.session_state for k in ['hv', 'spread', 'num_nd']):
        st.subheader("📈 Evaluation Metrics")
        with st.expander("View All Evaluation Metrics", expanded=False):
            st.metric("Hypervolume", f"{st.session_state.hv:.2f}")
            st.metric("Non-Dominated Solutions", f"{st.session_state.num_nd}")
            st.metric("Spread", f"{st.session_state.spread:.4f}")


    # Welcome screen
    st.info("Use the sidebar to configure your data file and click **Initialize & Analyze Data** to get started!")
    
    st.markdown("""
    ### About This Comparison Optimizer
    
    This application compares **NSGA-II** and **ε-Constraint** methods for supply chain optimization with **selective NA handling**.
    
    **Key Features:**
    - **Multi-Method Optimization**: Run NSGA-II (blue), ε-Constraint (red), or Hybrid (green) methods
    - **Stacked Results**: Results from different methods stack on the same Pareto front with color coding
    - **Result Replacement**: Running the same method again replaces its previous results
    - **Multi-objective Optimization**: Minimizes cost while maximizing supplier scores
    - **Complex Constraints**: Handles depot-specific supplier availability
    - **Interactive Analysis**: Click points to explore solutions
    
    **Objectives:**
    - **Minimize Cost**: Total operational cost
    - **Maximize Score**: Supplier performance score
    """)
    
    # System requirements
    with st.expander("📋 System Requirements & Data Format"):
        st.markdown("""
        **Required Excel Sheets:**
        - **Obj1_Coeff**: Cost coefficients (COC Rebate, DEL Rebate, Cost of Collection, Zone Differentials)
        - **Obj2_Coeff**: Supplier scoring data
        - **Annual Volumes**: Volume data for each depot
        
        **Data Handling:**
        - Automatically detects 'NA' or missing values
        - Only includes valid depot-supplier-operation combinations
        """)

else:
    # Welcome screen
    st.info("👆 Use the sidebar to configure your data file and click **Initialize & Analyze Data** to get started!")
    
    st.markdown("""
    ### 🎯 About This Comparison Optimizer
    
    This application compares **NSGA-II** and **ε-Constraint** methods for supply chain optimization with **selective NA handling**.
    
    **Key Features:**
    - **Multi-Method Optimization**: Run NSGA-II (blue), ε-Constraint (red), or Hybrid (green) methods
    - **Stacked Results**: Results from different methods stack on the same Pareto front with color coding
    - **Result Replacement**: Running the same method again replaces its previous results
    - **Multi-objective Optimization**: Minimizes cost while maximizing supplier scores
    - **Complex Constraints**: Handles depot-specific supplier availability
    - **Interactive Analysis**: Click points to explore solutions
    
    **Objectives:**
    - **Minimize Cost**: Total operational cost
    - **Maximize Score**: Supplier performance score
    """)
    
    # Parameter guidance section
    with st.expander("⚙️ NSGA-II Parameter Tuning Guide", expanded=False):
        st.markdown("### 🎛️ Parameter Effects Overview")
        
        # Parameter effects table
        param_effects_data = {
            "Parameter": [
                "Number of Generations (n_gen)",
                "Population Size (pop_size)",
                "Offspring Size (offspring_size)",
                "Crossover Probability (cxpb)",
                "Mutation Probability (mutpb)",
                "Individual Mutation Probability (indpb)"
            ],
            "What It Controls": [
                "Convergence depth - How many evolution cycles",
                "Diversity of solutions - Individuals kept per generation",
                "Exploration range - New individuals created each cycle",
                "Solution mixing - Chance two parents create offspring",
                "Random exploration - Chance entire individual mutates",
                "Fine-tuning granularity - Chance each gene mutates"
            ],
            "Too Low →": [
                "Early convergence, suboptimal solutions",
                "Narrow Pareto front, missed trade-offs",
                "Limited exploration of solution space",
                "Limited exploration, convergence issues",
                "Stuck in local optima",
                "Solutions don't improve enough"
            ],
            "Too High →": [
                "Wasted computation time",
                "Longer compute time, diminishing returns",
                "Overloads selection, reduces elitism",
                "Too much disruption, convergence stalls",
                "Random noise, no learning",
                "Chaotic behavior, no stability"
            ]
        }
        
        param_effects_df = pd.DataFrame(param_effects_data)
        st.dataframe(param_effects_df, use_container_width=True, hide_index=True)
        
        st.markdown("### 🎯 Recommended Starting Values")
        
        # Recommended values table
        recommended_data = {
            "Parameter": [
                "Population Size (pop_size)",
                "Number of Generations (n_gen)",
                "Offspring Size (offspring_size)",
                "Crossover Probability (cxpb)",
                "Mutation Probability (mutpb)",
                "Individual Mutation Rate (indpb)",
                "Random Seed"
            ],
            "Recommended Value": [
                "100 – 200 (start at 150)",
                "200 – 500 (start at 300)",
                "Equal to pop_size (e.g., 150)",
                "0.9 – 0.95",
                "0.2 – 0.3",
                "1/num_genes (e.g., 0.05 – 0.1)",
                "Any fixed number (e.g., 42)"
            ],
            "Why This Range": [
                "More diversity, better global search",
                "More time to refine solutions",
                "Balanced evolution process",
                "Encourage recombination of good traits",
                "Maintain diversity, escape local optima",
                "Small per-gene mutation for careful exploration",
                "Ensures reproducible results"
            ]
        }
        
        recommended_df = pd.DataFrame(recommended_data)
        st.dataframe(recommended_df, use_container_width=True, hide_index=True)
        
        st.markdown("""
        ### 💡 Tuning Tips
        
        **For Better Results:**
        - Start with recommended values, then adjust based on results
        - **Small problems**: Lower population size (50-100), fewer generations (100-200)
        - **Complex problems**: Higher population size (200-500), more generations (300-500)
        - **Slow convergence**: Increase mutation probability or reduce population size
        - **Poor diversity**: Increase population size or mutation rates
        - **Unstable results**: Lower mutation rates, ensure fixed random seed
        
        **Performance vs Quality Trade-offs:**
        - 🚀 **Faster**: Smaller population, fewer generations
        - 🎯 **Better quality**: Larger population, more generations
        - ⚖️ **Balanced**: Use the recommended starting values above
        """)
    
    # System requirements
    with st.expander("📋 System Requirements & Data Format"):
        st.markdown("""
        **Required Excel Sheets:**
        - **Obj1_Coeff**: Cost coefficients (COC Rebate, DEL Rebate, Cost of Collection, Zone Differentials)
        - **Obj2_Coeff**: Supplier scoring data
        - **Annual Volumes**: Volume data for each depot
        
        **Data Handling:**
        - Automatically detects 'NA' or missing values
        - Only includes valid depot-supplier-operation combinations
        """)


# Footer
st.markdown("---")
st.markdown("*Built for comparing NSGA-II and ε-Constraint optimization*")