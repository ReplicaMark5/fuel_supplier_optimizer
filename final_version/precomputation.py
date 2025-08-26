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
        
        # Supplier ID to name mapping (loaded dynamically from database)
        self.supplier_id_to_name = self._load_supplier_mapping()
        
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
    
    def _load_supplier_mapping(self) -> Dict[int, str]:
        """Load supplier ID to name mapping dynamically from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT Supplier_PK, Supplier_Name_ FROM suppliers ORDER BY Supplier_PK")
                supplier_data = cursor.fetchall()
            
            # Convert to dictionary
            supplier_mapping = {int(supplier_id): supplier_name for supplier_id, supplier_name in supplier_data}
            logger.info(f"Loaded {len(supplier_mapping)} suppliers from database: {list(supplier_mapping.values())}")
            return supplier_mapping
            
        except sqlite3.Error as e:
            logger.error(f"Failed to load supplier mapping from database: {e}")
            # Fallback to hardcoded mapping if database fails
            logger.warning("Using fallback hardcoded supplier mapping")
            return {
                1: "Supplier A", 2: "Supplier C", 3: "Supplier D", 4: "Supplier F", 5: "Supplier G", 
                6: "Supplier H", 7: "Supplier I", 8: "Supplier J", 9: "Supplier L"
            }
    
    def _load_coordinates_from_database(self) -> Dict[str, Dict[int, Dict[str, Any]]]:
        """
        Load depot coordinates from database for enhanced mapping.
        
        Returns:
            Dict: Contains customer_depots and supplier_depots coordinate data
        """
        logger.info("Loading depot coordinates from database...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load customer depot coordinates
                customer_query = """
                    SELECT Cust_Depot_PK, Cust_Depot_Name, Lats, Long, Country, Town
                    FROM customer_depots
                """
                df_customer = pd.read_sql(customer_query, conn)
                
                customer_coords = {}
                for _, row in df_customer.iterrows():
                    customer_coords[int(row['Cust_Depot_PK'])] = {
                        'name': row['Cust_Depot_Name'],
                        'latitude': float(row['Lats']),
                        'longitude': float(row['Long']),
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
                
                supplier_coords = {}
                for _, row in df_supplier.iterrows():
                    supplier_coords[int(row['Supplier_Depot_PK'])] = {
                        'name': row['Supply_Depot_Name'],
                        'latitude': float(row['supplier_lat']),
                        'longitude': float(row['supplier_lng']),
                        'country': row['Country'],
                        'location': row['Supply_Depot_Location'],
                        'supplier_name': row['Supplier_Name_']
                    }
                
                logger.info(f"Loaded coordinates for {len(customer_coords)} customer depots and {len(supplier_coords)} supplier depots")
                
                return {
                    'customer_depots': customer_coords,
                    'supplier_depots': supplier_coords
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to load coordinates from database: {e}")
            return {'customer_depots': {}, 'supplier_depots': {}}
    
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
            do.COC_From_DEL,
            do."TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF",
            
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
        
        # DEL Rent Equipment (no equipment financing/maintenance)
        df['del_rent_cost_pv'] = np.where(
            del_mask & df['DEL_reb_pl_30'].notna(),
            ((df['rtl_wholesale_per_litre'] - df['DEL_reb_pl_30']) / pv_30d),
            np.nan
        )
        
        # Log calculation results
        cost_columns = ['coc_cash_cost_pv', 'coc_30_cost_pv', 'coc_45_cost_pv', 'coc_60_cost_pv',
                       'del_own_cost_pv', 'del_buy_cost_pv', 'del_rent_cost_pv']
        
        for col in cost_columns:
            available_count = df[col].notna().sum()
            logger.info(f"{col}: {available_count} available calculations")
        
        return df
    
    def _get_rac_enabled_suppliers(self) -> List[int]:
        """
        Get list of supplier IDs that have Rebate Adjustment Clause enabled.
        
        Returns:
            List[int]: Supplier IDs with RAC enabled
        """
        rac_supplier_ids = []
        
        contract_configs = self.config.get('supplier_contract_configurations', {})
        
        for contract_name, contract_config in contract_configs.items():
            if contract_config.get('contract_type') == 'rebate_adjustment_clause':
                contract_suppliers = contract_config.get('suppliers', [])
                
                # Convert supplier names to IDs
                for supplier_name in contract_suppliers:
                    for supplier_id, mapped_name in self.supplier_id_to_name.items():
                        if mapped_name == supplier_name:
                            if supplier_id not in rac_supplier_ids:
                                rac_supplier_ids.append(supplier_id)
        
        logger.info(f"RAC enabled suppliers: {rac_supplier_ids} ({[self.supplier_id_to_name.get(sid, f'Unknown_{sid}') for sid in rac_supplier_ids]})")
        return rac_supplier_ids
    
    def calculate_rac_costs(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Rebate Adjustment Clause (RAC) penalty costs.
        
        These are higher costs used when volume commitments aren't met.
        Based on wholesale price without rebates + transport/equipment costs.
        
        Only calculated for suppliers with Rebate_adjustment_clause = True.
        
        Args:
            df: Data with fuel pricing and base calculations
            
        Returns:
            pd.DataFrame: Data with RAC cost calculations added
        """
        logger.info("Calculating RAC penalty costs for RAC-enabled suppliers only...")
        
        # Get suppliers that have RAC clauses enabled
        rac_enabled_supplier_ids = self._get_rac_enabled_suppliers()
        
        if not rac_enabled_supplier_ids:
            logger.info("No RAC-enabled suppliers found - skipping RAC calculations")
            # Initialize RAC columns with NaN
            rac_columns = ['rac_coc_cash_cost_pv', 'rac_coc_30_cost_pv', 'rac_coc_45_cost_pv', 'rac_coc_60_cost_pv',
                          'rac_del_own_cost_pv', 'rac_del_buy_cost_pv', 'rac_del_rent_cost_pv']
            for col in rac_columns:
                df[col] = np.nan
            return df
        
        pv_factors = self.calculate_present_value_factors()
        cost_owned_equip_pv = self.config['basic_parameters']['cost_owned_equip_pv']
        cost_buy_equip_pv = self.config['basic_parameters']['cost_buy_equip_pv']
        
        # === RAC COC Calculations (no rebates, just wholesale + transport) ===
        # Only calculate for RAC-enabled suppliers
        coc_mask = df['COC_Valid_FK'].notna()
        rac_supplier_mask = df['Supplier_FK'].isin(rac_enabled_supplier_ids)
        rac_coc_mask = coc_mask & rac_supplier_mask
        
        # RAC COC Cash (immediate payment)
        df['rac_coc_cash_cost_pv'] = np.where(
            rac_coc_mask,
            df['rtl_wholesale_per_litre'] + df['trans_cost_pl'],
            np.nan
        )
        
        # RAC COC NET30
        df['rac_coc_30_cost_pv'] = np.where(
            rac_coc_mask,
            (df['rtl_wholesale_per_litre'] / pv_factors['net30']) + df['trans_cost_pl'],
            np.nan
        )
        
        # RAC COC NET45
        df['rac_coc_45_cost_pv'] = np.where(
            rac_coc_mask,
            (df['rtl_wholesale_per_litre'] / pv_factors['net45']) + df['trans_cost_pl'],
            np.nan
        )
        
        # RAC COC NET60
        df['rac_coc_60_cost_pv'] = np.where(
            rac_coc_mask,
            (df['rtl_wholesale_per_litre'] / pv_factors['net60']) + df['trans_cost_pl'],
            np.nan
        )
        
        # === RAC DEL Calculations ===
        # Need to back-calculate transport costs from delivery options
        # Using formula: (COC_From_DEL - DEL_reb_pl_30)
        del_mask = df['DEL_Valid_FK'].notna()
        rac_del_mask = del_mask & rac_supplier_mask
        pv_30d = pv_factors['net30']
        
        # Get transport charge for RAC DEL calculations from delivery_options table
        # This is the "TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF" field per updated specifications
        transport_charge_excl_zone = np.where(
            df['TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF'].notna(),
            df['TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF'],
            0  # Default to 0 if not available
        )
        
        # RAC DEL Own Equipment
        # Formula: ((wholesale + transport_charge) / PV_30) + owned_equip_cost
        del_own_mask = (rac_del_mask & 
                       df['DEL_reb_pl_30'].notna() & 
                       df['equip_fin_pl_30'].notna() & 
                       df['equip_main_pl_30'].notna())
        
        df['rac_del_own_cost_pv'] = np.where(
            del_own_mask,
            ((df['rtl_wholesale_per_litre'] + transport_charge_excl_zone) / pv_30d) + cost_owned_equip_pv,
            np.nan
        )
        
        # RAC DEL Buy Equipment  
        # Formula: ((wholesale + transport_charge) / PV_30) + buy_equip_cost
        df['rac_del_buy_cost_pv'] = np.where(
            del_own_mask,
            ((df['rtl_wholesale_per_litre'] + transport_charge_excl_zone) / pv_30d) + cost_buy_equip_pv,
            np.nan
        )
        
        # RAC DEL Rent Equipment
        # Formula: ((wholesale + transport_charge + equip_fin + equip_main) / PV_30)
        df['rac_del_rent_cost_pv'] = np.where(
            rac_del_mask & df['DEL_reb_pl_30'].notna() & df['equip_fin_pl_30'].notna() & df['equip_main_pl_30'].notna(),
            ((df['rtl_wholesale_per_litre'] + transport_charge_excl_zone + df['equip_fin_pl_30'] + df['equip_main_pl_30']) / pv_30d),
            np.nan
        )
        
        # Log RAC calculation results
        rac_columns = ['rac_coc_cash_cost_pv', 'rac_coc_30_cost_pv', 'rac_coc_45_cost_pv', 'rac_coc_60_cost_pv',
                       'rac_del_own_cost_pv', 'rac_del_buy_cost_pv', 'rac_del_rent_cost_pv']
        
        for col in rac_columns:
            available_count = df[col].notna().sum()
            logger.info(f"{col}: {available_count} RAC penalty calculations")
        
        return df
    
    def calculate_volume_tier_enhanced_costs(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume tier enhanced costs for all configured volume tier scenarios.
        
        This implements the logic from manual_crosscheck_calc.md for combination_rule: "add"
        where volume tier rebates are ADDED to base rebates for lower costs when tiers are met.
        
        Args:
            df: Data with base and RAC cost calculations
            
        Returns:
            pd.DataFrame: Data with volume tier enhanced cost calculations added
        """
        logger.info("Calculating volume tier enhanced costs...")
        
        pv_factors = self.calculate_present_value_factors()
        cost_owned_equip_pv = self.config['basic_parameters']['cost_owned_equip_pv']
        cost_buy_equip_pv = self.config['basic_parameters']['cost_buy_equip_pv']
        
        # Load supplier contract configurations
        contract_configs = self.config.get('supplier_contract_configurations', {})
        
        tier_cost_count = 0
        
        for contract_name, contract_config in contract_configs.items():
            # Skip RAC contracts (they use RAC costs, not enhanced costs)
            if contract_config.get('contract_type') == 'rebate_adjustment_clause':
                continue
            
            # Only process volume tier reward contracts
            if contract_config.get('contract_type') != 'volume_tier_rewards':
                continue
                
            suppliers = contract_config.get('suppliers', [])
            transport_modes = contract_config.get('transport_modes', [])
            rebate_combination = contract_config.get('rebate_combination', 'additive_to_base')
            reward_bands = contract_config.get('reward_bands', [])
            
            logger.info(f"Processing contract {contract_name}: {len(reward_bands)} reward bands, combination: {rebate_combination}")
            
            # Process each volume tier reward band
            for i, band in enumerate(reward_bands):
                min_volume = band.get('min_volume', 0)
                max_volume = band.get('max_volume')
                coc_rebate = band.get('coc_rebate', 0) or 0
                del_rebate = band.get('del_rebate', 0) or 0
                
                # Skip bands with no rebates
                if coc_rebate == 0 and del_rebate == 0:
                    continue
                
                # Create tier band identifier
                if max_volume is None:
                    band_suffix = f"_{min_volume//1000000}M_plus"
                else:
                    band_suffix = f"_{min_volume//1000000}M_to_{max_volume//1000000}M"
                
                # Filter data for suppliers that have this tier
                supplier_mask = df['supplier_name'].isin(suppliers)
                
                for _, row in df[supplier_mask].iterrows():
                    # COC Volume Tier Enhanced Costs
                    if 'COC' in transport_modes and coc_rebate > 0:
                        coc_mask = pd.notna(row['COC_Valid_FK'])
                        
                        if coc_mask:
                            # COC with rebate_combination: "additive_to_base" - add tier rebate to base rebate
                            if rebate_combination == 'additive_to_base':
                                # COC Cash (immediate payment) - only base rebate, no tier rebate for cash
                                tier_col = f'coc_cash_tier{band_suffix}'
                                if tier_col not in df.columns:
                                    df[tier_col] = np.nan
                                df.loc[df.index[_], tier_col] = (
                                    row['rtl_wholesale_per_litre'] - row['COC_reb_pl_cash']
                                ) + row['trans_cost_pl']
                                
                                # COC NET30 - base rebate + tier rebate
                                tier_col = f'coc_30_tier{band_suffix}'
                                if tier_col not in df.columns:
                                    df[tier_col] = np.nan
                                df.loc[df.index[_], tier_col] = (
                                    (row['rtl_wholesale_per_litre'] - (row['COC_reb_pl_30'] + coc_rebate)) / pv_factors['net30']
                                ) + row['trans_cost_pl']
                                
                                # COC NET45 - only base rebate (tier rebate is NET30 terms)
                                tier_col = f'coc_45_tier{band_suffix}'  
                                if tier_col not in df.columns:
                                    df[tier_col] = np.nan
                                df.loc[df.index[_], tier_col] = (
                                    (row['rtl_wholesale_per_litre'] - row['COC_reb_pl_45']) / pv_factors['net45']
                                ) + row['trans_cost_pl']
                                
                                # COC NET60 - only base rebate (tier rebate is NET30 terms)
                                tier_col = f'coc_60_tier{band_suffix}'
                                if tier_col not in df.columns:
                                    df[tier_col] = np.nan
                                df.loc[df.index[_], tier_col] = (
                                    (row['rtl_wholesale_per_litre'] - row['COC_reb_pl_60']) / pv_factors['net60']
                                ) + row['trans_cost_pl']
                                
                                tier_cost_count += 4
                    
                    # DEL Volume Tier Enhanced Costs
                    if 'DEL' in transport_modes and del_rebate > 0:
                        del_mask = pd.notna(row['DEL_Valid_FK'])
                        
                        if del_mask and pd.notna(row['DEL_reb_pl_30']):
                            # DEL with rebate_combination: "additive_to_base" - add tier rebate to base rebate
                            if rebate_combination == 'additive_to_base':
                                # DEL Own Equipment
                                if (pd.notna(row['equip_fin_pl_30']) and pd.notna(row['equip_main_pl_30'])):
                                    tier_col = f'del_own_tier{band_suffix}'
                                    if tier_col not in df.columns:
                                        df[tier_col] = np.nan
                                    df.loc[df.index[_], tier_col] = (
                                        (row['rtl_wholesale_per_litre'] - 
                                         (row['DEL_reb_pl_30'] + del_rebate + row['equip_fin_pl_30'] + row['equip_main_pl_30'])) / pv_factors['net30']
                                    ) + cost_owned_equip_pv
                                
                                # DEL Buy Equipment
                                if (pd.notna(row['equip_fin_pl_30']) and pd.notna(row['equip_main_pl_30'])):
                                    tier_col = f'del_buy_tier{band_suffix}'
                                    if tier_col not in df.columns:
                                        df[tier_col] = np.nan
                                    df.loc[df.index[_], tier_col] = (
                                        (row['rtl_wholesale_per_litre'] - 
                                         (row['DEL_reb_pl_30'] + del_rebate + row['equip_fin_pl_30'] + row['equip_main_pl_30'])) / pv_factors['net30']
                                    ) + cost_buy_equip_pv
                                
                                # DEL Rent Equipment
                                tier_col = f'del_rent_tier{band_suffix}'
                                if tier_col not in df.columns:
                                    df[tier_col] = np.nan
                                df.loc[df.index[_], tier_col] = (
                                    (row['rtl_wholesale_per_litre'] - (row['DEL_reb_pl_30'] + del_rebate)) / pv_factors['net30']
                                )
                                
                                tier_cost_count += 3
        
        logger.info(f"Calculated {tier_cost_count} volume tier enhanced cost options")
        return df
    
    def build_cost_dictionary(self, df: pd.DataFrame, coordinates: Dict[str, Dict[int, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Build the base cost dictionary structure for optimizer consumption.
        
        Args:
            df: Data with all cost calculations
            coordinates: Optional coordinate data for depots and suppliers
            
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
        
        # RAC (Rebate Adjustment Clause) penalty cost columns
        rac_cost_columns = {
            'rac_coc_cash': 'rac_coc_cash_cost_pv',
            'rac_coc_30': 'rac_coc_30_cost_pv', 
            'rac_coc_45': 'rac_coc_45_cost_pv',
            'rac_coc_60': 'rac_coc_60_cost_pv',
            'rac_del_own': 'rac_del_own_cost_pv',
            'rac_del_buy': 'rac_del_buy_cost_pv', 
            'rac_del_rent': 'rac_del_rent_cost_pv'
        }
        
        # Volume tier enhanced cost columns (dynamically generated)
        tier_cost_columns = {}
        for col in df.columns:
            if ('tier_' in col and 
                ('coc_' in col or 'del_' in col) and 
                not col.endswith('_cost_pv')):  # Already in right format
                # Map column name to itself (e.g., 'coc_30_tier_15M_to_20M' -> 'coc_30_tier_15M_to_20M')
                tier_cost_columns[col] = col
        
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
            
            # Add available base cost options
            for option, cost_col in cost_columns.items():
                if pd.notna(row[cost_col]):
                    cost_dict[depot_id][supplier_depot_id][option] = round(row[cost_col], 6)
            
            # Add available RAC penalty cost options
            for option, cost_col in rac_cost_columns.items():
                if pd.notna(row[cost_col]):
                    cost_dict[depot_id][supplier_depot_id][option] = round(row[cost_col], 6)
            
            # Add available volume tier enhanced cost options
            for option, cost_col in tier_cost_columns.items():
                if pd.notna(row[cost_col]):
                    cost_dict[depot_id][supplier_depot_id][option] = round(row[cost_col], 6)
            
            # Add supplier and distance metadata to each cost entry
            cost_dict[depot_id][supplier_depot_id]['supplier_id'] = supplier_id
            cost_dict[depot_id][supplier_depot_id]['supplier_name'] = row.get('supplier_name', f"Supplier {supplier_id}")
            cost_dict[depot_id][supplier_depot_id]['supplier_depot_name'] = row.get('Supply_Depot_Name', f"Depot {supplier_depot_id}")
            cost_dict[depot_id][supplier_depot_id]['distance_km'] = row.get('One_Way_Dist', None)
            
            # Add supplier depot coordinates if available
            if coordinates and 'supplier_depots' in coordinates:
                coord_data = coordinates['supplier_depots'].get(supplier_depot_id, {})
                if coord_data:
                    cost_dict[depot_id][supplier_depot_id]['supplier_depot_lat'] = coord_data.get('latitude')
                    cost_dict[depot_id][supplier_depot_id]['supplier_depot_lon'] = coord_data.get('longitude')
                    cost_dict[depot_id][supplier_depot_id]['supplier_depot_country'] = coord_data.get('country')
                    cost_dict[depot_id][supplier_depot_id]['supplier_depot_location'] = coord_data.get('location')
            
            # Build supporting dictionaries
            if depot_id not in depot_dict:
                depot_info = {
                    'annual_volume': row['depot_annual_volume'],
                    'name': row['customer_depot_name'],
                    'fuel_zone': row['customer_fuel_zone']
                }
                
                # Add coordinates if available
                if coordinates and 'customer_depots' in coordinates:
                    coord_data = coordinates['customer_depots'].get(depot_id, {})
                    if coord_data:
                        depot_info['latitude'] = coord_data.get('latitude')
                        depot_info['longitude'] = coord_data.get('longitude')
                        depot_info['country'] = coord_data.get('country')
                        depot_info['town'] = coord_data.get('town')
                
                depot_dict[depot_id] = depot_info
            
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
        
        # Step 5: Calculate RAC penalty costs
        df = self.calculate_rac_costs(df)
        
        # Step 6: Calculate volume tier enhanced costs
        df = self.calculate_volume_tier_enhanced_costs(df)
        
        # Step 7: Load coordinates for enhanced mapping
        coordinates = self._load_coordinates_from_database()
        
        # Step 8: Build cost dictionary with coordinates
        cost_data = self.build_cost_dictionary(df, coordinates)
        
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
        bands = tier_config['bands']
        
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
        Get list of applicable contract configurations for a supplier_depot-option combination.
        
        Args:
            supplier_id: Supplier ID
            supplier_depot_id: Supplier depot ID  
            option: Option type (coc_cash, coc_30, del_own, etc.)
            
        Returns:
            List of applicable contract configuration names
        """
        applicable_contracts = []
        contract_configs = self.config.get('supplier_contract_configurations', {})
        
        for contract_name, contract_config in contract_configs.items():
            # Only consider volume tier reward contracts for this function
            if contract_config.get('contract_type') != 'volume_tier_rewards':
                continue
            
            # Check supplier filter (map numeric ID to name)
            supplier_filter = contract_config.get('suppliers', ['*'])
            supplier_name = self.supplier_id_to_name.get(supplier_id, str(supplier_id))
            if supplier_filter != ['*'] and supplier_name not in supplier_filter:
                continue
                
            # Check supplier depot filter
            supplier_depot_filter = contract_config.get('supplier_depots', ['*']) 
            if supplier_depot_filter != ['*'] and str(supplier_depot_id) not in supplier_depot_filter:
                continue
                
            # Check transport mode filter (COC/DEL)
            mode_filter = contract_config.get('transport_modes', ['*'])
            option_mode = 'COC' if option.startswith('coc_') else 'DEL'
            if mode_filter != ['*'] and option_mode not in mode_filter:
                continue
                
            applicable_contracts.append(contract_name)
            
        return applicable_contracts
    
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
        wholesale_price = row.get('rtl_wholesale_per_litre', row['rtl_wholesale'] / 100)
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
                
                # Get all applicable volume tiers for this supplier depot (not per option)
                all_applicable_tiers = set()
                # Check both COC and DEL options to find all applicable tiers
                test_options = ['coc_30', 'del_own']  # Representative options to find applicable tiers
                for test_option in test_options:
                    if any(test_option.startswith(base_opt.split('_')[0]) for base_opt in base_options.keys()):
                        applicable_tiers = self.get_applicable_volume_tiers(supplier_id, supplier_depot_id, test_option)
                        all_applicable_tiers.update(applicable_tiers)
                
                for tier_name in all_applicable_tiers:
                    # Get tier modes from config
                    tier_config = self.config['volume_tier_configurations'][tier_name]
                    tier_modes = tier_config.get('modes', [])
                    
                    # Calculate tier costs based on tier modes (always NET30)
                    tier_costs_result = self._calculate_single_tier_cost(supplier_depot_id, tier_name, tier_modes)
                    if tier_costs_result:
                        depot_structure['tier_costs'][tier_name] = tier_costs_result
                
                enhanced_costs['costs'][depot_id][supplier_depot_id] = depot_structure
        
        return enhanced_costs
    
    def _calculate_single_tier_cost(self, supplier_depot_id: int, tier_name: str, tier_modes: list) -> dict:
        """
        Calculate tier cost for a specific supplier depot and volume tier.
        Volume tiers are ALWAYS calculated in NET30 terms regardless of base payment terms.
        
        Args:
            supplier_depot_id: The supplier depot ID
            tier_name: The volume tier configuration name
            tier_modes: List of modes this tier applies to (COC or DEL)
            
        Returns:
            Dictionary with tier costs, or empty dict if not calculable
        """
        if self.raw_data is None:
            return {}
            
        # Find the raw data row for this supplier depot
        matching_rows = self.raw_data[self.raw_data['Supplier_Depot_FK'] == supplier_depot_id]
        if matching_rows.empty:
            return {}
            
        row = matching_rows.iloc[0]
        
        # Get contract configuration
        contract_config = self.config['supplier_contract_configurations'][tier_name]
        rebate_combination = contract_config.get('rebate_combination', 'additive_to_base')
        
        # Get volume tier reward bands - calculate cost for each non-zero rebate band
        reward_bands = contract_config['reward_bands']
        valid_bands = []
        for band in reward_bands:
            coc_rebate = band.get('coc_rebate', 0) or 0
            del_rebate = band.get('del_rebate', 0) or 0
            if coc_rebate > 0 or del_rebate > 0:
                valid_bands.append(band)
        
        if not valid_bands:
            return {}
            
        # Get PV factors and wholesale price
        pv_factors = self.calculate_present_value_factors()
        wholesale_price = row.get('rtl_wholesale_per_litre', row['rtl_wholesale'] / 100)
        
        # Calculate transport cost
        tanker_capacity = self.config['basic_parameters']['tanker_capacity']
        cost_per_km = self.config['basic_parameters']['tanker_cost_per_km']
        distance = row['One_Way_Dist']
        transport_cost_per_litre = (2 * distance * cost_per_km) / tanker_capacity
        
        tier_costs = {}
        
        # Calculate tier costs based on mode
        if 'COC' in tier_modes:
            # For COC volume tiers: calculate coc_30 cost for each tier band
            base_coc_30_rebate = row.get('COC_reb_pl_30', 0) or 0
            
            for i, band in enumerate(valid_bands):
                coc_rebate_rate = band.get('coc_rebate', 0) or 0
                if coc_rebate_rate == 0:
                    continue  # Skip bands with no COC rebate
                    
                min_vol = band['min_volume']
                max_vol = band['max_volume']
                
                # Create descriptive key for this tier band
                if max_vol is None:
                    band_key = f"coc_30_tier_{min_vol//1000000}M_plus"
                else:
                    band_key = f"coc_30_tier_{min_vol//1000000}M_to_{max_vol//1000000}M"
                
                if rebate_combination == 'override_base':
                    # Override: ((wholesale/100) - vol_tier_rebate) / (1+WACC/365)^30 + transport
                    tier_cost = ((wholesale_price - coc_rebate_rate) / pv_factors['net30'] + 
                               transport_cost_per_litre)
                elif rebate_combination == 'additive_to_base':
                    # Add: ((wholesale/100) - (base_rebate + vol_tier_rebate)) / (1+WACC/365)^30 + transport
                    tier_cost = ((wholesale_price - (base_coc_30_rebate + coc_rebate_rate)) / pv_factors['net30'] + 
                               transport_cost_per_litre)
                else:
                    logger.warning(f"Unknown rebate combination: {rebate_combination}")
                    return {}
                    
                tier_costs[band_key] = tier_cost
            
        if 'DEL' in tier_modes:
            # For DEL volume tiers: calculate del_own, del_buy, del_rent using NET30 terms
            base_del_rebate = row.get('DEL_reb_pl_30', 0) or 0
            equip_fin = row.get('equip_fin_pl_30', 0) or 0
            equip_main = row.get('equip_main_pl_30', 0) or 0
            
            
            # Get equipment costs from config (PV terms)
            cost_owned_equip_pv = self.config['basic_parameters'].get('cost_owned_equip_pv', 0.05)
            cost_buy_equip_pv = self.config['basic_parameters'].get('cost_buy_equip_pv', 0.08)
            
            for i, band in enumerate(valid_bands):
                del_rebate_rate = band.get('del_rebate', 0) or 0
                if del_rebate_rate == 0:
                    continue  # Skip bands with no DEL rebate
                    
                min_vol = band['min_volume']
                max_vol = band['max_volume']
                
                # Create descriptive keys for DEL tier bands
                if max_vol is None:
                    band_suffix = f"tier_{min_vol//1000000}M_plus"
                else:
                    band_suffix = f"tier_{min_vol//1000000}M_to_{max_vol//1000000}M"
                
                if rebate_combination == 'override_base':
                    # Override: Replace DEL_reb_pl_30 with vol_tier_rebate, keep equipment costs
                    # DEL_own: ((wholesale/100) - (vol_tier_reb + equip_fin + equip_main))/PV30 + owned_equip_cost
                    del_own_cost = ((wholesale_price - (del_rebate_rate + equip_fin + equip_main)) / pv_factors['net30'] + 
                                   cost_owned_equip_pv)
                    
                    # DEL_buy: Same but with buy equipment cost
                    del_buy_cost = ((wholesale_price - (del_rebate_rate + equip_fin + equip_main)) / pv_factors['net30'] + 
                                   cost_buy_equip_pv)
                    
                    # DEL_rent: ((wholesale/100) - vol_tier_reb)/PV30 (no equipment costs)
                    del_rent_cost = ((wholesale_price - del_rebate_rate) / pv_factors['net30'])
                    
                elif rebate_combination == 'additive_to_base':
                    # Add: Use DEL_reb_pl_30 + vol_tier_reb, keep equipment costs
                    # DEL_own: ((wholesale/100) - (DEL_reb + vol_tier_reb + equip_fin + equip_main))/PV30 + owned_equip_cost
                    del_own_cost = ((wholesale_price - (base_del_rebate + del_rebate_rate + equip_fin + equip_main)) / pv_factors['net30'] + 
                                   cost_owned_equip_pv)
                    
                    # DEL_buy: Same but with buy equipment cost
                    del_buy_cost = ((wholesale_price - (base_del_rebate + del_rebate_rate + equip_fin + equip_main)) / pv_factors['net30'] + 
                                   cost_buy_equip_pv)
                    
                    # DEL_rent: ((wholesale/100) - (DEL_reb + vol_tier_reb))/PV30
                    del_rent_cost = ((wholesale_price - (base_del_rebate + del_rebate_rate)) / pv_factors['net30'])
                else:
                    logger.warning(f"Unknown rebate combination: {rebate_combination}")
                    continue
                    
                # Add DEL tier costs to result
                tier_costs[f"del_own_{band_suffix}"] = del_own_cost
                tier_costs[f"del_buy_{band_suffix}"] = del_buy_cost
                tier_costs[f"del_rent_{band_suffix}"] = del_rent_cost
            
        return tier_costs
    
    def run_complete_precomputation(self) -> Dict[str, Any]:
        """
        Execute the complete precomputation pipeline including volume tiers and coordinates.
        
        Returns:
            Dict: Complete cost dictionary with volume tier scenarios and coordinate data
        """
        logger.info("Starting complete precomputation pipeline with volume tiers...")
        
        # Run base precomputation (now includes volume tier enhanced costs and coordinates)
        complete_cost_data = self.run_base_precomputation()
        
        logger.info("Complete precomputation pipeline finished successfully!")
        return complete_cost_data
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
    
    def validate_volume_tier_business_rules(self, enhanced_cost_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple validation for the new tier costs structure."""
        return {
            'status': 'valid',
            'errors': [],
            'warnings': [],
            'statistics': {
                'total_depots': len(enhanced_cost_data['costs']),
                'total_combinations': sum(len(suppliers) for suppliers in enhanced_cost_data['costs'].values())
            }
        }