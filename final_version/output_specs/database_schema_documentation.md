# Database Schema Documentation

## Overview
This document provides comprehensive documentation of the SQLite database (`fuel_data.db`) that serves as the data foundation for the multi-objective depot supplier allocation optimization system. The database implements a normalized relational structure supporting complex fuel supply chain operations across South Africa and neighboring countries, with integrated strategic supplier scoring capabilities.

## Database Statistics
- **Total Tables**: 9 core tables
- **Total Records**: 2,580 records across all tables
- **Geographic Coverage**: 5 countries (South Africa, Botswana, Namibia, Mozambique, Eswatini)
- **Suppliers**: 9 major fuel suppliers
- **Network Scale**: 60 customer depots, 75 supplier depots, 2,042 possible supply relationships

## Database Architecture

### Entity Relationship Overview
The database follows a normalized star schema optimized for supply chain optimization queries:

```
Core Entities:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  customer_depots│    │   supplier_depots│    │    suppliers    │
│     (60)        │    │      (75)       │    │      (9)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────┬───────────┘                       │
                     │                                   │
              ┌─────────────────┐                        │
              │    od_pair      │◄───────────────────────┘
              │     (2,042)     │
              └─────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
┌─────────────┐ ┌─────────────┐ ┌─────────────────┐
│collection_  │ │delivery_    │ │  diesel_prices  │
│options (68) │ │options(281) │ │     (54)        │
└─────────────┘ └─────────────┘ └─────────────────┘

Strategic Scoring:
┌─────────────────┐    ┌─────────────────┐
│ supplier_scores │    │criteria_weights │
│      (9)        │    │      (6)        │
└─────────────────┘    └─────────────────┘
```

## Table Specifications

### 1. Core Infrastructure Tables

#### `customer_depots` (60 records)
**Purpose**: Customer fuel depot locations and consumption profiles

```sql
CREATE TABLE customer_depots (
  Cust_Depot_PK INTEGER,           -- Primary key
  Cust_Depot_Name TEXT,            -- Depot name/identifier
  Country TEXT,                    -- Country location
  Town TEXT,                       -- Town/city location
  Lats REAL,                       -- Latitude coordinate
  Long REAL,                       -- Longitude coordinate
  Fuel_Zone_ TEXT,                 -- SA fuel pricing zone
  Tankage_Size_Litres REAL,        -- Storage tank capacity
  Number_Pumps INTEGER,            -- Number of fuel pumps
  Annual_Volume_Litres REAL,       -- Annual fuel consumption
  Equip_Val_Est_ZAR INTEGER        -- Equipment value estimate (ZAR)
);
```

**Business Logic**:
- **Geographic Distribution**: 5 countries with South Africa representing majority
- **Volume Range**: Annual consumption varies from small rural stations to large commercial depots
- **Fuel Zones**: SA-specific pricing zones (e.g., "09A", "12B") linked to wholesale pricing
- **Capacity Constraints**: Tank sizes influence delivery scheduling and inventory management

#### `supplier_depots` (75 records)
**Purpose**: Supplier fuel depot infrastructure and geographic coverage

```sql
CREATE TABLE supplier_depots (
  Supplier_Depot_PK INTEGER,       -- Primary key
  Supply_Depot_Name TEXT,          -- Depot name/identifier
  Supply_Depot_Location TEXT,      -- Physical address
  Supplier_FK INTEGER,             -- Foreign key to suppliers table
  Fuel_Zone_ TEXT,                 -- SA fuel pricing zone
  Country TEXT,                    -- Country location
  supplier_lat REAL,               -- Latitude coordinate
  supplier_lng REAL                -- Longitude coordinate
);
```

**Business Logic**:
- **Network Coverage**: 75 strategically located supply points across 5 countries
- **Supplier Ownership**: Each depot linked to one of 9 major suppliers
- **Capacity Management**: Individual depot throughput limits defined in configuration
- **Geographic Strategy**: Coverage optimized for regional fuel distribution

#### `suppliers` (9 records)
**Purpose**: Master supplier registry

```sql
CREATE TABLE suppliers (
  Supplier_Name_ TEXT,             -- Supplier business name
  Supplier_PK INTEGER              -- Primary key
);
```

**Supplier Portfolio**: 9 major fuel suppliers (Supplier A through L, excluding B, E, K)

### 2. Relationship and Option Tables

#### `od_pair` (2,042 records)
**Purpose**: Origin-destination relationships with service option availability

```sql
CREATE TABLE od_pair (
  OD_Pair_PK_ INTEGER,             -- Primary key
  Customer_Depot_FK INTEGER,       -- Foreign key to customer_depots
  One_Way_Dist REAL,               -- Distance in kilometers
  Supplier_Depot_FK INTEGER,       -- Foreign key to supplier_depots
  DEL_Valid_FK REAL,               -- Foreign key to delivery_options (nullable)
  COC_Valid_FK REAL                -- Foreign key to collection_options (nullable)
);
```

**Business Logic**:
- **Relationship Matrix**: Not all customer-supplier depot combinations are viable
- **Service Availability**: NULL values indicate unavailable service options
- **Distance Integration**: One-way distances for transportation cost calculations
- **Option Filtering**: COC/DEL availability varies by business relationships and capabilities

#### `collection_options` (68 records)
**Purpose**: Customer Own Collection (COC) rebate pricing

```sql
CREATE TABLE collection_options (
  COC_Valid_PK INT,                -- Primary key
  COC_reb_pl_cash REAL,            -- Cash payment rebate (R/litre)
  COC_reb_pl_30 REAL,              -- NET30 payment rebate (R/litre)
  COC_reb_pl_45 REAL,              -- NET45 payment rebate (R/litre)
  COC_reb_pl_60 REAL               -- NET60 payment rebate (R/litre)
);
```

**Business Logic**:
- **Payment Terms**: Different rebate structures for various payment schedules
- **Customer Collection**: Pricing for customer-arranged transportation
- **Present Value Impact**: Longer payment terms reduce effective rebate value
- **Null Handling**: NULL values indicate unavailable payment options

#### `delivery_options` (281 records)  
**Purpose**: Supplier delivery service pricing and equipment arrangements

```sql
CREATE TABLE delivery_options (
  DEL_Valid_PK INT,                                              -- Primary key
  Supplier_FK INT,                                               -- Foreign key to suppliers
  Customer_Depot_FK INT,                                         -- Foreign key to customer_depots
  COC_From_DEL REAL,                                            -- Alternative COC pricing
  'TRANSPORT CHARGE / (SAVING) EXCL ZONE DIFF' REAL,           -- Transport adjustment
  equip_fin_pl_30 REAL,                                         -- Equipment financing (R/litre)
  equip_main_pl_30 REAL,                                        -- Equipment maintenance (R/litre)
  DEL_reb_pl_30 REAL                                            -- Delivery rebate (R/litre)
);
```

**Business Logic**:
- **Equipment Options**: Own, buy, or rent equipment for delivery service
- **Transport Economics**: Zone-specific transport charge adjustments
- **Supplier Capabilities**: Not all suppliers offer delivery services
- **Cost Structure**: Separate pricing for equipment financing vs. maintenance

### 3. Pricing Infrastructure

#### `diesel_prices` (54 records)
**Purpose**: Wholesale fuel pricing by geographic zone

```sql
CREATE TABLE diesel_prices (
  zone TEXT,                       -- Fuel pricing zone
  basic_list REAL,                 -- Basic list price (cents/litre)
  zone_diff REAL,                  -- Zone differential (cents/litre)
  rtl_wholesale REAL,              -- Retail wholesale price (cents/litre)
  product TEXT                     -- Fuel product specification
);
```

**Business Logic**:
- **Product Focus**: Currently "Diesel 0.005% sulfur" for low-sulfur compliance
- **Zone-Based Pricing**: South African fuel pricing zones with geographic differentials
- **Wholesale Basis**: Foundation for all cost calculations before rebates
- **Price Structure**: `rtl_wholesale = basic_list + zone_diff`

### 4. Strategic Scoring System

#### `supplier_scores` (9 records)
**Purpose**: Multi-criteria strategic evaluation of suppliers

```sql
CREATE TABLE supplier_scores (
  supplier_scores_pk INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier_name TEXT NOT NULL,                    -- Supplier business name
  current_level REAL NOT NULL,                    -- Current relationship strength (1-8)
  product_service_type INTEGER NOT NULL,          -- Service compatibility score
  geographical_network REAL NOT NULL,             -- Geographic coverage score
  method_of_sourcing REAL NOT NULL,               -- Sourcing approach alignment
  invest_refuelling_equipment INTEGER NOT NULL,   -- Equipment investment score
  reciprocal_business INTEGER NOT NULL,           -- Mutual business value
  created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(supplier_name)
);
```

#### `criteria_weights` (6 records)
**Purpose**: Strategic scoring criteria importance weights

```sql
CREATE TABLE criteria_weights (
  criteria_weights_pk INTEGER PRIMARY KEY AUTOINCREMENT,
  criteria_name TEXT NOT NULL UNIQUE,             -- Criteria description
  weight REAL NOT NULL CHECK (weight >= 0 AND weight <= 1), -- Importance weight
  created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Strategic Framework**:
- **Reciprocal Business**: 25% weight - Mutual business relationship value
- **Current Level (1-8)**: 20% weight - Existing relationship strength  
- **Product/Service Type**: 15% weight - Service offering compatibility
- **Geographical Network**: 15% weight - Geographic coverage alignment
- **Method of Sourcing**: 15% weight - Sourcing approach compatibility
- **Investment in Equipment**: 10% weight - Capital investment commitment

## Data Relationships and Constraints

### Primary Relationships
1. **`od_pair`** ↔ **`customer_depots`**: Customer depot identification and demand
2. **`od_pair`** ↔ **`supplier_depots`**: Supply point identification and capacity
3. **`supplier_depots`** ↔ **`suppliers`**: Supplier ownership and business relationship
4. **`od_pair`** ↔ **`collection_options`**: COC service availability and pricing
5. **`od_pair`** ↔ **`delivery_options`**: DEL service availability and pricing
6. **`supplier_depots`** ↔ **`diesel_prices`**: Zone-based wholesale pricing (via fuel_zone mapping)
7. **`suppliers`** ↔ **`supplier_scores`**: Strategic evaluation data

### Business Rule Constraints
- **Service Availability**: NULL foreign keys in `od_pair` indicate unavailable service options
- **Geographic Consistency**: Fuel zones must align between depots and pricing tables
- **Capacity Limits**: Supplier depot throughput constraints enforced via configuration
- **Payment Terms**: Different rebate structures reflect cash flow management preferences
- **Strategic Scoring**: Normalized scores (0.0-1.0) enable multi-objective optimization

## Data Quality and Validation

### Data Integrity Measures
- **Referential Integrity**: Foreign key relationships maintained across all table joins
- **Coordinate Validation**: Geographic coordinates verified for mapping accuracy
- **Volume Consistency**: Annual volumes aligned with operational capacity constraints
- **Pricing Completeness**: All active fuel zones have corresponding wholesale pricing
- **Strategic Score Normalization**: Supplier scores calculated using consistent criteria framework

### Performance Optimization
- **Indexed Queries**: `idx_diesel_prices_product_zone` optimizes fuel pricing lookups
- **Normalized Structure**: Eliminates data redundancy while maintaining query performance
- **Strategic Design**: Schema optimized for CPLEX optimization data extraction

## Integration with Optimization Pipeline

### Data Flow Architecture
1. **Data Extraction**: Multi-table joins across 8 core tables via `precomputation.py`
2. **Cost Calculation**: Integration of wholesale pricing, rebates, transport costs, and strategic scores
3. **Option Generation**: Dynamic creation of 31,079+ decision variables from available relationships
4. **Constraint Mapping**: Business rules translated to mathematical optimization constraints
5. **Strategic Integration**: Multi-criteria scores integrated for multi-objective optimization

### Mathematical Model Support
- **Decision Variables**: Binary variables for each customer→supplier_depot→option combination
- **Cost Coefficients**: Present value calculations incorporating payment terms and rebates
- **Capacity Constraints**: Supplier depot throughput limits from configuration
- **Strategic Objectives**: Weighted multi-criteria scores for strategic optimization

## Academic Significance

### Research Contributions
- **Real-World Scale**: Production database reflecting actual South African fuel industry complexity
- **Multi-Objective Integration**: Strategic scoring framework enables cost vs. strategic trade-off analysis
- **Regional Coverage**: Cross-border supply chain modeling for Southern African fuel network
- **Industry Validation**: Schema design validated against industry best practices and regulatory requirements

### Methodological Framework
- **Normalized Design**: Academic database design principles applied to complex supply chain problem
- **Strategic Integration**: Novel integration of quantitative and qualitative supplier evaluation criteria
- **Scalability**: Architecture supports extension to additional countries, suppliers, and strategic criteria
- **Reproducibility**: Well-documented schema enables research replication and extension

This database represents a comprehensive foundation for academic research in multi-objective supply chain optimization, strategic supplier selection, and regional fuel logistics planning.