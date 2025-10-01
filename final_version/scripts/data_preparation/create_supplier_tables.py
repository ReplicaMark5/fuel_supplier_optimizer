#!/usr/bin/env python3
"""
Script to create supplier_scores and criteria_weights tables in the fuel_data.db database
and import data from Strategic Supplier Scores.xlsx
"""

import sqlite3
import pandas as pd
from pathlib import Path
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_tables(db_path=str(Path(__file__).resolve().parents[2] / "data/databases/fuel_data.db")):
    """Create the supplier_scores and criteria_weights tables."""
    logger.info("Creating supplier_scores and criteria_weights tables...")
    os.makedirs(Path(db_path).parent, exist_ok=True)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Drop tables if they exist (for clean slate)
            cursor.execute("DROP TABLE IF EXISTS supplier_scores")
            cursor.execute("DROP TABLE IF EXISTS criteria_weights")
            
            # Create supplier_scores table
            create_supplier_scores_sql = """
            CREATE TABLE supplier_scores (
                supplier_scores_pk INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_name TEXT NOT NULL,
                current_level REAL NOT NULL,
                product_service_type INTEGER NOT NULL,
                geographical_network REAL NOT NULL,
                method_of_sourcing REAL NOT NULL,
                invest_refuelling_equipment INTEGER NOT NULL,
                reciprocal_business INTEGER NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(supplier_name)
            );
            """
            
            # Create criteria_weights table
            create_criteria_weights_sql = """
            CREATE TABLE criteria_weights (
                criteria_weights_pk INTEGER PRIMARY KEY AUTOINCREMENT,
                criteria_name TEXT NOT NULL UNIQUE,
                weight REAL NOT NULL CHECK (weight >= 0 AND weight <= 1),
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            cursor.execute(create_supplier_scores_sql)
            cursor.execute(create_criteria_weights_sql)
            
            conn.commit()
            logger.info("Tables created successfully")
            
    except sqlite3.Error as e:
        logger.error(f"Database error while creating tables: {e}")
        raise

def import_excel_data(excel_path, db_path=str(Path(__file__).resolve().parents[2] / "data/databases/fuel_data.db")):
    """Import data from Excel file into the database tables."""
    logger.info(f"Importing data from {excel_path}")
    os.makedirs(Path(db_path).parent, exist_ok=True)
    
    try:
        # Read Excel data
        scores_df = pd.read_excel(excel_path, sheet_name='scores')
        weights_df = pd.read_excel(excel_path, sheet_name='weights')
        
        logger.info(f"Read {len(scores_df)} supplier scores and {len(weights_df)} criteria weights")
        
        with sqlite3.connect(db_path) as conn:
            # Import supplier scores
            for _, row in scores_df.iterrows():
                insert_scores_sql = """
                INSERT INTO supplier_scores 
                (supplier_name, current_level, product_service_type, geographical_network, 
                 method_of_sourcing, invest_refuelling_equipment, reciprocal_business)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor = conn.cursor()
                cursor.execute(insert_scores_sql, (
                    row['Suppliers'],
                    row['Current Level (1-8)'],
                    row['Product / Service Type'],
                    row['Geographical Network'],
                    row['Method of Sourcing'],
                    row['Invest in Refuelling Equipment'],
                    row['Reciprocal Business']
                ))
            
            # Import criteria weights
            for _, row in weights_df.iterrows():
                insert_weights_sql = """
                INSERT INTO criteria_weights (criteria_name, weight)
                VALUES (?, ?)
                """
                
                cursor.execute(insert_weights_sql, (
                    row['Criteria'],
                    row['weights']
                ))
            
            conn.commit()
            logger.info("Data imported successfully")
            
    except Exception as e:
        logger.error(f"Error importing data: {e}")
        raise

def validate_data(db_path=str(Path(__file__).resolve().parents[2] / "data/databases/fuel_data.db")):
    """Validate the imported data."""
    logger.info("Validating imported data...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check supplier_scores table
            cursor.execute("SELECT COUNT(*) FROM supplier_scores")
            scores_count = cursor.fetchone()[0]
            logger.info(f"supplier_scores table: {scores_count} records")
            
            # Check criteria_weights table  
            cursor.execute("SELECT COUNT(*) FROM criteria_weights")
            weights_count = cursor.fetchone()[0]
            logger.info(f"criteria_weights table: {weights_count} records")
            
            # Show sample data from supplier_scores
            cursor.execute("SELECT * FROM supplier_scores LIMIT 3")
            scores_sample = cursor.fetchall()
            logger.info("Sample supplier_scores data:")
            for row in scores_sample:
                logger.info(f"  {row}")
            
            # Show all criteria weights
            cursor.execute("SELECT criteria_name, weight FROM criteria_weights ORDER BY criteria_name")
            weights_data = cursor.fetchall()
            logger.info("All criteria weights:")
            for criteria, weight in weights_data:
                logger.info(f"  {criteria}: {weight}")
            
            # Validate weights sum to 1.0
            cursor.execute("SELECT SUM(weight) FROM criteria_weights")
            total_weight = cursor.fetchone()[0]
            logger.info(f"Total weight sum: {total_weight} (should be close to 1.0)")
            
            if abs(total_weight - 1.0) > 0.001:
                logger.warning(f"Warning: Total weights do not sum to 1.0 (actual: {total_weight})")
            
    except sqlite3.Error as e:
        logger.error(f"Database error during validation: {e}")
        raise

def main():
    """Main function to create tables and import data."""
    excel_path = "/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Final_Data_2/Strategic Supplier Scores.xlsx"
    db_path = str(Path(__file__).resolve().parents[2] / "data/databases/fuel_data.db")
    
    logger.info("Starting supplier tables creation and data import...")
    
    try:
        # Step 1: Create tables
        create_tables(db_path)
        
        # Step 2: Import data
        import_excel_data(excel_path, db_path)
        
        # Step 3: Validate data
        validate_data(db_path)
        
        logger.info("All operations completed successfully!")
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
