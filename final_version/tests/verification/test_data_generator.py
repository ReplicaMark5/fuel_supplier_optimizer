#!/usr/bin/env python3
"""
Test Data Generator for Fuel Optimizer Verification

Creates controlled, minimal datasets for testing optimizer logic with predictable outcomes.
Each test scenario generates a complete precomputed_data dictionary and config file.
"""

import json
import sqlite3
import os
from typing import Dict, List, Any, Tuple
from pathlib import Path


class OptimizationTestDataGenerator:
    """Generates controlled test data for fuel optimizer verification."""

    def __init__(self, output_dir: str = "test_scenarios"):
        """Initialize test data generator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def create_test_scenario_1_basic_assignment(self) -> Tuple[Dict[str, Any], str]:
        """
        Test Scenario 1: Basic Assignment Constraint
        - 2 customer depots, 2 supplier depots, obvious cost difference
        - Expected: Both depots choose cheaper supplier
        """
        scenario_name = "scenario_1_basic_assignment"

        # Create test database
        db_path = self.output_dir / f"{scenario_name}.db"
        self._create_basic_test_database(db_path)

        # Create precomputed data
        precomputed_data = {
            'depots': {
                1: {'name': 'Customer Depot A', 'annual_volume': 10000},
                2: {'name': 'Customer Depot B', 'annual_volume': 20000}
            },
            'suppliers': {
                1: {'name': 'Supplier X', 'strategic_score': 0.5},
                2: {'name': 'Supplier Y', 'strategic_score': 0.5}
            },
            'costs': {
                1: {  # Customer depot 1
                    101: {  # Supplier depot 101 (Supplier X)
                        'supplier_id': 1,
                        'supplier_name': 'Supplier X',
                        'distance_km': 100,
                        'strategic_score': 0.5,
                        'coc_cash': 1.0000,    # R1.00/L - cheaper option
                        'coc_30': 1.0200,
                        'del_own': 1.0500
                    },
                    102: {  # Supplier depot 102 (Supplier Y)
                        'supplier_id': 2,
                        'supplier_name': 'Supplier Y',
                        'distance_km': 150,
                        'strategic_score': 0.5,
                        'coc_cash': 2.0000,    # R2.00/L - expensive option
                        'coc_30': 2.0200,
                        'del_own': 2.0500
                    }
                },
                2: {  # Customer depot 2 - same cost structure
                    101: {
                        'supplier_id': 1,
                        'supplier_name': 'Supplier X',
                        'distance_km': 120,
                        'strategic_score': 0.5,
                        'coc_cash': 1.0000,
                        'coc_30': 1.0200,
                        'del_own': 1.0500
                    },
                    102: {
                        'supplier_id': 2,
                        'supplier_name': 'Supplier Y',
                        'distance_km': 180,
                        'strategic_score': 0.5,
                        'coc_cash': 2.0000,
                        'coc_30': 2.0200,
                        'del_own': 2.0500
                    }
                }
            }
        }

        # Create config (no volume tiers, no capacity constraints)
        config = {
            "supplier_contract_configurations": {},
            "supplier_depot_capacity_limits": {},
            "country_allocation_constraints": {"enabled": False}
        }

        config_path = self.output_dir / f"{scenario_name}_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return precomputed_data, str(config_path)

    def create_test_scenario_2_capacity_constraint(self) -> Tuple[Dict[str, Any], str]:
        """
        Test Scenario 2: Capacity Constraint Enforcement
        - Same as scenario 1, but cheaper supplier has limited capacity
        - Expected: Some depots forced to expensive supplier when capacity reached
        """
        scenario_name = "scenario_2_capacity_constraint"

        # Start with scenario 1 data
        precomputed_data, _ = self.create_test_scenario_1_basic_assignment()

        # Create config with capacity constraint
        config = {
            "supplier_contract_configurations": {},
            "supplier_depot_capacity_limits": {
                "101": 15000,  # Supplier X depot can only handle 15,000L (total demand is 30,000L)
                "102": 50000   # Supplier Y depot has plenty of capacity
            },
            "country_allocation_constraints": {"enabled": False}
        }

        config_path = self.output_dir / f"{scenario_name}_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return precomputed_data, str(config_path)

    def create_test_scenario_3_infeasible_capacity(self) -> Tuple[Dict[str, Any], str]:
        """
        Test Scenario 3: Infeasible Capacity
        - Total demand exceeds total capacity
        - Expected: Model should detect infeasibility
        """
        scenario_name = "scenario_3_infeasible_capacity"

        # Start with scenario 1 data
        precomputed_data, _ = self.create_test_scenario_1_basic_assignment()

        # Create config with insufficient total capacity
        config = {
            "supplier_contract_configurations": {},
            "supplier_depot_capacity_limits": {
                "101": 10000,  # Total capacity: 20,000L
                "102": 10000   # Total demand: 30,000L → Infeasible
            },
            "country_allocation_constraints": {"enabled": False}
        }

        config_path = self.output_dir / f"{scenario_name}_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return precomputed_data, str(config_path)

    def create_test_scenario_4_all_units_volume_tier(self) -> Tuple[Dict[str, Any], str]:
        """
        Test Scenario 4: All-Units Volume Tier
        - 1 depot with volume that qualifies for tier discount
        - Expected: Should choose tier option if discount > base cost
        """
        scenario_name = "scenario_4_all_units_tier"

        # Single depot with 30M liter volume to qualify for tier
        precomputed_data = {
            'depots': {
                1: {'name': 'Large Customer Depot', 'annual_volume': 30000000}  # 30M liters
            },
            'suppliers': {
                1: {'name': 'Tier Supplier', 'strategic_score': 0.6}
            },
            'costs': {
                1: {  # Customer depot 1
                    101: {  # Supplier depot 101
                        'supplier_id': 1,
                        'supplier_name': 'Tier Supplier',
                        'distance_km': 100,
                        'strategic_score': 0.6,
                        # Base costs
                        'coc_cash': 1.0000,    # R1.00/L base cost
                        'coc_30': 1.0200,
                        'del_own': 1.0500,
                        # Tier-enhanced costs (25M+ tier with R0.05/L rebate)
                        'coc_cash_tier_25M_plus': 0.9500,   # R0.95/L - should be chosen
                        'coc_30_tier_25M_plus': 0.9700,
                        'del_own_tier_25M_plus': 1.0000
                    }
                }
            }
        }

        # Create config with all-units volume tier
        config = {
            "supplier_contract_configurations": {
                "tier_supplier_contract": {
                    "contract_type": "volume_tier_rewards",
                    "tiering_regime": "all_units",
                    "suppliers": ["Tier Supplier"],
                    "transport_modes": ["COC", "DEL"],
                    "volume_calculation_modes": ["COC", "DEL"],
                    "reward_bands": [
                        {
                            "min_volume": 25000000,  # 25M liter threshold
                            "max_volume": None,
                            "coc_rebate": 0.05,      # R0.05/L rebate
                            "del_rebate": 0.05
                        }
                    ]
                }
            },
            "supplier_depot_capacity_limits": {},
            "country_allocation_constraints": {"enabled": False}
        }

        config_path = self.output_dir / f"{scenario_name}_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return precomputed_data, str(config_path)

    def create_test_scenario_5_below_tier_threshold(self) -> Tuple[Dict[str, Any], str]:
        """
        Test Scenario 5: All-Units Below Threshold
        - Same tier structure as scenario 4, but volume below threshold
        - Expected: Should choose base option (doesn't qualify for tier)
        """
        scenario_name = "scenario_5_below_threshold"

        # Start with scenario 4 structure but reduce volume
        precomputed_data, _ = self.create_test_scenario_4_all_units_volume_tier()
        precomputed_data['depots'][1]['annual_volume'] = 20000000  # 20M liters - below 25M threshold

        # Use same config as scenario 4
        config_path = self.output_dir / f"{scenario_name}_config.json"
        with open(config_path, 'w') as f:
            with open(self.output_dir / "scenario_4_all_units_tier_config.json", 'r') as src:
                config = json.load(src)
            json.dump(config, f, indent=2)

        return precomputed_data, str(config_path)

    def create_test_scenario_6_incremental_tiers(self) -> Tuple[Dict[str, Any], str]:
        """
        Test Scenario 6: Incremental Volume Tier
        - Tests incremental band-splitting logic
        - Expected: Volume should split across bands correctly
        """
        scenario_name = "scenario_6_incremental_tiers"

        # Single depot with 30M liter volume for incremental bands
        precomputed_data = {
            'depots': {
                1: {'name': 'Incremental Customer', 'annual_volume': 30000000}  # 30M liters
            },
            'suppliers': {
                1: {'name': 'Incremental Supplier', 'strategic_score': 0.7}
            },
            'costs': {
                1: {  # Customer depot 1
                    101: {  # Supplier depot 101
                        'supplier_id': 1,
                        'supplier_name': 'Incremental Supplier',
                        'distance_km': 100,
                        'strategic_score': 0.7,
                        # Base costs (for 0-25M band)
                        'coc_cash': 1.0000,    # R1.00/L for base band
                        'coc_30': 1.0200,
                        'del_own': 1.0500,
                        # Tier-enhanced costs for 25M+ band
                        'coc_cash_tier_25M_plus': 0.9000,   # R0.90/L for incremental band
                        'coc_30_tier_25M_plus': 0.9200,
                        'del_own_tier_25M_plus': 0.9500
                    }
                }
            }
        }

        # Create config with incremental volume tier
        config = {
            "supplier_contract_configurations": {
                "incremental_supplier_contract": {
                    "contract_type": "volume_tier_rewards",
                    "tiering_regime": "incremental",
                    "suppliers": ["Incremental Supplier"],
                    "transport_modes": ["COC", "DEL"],
                    "volume_calculation_modes": ["COC", "DEL"],
                    "reward_bands": [
                        {
                            "min_volume": 0,
                            "max_volume": 25000000,  # Base band: 0-25M
                            "coc_rebate": 0.00,      # No rebate for base band
                            "del_rebate": 0.00
                        },
                        {
                            "min_volume": 25000000,  # Incremental band: 25M+
                            "max_volume": None,
                            "coc_rebate": 0.10,      # R0.10/L rebate for incremental
                            "del_rebate": 0.10
                        }
                    ]
                }
            },
            "supplier_depot_capacity_limits": {},
            "country_allocation_constraints": {"enabled": False}
        }

        config_path = self.output_dir / f"{scenario_name}_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return precomputed_data, str(config_path)

    def create_test_scenario_7_multi_objective(self) -> Tuple[Dict[str, Any], str]:
        """
        Test Scenario 7: Multi-Objective Trade-off
        - Cost vs Strategic Score optimization
        - Expected: Different modes should choose different suppliers
        """
        scenario_name = "scenario_7_multi_objective"

        precomputed_data = {
            'depots': {
                1: {'name': 'Trade-off Depot', 'annual_volume': 10000000}  # 10M liters
            },
            'suppliers': {
                1: {'name': 'Cheap Supplier', 'strategic_score': 0.3},     # Low strategic value
                2: {'name': 'Strategic Supplier', 'strategic_score': 0.9}  # High strategic value
            },
            'costs': {
                1: {  # Customer depot 1
                    101: {  # Supplier depot 101 - Cheap
                        'supplier_id': 1,
                        'supplier_name': 'Cheap Supplier',
                        'distance_km': 100,
                        'strategic_score': 0.3,  # Low strategic score
                        'coc_cash': 1.0000,    # R1.00/L - cheaper
                        'coc_30': 1.0200,
                        'del_own': 1.0500
                    },
                    102: {  # Supplier depot 102 - Strategic
                        'supplier_id': 2,
                        'supplier_name': 'Strategic Supplier',
                        'distance_km': 120,
                        'strategic_score': 0.9,  # High strategic score
                        'coc_cash': 1.2000,    # R1.20/L - more expensive
                        'coc_30': 1.2200,
                        'del_own': 1.2500
                    }
                }
            }
        }

        # No special contracts for this test
        config = {
            "supplier_contract_configurations": {},
            "supplier_depot_capacity_limits": {},
            "country_allocation_constraints": {"enabled": False}
        }

        config_path = self.output_dir / f"{scenario_name}_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return precomputed_data, str(config_path)

    def create_test_scenario_8_rac_contract(self) -> Tuple[Dict[str, Any], str]:
        """
        Test Scenario 8: RAC Contract Logic
        - Rebate Adjustment Clause with volume threshold
        - Expected: Above threshold = base cost, below threshold = penalty cost
        """
        scenario_name = "scenario_8_rac_contract"

        precomputed_data = {
            'depots': {
                1: {'name': 'RAC Test Depot', 'annual_volume': 15000000}  # 15M liters - below 20M threshold
            },
            'suppliers': {
                1: {'name': 'RAC Supplier', 'strategic_score': 0.6}
            },
            'costs': {
                1: {  # Customer depot 1
                    101: {  # Supplier depot 101
                        'supplier_id': 1,
                        'supplier_name': 'RAC Supplier',
                        'distance_km': 100,
                        'strategic_score': 0.6,
                        # Base costs (used if commitment met)
                        'coc_cash': 1.0000,    # R1.00/L base cost
                        'coc_30': 1.0200,
                        'del_own': 1.0500,
                        # RAC penalty costs (used if commitment not met)
                        'rac_coc_30': 1.1000,  # R1.10/L penalty cost
                        'rac_del_own': 1.1500
                    }
                }
            }
        }

        # Create config with RAC contract
        config = {
            "supplier_contract_configurations": {
                "rac_supplier_contract": {
                    "contract_type": "rebate_adjustment_clause",
                    "suppliers": ["RAC Supplier"],
                    "transport_modes": ["COC", "DEL"],
                    "volume_calculation_modes": ["COC", "DEL"],
                    "commitment_threshold": 20000000  # 20M liter threshold
                }
            },
            "supplier_depot_capacity_limits": {},
            "country_allocation_constraints": {"enabled": False}
        }

        config_path = self.output_dir / f"{scenario_name}_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return precomputed_data, str(config_path)

    def _create_basic_test_database(self, db_path: Path):
        """Create a minimal test database for scenarios that need it."""
        # Remove existing database
        if db_path.exists():
            os.remove(db_path)

        # Create new database with minimal structure
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create basic tables (minimal structure for testing)
        cursor.execute('''
            CREATE TABLE customer_depots (
                depot_id INTEGER PRIMARY KEY,
                depot_name TEXT,
                annual_volume REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE supplier_depots (
                supplier_depot_id INTEGER PRIMARY KEY,
                supplier_id INTEGER,
                supplier_name TEXT
            )
        ''')

        # Insert test data
        cursor.execute("INSERT INTO customer_depots VALUES (1, 'Customer Depot A', 10000)")
        cursor.execute("INSERT INTO customer_depots VALUES (2, 'Customer Depot B', 20000)")
        cursor.execute("INSERT INTO supplier_depots VALUES (101, 1, 'Supplier X')")
        cursor.execute("INSERT INTO supplier_depots VALUES (102, 2, 'Supplier Y')")

        conn.commit()
        conn.close()

    def get_expected_results(self, scenario_name: str) -> Dict[str, Any]:
        """Return expected results for each test scenario."""
        expected_results = {
            "scenario_1_basic_assignment": {
                "expected_total_cost": 30000.00,  # (10,000 + 20,000) × R1.00
                "expected_allocations": [
                    {"depot_id": 1, "supplier_depot_id": 101, "option": "coc_cash"},
                    {"depot_id": 2, "supplier_depot_id": 101, "option": "coc_cash"}
                ],
                "description": "Both depots should choose cheaper Supplier X"
            },
            "scenario_2_capacity_constraint": {
                "expected_total_cost": 50000.00,  # 10,000×R1.00 + 20,000×R2.00
                "expected_allocations": [
                    {"depot_id": 1, "supplier_depot_id": 101, "option": "coc_cash"},  # First 15k to cheap supplier
                    {"depot_id": 2, "supplier_depot_id": 102, "option": "coc_cash"}   # Forced to expensive supplier
                ],
                "expected_supplier_usage": {
                    101: 10000,  # Depot A volume
                    102: 20000   # Depot B volume
                },
                "description": "Depot A remains with cheap supplier, Depot B forced to expensive due to capacity"
            },
            "scenario_3_infeasible_capacity": {
                "expected_status": "infeasible",
                "description": "Should detect infeasibility due to insufficient total capacity"
            },
            "scenario_4_all_units_tier": {
                "expected_total_cost": 28500000.00,  # 30M × R0.95
                "expected_allocations": [
                    {"depot_id": 1, "supplier_depot_id": 101, "option": "coc_cash_tier_25M_plus"}
                ],
                "active_tiers": ["tier_supplier_contract_25M_plus"],
                "description": "Should choose tier option with R0.05/L savings"
            },
            "scenario_5_below_threshold": {
                "expected_total_cost": 20000000.00,  # 20M × R1.00
                "expected_allocations": [
                    {"depot_id": 1, "supplier_depot_id": 101, "option": "coc_cash"}
                ],
                "active_tiers": [],
                "description": "Should choose base option (doesn't qualify for tier)"
            },
            "scenario_6_incremental_tiers": {
                "expected_total_cost": 29500000.00,  # 25M×R1.00 + 5M×R0.90
                "band_allocations": {
                    "0_to_25M": 25000000,    # Base band gets 25M liters
                    "25M_plus": 5000000      # Incremental band gets 5M liters
                },
                "description": "Volume should split: 25M at base cost + 5M at tier cost"
            },
            "scenario_7_multi_objective": {
                "cost_only": {
                    "expected_supplier": "Cheap Supplier",
                    "expected_cost": 10000000.00  # 10M × R1.00
                },
                "strategic_only": {
                    "expected_supplier": "Strategic Supplier",
                    "expected_strategic_score": 0.9
                },
                "epsilon_constraint_0_8": {
                    "expected_supplier": "Strategic Supplier",  # Only option with score ≥ 0.8
                    "expected_cost": 12000000.00  # 10M × R1.20
                },
                "description": "Different objectives should choose different suppliers"
            },
            "scenario_8_rac_contract": {
                "expected_total_cost": 16500000.00,  # 15M × R1.10 (penalty cost)
                "expected_allocations": [
                    {"depot_id": 1, "supplier_depot_id": 101, "option": "rac_coc_30"}
                ],
                "rac_status": "below_threshold",
                "description": "Below 20M threshold, should use RAC penalty cost"
            }
        }

        return expected_results.get(scenario_name, {})


def main():
    """Generate all test scenarios."""
    print("Generating test data for fuel optimizer verification...")

    generator = OptimizationTestDataGenerator()

    scenarios = [
        ("Basic Assignment", generator.create_test_scenario_1_basic_assignment),
        ("Capacity Constraint", generator.create_test_scenario_2_capacity_constraint),
        ("Infeasible Capacity", generator.create_test_scenario_3_infeasible_capacity),
        ("All-Units Volume Tier", generator.create_test_scenario_4_all_units_volume_tier),
        ("Below Tier Threshold", generator.create_test_scenario_5_below_tier_threshold),
        ("Incremental Tiers", generator.create_test_scenario_6_incremental_tiers),
        ("Multi-Objective", generator.create_test_scenario_7_multi_objective),
        ("RAC Contract", generator.create_test_scenario_8_rac_contract)
    ]

    print(f"\nGenerated test scenarios in: {generator.output_dir}")
    for name, scenario_func in scenarios:
        try:
            precomputed_data, config_path = scenario_func()
            expected = generator.get_expected_results(scenario_func.__name__.replace("create_test_", ""))
            print(f"✅ {name}: {len(precomputed_data['costs'])} depots, {len(precomputed_data['suppliers'])} suppliers")
            if expected:
                print(f"   Expected: {expected.get('description', 'No description')}")
        except Exception as e:
            print(f"❌ {name}: Error - {e}")

    print(f"\nTest data generation complete!")


if __name__ == "__main__":
    main()
