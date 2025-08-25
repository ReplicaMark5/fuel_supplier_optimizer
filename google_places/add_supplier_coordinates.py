import sqlite3
import googlemaps
from Config import GOOGLE_API_KEY

def get_depot_coordinates(depot_address, gmaps):
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

def main():
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
    
    # Connect to database
    conn = sqlite3.connect('fuel_data_3.db')
    cursor = conn.cursor()
    
    # First, add the latitude and longitude columns if they don't exist
    try:
        cursor.execute("ALTER TABLE supplier_depots ADD COLUMN supplier_lat REAL")
        cursor.execute("ALTER TABLE supplier_depots ADD COLUMN supplier_lng REAL")
        print("Added supplier_lat and supplier_lng columns to supplier_depots table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Columns supplier_lat and supplier_lng already exist")
        else:
            raise e
    
    # Get all unique supplier depot locations that don't have coordinates yet
    cursor.execute("""
        SELECT DISTINCT Supply_Depot_Location 
        FROM supplier_depots 
        WHERE supplier_lat IS NULL OR supplier_lng IS NULL
    """)
    unique_locations = cursor.fetchall()
    
    print(f"Found {len(unique_locations)} unique locations to geocode")
    
    # Create a mapping of locations to coordinates
    location_coordinates = {}
    
    for (location,) in unique_locations:
        print(f"\nGetting coordinates for: {location}")
        lat, lng = get_depot_coordinates(location, gmaps)
        
        if lat is not None and lng is not None:
            location_coordinates[location] = (lat, lng)
            print(f"  Coordinates: ({lat}, {lng})")
        else:
            print(f"  Warning: Could not get coordinates for {location}")
    
    # Update all supplier depots with the same location
    updates_made = 0
    for location, (lat, lng) in location_coordinates.items():
        cursor.execute("""
            UPDATE supplier_depots 
            SET supplier_lat = ?, supplier_lng = ?
            WHERE Supply_Depot_Location = ?
        """, (lat, lng, location))
        
        rows_updated = cursor.rowcount
        updates_made += rows_updated
        print(f"Updated {rows_updated} depots with location '{location}'")
    
    # Commit changes
    conn.commit()
    
    # Verify updates
    cursor.execute("""
        SELECT Supply_Depot_Location, supplier_lat, supplier_lng, COUNT(*) as count
        FROM supplier_depots 
        WHERE supplier_lat IS NOT NULL AND supplier_lng IS NOT NULL
        GROUP BY Supply_Depot_Location, supplier_lat, supplier_lng
        ORDER BY Supply_Depot_Location
    """)
    
    print(f"\nVerification - Updated locations ({updates_made} total depots updated):")
    for row in cursor.fetchall():
        location, lat, lng, count = row
        print(f"  {location}: ({lat}, {lng}) - {count} depots")
    
    # Check for any remaining locations without coordinates
    cursor.execute("""
        SELECT Supply_Depot_Location, COUNT(*) as count
        FROM supplier_depots 
        WHERE supplier_lat IS NULL OR supplier_lng IS NULL
        GROUP BY Supply_Depot_Location
    """)
    
    remaining = cursor.fetchall()
    if remaining:
        print(f"\nWarning - Locations still without coordinates:")
        for location, count in remaining:
            print(f"  {location}: {count} depots")
    else:
        print("\nSuccess - All supplier depot locations now have coordinates!")
    
    conn.close()
    print(f"\nCompleted! Updated coordinates for {len(location_coordinates)} unique locations.")

if __name__ == "__main__":
    main()