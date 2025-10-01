# Depot Allocation Methodology Documentation

## Overview

This document describes the geospatial depot allocation methodology used for data preparation in the thesis research. The system automatically assigns customer depots to supplier depots based on geographic proximity constraints, forming the foundation for supply chain optimization analysis.

## Fundamental Implementation Approach

### Data Sources
The allocation system processes three primary datasets from an Excel workbook:
- **Supplier_Depots**: Contains supplier depot information with addresses
- **Customer_Depots**: Contains customer depot locations with latitude/longitude coordinates
- **Complete_Matches**: Existing depot pairings to avoid duplication

### Core Algorithm Components

#### 1. Coordinate Geocoding
The system utilizes the Google Geocoding API to convert supplier depot addresses into precise geographic coordinates (latitude/longitude). This standardizes location data across all depots.

```python
def get_depot_coordinates(depot_name, gmaps):
    geocode_result = gmaps.geocode(f"{depot_name}, South Africa")
    return location['lat'], location['lng']
```

#### 2. Distance Calculation
Geographic distances are computed using the Haversine formula, which calculates great-circle distances between two points on Earth's surface. This accounts for the Earth's curvature and provides accurate distance measurements.

```python
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers
    # Haversine formula implementation
    return distance
```

#### 3. Proximity-Based Allocation
The system applies a 500-kilometer radius constraint to determine feasible supplier-customer depot pairings. This threshold represents a practical transportation distance for supply chain operations.

### Allocation Logic Flow

1. **Data Ingestion**: Load supplier depots, customer depots, and existing matches
2. **Geocoding**: Convert supplier addresses to coordinates using Google's API
3. **Distance Matrix Generation**: Calculate distances between all supplier-customer pairs
4. **Constraint Application**: Filter pairings within 500km radius
5. **Duplication Prevention**: Exclude existing matches to avoid redundancy
6. **Output Generation**: Export new allocations to CSV format

## Theoretical Foundation

### Geographic Information Systems (GIS) Theory

The depot allocation methodology is grounded in spatial analysis principles from Geographic Information Systems theory:

#### Proximity Analysis
The core concept relies on **Tobler's First Law of Geography**: "Everything is related to everything else, but near things are more related than distant things." This principle justifies using geographic proximity as a primary criterion for depot allocation.

#### Service Area Analysis
The 500km radius constraint implements a **service area buffer zone** around each supplier depot. This creates circular catchment areas that define the theoretical maximum service range for each supplier facility.

### Spatial Optimization Theory

#### Location-Allocation Problems
The methodology addresses a classic **Location-Allocation Problem** in spatial optimization, where the goal is to optimally assign demand points (customer depots) to supply points (supplier depots) based on spatial constraints.

#### Distance Decay Function
The implementation applies a **step function distance decay model**:
- Distance ≤ 500km: Full allocation feasibility
- Distance > 500km: Zero allocation feasibility

This binary model simplifies the complex relationship between distance and transportation feasibility.

### Network Theory Applications

#### Graph Theory Foundation
The depot allocation creates a **bipartite graph** structure where:
- **Vertices**: Supplier depots and customer depots (two distinct sets)
- **Edges**: Feasible transportation links within distance constraints
- **Edge Weights**: Geographic distances between depot pairs

#### Network Accessibility
The methodology evaluates **network accessibility** by measuring the potential connectivity between supply and demand nodes within the transportation network.

### Transportation Geography Principles

#### Spatial Interaction Model
The allocation follows **gravity model principles** where interaction probability decreases with distance. However, the implementation uses a simplified binary threshold rather than a continuous decay function.

#### Central Place Theory
The supplier depot network implicitly follows **Central Place Theory** concepts, where each supplier depot serves as a central place providing services to surrounding customer locations within its hinterland (500km radius).

## Algorithmic Complexity

### Time Complexity
- **Geocoding Phase**: O(n) where n = number of supplier depots
- **Distance Calculation**: O(n × m) where n = suppliers, m = customers
- **Overall Complexity**: O(n × m + API_calls)

### Space Complexity
- **Coordinate Storage**: O(n) for supplier coordinates
- **Allocation Results**: O(k) where k = valid allocations
- **Overall Space**: O(n + m + k)

## Practical Applications

### Supply Chain Network Design
The allocation results provide the foundation for:
- **Network topology analysis**: Understanding connectivity patterns
- **Service coverage assessment**: Identifying under-served regions
- **Capacity planning**: Matching supply and demand geographically

### Transportation Planning
The distance matrix enables:
- **Route optimization**: Shortest path calculations between depots
- **Cost estimation**: Transportation cost modeling based on distances
- **Logistics efficiency**: Minimizing total transportation distances

## Limitations and Considerations

### Geographic Constraints
- **Euclidean vs. Network Distance**: Haversine distances represent straight-line distances, not actual road network distances
- **Terrain Considerations**: The model doesn't account for geographic barriers or terrain difficulty

### Operational Constraints
- **Static Analysis**: The allocation is time-independent and doesn't consider dynamic factors
- **Binary Threshold**: The 500km constraint creates hard boundaries that may not reflect operational flexibility

### Data Quality Dependencies
- **Geocoding Accuracy**: Results depend on Google API accuracy and address quality
- **Coordinate Precision**: Customer depot coordinates must be accurate for meaningful distance calculations

## Integration with Optimization Framework

This depot allocation methodology serves as the **data preparation phase** for subsequent supply chain optimization models. The generated allocation matrix becomes an input constraint for:

1. **Multi-objective optimization**: Balancing cost, service level, and sustainability objectives
2. **Capacity planning**: Ensuring supplier-customer pairings respect capacity constraints
3. **Strategic decision-making**: Supporting long-term network design decisions

The geographic feasibility constraints established by this methodology ensure that optimization solutions remain practically implementable within real-world transportation networks.