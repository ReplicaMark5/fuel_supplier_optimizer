#!/usr/bin/env python3
"""
Fuel Depot Allocation Precomputation Module

Loads data from SQLite database, applies user parameters, and calculates
all base cost coefficients in Present Value terms for optimization.

This module handles:
- Database loading and joins
- Fuel zone mapping (SA: 09A->9A, International: country pricing)  
- Present Value calculations for all cost components
- Option availability filtering (NULL = not available)
- Base cost dictionary generation (volume tiers handled separately)
"""

import json
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FuelOptimizationPrecomputation:
    """Main precomputation class for fuel depot allocation optimization."""
    
    def __init__(self, config_path: str = "optimization_config.json", db_path: str = "fuel_data.db"):
        """Initialize with configuration and database paths."""
        self.config_path = config_path
        self.db_path = db_path
        self.config = self._load_config()
        self.raw_data = None
        self.base_costs = {}
        
        # Supplier ID to name mapping (for volume tier filtering)
        self.supplier_id_to_name = {
            1: "Supplier A", 2: "Supplier C", 3: "Supplier D", 4: "Supplier F", 5: "Supplier G", 
            6: "Supplier H", 7: "Supplier I", 8: "Supplier J", 9: "Supplier L"
        }
        
        # Cache PV factors to avoid redundant calculations
        self._cached_pv_factors = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load and validate optimization configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def load_data_from_database(self) -> pd.DataFrame:
        """
        Load and join all necessary tables from the reorganized database.
        
        Returns:
            pd.DataFrame: Combined dataset with all required columns
        """
        logger.info("Loading data from database...")
        
        query = """
        SELECT 
            -- Core identifiers
            od.Customer_Depot_FK,
            od.Supplier_Depot_FK,
            sd.Supplier_FK,
            
            -- Distance and availability
            od.One_Way_Dist,
            od.COC_Valid_FK,
            od.DEL_Valid_FK,
            
            -- Customer depot information
            cd.Annual_Volume_Litres as depot_annual_volume,
            cd.Cust_Depot_Name as customer_depot_name,
            cd.Fuel_Zone_ as customer_fuel_zone,
            
            -- Supplier depot information  
            sd.Supply_Depot_Name,
            sd.Fuel_Zone_ as supplier_fuel_zone,
            sd.Supply_Depot_Location as Supply_Depot_Address,
            
            -- Supplier information (from suppliers table)
            s.Supplier_Name_ as supplier_name,
            
            -- Collection option rebates (from collection_options table)
            co.COC_reb_pl_cash,
            co.COC_reb_pl_30,
            co.COC_reb_pl_45,
            co.COC_reb_pl_60,
            
            -- Delivery option rebates and equipment costs (from delivery_options table)
            do.DEL_reb_pl_30,
            do.equip_fin_pl_30,
            do.equip_main_pl_30,
            
            -- Fuel pricing (matched by supplier depot fuel zone)
            dp.rtl_wholesale,
            dp.product as fuel_product
            
        FROM od_pair od
        
        -- Join customer depots
        LEFT JOIN customer_depots cd ON od.Customer_Depot_FK = cd.Cust_Depot_PK
        
        -- Join supplier depots (now directly from od_pair)
        LEFT JOIN supplier_depots sd ON od.Supplier_Depot_FK = sd.Supplier_Depot_PK
        
        -- Join suppliers table to get supplier names
        LEFT JOIN suppliers s ON sd.Supplier_FK = s.Supplier_PK
        
        -- Join collection options (when COC is valid)
        LEFT JOIN collection_options co ON od.COC_Valid_FK = co.COC_Valid_PK
        
        -- Join delivery options (when DEL is valid)
        LEFT JOIN delivery_options do ON od.DEL_Valid_FK = do.DEL_Valid_PK
        
        -- Join diesel prices (with fuel zone mapping)
        LEFT JOIN diesel_prices dp ON LTRIM(sd.Fuel_Zone_, '0') = dp.zone 
            AND dp.product = ?
            
        -- Only include records where at least one option (COC or DEL) is available
        WHERE (od.COC_Valid_FK IS NOT NULL OR od.DEL_Valid_FK IS NOT NULL)
            AND od.Supplier_Depot_FK IS NOT NULL
            
        ORDER BY od.Customer_Depot_FK, od.Supplier_Depot_FK
        """
        
        fuel_type = self.config['basic_parameters']['fuel_type']
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=[fuel_type])
            
            logger.info(f"Loaded {len(df)} records from database")
            logger.info(f"Columns: {list(df.columns)}")
            
            # Store raw data for reference
            self.raw_data = df.copy()
            
            return df
            
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}")
    
    def apply_fuel_zone_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply fuel zone mapping and international pricing.
        
        Args:
            df: Raw data DataFrame
            
        Returns:
            pd.DataFrame: Data with fuel zone mapping applied
        """
        logger.info("Applying fuel zone mapping...")
        
        # Clean fuel zones for SA depots (09A -> 9A, 01A -> 1A)
        df['fuel_zone_clean'] = df['supplier_fuel_zone'].str.lstrip('0').fillna('')
        
        # Identify international depots (NULL fuel zones)
        df['is_international'] = df['supplier_fuel_zone'].isnull()
        
        # Map countries for international depots
        international_mapping = {
            'Francistown': 'Botswana',
            'Gaborone': 'Botswana', 
            'Matola': 'Mozambique',
            'Matsapha': 'Eswatini',
            'Walvis Bay': 'Namibia'
        }
        
        def get_country(address):
            if pd.isna(address):
                return None
            for city, country in international_mapping.items():
                if city in str(address):
                    return country
            return None
        
        df['depot_country'] = df['Supply_Depot_Address'].apply(get_country)
        
        # Apply fuel pricing based on location type
        international_prices = self.config['international_fuel_prices']
        
        df['rtl_wholesale_per_litre'] = np.where(
            df['is_international'],
            df['depot_country'].map(international_prices),  # International pricing (R/litre)
            df['rtl_wholesale'] / 100  # SA pricing (cents to rand per litre)
        )
        
        # Log mapping results
        sa_depots = (~df['is_international']).sum()
        intl_depots = df['is_international'].sum()
        missing_pricing = df['rtl_wholesale_per_litre'].isnull().sum()
        
        logger.info(f"SA depots: {sa_depots}, International depots: {intl_depots}")
        logger.info(f"Missing fuel pricing: {missing_pricing} records")
        
        return df
    
    def calculate_present_value_factors(self) -> Dict[str, float]:
        """Calculate PV factors for different payment terms (cached)."""
        if self._cached_pv_factors is not None:
            return self._cached_pv_factors
            
        wacc_percent = self.config['basic_parameters']['wacc_percent']
        wacc_decimal = wacc_percent / 100.0  # Convert percentage to decimal
        
        pv_factors = {
            'cash': 1.0,  # No discounting for cash
            'net30': (1 + wacc_decimal/365) ** 30,
            'net45': (1 + wacc_decimal/365) ** 45, 
            'net60': (1 + wacc_decimal/365) ** 60
        }
        
        # Cache the result
        self._cached_pv_factors = pv_factors
        logger.info(f"PV factors calculated and cached: {pv_factors}")
        return pv_factors
    
    def calculate_transport_costs(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate transport costs for COC options.
        
        Args:
            df: Data with distance information
            
        Returns:
            pd.DataFrame: Data with transport costs added
        """
        tanker_cost_per_km = self.config['basic_parameters']['tanker_cost_per_km']
        tanker_capacity = self.config['basic_parameters']['tanker_capacity']
        
        # Only calculate transport costs for COC options where distance is available
        df['trans_cost_pl'] = np.where(
            df['COC_Valid_FK'].notna() & df['One_Way_Dist'].notna(),
            (df['One_Way_Dist'] * 2 * tanker_cost_per_km) / tanker_capacity,
            0  # No transport cost for DEL options or missing distances
        )
        
        logger.info(f"Transport costs calculated for {(df['trans_cost_pl'] > 0).sum()} COC records")
        return df
    
    def calculate_base_costs(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all base cost options in Present Value terms.
        
        Args:
            df: Data with fuel pricing and rebates
            
        Returns:
            pd.DataFrame: Data with all cost calculations added
        """
        logger.info("Calculating base costs...")
        
        pv_factors = self.calculate_present_value_factors()
        
        # User-specified equipment costs (already in PV terms)
        cost_owned_equip_pv = self.config['basic_parameters']['cost_owned_equip_pv']
        cost_buy_equip_pv = self.config['basic_parameters']['cost_buy_equip_pv']
        
        # === COC Option Calculations ===
        # Only calculate where COC is valid
        coc_mask = df['COC_Valid_FK'].notna()
        
        # COC Cash (immediate payment)
        df['coc_cash_cost_pv'] = np.where(
            coc_mask & df['COC_reb_pl_cash'].notna(),
            (df['rtl_wholesale_per_litre'] - df['COC_reb_pl_cash']) + df['trans_cost_pl'],
            np.nan
        )
        
        # COC NET30 (30-day payment)
        df['coc_30_cost_pv'] = np.where(
            coc_mask & df['COC_reb_pl_30'].notna(),
            ((df['rtl_wholesale_per_litre'] - df['COC_reb_pl_30']) / pv_factors['net30']) + df['trans_cost_pl'],
            np.nan
        )
        
        # COC NET45 (45-day payment)
        df['coc_45_cost_pv'] = np.where(
            coc_mask & df['COC_reb_pl_45'].notna(),
            ((df['rtl_wholesale_per_litre'] - df['COC_reb_pl_45']) / pv_factors['net45']) + df['trans_cost_pl'],
            np.nan
        )
        
        # COC NET60 (60-day payment) 
        df['coc_60_cost_pv'] = np.where(
            coc_mask & df['COC_reb_pl_60'].notna(),
            ((df['rtl_wholesale_per_litre'] - df['COC_reb_pl_60']) / pv_factors['net60']) + df['trans_cost_pl'],
            np.nan
        )
        
        # === DEL Option Calculations ===
        # All DEL values are NET30 and need PV discount
        del_mask = df['DEL_Valid_FK'].notna()
        pv_30d = pv_factors['net30']
        
        # DEL Own Equipment
        del_own_mask = (del_mask & 
                       df['DEL_reb_pl_30'].notna() & 
                       df['equip_fin_pl_30'].notna() & 
                       df['equip_main_pl_30'].notna())
        
        df['del_own_cost_pv'] = np.where(
            del_own_mask,
            ((df['rtl_wholesale_per_litre'] - 
              (df['DEL_reb_pl_30'] + df['equip_fin_pl_30'] + df['equip_main_pl_30'])) / pv_30d) + 
             cost_owned_equip_pv,
            np.nan
        )
        
        # DEL Buy Equipment  
        df['del_buy_cost_pv'] = np.where(
            del_own_mask,  # Same availability as own equipment
            ((df['rtl_wholesale_per_litre'] - 
              (df['DEL_reb_pl_30'] + df['equip_fin_pl_30'] + df['equip_main_pl_30'])) / pv_30d) + 
             cost_buy_equip_pv,
            np.nan
        )
        
        # DEL Rent Equipment (simpler - no equipment financing/maintenance)
        df['del_rent_cost_pv'] = np.where(
            del_mask & df['DEL_reb_pl_30'].notna(),
            (df['rtl_wholesale_per_litre'] - df['DEL_reb_pl_30']) / pv_30d,
            np.nan
        )
        
        # Log calculation results
        cost_columns = ['coc_cash_cost_pv', 'coc_30_cost_pv', 'coc_45_cost_pv', 'coc_60_cost_pv',
                       'del_own_cost_pv', 'del_buy_cost_pv', 'del_rent_cost_pv']
        
        for col in cost_columns:
            available_count = df[col].notna().sum()
            logger.info(f"{col}: {available_count} available calculations")
        
        return df
    
    def build_cost_dictionary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Build the base cost dictionary structure for optimizer consumption.
        
        Args:
            df: Data with all cost calculations
            
        Returns:
            Dict: Nested cost dictionary by depot -> supplier -> option
        """
        logger.info("Building cost dictionary...")
        
        cost_dict = {}
        depot_dict = {}
        supplier_dict = {}
        
        cost_columns = {
            'coc_cash': 'coc_cash_cost_pv',
            'coc_30': 'coc_30_cost_pv', 
            'coc_45': 'coc_45_cost_pv',
            'coc_60': 'coc_60_cost_pv',
            'del_own': 'del_own_cost_pv',
            'del_buy': 'del_buy_cost_pv', 
            'del_rent': 'del_rent_cost_pv'
        }
        
        for _, row in df.iterrows():
            depot_id = row['Customer_Depot_FK']
            supplier_id = row['Supplier_FK']
            supplier_depot_id = row['Supplier_Depot_FK']
            
            # Skip rows with missing supplier information
            if pd.isna(supplier_id) or pd.isna(supplier_depot_id):
                continue
                
            # Convert to int to avoid float issues
            supplier_id = int(supplier_id)
            supplier_depot_id = int(supplier_depot_id)
            
            # Initialize nested dictionaries by supplier depot (not just supplier)
            if depot_id not in cost_dict:
                cost_dict[depot_id] = {}
            if supplier_depot_id not in cost_dict[depot_id]:
                cost_dict[depot_id][supplier_depot_id] = {}
            
            # Add available cost options only
            for option, cost_col in cost_columns.items():
                if pd.notna(row[cost_col]):
                    cost_dict[depot_id][supplier_depot_id][option] = round(row[cost_col], 6)
            
            # Build supporting dictionaries
            if depot_id not in depot_dict:
                depot_dict[depot_id] = {
                    'annual_volume': row['depot_annual_volume'],
                    'name': row['customer_depot_name'],
                    'fuel_zone': row['customer_fuel_zone']
                }
            
            if supplier_id not in supplier_dict:
                supplier_name = row.get('supplier_name', f"Supplier {supplier_id}")
                supplier_dict[supplier_id] = {
                    'name': supplier_name,
                    'depots': []
                }
            
            # Track supplier depot relationships
            if supplier_depot_id not in supplier_dict[supplier_id]['depots']:
                supplier_dict[supplier_id]['depots'].append(supplier_depot_id)
        
        # Log dictionary statistics
        total_combinations = sum(len(supplier_depots) for supplier_depots in cost_dict.values())
        total_options = sum(len(options) for depot in cost_dict.values() 
                           for options in depot.values())
        
        logger.info(f"Cost dictionary built: {len(cost_dict)} depots, "
                   f"{total_combinations} depot-supplier_depot combinations, "
                   f"{total_options} total cost options")
        
        return {
            'costs': cost_dict,
            'depots': depot_dict,
            'suppliers': supplier_dict,
            'metadata': {
                'fuel_type': self.config['basic_parameters']['fuel_type'],
                'wacc_percent': self.config['basic_parameters']['wacc_percent'],
                'total_depots': len(depot_dict),
                'total_suppliers': len(supplier_dict),
                'total_cost_options': total_options
            }
        }
    
    def run_base_precomputation(self) -> Dict[str, Any]:
        """
        Execute the complete base precomputation pipeline.
        
        Returns:
            Dict: Complete cost dictionary ready for optimization
        """
        logger.info("Starting base precomputation pipeline...")
        
        # Step 1: Load data from database
        df = self.load_data_from_database()
        
        # Step 2: Apply fuel zone mapping
        df = self.apply_fuel_zone_mapping(df)
        
        # Step 3: Calculate transport costs
        df = self.calculate_transport_costs(df)
        
        # Step 4: Calculate all base costs
        df = self.calculate_base_costs(df)
        
        # Step 5: Build cost dictionary
        cost_data = self.build_cost_dictionary(df)
        
        logger.info("Base precomputation completed successfully!")
        return cost_data
    
    def calculate_volume_tier_rebate(self, volume_litres: float, tier_config: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate volume tier rebate for a given volume and tier configuration.
        
        Args:
            volume_litres: Annual volume in litres
            tier_config: Volume tier configuration from config file
            
        Returns:
            Dict with rebate calculation details
        """
        bands = tier_config['tiers']['bands']
        logic = tier_config['tiers']['logic']  # 'stacked' or 'all_units'
        
        total_rebate = 0.0
        applicable_bands = []
        
        if logic == 'stacked':
            # Stacked/incremental logic: different rebates for different volume ranges
            processed_volume = 0
            
            for band in bands:
                min_vol = band['min_volume']
                max_vol = band['max_volume'] or float('inf')
                band_rebate = band['rebate']
                
                # Skip bands that don't apply to this volume
                if volume_litres < min_vol:
                    break
                    
                # For stacked logic, determine volume processed in this band
                # Treat max_vol as exclusive upper bound (15M should qualify for 15M+ tier)
                if max_vol != float('inf') and volume_litres >= max_vol:
                    # If volume reaches or exceeds max_vol, process up to (but not including) max_vol
                    band_upper_limit = max_vol
                else:
                    # If volume is below max_vol, process all remaining volume
                    band_upper_limit = volume_litres
                    
                volume_in_band = band_upper_limit - max(processed_volume, min_vol)
                volume_in_band = max(0, volume_in_band)
                
                if volume_in_band > 0:
                    band_contribution = volume_in_band * band_rebate  # Rebates are in rands, not cents
                    total_rebate += band_contribution
                    
                    applicable_bands.append({
                        'min_volume': min_vol,
                        'max_volume': max_vol,
                        'volume_in_band': volume_in_band,
                        'rebate_cents': band_rebate,
                        'contribution': band_contribution
                    })
                    
                    processed_volume += volume_in_band
                    
        elif logic == 'all_units':
            # All units logic: single rebate rate applies to entire volume
            applicable_rebate = 0.0
            
            for band in bands:
                min_vol = band['min_volume']
                max_vol = band['max_volume'] or float('inf')
                
                if min_vol <= volume_litres < max_vol:
                    applicable_rebate = band['rebate']
                    applicable_bands.append({
                        'min_volume': min_vol,
                        'max_volume': max_vol,
                        'volume_in_band': volume_litres,
                        'rebate_cents': applicable_rebate,
                        'contribution': volume_litres * applicable_rebate
                    })
                    break
            
            total_rebate = volume_litres * applicable_rebate  # Rebates are in rands, not cents
        
        # Apply PV discount (all volume tier rebates are NET30)
        pv_factors = self.calculate_present_value_factors()
        total_rebate_pv = total_rebate / pv_factors['net30']
        
        return {
            'total_rebate_nominal': total_rebate,
            'total_rebate_pv': total_rebate_pv,
            'rebate_per_litre_pv': total_rebate_pv / volume_litres if volume_litres > 0 else 0,
            'logic': logic,
            'applicable_bands': applicable_bands,
            'tier_name': tier_config.get('description', 'Unknown')
        }
    
    def get_applicable_volume_tiers(self, supplier_id: int, supplier_depot_id: int, option: str) -> List[str]:
        """
        Get list of applicable volume tier configurations for a supplier_depot-option combination.
        
        Args:
            supplier_id: Supplier ID
            supplier_depot_id: Supplier depot ID  
            option: Option type (coc_cash, coc_30, del_own, etc.)
            
        Returns:
            List of applicable tier configuration names
        """
        applicable_tiers = []
        volume_tiers = self.config.get('volume_tier_configurations', {})
        
        for tier_name, tier_config in volume_tiers.items():
            # Check scope filters
            scope = tier_config.get('scope_filters', {})
            
            # Check supplier filter (map numeric ID to letter name)
            supplier_filter = scope.get('suppliers', ['*'])
            supplier_name = self.supplier_id_to_name.get(supplier_id, str(supplier_id))
            if supplier_filter != ['*'] and supplier_name not in supplier_filter:
                continue
                
            # Check supplier depot filter (CHANGED: now filtering by supplier depot ID)
            supplier_depot_filter = scope.get('supplier_depots', ['*']) 
            if supplier_depot_filter != ['*'] and str(supplier_depot_id) not in supplier_depot_filter:
                continue
                
            # Check mode filter (COC/DEL)
            mode_filter = scope.get('modes', ['*'])
            option_mode = 'COC' if option.startswith('coc_') else 'DEL'
            if mode_filter != ['*'] and option_mode not in mode_filter:
                continue
                
            # Check payment terms filter
            terms_filter = scope.get('terms', ['*'])
            option_term = option.replace('coc_', '').replace('del_', '').upper()
            if option_term == 'CASH':
                option_term = 'CASH'
            elif option_term in ['30', 'OWN', 'BUY', 'RENT']:
                option_term = 'NET30'  # All non-cash options are NET30
            elif option_term == '45':
                option_term = 'NET45'
            elif option_term == '60':
                option_term = 'NET60'
                
            if terms_filter != ['*'] and option_term not in terms_filter:
                continue
                
            applicable_tiers.append(tier_name)
            
        return applicable_tiers
    
    def _decompose_base_cost_components(self, row: pd.Series, option: str) -> Dict[str, float]:
        """
        Decompose base cost into components needed for volume tier combination rules.
        
        Args:
            row: DataFrame row with all cost calculation data
            option: Cost option (coc_cash, coc_30, del_own, etc.)
            
        Returns:
            Dict with wholesale_price, base_rebate_pv, transport_cost, equipment_cost
        """
        pv_factors = self.calculate_present_value_factors()
        wholesale_price = row['rtl_wholesale_per_litre']
        transport_cost = row.get('trans_cost_pl', 0.0)
        
        # Equipment costs from config (already in PV terms)
        cost_owned_equip_pv = self.config['basic_parameters']['cost_owned_equip_pv']
        cost_buy_equip_pv = self.config['basic_parameters']['cost_buy_equip_pv']
        
        if option == 'coc_cash':
            base_rebate = row.get('COC_reb_pl_cash', 0.0)
            base_rebate_pv = base_rebate  # No PV discount for cash
            equipment_cost = 0.0
            
        elif option == 'coc_30':
            base_rebate = row.get('COC_reb_pl_30', 0.0)
            base_rebate_pv = base_rebate / pv_factors['net30']
            equipment_cost = 0.0
            
        elif option == 'coc_45':
            base_rebate = row.get('COC_reb_pl_45', 0.0)
            base_rebate_pv = base_rebate / pv_factors['net45']
            equipment_cost = 0.0
            
        elif option == 'coc_60':
            base_rebate = row.get('COC_reb_pl_60', 0.0)
            base_rebate_pv = base_rebate / pv_factors['net60']
            equipment_cost = 0.0
            
        elif option == 'del_own':
            base_rebate = (row.get('DEL_reb_pl_30', 0.0) + 
                          row.get('equip_fin_pl_30', 0.0) + 
                          row.get('equip_main_pl_30', 0.0))
            base_rebate_pv = base_rebate / pv_factors['net30']
            equipment_cost = cost_owned_equip_pv
            
        elif option == 'del_buy':
            base_rebate = (row.get('DEL_reb_pl_30', 0.0) + 
                          row.get('equip_fin_pl_30', 0.0) + 
                          row.get('equip_main_pl_30', 0.0))
            base_rebate_pv = base_rebate / pv_factors['net30']
            equipment_cost = cost_buy_equip_pv
            
        elif option == 'del_rent':
            base_rebate = row.get('DEL_reb_pl_30', 0.0)
            base_rebate_pv = base_rebate / pv_factors['net30']
            equipment_cost = 0.0
            
        else:
            # Fallback for unknown options
            base_rebate_pv = 0.0
            equipment_cost = 0.0
        
        return {
            'wholesale_price': wholesale_price,
            'base_rebate_pv': base_rebate_pv,
            'transport_cost': transport_cost,
            'equipment_cost': equipment_cost
        }
    
    def _apply_combination_rule(self, components: Dict[str, float], volume_tier_rebate_pv: float, 
                               combination_rule: str) -> float:
        """
        Apply combination rule logic to calculate final cost.
        
        Args:
            components: Base cost components from _decompose_base_cost_components
            volume_tier_rebate_pv: Volume tier rebate in PV terms
            combination_rule: 'add', 'override', 'multiply'
            
        Returns:
            Final cost per litre
        """
        wholesale_price = components['wholesale_price']
        base_rebate_pv = components['base_rebate_pv']
        transport_cost = components['transport_cost']
        equipment_cost = components['equipment_cost']
        
        if combination_rule == 'add':
            # Volume tier rebate adds to base rebate
            total_rebate_pv = base_rebate_pv + volume_tier_rebate_pv
            final_cost = wholesale_price - total_rebate_pv + transport_cost + equipment_cost
            
        elif combination_rule == 'override':
            # Volume tier rebate replaces base rebate entirely
            final_cost = wholesale_price - volume_tier_rebate_pv + transport_cost + equipment_cost
            
        elif combination_rule == 'multiply':
            # Volume tier multiplies the base rebate (volume_tier_rebate_pv is the multiplier)
            enhanced_base_rebate_pv = base_rebate_pv * volume_tier_rebate_pv
            final_cost = wholesale_price - enhanced_base_rebate_pv + transport_cost + equipment_cost
            
        else:
            # Fallback to add logic
            total_rebate_pv = base_rebate_pv + volume_tier_rebate_pv
            final_cost = wholesale_price - total_rebate_pv + transport_cost + equipment_cost
            
        return final_cost

    def calculate_tier_costs(self, base_costs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate tier costs (using volume tier rebates) for optimizer integration.
        
        Args:
            base_costs: Base cost dictionary from Phase 1
            
        Returns:
            Enhanced cost dictionary with both base_costs and tier_costs
        """
        logger.info("Calculating tier costs for optimizer...")
        
        enhanced_costs = {
            'costs': {},
            'depots': base_costs['depots'].copy(),
            'suppliers': base_costs['suppliers'].copy(), 
            'supplier_depots': {},
            'metadata': base_costs['metadata'].copy()
        }
        
        # Process each depot-supplier_depot combination
        for depot_id, supplier_depots in base_costs['costs'].items():
            enhanced_costs['costs'][depot_id] = {}
            
            for supplier_depot_id, base_options in supplier_depots.items():
                # Get supplier info from base costs metadata
                supplier_depot_info = {}
                if self.raw_data is not None:
                    matching_rows = self.raw_data[self.raw_data['Supplier_Depot_FK'] == supplier_depot_id]
                    if not matching_rows.empty:
                        row = matching_rows.iloc[0]
                        supplier_depot_info = {
                            'supplier_id': int(row['Supplier_FK']),
                            'supplier_name': row.get('supplier_name', f"Supplier {int(row['Supplier_FK'])}"),
                            'supplier_depot_name': row.get('Supply_Depot_Name', ''),
                            'distance_km': row.get('One_Way_Dist'),
                            'available_options': list(base_options.keys())
                        }
                
                # Initialize depot structure with base costs
                depot_structure = {
                    'base_costs': base_options.copy(),
                    'tier_costs': {},
                    **supplier_depot_info
                }
                
                # Calculate tier costs for applicable volume tiers
                supplier_id = supplier_depot_info.get('supplier_id', 1)
                for option in base_options.keys():
                    # Get applicable volume tiers for this supplier depot + option
                    applicable_tiers = self.get_applicable_volume_tiers(supplier_id, supplier_depot_id, option)
                    
                    for tier_name in applicable_tiers:
                        if tier_name not in depot_structure['tier_costs']:
                            depot_structure['tier_costs'][tier_name] = {}
                        
                        # Calculate tier cost using volume tier rebate
                        tier_cost = self._calculate_single_tier_cost(supplier_depot_id, option, tier_name)
                        if tier_cost is not None:
                            depot_structure['tier_costs'][tier_name][option] = tier_cost
                
                enhanced_costs['costs'][depot_id][supplier_depot_id] = depot_structure
        
        return enhanced_costs
                        
                        if not applicable_tiers:
                            # No volume tiers apply - use base cost
                            enhanced_costs['costs'][depot_id][supplier_depot_id]['volume_scenarios'][volume][option] = base_cost
                        else:
                            # Get cost components for this supplier depot and option
                            cost_components = supplier_depot_cost_components.get(supplier_depot_id, {}).get(option)
                            
                            if cost_components is None:
                                # Fallback to base cost if components not available
                                enhanced_costs['costs'][depot_id][supplier_depot_id]['volume_scenarios'][volume][option] = base_cost
                                continue
                            
                            # Calculate volume tier rebates and determine final cost
                            applied_tiers = []
                            final_cost = base_cost  # Fallback value
                            
                            for tier_name in applicable_tiers:
                                tier_config = self.config['volume_tier_configurations'][tier_name]
                                tier_result = self.calculate_volume_tier_rebate(volume, tier_config)
                                combination_rule = tier_config.get('combination_rule', {}).get('with_base_rebates', 'add')
                                
                                # Special handling: if volume is 0 or no meaningful rebate, use base cost
                                if volume == 0 or abs(tier_result['rebate_per_litre_pv']) < 0.0001:
                                    final_cost = base_cost
                                else:
                                    # Apply combination rule using decomposed components
                                    final_cost = self._apply_combination_rule(
                                        components=cost_components,
                                        volume_tier_rebate_pv=tier_result['rebate_per_litre_pv'],
                                        combination_rule=combination_rule
                                    )
                                
                                applied_tiers.append({
                                    'tier_name': tier_name,
                                    'rebate_pv': tier_result['rebate_per_litre_pv'],
                                    'combination_rule': combination_rule,
                                    'logic': tier_result['logic']
                                })
                                
                                # For multiple tiers, only the last one determines final cost
                                # (This handles complex scenarios where multiple tiers might apply)
                            
                            # Store final calculated cost
                            enhanced_costs['costs'][depot_id][supplier_depot_id]['volume_scenarios'][volume][option] = final_cost
                            
                            # Store metadata for volume tier analysis
                            if 'volume_tier_metadata' not in enhanced_costs['costs'][depot_id][supplier_depot_id]['volume_scenarios'][volume]:
                                enhanced_costs['costs'][depot_id][supplier_depot_id]['volume_scenarios'][volume]['volume_tier_metadata'] = {
                                    'total_rebate_pv': base_cost - final_cost,  # Calculate effective rebate
                                    'applied_tiers': applied_tiers
                                }
        
        # Update metadata
        enhanced_costs['metadata']['volume_breakpoints'] = volume_scenarios
        enhanced_costs['metadata']['total_volume_scenarios'] = len(volume_scenarios)
        enhanced_costs['metadata']['volume_tier_enabled'] = True
        
        logger.info(f"Volume tier calculations completed for {len(volume_scenarios)} volume scenarios")
        return enhanced_costs
    
    def run_complete_precomputation(self) -> Dict[str, Any]:
        """
        Execute the complete precomputation pipeline including volume tiers.
        
        Returns:
            Dict: Complete cost dictionary with volume tier scenarios
        """
        logger.info("Starting complete precomputation pipeline with volume tiers...")
        
        # Step 1: Run base precomputation
        base_cost_data = self.run_base_precomputation()
        
        # Step 2: Get volume scenarios from config
        volume_scenarios = self.config['precomputation_settings']['volume_scenarios']['breakpoints']
        
        # Step 3: Calculate tier costs for optimizer
        enhanced_cost_data = self.calculate_tier_costs(base_cost_data)
        
        logger.info("Complete precomputation pipeline finished successfully!")
        return enhanced_cost_data
    
    def validate_volume_tier_business_rules(self, enhanced_cost_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate volume tier business rules and data integrity.
        
        Args:
            enhanced_cost_data: Enhanced cost dictionary with volume tiers
            
        Returns:
            Dict: Validation results with warnings and errors
        """
        logger.info("Validating volume tier business rules...")
        
        validation_results = {
            'status': 'valid',
            'warnings': [],
            'errors': [],
            'statistics': {
                'total_depots': 0,
                'total_combinations': 0,
                'combinations_with_volume_tiers': 0,
                'average_volume_tier_rebate': 0.0,
                'max_volume_tier_rebate': 0.0
            }
        }
        
        total_combinations = 0
        combinations_with_tiers = 0
        total_rebate_sum = 0.0
        total_rebate_entries = 0  # Count individual rebate entries, not combinations
        max_rebate = 0.0
        
        # Validate enhanced cost structure
        for depot_id, supplier_depots in enhanced_cost_data['costs'].items():
            validation_results['statistics']['total_depots'] += 1
            
            for supplier_depot_id, data in supplier_depots.items():
                total_combinations += 1
                
                # Validate base costs exist
                if not data.get('base_costs'):
                    validation_results['errors'].append(
                        f"Depot {depot_id} - Supplier Depot {supplier_depot_id}: Missing base costs"
                    )
                    continue
                
                # Validate volume scenarios
                volume_scenarios = data.get('volume_scenarios', {})
                if not volume_scenarios:
                    validation_results['warnings'].append(
                        f"Depot {depot_id} - Supplier Depot {supplier_depot_id}: No volume scenarios"
                    )
                    continue
                
                # Check volume tier applications
                has_volume_tiers = False
                for volume, scenario_data in volume_scenarios.items():
                    volume_tier_metadata = scenario_data.get('volume_tier_metadata')
                    if volume_tier_metadata and volume_tier_metadata.get('total_rebate_pv', 0) > 0:
                        has_volume_tiers = True
                        rebate = volume_tier_metadata['total_rebate_pv']
                        total_rebate_sum += rebate
                        total_rebate_entries += 1  # Count each rebate entry
                        max_rebate = max(max_rebate, rebate)
                        
                        # Validate cost reasonableness (enhanced costs should be <= base costs)
                        for option, enhanced_cost in scenario_data.items():
                            if option in data['base_costs']:
                                base_cost = data['base_costs'][option]
                                if enhanced_cost > base_cost:
                                    validation_results['errors'].append(
                                        f"Depot {depot_id} - Supplier Depot {supplier_depot_id}: "
                                        f"Enhanced cost ({enhanced_cost:.6f}) > base cost ({base_cost:.6f}) for {option}"
                                    )
                
                if has_volume_tiers:
                    combinations_with_tiers += 1
        
        # Update statistics
        validation_results['statistics']['total_combinations'] = total_combinations
        validation_results['statistics']['combinations_with_volume_tiers'] = combinations_with_tiers
        validation_results['statistics']['max_volume_tier_rebate'] = max_rebate
        validation_results['statistics']['total_rebate_entries'] = total_rebate_entries
        
        if total_rebate_entries > 0:
            validation_results['statistics']['average_volume_tier_rebate'] = total_rebate_sum / total_rebate_entries
        
        # Validate volume tier configurations
        for tier_name, tier_config in self.config.get('volume_tier_configurations', {}).items():
            # Check monotonicity requirement
            if tier_config.get('operational_rules', {}).get('ladder_monotonicity', True):
                bands = tier_config['tiers']['bands']
                for i in range(1, len(bands)):
                    prev_rebate = bands[i-1]['rebate']
                    curr_rebate = bands[i]['rebate']
                    if curr_rebate < prev_rebate:
                        validation_results['warnings'].append(
                            f"Volume tier {tier_name}: Non-monotonic rebates - "
                            f"band {i-1} ({prev_rebate}) > band {i} ({curr_rebate})"
                        )
            
            # Check for gaps in volume ranges
            bands = tier_config['tiers']['bands']
            for i in range(1, len(bands)):
                prev_max = bands[i-1]['max_volume']
                curr_min = bands[i]['min_volume']
                if prev_max is not None and prev_max != curr_min:
                    validation_results['warnings'].append(
                        f"Volume tier {tier_name}: Gap in volume ranges - "
                        f"band {i-1} ends at {prev_max}, band {i} starts at {curr_min}"
                    )
        
        # Set final status
        if validation_results['errors']:
            validation_results['status'] = 'invalid'
        elif validation_results['warnings']:
            validation_results['status'] = 'valid_with_warnings'
        
        logger.info(f"Validation complete: {validation_results['status']}")
        logger.info(f"Combinations with volume tiers: {combinations_with_tiers}/{total_combinations}")
        logger.info(f"Max volume tier rebate: R{max_rebate:.6f}/litre")
        
        return validation_results
    
    def run_complete_precomputation_with_validation(self) -> Dict[str, Any]:
        """
        Execute complete precomputation with validation.
        
        Returns:
            Dict: Complete results with cost data and validation
        """
        logger.info("Starting complete precomputation with validation...")
        
        # Run enhanced precomputation
        enhanced_cost_data = self.run_complete_precomputation()
        
        # Validate business rules
        validation_results = self.validate_volume_tier_business_rules(enhanced_cost_data)
        
        # Return combined results
        return {
            'cost_data': enhanced_cost_data,
            'validation': validation_results,
            'status': validation_results['status']
        }
    
    def query_depot_costs(self, depot_id: int, results: Dict[str, Any], volume_filter: int = None, show_details: bool = True) -> None:
        """
        Display all available costs for a specific customer depot.
        
        Args:
            depot_id: Customer depot ID to query
            results: Results from run_complete_precomputation_with_validation()
            volume_filter: Optional volume scenario to focus on (litres)
            show_details: Whether to show detailed cost breakdowns
        """
        print(f"\n{'='*80}")
        print(f"COST QUERY RESULTS FOR CUSTOMER DEPOT {depot_id}")
        print(f"{'='*80}")
        
        cost_data = results['cost_data']
        
        # Check if depot exists
        if depot_id not in cost_data['costs']:
            print(f"❌ Depot {depot_id} not found in cost data")
            available_depots = list(cost_data['costs'].keys())
            print(f"Available depots: {sorted(available_depots)}")
            return
        
        # Get depot info
        depot_info = cost_data['depots'].get(depot_id, {})
        depot_data = cost_data['costs'][depot_id]
        
        print(f"Depot Name: {depot_info.get('name', 'Unknown')}")
        print(f"Annual Volume: {depot_info.get('annual_volume', 'Unknown'):,} litres")
        print(f"Fuel Zone: {depot_info.get('fuel_zone', 'Unknown')}")
        print(f"Available Supplier Depots: {len(depot_data)}")
        
        # Summary statistics
        total_options = 0
        for supplier_depot_data in depot_data.values():
            total_options += len(supplier_depot_data.get('base_costs', {}))
        print(f"Total Cost Options: {total_options}")
        
        print(f"\n{'-'*80}")
        print("SUPPLIER DEPOT BREAKDOWN:")
        print(f"{'-'*80}")
        
        for supplier_depot_id, data in depot_data.items():
            supplier_id = data.get('supplier_id', 'Unknown')
            supplier_name = data.get('supplier_name', f'Supplier {supplier_id}')
            supplier_depot_name = data.get('supplier_depot_name', 'Unknown Depot')
            distance_km = data.get('distance_km', 'N/A')
            base_costs = data.get('base_costs', {})
            volume_scenarios = data.get('volume_scenarios', {})
            
            print(f"\n📍 {supplier_depot_name} (Depot ID: {supplier_depot_id})")
            print(f"   Supplier: {supplier_name} (ID: {supplier_id})")
            print(f"   Distance: {distance_km} km" if distance_km != 'N/A' else "   Distance: N/A (DEL only)")
            print(f"   Available Options: {list(base_costs.keys())}")
            
            if show_details:
                # Collect volume tier scenarios that have enhanced costs
                volume_scenarios_with_tiers = {}
                if volume_scenarios:
                    for vol, scenario_data in volume_scenarios.items():
                        # Check if any costs differ from base costs (indicating volume tier applied)
                        has_enhanced_costs = False
                        for option in base_costs.keys():
                            if option in scenario_data:
                                base_cost = base_costs[option]
                                enhanced_cost = scenario_data[option]
                                if abs(enhanced_cost - base_cost) > 0.000001:  # Significant difference
                                    has_enhanced_costs = True
                                    break
                        
                        if has_enhanced_costs:
                            volume_scenarios_with_tiers[vol] = scenario_data
                
                if volume_filter and volume_filter in volume_scenarios:
                    # Show specific volume scenario in tabular format
                    scenario_data = volume_scenarios[volume_filter]
                    print(f"\n   COST BREAKDOWN ({volume_filter:,} litres):")
                    print(f"   {'OPTION':<15} {'BASE COST':<18} {'VOLUME TIER COST':<18} {'SAVINGS':<12}")
                    print(f"   {'-'*15} {'-'*18} {'-'*18} {'-'*12}")
                    
                    for option in base_costs.keys():
                        base_cost = base_costs[option]
                        enhanced_cost = scenario_data.get(option, base_cost)
                        savings = base_cost - enhanced_cost
                        option_display = option.replace('_', ' ').upper()
                        
                        if abs(savings) > 0.000001:
                            print(f"   {option_display:<15} R{base_cost:<16.6f} R{enhanced_cost:<16.6f} R{savings:<10.6f}")
                        else:
                            print(f"   {option_display:<15} R{base_cost:<16.6f} {'N/A':<18} {'N/A':<12}")
                
                elif volume_scenarios_with_tiers:
                    # Show vertical volume tier display - clearer format
                    print(f"\n   📊 VOLUME TIER ANALYSIS:")
                    
                    # Get sorted volume thresholds  
                    sorted_volumes = sorted(volume_scenarios_with_tiers.keys())
                    
                    # Group by option type for cleaner display
                    for option in base_costs.keys():
                        base_cost = base_costs[option]
                        option_display = option.replace('_', ' ').upper()
                        
                        # Check if this option has any volume tier variations
                        has_tier_variations = False
                        tier_costs = {}
                        
                        for vol in sorted_volumes:
                            scenario_data = volume_scenarios_with_tiers[vol]
                            enhanced_cost = scenario_data.get(option, base_cost)
                            tier_costs[vol] = enhanced_cost
                            
                            if abs(enhanced_cost - base_cost) > 0.000001:
                                has_tier_variations = True
                        
                        if has_tier_variations:
                            print(f"\n   🎯 {option_display}:")
                            print(f"      Base Cost: R{base_cost:.6f}/litre")
                            print(f"      Volume Tier Costs:")
                            
                            for vol in sorted_volumes:
                                enhanced_cost = tier_costs[vol]
                                savings = base_cost - enhanced_cost
                                vol_display = f"{vol//1000000}M" if vol > 0 else "0"
                                
                                if abs(savings) > 0.000001:
                                    savings_display = f"R{savings:+.6f}"
                                    print(f"         {vol_display:>4} litres: R{enhanced_cost:.6f}/litre ({savings_display})")
                                else:
                                    print(f"         {vol_display:>4} litres: R{enhanced_cost:.6f}/litre (base cost)")
                        else:
                            # No volume tier variations - just show base cost
                            print(f"\n   ⚪ {option_display}: R{base_cost:.6f}/litre (no volume tiers)")
                    
                    print(f"   📈 Volume scenarios tested: {len(sorted_volumes)}")
                        
                    # Show applied tiers info
                    print(f"\n   Volume Tier Details:")
                    for vol in sorted_volumes[:3]:
                        scenario_data = volume_scenarios_with_tiers[vol]
                        volume_tier_metadata = scenario_data.get('volume_tier_metadata')
                        if volume_tier_metadata:
                            applied_tiers = volume_tier_metadata.get('applied_tiers', [])
                            if applied_tiers:
                                tier_names = [t['tier_name'] for t in applied_tiers]
                                rebate_pv = volume_tier_metadata.get('total_rebate_pv', 0)
                                print(f"     {vol:,} litres: {tier_names} (R{rebate_pv:.6f}/L rebate)")
                
                else:
                    print(f"   \n   BASE COSTS (Present Value):")
                    for option, cost in base_costs.items():
                        option_display = option.replace('_', ' ').upper()
                        print(f"     {option_display:<12}: R{cost:.6f}/litre")
                    print(f"     No volume tier rebates apply to this supplier depot")
            
            print()  # Blank line between supplier depots
        
        # Show cost comparison summary
        if show_details:
            print(f"\n{'-'*80}")
            print("LOWEST COST SUMMARY:")
            print(f"{'-'*80}")
            
            all_costs = {}
            for supplier_depot_id, data in depot_data.items():
                base_costs = data.get('base_costs', {})
                supplier_name = data.get('supplier_name', f'Supplier {data.get("supplier_id", "Unknown")}')
                supplier_depot_name = data.get('supplier_depot_name', 'Unknown Depot')
                for option, cost in base_costs.items():
                    option_key = f"{option} ({supplier_name} - {supplier_depot_name})"
                    all_costs[option_key] = cost
            
            # Sort by cost (lowest first)
            sorted_costs = sorted(all_costs.items(), key=lambda x: x[1])
            
            print("Lowest cost options (base costs):")
            for i, (option_key, cost) in enumerate(sorted_costs[:10]):  # Top 10
                print(f"  {i+1:2d}. {option_key:<40}: R{cost:.6f}/litre")
            
            if len(sorted_costs) > 10:
                print(f"     ... and {len(sorted_costs) - 10} more options")
        
        print(f"\n{'='*80}")
        print("QUERY COMPLETE")
        print(f"{'='*80}\n")


def main():
    """Main function for testing the precomputation module."""
    try:
        # Initialize precomputation
        precomp = FuelOptimizationPrecomputation()
        
        # Run complete precomputation with validation
        print("🚀 Running complete precomputation with validation...")
        complete_results = precomp.run_complete_precomputation_with_validation()
        
        print(f"✅ Precomputation complete! Status: {complete_results['status']}")
        
        # Query a few depots to demonstrate the functionality
        print("\n🔍 Demonstrating depot cost queries...")
        test_depots = [1, 5, 10]  # Change these to any depot IDs you want
        
        for depot_id in test_depots:
            precomp.query_depot_costs(depot_id=depot_id, results=complete_results)
            
        print("🎯 Demo complete! You can now use query_depot_costs() for any depot.")
        
    except Exception as e:
        logger.error(f"Precomputation failed: {e}")
        raise


if __name__ == "__main__":
    main()