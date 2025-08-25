#!/usr/bin/env python3
"""
Optimization Results Mapping Module

This module creates interactive maps showing the fuel depot allocation optimization results.
It visualizes customer depots, supplier depots, and allocation connections on a map of 
South Africa and neighboring countries.
"""

import sqlite3
import pandas as pd
import folium
from folium import plugins
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class OptimizationMapper:
    """
    Creates interactive maps showing optimization allocation results.
    """
    
    def __init__(self, db_path: str = "fuel_data.db"):
        """Initialize mapper with database connection."""
        self.db_path = db_path
        self.customer_coords = {}
        self.supplier_coords = {}
        
        # Color schemes for different suppliers - using both hex and folium color names
        self.supplier_colors = {
            'Supplier A': {'hex': '#FF0000', 'folium': 'red'},     # Red  
            'Supplier C': {'hex': '#0066CC', 'folium': 'blue'},   # Blue
            'Supplier D': {'hex': '#00AA00', 'folium': 'green'},  # Green
            'Supplier F': {'hex': '#FF8000', 'folium': 'orange'}, # Orange
            'Supplier G': {'hex': '#800080', 'folium': 'purple'}, # Purple
            'Supplier H': {'hex': '#006600', 'folium': 'darkgreen'}, # Dark Green
            'Supplier I': {'hex': '#FF00FF', 'folium': 'pink'},   # Magenta/Pink
            'Supplier J': {'hex': '#00AAAA', 'folium': 'lightblue'}, # Cyan/Light Blue
            'Supplier L': {'hex': '#800000', 'folium': 'darkred'} # Maroon/Dark Red
        }
        
        # Load coordinates from database
        self._load_coordinates()
    
    def _load_coordinates(self):
        """Load depot coordinates from database."""
        logger.info("Loading depot coordinates from database...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load customer depot coordinates
                customer_query = """
                    SELECT Cust_Depot_PK, Cust_Depot_Name, Lats, Long, Country, Town
                    FROM customer_depots
                """
                df_customer = pd.read_sql(customer_query, conn)
                
                for _, row in df_customer.iterrows():
                    self.customer_coords[row['Cust_Depot_PK']] = {
                        'name': row['Cust_Depot_Name'],
                        'lat': row['Lats'],
                        'lng': row['Long'],
                        'country': row['Country'],
                        'town': row['Town']
                    }
                
                # Load supplier depot coordinates  
                supplier_query = """
                    SELECT sd.Supplier_Depot_PK, sd.Supply_Depot_Name, sd.supplier_lat, 
                           sd.supplier_lng, sd.Country, sd.Supply_Depot_Location, s.Supplier_Name_
                    FROM supplier_depots sd
                    JOIN suppliers s ON sd.Supplier_FK = s.Supplier_PK
                """
                df_supplier = pd.read_sql(supplier_query, conn)
                
                for _, row in df_supplier.iterrows():
                    self.supplier_coords[row['Supplier_Depot_PK']] = {
                        'name': row['Supply_Depot_Name'],
                        'lat': row['supplier_lat'],
                        'lng': row['supplier_lng'],
                        'country': row['Country'],
                        'location': row['Supply_Depot_Location'],
                        'supplier_name': row['Supplier_Name_']
                    }
                
                logger.info(f"Loaded coordinates for {len(self.customer_coords)} customer depots and {len(self.supplier_coords)} supplier depots")
                
        except Exception as e:
            logger.error(f"Failed to load coordinates: {e}")
            raise
    
    def create_allocation_map(self, optimization_results: Dict[str, Any], save_path: str = "optimization_allocation_map.html") -> str:
        """
        Create an interactive map showing optimization allocation results.
        
        Args:
            optimization_results: Results from optimizer containing allocations
            save_path: Path to save the HTML map file
            
        Returns:
            str: Path to the generated HTML map file
        """
        logger.info("Creating optimization allocation map...")
        
        # Calculate map center (South Africa region)
        center_lat = -28.0
        center_lng = 24.0
        
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=5,
            tiles='OpenStreetMap'
        )
        
        # Add additional tile layers for better visualization
        folium.TileLayer(
            'Stamen Terrain', 
            name='Terrain',
            attr='Map tiles by Stamen Design, CC BY 3.0'
        ).add_to(m)
        folium.TileLayer(
            'CartoDB positron', 
            name='Light',
            attr='© OpenStreetMap contributors, © CartoDB'
        ).add_to(m)
        
        # Track allocations for statistics
        allocation_stats = {}
        total_cost = 0
        total_volume = 0
        
        # Process allocations from optimization results
        allocations = optimization_results.get('allocations', [])
        
        if not allocations:
            logger.warning("No allocations found in optimization results")
            return save_path
        
        # Add allocation connections (lines between customer and supplier depots)
        for allocation in allocations:
            customer_depot_id = allocation['customer_depot_id']
            supplier_depot_id = allocation['supplier_depot_id']
            supplier_name = allocation['supplier_name']
            annual_volume = allocation['annual_volume']
            cost_per_litre = allocation['cost_per_litre']
            total_cost_allocation = allocation['total_cost']
            option_type = allocation['option_type']
            cost_type = allocation.get('cost_type', 'base')
            
            # Get coordinates
            if customer_depot_id not in self.customer_coords:
                logger.warning(f"Customer depot {customer_depot_id} coordinates not found")
                continue
                
            if supplier_depot_id not in self.supplier_coords:
                logger.warning(f"Supplier depot {supplier_depot_id} coordinates not found")
                continue
            
            customer_coord = self.customer_coords[customer_depot_id]
            supplier_coord = self.supplier_coords[supplier_depot_id]
            
            # Get supplier color (hex for lines)
            supplier_color_info = self.supplier_colors.get(supplier_name, {'hex': '#000000', 'folium': 'black'})
            supplier_color = supplier_color_info['hex']
            
            # Create connection line
            line_coords = [
                [customer_coord['lat'], customer_coord['lng']],
                [supplier_coord['lat'], supplier_coord['lng']]
            ]
            
            # Line thickness based on volume (scaled for visibility)
            line_weight = max(2, min(8, annual_volume / 1000000))  # 2-8px based on millions of litres
            
            # Line opacity based on cost type
            line_opacity = 0.9 if cost_type == 'rac_penalty' else 0.7 if cost_type == 'tier_enhanced' else 0.5
            
            # Create popup content for the connection line
            popup_content = f"""
            <b>Allocation Details</b><br>
            Customer: {customer_coord['name']} ({customer_coord['town']})<br>
            Supplier: {supplier_coord['name']} ({supplier_name})<br>
            Option: {option_type}<br>
            Cost Type: {cost_type}<br>
            Volume: {annual_volume:,.0f} L<br>
            Cost/L: R {cost_per_litre:.4f}<br>
            Total Cost: R {total_cost_allocation:,.2f}
            """
            
            folium.PolyLine(
                locations=line_coords,
                color=supplier_color,
                weight=line_weight,
                opacity=line_opacity,
                popup=folium.Popup(popup_content, max_width=300)
            ).add_to(m)
            
            # Track statistics
            if supplier_name not in allocation_stats:
                allocation_stats[supplier_name] = {
                    'allocations': 0,
                    'total_volume': 0,
                    'total_cost': 0,
                    'color': supplier_color  # hex color for legend
                }
            
            allocation_stats[supplier_name]['allocations'] += 1
            allocation_stats[supplier_name]['total_volume'] += annual_volume
            allocation_stats[supplier_name]['total_cost'] += total_cost_allocation
            
            total_cost += total_cost_allocation
            total_volume += annual_volume
        
        # Add customer depot markers (all black with different icons for allocated/unallocated)
        for depot_id, coord in self.customer_coords.items():
            # Find if this depot has allocations
            depot_allocations = [a for a in allocations if a['customer_depot_id'] == depot_id]
            
            if depot_allocations:
                # Depot has allocation - use black marker with filled circle
                icon_name = 'circle'
                allocation_info = depot_allocations[0]  # Should only be one allocation per depot
                
                popup_content = f"""
                <b>Customer Depot: {coord['name']}</b><br>
                Location: {coord['town']}, {coord['country']}<br>
                <br><b>Allocation:</b><br>
                Supplier: {allocation_info['supplier_name']}<br>
                Volume: {allocation_info['annual_volume']:,.0f} L<br>
                Cost: R {allocation_info['total_cost']:,.2f}
                """
            else:
                # No allocation - use black marker with empty circle
                icon_name = 'circle-o'
                popup_content = f"""
                <b>Customer Depot: {coord['name']}</b><br>
                Location: {coord['town']}, {coord['country']}<br>
                Status: <span style="color:red">No Allocation</span>
                """
            
            folium.Marker(
                location=[coord['lat'], coord['lng']],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"Customer: {coord['name']}",
                icon=folium.Icon(color='black', icon=icon_name, prefix='fa')
            ).add_to(m)
        
        # Add marker clustering to handle overlapping points
        marker_cluster = plugins.MarkerCluster().add_to(m)
        
        # Add supplier depot markers
        for depot_id, coord in self.supplier_coords.items():
            # Find allocations from this supplier depot
            supplier_allocations = [a for a in allocations if a['supplier_depot_id'] == depot_id]
            
            supplier_name = coord['supplier_name']
            supplier_color_info = self.supplier_colors.get(supplier_name, {'hex': '#000000', 'folium': 'black'})
            folium_color = supplier_color_info['folium']
            
            # Add slight offset to reduce exact overlaps
            lat_offset = 0.002 * ((depot_id % 5) - 2)  # Small random-ish offset
            lng_offset = 0.002 * (((depot_id * 3) % 5) - 2)
            
            if supplier_allocations:
                total_supplier_volume = sum(a['annual_volume'] for a in supplier_allocations)
                total_supplier_cost = sum(a['total_cost'] for a in supplier_allocations)
                
                popup_content = f"""
                <b>Supplier Depot: {coord['name']}</b><br>
                Supplier: {supplier_name}<br>
                Location: {coord['location']}, {coord['country']}<br>
                <br><b>Allocations: {len(supplier_allocations)}</b><br>
                Total Volume: {total_supplier_volume:,.0f} L<br>
                Total Cost: R {total_supplier_cost:,.2f}
                """
            else:
                popup_content = f"""
                <b>Supplier Depot: {coord['name']}</b><br>
                Supplier: {supplier_name}<br>
                Location: {coord['location']}, {coord['country']}<br>
                Status: <span style="color:gray">Not Used</span>
                """
            
            folium.Marker(
                location=[coord['lat'] + lat_offset, coord['lng'] + lng_offset],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"Supplier: {coord['name']} ({supplier_name})",
                icon=folium.Icon(color=folium_color, icon='industry', prefix='fa')
            ).add_to(marker_cluster)
        
        # Add legend for suppliers
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 250px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <b>Fuel Depot Allocation Results</b><br>
        <hr style="margin:5px 0;">
        '''
        
        # Add supplier legend entries
        for supplier, stats in allocation_stats.items():
            avg_cost = stats['total_cost'] / stats['total_volume'] if stats['total_volume'] > 0 else 0
            legend_html += f'''
            <div style="margin: 3px 0;">
                <span style="color: {stats['color']}; font-size: 16px;">●</span> 
                <b>{supplier}</b><br>
                &nbsp;&nbsp;&nbsp;Depots: {stats['allocations']}<br>
                &nbsp;&nbsp;&nbsp;Volume: {stats['total_volume']/1000000:.1f}M L<br>
                &nbsp;&nbsp;&nbsp;Avg Cost: R {avg_cost:.3f}/L
            </div>
            '''
        
        legend_html += f'''
        <hr style="margin:5px 0;">
        <b>Total Volume:</b> {total_volume/1000000:.1f}M L<br>
        <b>Total Cost:</b> R {total_cost:,.0f}<br>
        <b>Avg Cost:</b> R {total_cost/total_volume if total_volume > 0 else 0:.4f}/L
        </div>
        '''
        
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add fullscreen button
        plugins.Fullscreen().add_to(m)
        
        # Add measure control for distances
        plugins.MeasureControl().add_to(m)
        
        # Save map
        m.save(save_path)
        
        logger.info(f"Optimization allocation map saved to: {save_path}")
        logger.info(f"Map shows {len(allocations)} allocations across {len(allocation_stats)} suppliers")
        
        return save_path