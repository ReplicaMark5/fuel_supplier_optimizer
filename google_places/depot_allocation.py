import pandas as pd
import googlemaps
import math
from Config import GOOGLE_API_KEY

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on earth (in km)"""
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance = R * c
    
    return distance

def get_depot_coordinates(depot_name, gmaps):
    """Get coordinates for a depot using Google Geocoding API"""
    try:
        # Use geocoding API instead of places
        geocode_result = gmaps.geocode(f"{depot_name}, South Africa")
        
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            print(f"Could not find coordinates for {depot_name}")
            return None, None
    except Exception as e:
        print(f"Error getting coordinates for {depot_name}: {e}")
        return None, None

def main():
    # Read Excel file
    excel_path = "/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Google Distance Templates/Match_Sup_Cust_Dep.xlsx"
    
    # Read supplier depots (first sheet: 'Supplier_Depots')
    supplier_df = pd.read_excel(excel_path, sheet_name='Supplier_Depots')
    print("Supplier Depots data:")
    print(supplier_df.head())
    print(f"Supplier columns: {supplier_df.columns.tolist()}")
    
    # Read customer depots (second sheet: 'Customer_Depots')
    customer_df = pd.read_excel(excel_path, sheet_name='Customer_Depots')
    print("\nCustomer Depots data:")
    print(customer_df.head())
    print(f"Customer columns: {customer_df.columns.tolist()}")
    
    # Read existing matches (third sheet: 'Complete_Matches')
    existing_matches_df = pd.read_excel(excel_path, sheet_name='Complete_Matches')
    print("\nExisting Matches data:")
    print(existing_matches_df.head())
    print(f"Existing Matches columns: {existing_matches_df.columns.tolist()}")
    
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
    
    # Create set of existing matches for quick lookup
    existing_matches = set()
    for _, match_row in existing_matches_df.iterrows():
        customer_fk = match_row['Customer_Depot_FK']
        supplier_fk = match_row['Supplier_Depot_FK']
        existing_matches.add((customer_fk, supplier_fk))
    
    print(f"Loaded {len(existing_matches)} existing matches to exclude")
    
    # Get coordinates for each supplier depot
    supplier_coordinates = {}
    for _, supplier_row in supplier_df.iterrows():
        supplier_address = supplier_row['Supply_Depot_Address'].strip()
        supplier_id = supplier_row['Supplier_Depot_PK']
        print(f"Getting coordinates for: {supplier_address}")
        lat, lng = get_depot_coordinates(supplier_address, gmaps)
        if lat and lng:
            supplier_coordinates[supplier_id] = {
                'address': supplier_address,
                'coords': (lat, lng)
            }
    
    # Find all customer depots within 500km radius of each supplier depot
    allocations = []
    
    for supplier_id, supplier_data in supplier_coordinates.items():
        supplier_lat, supplier_lng = supplier_data['coords']
        supplier_address = supplier_data['address']
        
        print(f"\nFinding customer depots within 500km of {supplier_address}...")
        
        for _, customer_row in customer_df.iterrows():
            customer_id = customer_row['Cust_Depot_ID']
            customer_lat = customer_row['Lat']
            customer_lng = customer_row['Long']
            
            distance = haversine_distance(supplier_lat, supplier_lng, customer_lat, customer_lng)
            
            if distance <= 500:  # Within 500km radius
                # Check if this combination already exists in Complete_Matches
                if (customer_id, supplier_id) not in existing_matches:
                    allocations.append({
                        'Customer_Depot_ID': customer_id,
                        'Supplier_Depot_ID': supplier_id,
                        'Distance_km': distance
                    })
                    print(f"  NEW Customer {customer_id} allocated (distance: {distance:.2f}km)")
                else:
                    print(f"  Customer {customer_id} already matched - skipping (distance: {distance:.2f}km)")
    
    # Create DataFrame and save to CSV
    if allocations:
        allocations_df = pd.DataFrame(allocations)
        csv_path = "/home/blake/projects/demo5/google_places/depot_allocations.csv"
        allocations_df[['Customer_Depot_ID', 'Supplier_Depot_ID']].to_csv(csv_path, index=False)
        print(f"\nAllocations saved to: {csv_path}")
        
        # Print summary
        print("\n" + "="*80)
        print("DEPOT ALLOCATION RESULTS SUMMARY")
        print("="*80)
        print(f"Total allocations: {len(allocations)}")
        
        # Group by supplier to show count per supplier
        supplier_counts = allocations_df.groupby('Supplier_Depot_ID').size()
        for supplier_id, count in supplier_counts.items():
            print(f"Supplier {supplier_id}: {count} customer depots allocated")
    else:
        print("No allocations found within 500km radius!")
    
    return allocations

if __name__ == "__main__":
    main()