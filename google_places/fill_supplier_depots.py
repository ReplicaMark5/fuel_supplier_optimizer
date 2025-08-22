import sqlite3
import googlemaps
import math
from Config import GOOGLE_API_KEY

def get_depot_coordinates_and_address(depot_address, gmaps):
    """Get coordinates for a depot using Google Geocoding API"""
    try:
        search_queries = [
            f"{depot_address}, South Africa",
            f"{depot_address}, Botswana", 
            f"{depot_address}, Mozambique",
            f"{depot_address}, Eswatini",
            f"{depot_address}, Namibia",
            depot_address  # Fallback without country
        ]
        
        for query in search_queries:
            geocode_result = gmaps.geocode(query)
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                return location['lat'], location['lng']
        
        print(f"Could not find coordinates for {depot_address}")
        return None, None
    except Exception as e:
        print(f"Error getting coordinates for {depot_address}: {e}")
        return None, None

def get_road_distance(origin_coords, destination_coords, gmaps):
    """Calculate on-road distance using Google Distance Matrix API"""
    try:
        origin = f"{origin_coords[0]},{origin_coords[1]}"
        destination = f"{destination_coords[0]},{destination_coords[1]}"
        
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
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
    
    # Connect to database
    conn = sqlite3.connect('fuel_data_2.db')
    cursor = conn.cursor()
    
    # Get supplier 5 depot information
    cursor.execute("""
        SELECT Supplier_Depot_PK, Supply_Depot_Location 
        FROM supplier_depots 
        WHERE Supplier_FK = 5
    """)
    supplier_depots = cursor.fetchall()
    
    print(f"Found {len(supplier_depots)} supplier 5 depots:")
    for depot_pk, location in supplier_depots:
        print(f"  {depot_pk}: {location}")
    
    # Get coordinates for supplier depots
    supplier_depot_coords = {}
    for depot_pk, location in supplier_depots:
        lat, lng = get_depot_coordinates_and_address(location, gmaps)
        if lat is not None and lng is not None:
            supplier_depot_coords[depot_pk] = (lat, lng)
            print(f"  Depot {depot_pk} coordinates: ({lat}, {lng})")
        else:
            print(f"  Warning: Could not get coordinates for depot {depot_pk}: {location}")
    
    # Get the specific OD pairs that need to be updated (2012-2042)
    od_pairs_list = list(range(2012, 2043))  # 2012 to 2042 inclusive
    placeholders = ','.join('?' * len(od_pairs_list))
    cursor.execute(f"""
        SELECT OD_Pair_PK_, Customer_Depot_FK 
        FROM od_pair 
        WHERE OD_Pair_PK_ IN ({placeholders})
    """, od_pairs_list)
    od_pairs_to_update = cursor.fetchall()
    
    print(f"\nFound {len(od_pairs_to_update)} OD pairs to update")
    
    # Get customer depot coordinates
    customer_depot_coords = {}
    for od_pair_pk, customer_depot_fk in od_pairs_to_update:
        cursor.execute("""
            SELECT Lats, Long 
            FROM customer_depots 
            WHERE Cust_Depot_PK = ?
        """, (customer_depot_fk,))
        
        result = cursor.fetchone()
        if result:
            customer_depot_coords[customer_depot_fk] = (result[0], result[1])
        else:
            print(f"Warning: Could not find coordinates for customer depot {customer_depot_fk}")
    
    # For each OD pair, find the closest supplier depot
    updates = []
    for od_pair_pk, customer_depot_fk in od_pairs_to_update:
        if customer_depot_fk not in customer_depot_coords:
            print(f"Skipping OD pair {od_pair_pk} - no customer coordinates")
            continue
            
        customer_coords = customer_depot_coords[customer_depot_fk]
        closest_depot = None
        min_distance = float('inf')
        
        print(f"\nProcessing OD pair {od_pair_pk}, Customer {customer_depot_fk}")
        print(f"Customer coordinates: {customer_coords}")
        
        # Calculate distance to each supplier depot
        for supplier_depot_pk, supplier_coords in supplier_depot_coords.items():
            distance = get_road_distance(customer_coords, supplier_coords, gmaps)
            
            if distance is not None:
                print(f"  Distance to supplier depot {supplier_depot_pk}: {distance:.2f} km")
                if distance < min_distance:
                    min_distance = distance
                    closest_depot = supplier_depot_pk
            else:
                print(f"  Could not calculate distance to supplier depot {supplier_depot_pk}")
        
        if closest_depot is not None:
            print(f"  Closest depot: {closest_depot} ({min_distance:.2f} km)")
            updates.append((closest_depot, round(min_distance, 2), od_pair_pk))
        else:
            print(f"  Warning: Could not find closest depot for OD pair {od_pair_pk}")
    
    # Apply updates to database
    print(f"\nApplying {len(updates)} updates to database...")
    
    for supplier_depot_fk, distance, od_pair_pk in updates:
        cursor.execute("""
            UPDATE od_pair 
            SET Supplier_Depot_FK = ?, One_Way_Dist = ?
            WHERE OD_Pair_PK_ = ?
        """, (supplier_depot_fk, distance, od_pair_pk))
        
        print(f"Updated OD pair {od_pair_pk}: supplier_depot_FK = {supplier_depot_fk}, distance = {distance} km")
    
    # Commit changes
    conn.commit()
    
    # Verify updates
    cursor.execute("""
        SELECT OD_Pair_PK_, Customer_Depot_FK, Supplier_Depot_FK, One_Way_Dist
        FROM od_pair 
        WHERE OD_Pair_PK_ IN ({})
    """.format(','.join('?' * len([u[2] for u in updates]))), [u[2] for u in updates])
    
    print("\nVerification - Updated records:")
    for row in cursor.fetchall():
        print(f"  OD_Pair_PK_: {row[0]}, Customer: {row[1]}, Supplier: {row[2]}, Distance: {row[3]} km")
    
    conn.close()
    print(f"\nCompleted! Updated {len(updates)} OD pairs.")

if __name__ == "__main__":
    main()