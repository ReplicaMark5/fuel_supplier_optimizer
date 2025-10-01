#!/usr/bin/env python3
"""
Extract Diesel wholesale pricing from the SA pricing PDF and load into SQLite.

Parses both:
- Diesel 0.05% sulfur
- Diesel 0.005% sulfur

Outputs to SQLite table: diesel_prices
Columns: zone, basic_list, zone_diff, rtl_wholesale, product
"""

import re
import sqlite3
from pathlib import Path
import os
import pandas as pd
import PyPDF2  # pip install PyPDF2

# ====== CONFIG ======
PDF_PATH = "/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Diesel_Prices.pdf"
DB_PATH  = str(Path(__file__).resolve().parents[2] / "data/databases/fuel_data.db")
TABLE    = "diesel_prices"
# ====================

def read_pdf_text(pdf_path: str) -> str:
    reader = PyPDF2.PdfReader(pdf_path)
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    # Keep line breaks; normalize spaces
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = raw.replace("\r", "\n")
    return raw

def clean_num(s: str) -> float:
    """Convert string number with commas to float"""
    return float(s.replace(",", ""))

def extract_rows(text: str) -> pd.DataFrame:
    """
    Extract diesel price data from PDF text.
    Looking for patterns like:
    1A 1,983.4 3.8 1987.17
    2A 10.1 1993.47
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows = []
    
    current_product = None
    last_basic = None
    
    product_05  = re.compile(r"Diesel\s*0\.05%?\s*sulfur", re.IGNORECASE)
    product_005 = re.compile(r"Diesel\s*0\.005%?\s*sulfur", re.IGNORECASE)
    
    for ln in lines:
        # Product headers
        if product_05.search(ln):
            current_product = "Diesel 0.05% sulfur"
            last_basic = None
            continue
        elif product_005.search(ln):
            current_product = "Diesel 0.005% sulfur"
            last_basic = None
            continue
        
        if not current_product:
            continue
            
        # Look for zone pattern: starts with digits followed by letter(s)
        zone_match = re.match(r'^(\d{1,2}[A-Z]+)', ln)
        if not zone_match:
            continue
            
        zone = zone_match.group(1)
        remainder = ln[zone_match.end():].strip()
        
        # Handle lines with zone names (like "9C GAUTENG", "35J Port Nolloth")
        # Remove location names but keep processing the line
        remainder = re.sub(r'^[A-Za-z\s]+', '', remainder).strip()
        
        # Find all numbers in the remainder
        nums = re.findall(r'\d{1,4}(?:,\d{3})*(?:\.\d+)?', remainder)
        
        # Convert to floats
        float_nums = []
        try:
            float_nums = [clean_num(n) for n in nums]
        except:
            continue
            
        # Determine the structure based on number of values
        basic_list = None
        zone_diff = None
        rtl_wholesale = None
        
        if len(float_nums) >= 3:
            # Format: zone basic_list zone_diff rtl_wholesale
            basic_list = float_nums[0]
            zone_diff = float_nums[1]
            rtl_wholesale = float_nums[2]
            last_basic = basic_list
        elif len(float_nums) == 2:
            # Format: zone zone_diff rtl_wholesale (use previous basic_list)
            basic_list = last_basic
            zone_diff = float_nums[0]
            rtl_wholesale = float_nums[1]
        else:
            continue
            
        if zone_diff is not None and rtl_wholesale is not None:
            rows.append({
                "zone": zone,
                "basic_list": basic_list,
                "zone_diff": zone_diff,
                "rtl_wholesale": rtl_wholesale,
                "product": current_product
            })
    
    if not rows:
        raise RuntimeError("No rows extracted—check PDF and patterns.")
    
    df = pd.DataFrame(rows).drop_duplicates().sort_values(["product", "zone"]).reset_index(drop=True)
    return df

def ensure_table(conn: sqlite3.Connection, table: str):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            zone TEXT,
            basic_list REAL,
            zone_diff REAL,
            rtl_wholesale REAL,
            product TEXT
        )
    """)
    # Helpful indexes for queries
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_product_zone ON {table}(product, zone)")

def main():
    pdf_path = Path(PDF_PATH)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    text = read_pdf_text(str(pdf_path))
    df = extract_rows(text)

    # Ensure destination directory exists
    os.makedirs(Path(DB_PATH).parent, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        ensure_table(conn, TABLE)
        # Clear existing data then append fresh
        conn.execute(f"DELETE FROM {TABLE}")
        conn.commit()

        # Write via pandas
        df.to_sql(TABLE, conn, if_exists="append", index=False)
        conn.commit()

        print(f"Replaced {TABLE} in {DB_PATH} with {len(df)} rows")
        
        # Show sample of extracted data
        print("\nSample extracted data:")
        print(df.head(10).to_string(index=False))
        
        # Show data grouped by product
        print(f"\nData summary:")
        print(f"Total rows: {len(df)}")
        for product in df['product'].unique():
            product_df = df[df['product'] == product]
            print(f"{product}: {len(product_df)} rows")
            print(f"  Zones: {sorted(product_df['zone'].unique())}")
            print(f"  Basic list values: {product_df['basic_list'].dropna().unique()}")
            print()

if __name__ == "__main__":
    main()
