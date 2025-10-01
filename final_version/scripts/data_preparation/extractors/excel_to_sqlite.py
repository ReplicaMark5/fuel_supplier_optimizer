import pandas as pd
from pathlib import Path
import sqlite3
import os

# Path to Excel file in Windows from WSL
excel_path = "/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Final_Data/Fuel_Data_Structured_3.xlsx"

# SQLite database path (local to current directory)
db_path = str(Path(__file__).resolve().parents[2] / "data/databases/fuel_data.db")

def examine_excel_structure():
    """Examine the structure of the Excel file"""
    print("Examining Excel file structure...")
    
    # Read all sheet names
    excel_file = pd.ExcelFile(excel_path)
    sheet_names = excel_file.sheet_names
    
    print(f"Found {len(sheet_names)} sheets: {sheet_names}")
    
    # Examine each sheet
    for sheet_name in sheet_names:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        print(f"\nSheet: {sheet_name}")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"Data types:")
        print(df.dtypes)
        print(f"First few rows:")
        print(df.head())
        print("-" * 50)

def convert_to_sqlite():
    """Convert Excel sheets to SQLite tables"""
    print("Converting Excel to SQLite...")
    # Ensure destination directory exists
    os.makedirs(Path(db_path).parent, exist_ok=True)
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create connection to SQLite database
    conn = sqlite3.connect(db_path)
    
    # Read all sheet names
    excel_file = pd.ExcelFile(excel_path)
    sheet_names = excel_file.sheet_names
    
    # Convert each sheet to a table
    for sheet_name in sheet_names:
        print(f"Converting sheet: {sheet_name}")
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        
        # Clean table name (replace spaces and special characters)
        table_name = sheet_name.replace(" ", "_").replace("-", "_").lower()
        
        # Write to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Created table: {table_name} with {len(df)} rows")
    
    # Close connection
    conn.close()
    print(f"Database created successfully: {db_path}")

def verify_database():
    """Verify the created database"""
    print("Verifying database...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"Tables in database: {[table[0] for table in tables]}")
    
    # Show info for each table
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"\nTable: {table_name}")
        print(f"Row count: {count}")
        print("Columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    
    conn.close()

if __name__ == "__main__":
    examine_excel_structure()
    convert_to_sqlite()
    verify_database()
