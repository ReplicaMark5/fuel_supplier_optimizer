# Fuel Zone Data Extraction Documentation

## Overview

This document describes the fuel zone data extraction methodology used to convert South African fuel pricing PDF documents into structured, machine-readable data. The system processes PDF-extracted text containing magisterial district fuel zone assignments, transforming unstructured regulatory documents into structured CSV format for spatial analysis and supply chain optimization.

## Primary Objective

The extraction methodology addresses the challenge of converting **regulatory PDF documents** containing fuel zone pricing information into **structured datasets** suitable for:

1. **Supply Chain Cost Modeling**: Integration of location-specific fuel costs into transportation optimization models
2. **Spatial Analysis**: Geographic visualization and analysis of fuel pricing zones across South Africa
3. **Data Integration**: Compatibility with GIS systems and optimization frameworks
4. **Research Applications**: Quantitative analysis of fuel cost impacts on logistics networks

### PDF-to-Data Conversion Pipeline

The methodology implements a two-stage conversion process:

#### Stage 1: PDF Text Extraction
- **Source**: Official South African fuel zone regulation PDFs
- **Output**: Semi-structured text file (`Fuel Zone Magisterial district Magi.txt`)
- **Challenges**: OCR artifacts, formatting inconsistencies, embedded tables

#### Stage 2: Text-to-CSV Structuring  
- **Input**: Extracted text with irregular formatting
- **Processing**: Pattern recognition and field parsing
- **Output**: Clean, structured CSV with standardized columns
- **Validation**: Data quality assurance and deduplication

## Fundamental Implementation Approach

### Data Structure Recognition
The system processes semi-structured text data containing fuel zone assignments with the pattern:
```
<Zone_Code> <District_Name> <Magisterial_Code> <Province>
```

Example: `09B Cape Town 501 Western Cape`

### Core Parsing Components

#### 1. Fuel Zone Pattern Recognition
Implements pattern matching for South African fuel zone codes:
```python
def looks_like_fuel_zone(token):
    # Pattern: two digits + one uppercase letter (e.g., 09B, 33J, 67C)
    return token[:2].isdigit() and token[2:].isalpha() and token[2:].isupper()
```

#### 2. Provincial Boundary Detection
Handles multi-word province names through hierarchical matching:
```python
PROVINCES = {
    "Eastern Cape", "Western Cape", "Northern Cape",
    "KwaZulu Natal", "Free State", "North West",
    "Mpumalanga", "Gauteng", "Limpopo"
}
```

#### 3. Structured Data Extraction
Parses variable-length district names by working backwards from province identification:
- **Zone Code**: First token (validated pattern)
- **Province**: Last token(s) (matched against known provinces)
- **Magisterial Code**: Token immediately before province
- **District Name**: Remaining middle tokens joined

### Processing Workflow

1. **Text Ingestion**: Read unstructured fuel zone text file
2. **Line Filtering**: Remove headers and invalid entries
3. **Token Analysis**: Split lines into components for parsing
4. **Pattern Matching**: Validate fuel zone codes and province names
5. **Data Extraction**: Extract structured fields using positional logic
6. **Deduplication**: Remove duplicate entries using composite keys
7. **CSV Export**: Generate structured output for further analysis

## Theoretical Foundation

### Administrative Geography Theory

#### Territorial Hierarchies
The fuel zone system implements a nested administrative hierarchy:
- **National Level**: South African fuel pricing regulation
- **Provincial Level**: Nine provincial boundaries
- **Magisterial Level**: Local administrative districts
- **Zone Level**: Fuel pricing regions within districts

#### Spatial Data Standardization
The extraction process supports **spatial data interoperability** by:
- Standardizing administrative boundary names
- Maintaining consistent geographic identifiers
- Enabling cross-referencing with other spatial datasets

### Text Processing and Data Mining

#### Semi-Structured Data Parsing
The methodology addresses challenges in **semi-structured data extraction**:
- **Variable Field Lengths**: District names with inconsistent word counts
- **Delimiter Ambiguity**: Space-separated fields with multi-word values
- **Format Inconsistencies**: Mixed data quality and formatting variations

#### Pattern Recognition Algorithms
Implements rule-based parsing using:
- **Regular Expressions**: Pattern matching for zone codes
- **Lexical Analysis**: Token-based field identification
- **Contextual Validation**: Province-based boundary checking

### Geographic Information Systems Integration

#### Administrative Boundary Coding
The fuel zone system provides:
- **Unique Identifiers**: Zone codes for spatial joining
- **Hierarchical References**: Province-district relationships
- **Administrative Lookup**: District name standardization

#### Spatial Data Preparation
Extracted data enables:
- **Choropleth Mapping**: Fuel price visualization by zone
- **Spatial Analysis**: Regional pricing pattern identification
- **Geographic Queries**: Location-based zone assignment

## Data Quality Assurance

### Validation Mechanisms
- **Pattern Validation**: Fuel zone code format verification
- **Reference Checking**: Province name validation against master list
- **Completeness Testing**: Required field presence validation
- **Duplicate Detection**: Composite key deduplication

### Error Handling Strategies
- **Malformed Entries**: Skip lines with invalid zone codes
- **Missing Provinces**: Reject records without valid provincial assignment
- **Encoding Issues**: UTF-8 with error tolerance for text processing
- **Header Contamination**: Automatic header line detection and removal

## Practical Applications

### Fuel Pricing Analysis
The structured fuel zone data supports:
- **Regional Price Modeling**: Zone-based fuel cost analysis
- **Transportation Cost Calculation**: Distance-weighted fuel pricing
- **Supply Chain Optimization**: Fuel cost integration in routing models

### Administrative Analysis
- **Policy Impact Assessment**: Fuel zone boundary effects
- **Market Segmentation**: Geographic pricing region analysis
- **Regulatory Compliance**: Zone-based pricing validation

## Integration with Supply Chain Models

### Transportation Cost Modeling
Fuel zones enable precise transportation cost calculation:
```
Fuel_Cost_per_km = Base_Fuel_Price[Zone] × Vehicle_Consumption_Rate
```

### Route Optimization Enhancement
Zone-based fuel pricing improves:
- **Multi-Zone Route Planning**: Dynamic fuel cost consideration
- **Cost-Optimal Routing**: Fuel price-aware path selection
- **Supply Chain Network Design**: Zone-aware facility location

### Operational Decision Support
- **Fleet Management**: Zone-based fuel budgeting
- **Strategic Planning**: Fuel cost impact on network design
- **Risk Assessment**: Fuel price volatility by region

## Output Specifications

### CSV Structure
The extraction produces standardized CSV output:
```csv
Fuel Zone,Magisterial district,Magisterial code,Province
09B,Cape Town,501,Western Cape
33J,Johannesburg,644,Gauteng
```

### Data Quality Metrics
- **Extraction Rate**: Percentage of successfully parsed lines
- **Validation Rate**: Proportion of records passing validation
- **Completeness**: Coverage across all provinces and districts

## Technical Considerations

### Scalability
- **Memory Efficiency**: Streaming text processing
- **Processing Speed**: Linear time complexity O(n)
- **Storage Optimization**: Minimal memory footprint

### Maintenance Requirements
- **Province Updates**: Accommodate administrative boundary changes
- **Zone Modifications**: Handle fuel zone redistricting
- **Format Evolution**: Adapt to source data format changes

## Integration Value

This fuel zone extraction methodology serves as a **foundational data preparation component** for supply chain research, providing:

1. **Geographic Granularity**: Fine-grained spatial fuel pricing data
2. **Administrative Alignment**: Consistency with official boundaries
3. **Cost Model Integration**: Direct input for transportation cost calculations
4. **Spatial Analysis Foundation**: Enables zone-based geographic analysis

The structured fuel zone data ensures that supply chain optimization models incorporate realistic, location-specific fuel costs, enhancing the practical applicability of research findings in South African logistics operations.