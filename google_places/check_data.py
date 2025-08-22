import pandas as pd

# Read the Distance sheet
excel_path = "/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Depot_Site_Allocation.xlsx"
distance_df = pd.read_excel(excel_path, sheet_name='Distance')

print(f"Total rows in Distance sheet: {len(distance_df)}")
print(f"Columns: {distance_df.columns.tolist()}")

# Check for missing values
print(f"\nMissing values:")
print(f"Site Name missing: {distance_df['Site Name'].isna().sum()}")
print(f"Supply Depot missing: {distance_df['Supply Depot'].isna().sum()}")

# Check for rows where both are present
valid_rows = distance_df.dropna(subset=['Site Name', 'Supply Depot'])
print(f"\nRows with both Site Name and Supply Depot: {len(valid_rows)}")

# Check for duplicates
duplicates = valid_rows.duplicated(subset=['Site Name', 'Supply Depot'])
print(f"Duplicate Site Name + Supply Depot pairs: {duplicates.sum()}")

# Show duplicates if any
if duplicates.sum() > 0:
    print("\nDuplicate pairs:")
    duplicate_pairs = valid_rows[duplicates]
    print(duplicate_pairs[['Site Name', 'Supply Depot']])

# Show unique combinations
unique_pairs = valid_rows.drop_duplicates(subset=['Site Name', 'Supply Depot'])
print(f"\nUnique Site Name + Supply Depot combinations: {len(unique_pairs)}")

# Show first few rows with missing data
missing_data = distance_df[distance_df['Site Name'].isna() | distance_df['Supply Depot'].isna()]
if len(missing_data) > 0:
    print(f"\nRows with missing data ({len(missing_data)} total):")
    print(missing_data.head(10))

# Show sample of valid data
print(f"\nSample of valid data:")
print(valid_rows.head(10))