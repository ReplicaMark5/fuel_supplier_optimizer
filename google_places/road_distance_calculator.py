import pandas as pd
import googlemaps
import csv
from Config import GOOGLE_API_KEY

def get_depot_coordinates_and_address(depot_name, gmaps):
    """Get coordinates and formatted address for a depot using Google Geocoding API"""
    try:
        # Try multiple search strategies including neighboring countries
        search_queries = [
            f"{depot_name}, South Africa",
            f"{depot_name}, Botswana", 
            f"{depot_name}, Mozambique",
            f"{depot_name}, Eswatini",
            f"{depot_name}, Namibia",
            f"{depot_name}"  # Fallback without country
        ]
        
        for query in search_queries:
            geocode_result = gmaps.geocode(query)
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                formatted_address = geocode_result[0]['formatted_address']
                return location['lat'], location['lng'], formatted_address
        
        print(f"Could not find coordinates for {depot_name}")
        return None, None, None
    except Exception as e:
        print(f"Error getting coordinates for {depot_name}: {e}")
        return None, None, None

def get_road_distance(origin_coords, destination_coords, gmaps):
    """Calculate on-road distance using Google Distance Matrix API"""
    try:
        # Format coordinates for Distance Matrix API
        origin = f"{origin_coords[0]},{origin_coords[1]}"
        destination = f"{destination_coords[0]},{destination_coords[1]}"
        
        # Get distance matrix
        result = gmaps.distance_matrix(
            origins=[origin],
            destinations=[destination],
            mode="driving",
            units="metric"
        )
        
        if result['status'] == 'OK':
            element = result['rows'][0]['elements'][0]
            if element['status'] == 'OK':
                distance_km = element['distance']['value'] / 1000  # Convert meters to km
                return distance_km
            else:
                print(f"Distance calculation failed: {element['status']}")
                return None
        else:
            print(f"Distance Matrix API failed: {result['status']}")
            return None
            
    except Exception as e:
        print(f"Error calculating road distance: {e}")
        return None

def main():
    print("Reading Excel file...")
    excel_path = "/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Google Distance Templates/Sup_Dep_Dist.xlsx"
    
    # Read all three sheets
    pairs_df = pd.read_excel(excel_path, sheet_name=0)  # Customer_Depot_FK, Supplier_Depot_FK
    suppliers_df = pd.read_excel(excel_path, sheet_name=1)  # Supplier_Depot_PK, Supply_Depot_Address
    customers_df = pd.read_excel(excel_path, sheet_name=2)  # Cust_Depot_PK, Lats, Long
    
    print("Pairs sheet data:")
    print(pairs_df.head())
    print(f"Pairs sheet columns: {pairs_df.columns.tolist()}")
    
    print("\nSuppliers sheet data:")
    print(suppliers_df.head())
    print(f"Suppliers sheet columns: {suppliers_df.columns.tolist()}")
    
    print("\nCustomers sheet data:")
    print(customers_df.head())
    print(f"Customers sheet columns: {customers_df.columns.tolist()}")
    
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
    
    # Create dictionaries for customer coordinates and supplier addresses
    customer_coordinates = {}
    for _, customer_row in customers_df.iterrows():
        customer_id = customer_row['Cust_Depot_PK']
        customer_lat = customer_row['Lats']
        customer_lng = customer_row['Long']
        customer_coordinates[customer_id] = (customer_lat, customer_lng)
    
    supplier_addresses = {}
    for _, supplier_row in suppliers_df.iterrows():
        supplier_id = supplier_row['Supplier_Depot_PK']
        supplier_address = supplier_row['Supply_Depot_Address']
        supplier_addresses[supplier_id] = supplier_address
    
    print(f"\nLoaded {len(customer_coordinates)} customer coordinates")
    print(f"Loaded {len(supplier_addresses)} supplier addresses")
    
    # Prepare results list
    results = []
    
    # Process each row in the pairs sheet
    for index, row in pairs_df.iterrows():
        customer_depot_fk = row['Customer_Depot_FK'] if pd.notna(row['Customer_Depot_FK']) else None
        supplier_depot_fk = row['Supplier_Depot_FK'] if pd.notna(row['Supplier_Depot_FK']) else None
        
        # Handle missing FK values by adding to results with null distance
        if customer_depot_fk is None or supplier_depot_fk is None:
            print(f"  Row {index}: missing FK values - adding with null distance")
            results.append({
                'Customer_Depot_FK': customer_depot_fk if customer_depot_fk is not None else 'NaN',
                'One_way_distance': 'NaN',
                'Supplier_Depot_FK': supplier_depot_fk if supplier_depot_fk is not None else 'NaN'
            })
            continue
        
        print(f"\nProcessing: Customer {customer_depot_fk} -> Supplier {supplier_depot_fk}")
        
        # Get customer coordinates
        if customer_depot_fk in customer_coordinates:
            customer_coords = customer_coordinates[customer_depot_fk]
            print(f"  Customer coordinates: {customer_coords}")
        else:
            print(f"  Warning: Customer depot '{customer_depot_fk}' not found in coordinates data")
            results.append({
                'Customer_Depot_FK': customer_depot_fk,
                'One_way_distance': 'NaN',
                'Supplier_Depot_FK': supplier_depot_fk
            })
            continue
        
        # Get supplier address
        if supplier_depot_fk in supplier_addresses:
            supplier_address = supplier_addresses[supplier_depot_fk]
            print(f"  Supplier address: {supplier_address}")
        else:
            print(f"  Warning: Supplier depot '{supplier_depot_fk}' not found in addresses data")
            results.append({
                'Customer_Depot_FK': customer_depot_fk,
                'One_way_distance': 'NaN',
                'Supplier_Depot_FK': supplier_depot_fk
            })
            continue
        
        # Get supplier coordinates using address
        supplier_lat, supplier_lng, formatted_address = get_depot_coordinates_and_address(supplier_address, gmaps)
        
        if supplier_lat is None or supplier_lng is None:
            print(f"  Warning: Could not get coordinates for supplier '{supplier_address}'")
            results.append({
                'Customer_Depot_FK': customer_depot_fk,
                'One_way_distance': 'NaN',
                'Supplier_Depot_FK': supplier_depot_fk
            })
            continue
        
        supplier_coords = (supplier_lat, supplier_lng)
        print(f"  Supplier coordinates: {supplier_coords}")
        
        # Calculate road distance
        road_distance = get_road_distance(customer_coords, supplier_coords, gmaps)
        
        if road_distance is not None:
            print(f"  Road distance: {road_distance:.2f} km")
            
            # Store result
            results.append({
                'Customer_Depot_FK': customer_depot_fk,
                'One_way_distance': round(road_distance, 2),
                'Supplier_Depot_FK': supplier_depot_fk
            })
        else:
            print(f"  Warning: Could not calculate road distance")
            results.append({
                'Customer_Depot_FK': customer_depot_fk,
                'One_way_distance': 'NaN',
                'Supplier_Depot_FK': supplier_depot_fk
            })
    
    # Write results to CSV
    output_file = '/home/blake/projects/demo5/google_places/road_distances.csv'
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Customer_Depot_FK', 'One_way_distance', 'Supplier_Depot_FK']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"\n" + "="*80)
    print(f"RESULTS SAVED TO: {output_file}")
    print(f"Total pairs processed: {len(results)}")
    print(f"Successful distance calculations: {len([r for r in results if r['One_way_distance'] != 'NaN'])}")
    print("="*80)
    
    # Also display a summary
    print("\nSUMMARY OF RESULTS:")
    for result in results:
        distance_str = f"{result['One_way_distance']} km" if result['One_way_distance'] != 'NaN' else "NaN"
        print(f"Customer {result['Customer_Depot_FK']} -> Supplier {result['Supplier_Depot_FK']}: {distance_str}")

if __name__ == "__main__":
    main()