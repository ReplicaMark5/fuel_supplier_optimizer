#!/usr/bin/env python3
"""
Optimization Results Mapping Module

This module creates interactive maps showing the fuel depot allocation optimization results.
It visualizes customer depots, supplier depots, and allocation connections on a map of 
South Africa and neighboring countries.
"""

import folium
from folium import plugins
import logging
from typing import Dict, List, Any, Tuple

# Configure logging
logger = logging.getLogger(__name__)

class OptimizationMapper:
    """
    Creates interactive maps showing optimization allocation results.
    """
    
    def __init__(self):
        """Initialize mapper for enhanced allocation mapping."""
        # Color schemes for different suppliers - using both hex and folium color names
        self.supplier_colors = {
            'Supplier A': {'hex': '#0A7368', 'folium': 'red'},     # Red  
            'Supplier C': {'hex': '#BBBF99', 'folium': 'blue'},   # Blue
            'Supplier D': {'hex': '#F2AC29', 'folium': 'green'},  # Green
            'Supplier F': {'hex': '#BF2604', 'folium': 'orange'}, # Orange
            'Supplier G': {'hex': '#489DAC', 'folium': 'purple'}, # Purple
            'Supplier H': {'hex': '#CF7288', 'folium': 'darkgreen'}, # Dark Green
            'Supplier I': {'hex': '#80035E', 'folium': 'pink'},   # Magenta/Pink
            'Supplier J': {'hex': '#321A89', 'folium': 'lightblue'}, # Cyan/Light Blue
            'Supplier L': {'hex': '#2F9928', 'folium': 'darkred'} # Maroon/Dark Red
        }
    
    
    
    def create_enhanced_allocation_map(self, comprehensive_data: Dict[str, Any], save_path: str = "enhanced_allocation_map.html") -> str:
        """
        Create an enhanced interactive map showing all routes and optimization results.
        
        Args:
            comprehensive_data: Complete data package containing:
                - optimization_results: Optimization results with allocations and capacity data
                - all_route_costs: Complete precomputed cost dictionary
                - capacity_limits: Supplier depot capacity limits
                - optimization_metadata: Additional optimization info
            save_path: Path to save the HTML map file
            
        Returns:
            str: Path to the generated HTML map file
        """
        logger.info("Creating enhanced optimization allocation map with all routes...")
        
        # Extract data from comprehensive package
        self.optimization_results = comprehensive_data['optimization_results']
        self.all_route_costs = comprehensive_data['all_route_costs']['costs']  # The cost dictionary
        self.customer_depot_info = comprehensive_data['all_route_costs']['depots']
        self.supplier_info = comprehensive_data['all_route_costs']['suppliers']
        self.capacity_limits = comprehensive_data['capacity_limits']
        self.optimization_metadata = comprehensive_data['optimization_metadata']
        
        # Store capacity utilization data if available
        self.capacity_utilization = self.optimization_results.get('supplier_depot_utilization', {})
        
        logger.info(f"Enhanced mapper loaded:")
        logger.info(f"  - {len(self.all_route_costs)} customer depots")
        logger.info(f"  - {sum(len(routes) for routes in self.all_route_costs.values())} total route combinations")
        logger.info(f"  - {len(self.optimization_results.get('allocations', []))} optimized allocations")
        logger.info(f"  - {len(self.capacity_limits)} supplier depot capacity limits")
        
        # Process all routes and generate enhanced visualizations
        self._process_all_routes()
        
        # Create enhanced map (for now, use existing method as base)
        # This will be expanded in Steps 3-5
        enhanced_map_path = self._create_enhanced_map(save_path)
        
        logger.info(f"Enhanced allocation map saved to: {enhanced_map_path}")
        return enhanced_map_path
    
    def _process_all_routes(self):
        """Process all possible routes from precomputed data and identify optimized ones."""
        logger.info("Processing all possible routes from precomputed data...")
        
        self.all_routes = {}
        self.optimized_routes = {}
        
        # Build lookup for optimized allocations (ensure string keys for consistent lookup)
        optimized_lookup = {}
        for allocation in self.optimization_results.get('allocations', []):
            customer_id = str(allocation['customer_depot_id'])
            supplier_depot_id = str(allocation['supplier_depot_id'])
            key = (customer_id, supplier_depot_id)
            optimized_lookup[key] = allocation
        
        # Process all possible routes from cost dictionary
        total_routes = 0
        for customer_id, supplier_depots in self.all_route_costs.items():
            self.all_routes[customer_id] = {}
            
            for supplier_depot_id, cost_data in supplier_depots.items():
                total_routes += 1
                
                # Extract all available cost options
                available_costs = self._extract_cost_options(cost_data)
                
                # Check if this route was optimized (ensure string comparison)
                route_key = (str(customer_id), str(supplier_depot_id))
                is_optimized = route_key in optimized_lookup
                optimized_info = optimized_lookup.get(route_key, {})
                
                route_info = {
                    'customer_id': customer_id,
                    'supplier_depot_id': supplier_depot_id,
                    'supplier_name': cost_data.get('supplier_name', 'Unknown'),
                    'distance_km': cost_data.get('distance_km', 0),
                    'available_costs': available_costs,
                    'is_optimized': is_optimized,
                    'optimized_option': optimized_info.get('option_type') if is_optimized else None,
                    'optimized_cost': optimized_info.get('cost_per_litre') if is_optimized else None
                }
                
                self.all_routes[customer_id][supplier_depot_id] = route_info
                
                # Store optimized routes separately for easy access
                if is_optimized:
                    self.optimized_routes[route_key] = route_info
        
        logger.info(f"Processed {total_routes} total route combinations")
        logger.info(f"Found {len(self.optimized_routes)} optimized routes")
    
    def _extract_cost_options(self, cost_data: Dict) -> Dict:
        """Extract all cost options from precomputed cost data."""
        available_costs = {}
        
        # Base cost options
        base_options = ['coc_cash', 'coc_30', 'coc_45', 'coc_60', 'del_own', 'del_rent']
        for option in base_options:
            if option in cost_data and cost_data[option] is not None:
                available_costs[option] = cost_data[option]
        
        # RAC penalty options
        rac_options = ['rac_coc_30', 'rac_del_own', 'rac_del_rent']
        rac_costs = {}
        for option in rac_options:
            if option in cost_data and cost_data[option] is not None:
                rac_costs[option] = cost_data[option]
        
        if rac_costs:
            available_costs['rac_options'] = rac_costs
        
        # Volume tier options (find dynamically)
        tier_costs = {}
        for key, value in cost_data.items():
            if 'tier_' in key and value is not None:
                tier_costs[key] = value
        
        if tier_costs:
            available_costs['tier_options'] = tier_costs
        
        return available_costs
    
    def _create_enhanced_map(self, save_path: str) -> str:
        """Create the enhanced map visualization with supplier-specific layers containing both depots and routes."""
        logger.info("Creating enhanced visualization with supplier-specific layers...")
        
        # Initialize map centered on South Africa with white theme
        center_lat, center_lon = -28.0, 25.0
        map_viz = folium.Map(
            location=[center_lat, center_lon], 
            zoom_start=5,
            tiles='CartoDB positron'  # White/light theme
        )
        
        # Create feature groups for layer control
        self.feature_groups = {}
        
        # Create base layer with only customer depots (always visible)
        base_layer = folium.FeatureGroup(name='📍 Customer Depots')
        self._add_customer_depot_markers(base_layer)
        base_layer.add_to(map_viz)
        
        # Create supplier-specific layers with both depots and routes
        self._create_supplier_layers(map_viz)
        
        # Add layer control panel
        folium.LayerControl(position='topright', collapsed=False).add_to(map_viz)
        
        # Save the enhanced map
        map_viz.save(save_path)
        logger.info(f"Enhanced map with supplier-specific layers saved to: {save_path}")
        
        return save_path
    
    def _create_supplier_layers(self, map_viz):
        """Create separate feature groups for each supplier's depots and routes."""
        logger.info("Creating supplier-specific layers with depots and routes...")
        
        # Group supplier depots by supplier name
        suppliers_data = {}
        for customer_routes in self.all_routes.values():
            for supplier_depot_id, route_info in customer_routes.items():
                supplier_name = route_info['supplier_name']
                if supplier_name not in suppliers_data:
                    suppliers_data[supplier_name] = []
                if supplier_depot_id not in [item['depot_id'] for item in suppliers_data[supplier_name]]:
                    suppliers_data[supplier_name].append({
                        'depot_id': supplier_depot_id,
                        'route_info': route_info
                    })
        
        # Create a feature group for each supplier
        for supplier_name in suppliers_data:
            # Get supplier color for the layer name
            supplier_color_info = self.supplier_colors.get(supplier_name, {'hex': '#000000'})
            color_hex = supplier_color_info['hex']
            
            # Create feature group with colored bullet point
            layer_name = f"🏭 {supplier_name}"
            supplier_layer = folium.FeatureGroup(name=layer_name, show=True)
            
            # Add supplier depots to this layer
            self._add_supplier_depots_to_layer(supplier_layer, suppliers_data[supplier_name])
            
            # Add all routes for this supplier (both potential and optimized)
            self._add_supplier_routes_to_layer(supplier_layer, supplier_name)
            
            # Add layer to map
            supplier_layer.add_to(map_viz)
            self.feature_groups[supplier_name] = supplier_layer
    
    def _add_supplier_depots_to_layer(self, layer, supplier_depots_data):
        """Add supplier depot markers to a specific layer."""
        for depot_data in supplier_depots_data:
            supplier_depot_id = depot_data['depot_id']
            route_info = depot_data['route_info']
            supplier_name = route_info['supplier_name']
            
            # Get supplier depot coordinates
            supplier_depot_data = None
            for customer_id, supplier_routes in self.all_route_costs.items():
                if int(supplier_depot_id) in supplier_routes:
                    supplier_depot_data = supplier_routes[int(supplier_depot_id)]
                    break
            
            if not supplier_depot_data:
                continue
                
            lat = supplier_depot_data.get('supplier_depot_lat')
            lon = supplier_depot_data.get('supplier_depot_lon')
            
            if not lat or not lon:
                continue
            
            # Get capacity information
            capacity_limit = self.capacity_limits.get(str(supplier_depot_id), 0)
            utilization_data = self.capacity_utilization.get(str(supplier_depot_id), {})
            utilization_pct = utilization_data.get('utilization_percent', 0)
            is_binding = utilization_data.get('is_binding_constraint', False)
            
            # Get depot name from route cost data (if available)
            depot_name = f'Depot {supplier_depot_id}'
            if supplier_depot_data and 'supplier_depot_name' in supplier_depot_data:
                depot_name = supplier_depot_data['supplier_depot_name']
            
            # Use supplier-specific hex color
            supplier_color_info = self.supplier_colors.get(supplier_name, {'hex': '#000000'})
            marker_color = supplier_color_info['hex']
            
            popup_content = f"""
            <b>{supplier_name} Depot {supplier_depot_id} ({depot_name})</b><br>
            Capacity Limit: {capacity_limit:,.0f} L<br>
            Utilization: {utilization_pct:.1f}%<br>
            Status: {'BINDING' if is_binding else 'Available'}<br>
            Location: {lat:.4f}, {lon:.4f}
            """
            
            # Add marker to the supplier's layer
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"{supplier_name} Depot {supplier_depot_id}",
                icon=plugins.BeautifyIcon(
                    icon='industry',
                    iconShape='marker',
                    borderColor=marker_color,
                    backgroundColor=marker_color,
                    textColor='white'
                )
            ).add_to(layer)
    
    def _add_supplier_routes_to_layer(self, layer, supplier_name):
        """Add all routes (potential and optimized) for a specific supplier to their layer."""
        logger.info(f"Adding routes for {supplier_name} to supplier layer...")
        
        routes_added = 0
        for customer_id, supplier_routes in self.all_routes.items():
            # Get customer depot coordinates (convert to int for dictionary lookup)
            customer_info = self.customer_depot_info.get(int(customer_id), {})
            customer_lat = customer_info.get('latitude')
            customer_lon = customer_info.get('longitude')
            
            if not customer_lat or not customer_lon:
                continue
                
            for supplier_depot_id, route_info in supplier_routes.items():
                # Only process routes for this specific supplier
                if route_info['supplier_name'] != supplier_name:
                    continue
                    
                # Get supplier depot coordinates from the route cost data
                supplier_depot_data = self.all_route_costs.get(int(customer_id), {}).get(int(supplier_depot_id), {})
                supplier_lat = supplier_depot_data.get('supplier_depot_lat')
                supplier_lon = supplier_depot_data.get('supplier_depot_lon')
                
                if not supplier_lat or not supplier_lon:
                    continue
                
                # Create route line coordinates
                line_coords = [[customer_lat, customer_lon], [supplier_lat, supplier_lon]]
                
                # Determine route color and style based on optimization status
                if route_info['is_optimized']:
                    # Optimized route: use supplier color, thicker line
                    supplier_color_info = self.supplier_colors.get(supplier_name, {'hex': '#000000'})
                    line_color = supplier_color_info['hex']
                    line_weight = 3
                    line_opacity = 0.8
                    
                    # Enhanced popup for optimized routes
                    annual_volume = customer_info.get('annual_volume', 0)
                    total_cost = annual_volume * route_info['optimized_cost'] if route_info['optimized_cost'] else 0
                    supplier_depot_name = supplier_depot_data.get('supplier_depot_name', f'Depot {supplier_depot_id}')
                    
                    popup_content = f"""
                    <div style="font-family: Arial, sans-serif;">
                        <h4 style="margin: 0 0 10px 0; color: #d63031;">OPTIMIZED ROUTE</h4>
                        <strong>Route:</strong> Customer Depot {customer_id} → {supplier_name} Depot {supplier_depot_id} ({supplier_depot_name})<br>
                        <strong>Option:</strong> {route_info['optimized_option']}<br>
                        <strong>Distance:</strong> {route_info['distance_km']:.1f} km<br>
                        <strong>Volume:</strong> {annual_volume:,.0f} L<br>
                        <strong>Cost/L:</strong> R {route_info['optimized_cost']:.4f}<br>
                        <strong>Total Cost:</strong> R {total_cost:,.2f}
                    </div>
                    """
                else:
                    # Potential route: use grey color, thinner line
                    line_color = '#808080'
                    line_weight = 1
                    line_opacity = 0.3
                    
                    # Detailed popup with all available cost options
                    popup_content = self._create_detailed_route_popup(
                        customer_id, 
                        supplier_depot_id, 
                        route_info, 
                        is_optimized=False
                    )
                
                try:
                    folium.PolyLine(
                        locations=line_coords,
                        color=line_color,
                        weight=line_weight,
                        opacity=line_opacity,
                        popup=folium.Popup(popup_content, max_width=450)
                    ).add_to(layer)
                    
                    routes_added += 1
                except Exception as e:
                    logger.error(f"Failed to add route {customer_id}->{supplier_depot_id} for {supplier_name}: {e}")
        
        logger.info(f"Added {routes_added} routes for {supplier_name}")
    
    def _create_detailed_route_popup(self, customer_id, supplier_depot_id, route_info, is_optimized=False):
        """Create detailed popup content showing all available cost options."""
        
        # Get customer depot info
        customer_info = self.customer_depot_info.get(int(customer_id), {})
        customer_name = customer_info.get('name', f'Depot {customer_id}')
        annual_volume = customer_info.get('annual_volume', 0)
        
        # Get detailed cost data from the cost dictionary
        cost_data = self.all_route_costs.get(int(customer_id), {}).get(int(supplier_depot_id), {})
        
        # Get supplier depot name from cost data
        supplier_depot_name = cost_data.get('supplier_depot_name', f'Depot {supplier_depot_id}')
        
        # Start building popup content
        status = "OPTIMIZED ROUTE" if is_optimized else "Potential Route (Not Selected)"
        popup_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 400px;">
            <h4 style="margin: 0 0 10px 0; color: {'#d63031' if is_optimized else '#636e72'};">
                {status}
            </h4>
            
            <div style="margin-bottom: 10px;">
                <strong>Route:</strong> {customer_name} → {route_info['supplier_name']} Depot {supplier_depot_id} ({supplier_depot_name})<br>
                <strong>Distance:</strong> {route_info['distance_km']:.1f} km<br>
                <strong>Annual Volume:</strong> {annual_volume:,.0f} L
            </div>
            
            <div style="border-top: 1px solid #ddd; padding-top: 10px;">
                <strong>Available Cost Options:</strong><br>
        """
        
        # Add base cost options
        base_options = {
            'coc_cash': 'COC Cash',
            'coc_30': 'COC NET30', 
            'coc_45': 'COC NET45',
            'coc_60': 'COC NET60',
            'del_own': 'DEL Own Equipment',
            'del_rent': 'DEL Rent Equipment'
        }
        
        popup_content += "<div style='margin: 5px 0;'><em>Base Options:</em></div>"
        for option_key, option_name in base_options.items():
            if option_key in cost_data and cost_data[option_key] is not None:
                cost_per_litre = cost_data[option_key]
                annual_cost = cost_per_litre * annual_volume
                popup_content += f"""
                <div style="margin-left: 10px; font-size: 0.9em;">
                    • {option_name}: <strong>R {cost_per_litre:.4f}/L</strong> 
                    (R {annual_cost:,.0f}/year)
                </div>
                """
        
        # Add RAC penalty options if available
        rac_options = {
            'rac_coc_30': 'RAC COC NET30',
            'rac_del_own': 'RAC DEL Own',
            'rac_del_rent': 'RAC DEL Rent'
        }
        
        rac_found = False
        for option_key in rac_options.keys():
            if option_key in cost_data and cost_data[option_key] is not None:
                if not rac_found:
                    popup_content += "<div style='margin: 10px 0 5px 0;'><em>RAC Penalty Options:</em></div>"
                    rac_found = True
                cost_per_litre = cost_data[option_key]
                annual_cost = cost_per_litre * annual_volume
                popup_content += f"""
                <div style="margin-left: 10px; font-size: 0.9em; color: #e17055;">
                    • {rac_options[option_key]}: <strong>R {cost_per_litre:.4f}/L</strong>
                    (R {annual_cost:,.0f}/year)
                </div>
                """
        
        # Add volume tier options if available
        tier_options = {}
        for key, value in cost_data.items():
            if 'tier_' in key and value is not None:
                tier_options[key] = value
        
        if tier_options:
            popup_content += "<div style='margin: 10px 0 5px 0;'><em>Volume Tier Options:</em></div>"
            for tier_key, cost_per_litre in tier_options.items():
                # Format tier name nicely
                tier_display = tier_key.replace('_tier_', ' Tier ').replace('_', ' ').title()
                annual_cost = cost_per_litre * annual_volume
                popup_content += f"""
                <div style="margin-left: 10px; font-size: 0.9em; color: #00b894;">
                    • {tier_display}: <strong>R {cost_per_litre:.4f}/L</strong>
                    (R {annual_cost:,.0f}/year)
                </div>
                """
        
        popup_content += """
            </div>
        </div>
        """
        
        return popup_content
    
    def _add_customer_depot_markers(self, map_viz):
        """Add customer depot markers to the map."""
        logger.info("Adding customer depot markers...")
        
        for customer_id, customer_info in self.customer_depot_info.items():
            lat = customer_info.get('latitude')
            lon = customer_info.get('longitude')
            
            if not lat or not lon:
                logger.warning(f"No coordinates found for customer depot {customer_id}")
                continue
            
            annual_volume = customer_info.get('annual_volume', 0)
            fuel_zone = customer_info.get('fuel_zone', 'Unknown')
            
            popup_content = f"""
            <b>Customer Depot {customer_id}</b><br>
            Annual Volume: {annual_volume:,.0f} L<br>
            Fuel Zone: {fuel_zone}<br>
            Location: {lat:.4f}, {lon:.4f}
            """
            
            # Use black folium Marker for customer depots
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=250),
                tooltip=f"Customer Depot {customer_id}",
                icon=folium.Icon(color='black', icon='home')
            ).add_to(map_viz)
