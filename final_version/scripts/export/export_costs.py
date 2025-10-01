#!/usr/bin/env python3
"""
Cost Dictionary Export Utility

Exports the complete precomputed cost dictionary from precomputation.py
in various formats for analysis and external use.
"""

import json
import pandas as pd
from pathlib import Path
from src.precomputation import FuelOptimizationPrecomputation
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def export_cost_dictionary(output_format='json', output_file=None):
    """
    Export the complete cost dictionary in specified format.
    
    Args:
        output_format (str): 'json', 'csv', 'excel', or 'all'
        output_file (str): Optional custom filename (without extension)
    
    Returns:
        dict: The cost dictionary that was exported
    """
    # Generate cost dictionary
    logger.info("Starting complete precomputation pipeline...")
    precomputer = FuelOptimizationPrecomputation()
    cost_data = precomputer.run_complete_precomputation()
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = output_file or f"fuel_costs_{timestamp}"
    
    if output_format in ['json', 'all']:
        json_file = f"{base_filename}.json"
        logger.info(f"Exporting JSON to {json_file}...")
        
        with open(json_file, 'w') as f:
            json.dump(cost_data, f, indent=2, default=str)
        
        logger.info(f"✅ JSON export completed: {json_file}")
    
    if output_format in ['csv', 'all']:
        csv_file = f"{base_filename}_flattened.csv"
        logger.info(f"Exporting CSV to {csv_file}...")
        
        # Flatten the nested dictionary for CSV
        flattened_data = []
        
        for depot_id, depot_data in cost_data['costs'].items():
            # Get depot info from the first supplier entry (they all have the same depot info)
            first_supplier_data = list(depot_data.values())[0] if depot_data else {}
            depot_volume = cost_data.get('customer_depots', {}).get(int(depot_id), {}).get('annual_volume', 0)
            depot_name = cost_data.get('customer_depots', {}).get(int(depot_id), {}).get('name', f'Depot_{depot_id}')
            
            for supplier_depot_id, options in depot_data.items():
                # Extract supplier info from the options dict itself
                supplier_name = options.get('supplier_name', 'Unknown')
                supplier_depot_name = options.get('supplier_depot_name', f'Depot_{supplier_depot_id}')
                distance_km = options.get('distance_km', None)
                
                # Identify base cost options (non-metadata keys)
                metadata_keys = {'supplier_id', 'supplier_name', 'supplier_depot_name', 'distance_km', 
                               'supplier_depot_lat', 'supplier_depot_lon', 'supplier_depot_country', 
                               'supplier_depot_location', 'tier_costs'}
                
                base_costs = {k: v for k, v in options.items() if k not in metadata_keys and isinstance(v, (int, float))}
                
                # Add base costs
                for option_type, cost in base_costs.items():
                    category = 'rac' if option_type.startswith('rac_') else 'tier_enhanced' if 'tier_' in option_type else 'base'
                    
                    flattened_data.append({
                        'customer_depot_id': depot_id,
                        'customer_depot_name': depot_name,
                        'customer_annual_volume': depot_volume,
                        'supplier_depot_id': supplier_depot_id,
                        'supplier_name': supplier_name,
                        'supplier_depot_name': supplier_depot_name,
                        'distance_km': distance_km,
                        'option_category': category,
                        'option_type': option_type,
                        'cost_per_litre': cost,
                        'annual_cost': cost * depot_volume if cost and depot_volume else None,
                        'tier_band': None,
                        'tier_contract': None
                    })
                
                # Add tier costs if they exist
                for tier_name, tier_costs in options.get('tier_costs', {}).items():
                    if isinstance(tier_costs, dict):
                        for option_type, cost in tier_costs.items():
                            flattened_data.append({
                                'customer_depot_id': depot_id,
                                'customer_depot_name': depot_name,
                                'customer_annual_volume': depot_volume,
                                'supplier_depot_id': supplier_depot_id,
                                'supplier_name': supplier_name,
                                'supplier_depot_name': supplier_depot_name,
                                'distance_km': distance_km,
                                'option_category': 'tier_enhanced',
                                'option_type': option_type,
                                'cost_per_litre': cost,
                                'annual_cost': cost * depot_volume if cost and depot_volume else None,
                                'tier_band': tier_name,
                                'tier_contract': 'supplier_C_tiers' if 'Supplier C' in supplier_name else 'supplier_I_DEL_tiers'
                            })
        
        df = pd.DataFrame(flattened_data)
        df.to_csv(csv_file, index=False)
        
        logger.info(f"✅ CSV export completed: {csv_file} ({len(flattened_data)} rows)")
    
    if output_format in ['excel', 'all']:
        excel_file = f"{base_filename}.xlsx"
        logger.info(f"Exporting Excel to {excel_file}...")
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = {
                'Metric': [
                    'Total Customer Depots',
                    'Total Supplier Depots', 
                    'Total Cost Options',
                    'Total Depot-Supplier Combinations',
                    'Export Timestamp'
                ],
                'Value': [
                    len(cost_data.get('customer_depots', {})),
                    len(cost_data.get('supplier_depots', {})),
                    cost_data.get('total_cost_options', 0),
                    cost_data.get('total_combinations', 0),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Customer depots sheet
            if 'customer_depots' in cost_data:
                depot_df = pd.DataFrame(cost_data['customer_depots']).T
                depot_df.to_excel(writer, sheet_name='Customer_Depots', index_label='depot_id')
            
            # Supplier depots sheet
            if 'supplier_depots' in cost_data:
                supplier_df = pd.DataFrame(cost_data['supplier_depots']).T
                supplier_df.to_excel(writer, sheet_name='Supplier_Depots', index_label='supplier_depot_id')
            
            # Flattened costs (same as CSV but in Excel)
            if 'flattened_data' in locals():
                costs_df = pd.DataFrame(flattened_data)
                costs_df.to_excel(writer, sheet_name='All_Costs', index=False)
        
        logger.info(f"✅ Excel export completed: {excel_file}")
    
    # Print summary
    logger.info(f"""
    📊 COST DICTIONARY EXPORT SUMMARY:
    - Customer Depots: {len(cost_data.get('customer_depots', {}))}
    - Supplier Depots: {len(cost_data.get('supplier_depots', {}))}
    - Total Cost Options: {cost_data.get('total_cost_options', 0):,}
    - Depot-Supplier Combinations: {cost_data.get('total_combinations', 0):,}
    - Formats Exported: {output_format}
    """)
    
    return cost_data

def main():
    """Command line interface for cost dictionary export."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export fuel optimization cost dictionary')
    parser.add_argument('--format', choices=['json', 'csv', 'excel', 'all'], 
                        default='json', help='Output format (default: json)')
    parser.add_argument('--output', help='Output filename (without extension)')
    
    args = parser.parse_args()
    
    try:
        cost_data = export_cost_dictionary(args.format, args.output)
        print("✅ Export completed successfully!")
        return cost_data
    except Exception as e:
        logger.error(f"❌ Export failed: {e}")
        raise

if __name__ == "__main__":
    main()