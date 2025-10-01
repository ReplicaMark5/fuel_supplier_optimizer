#!/usr/bin/env python3
"""
Fuel Optimizer Verification Suite

Comprehensive verification testing for the CPLEX fuel optimizer using controlled test scenarios
to validate mathematical correctness and business logic implementation.
"""

import sys
import os
import logging
import json
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import traceback

# Add parent directory to path to import fuel optimizer
sys.path.append(str(Path(__file__).parent.parent))

from src.fuel_optimizer_docplex import FuelDepotOptimizerDocplex
from test_data_generator import OptimizationTestDataGenerator

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Suppress optimizer info logs during testing
logger = logging.getLogger(__name__)


class OptimizerVerificationSuite:
    """Comprehensive verification testing for the fuel optimizer."""

    def __init__(self, output_dir: str = "verification_results"):
        """Initialize verification suite."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.generator = OptimizationTestDataGenerator("test_scenarios")
        self.test_results = []

    def run_all_verification_tests(self) -> Dict[str, Any]:
        """Run complete verification test suite."""
        print("🧪 FUEL OPTIMIZER VERIFICATION SUITE")
        print("=" * 50)

        # Test scenarios to run
        test_scenarios = [
            ("Basic Assignment Constraint", self._test_basic_assignment),
            ("Capacity Constraint Enforcement", self._test_capacity_constraints),
            ("Infeasible Capacity Detection", self._test_infeasible_capacity),
            ("All-Units Volume Tier Logic", self._test_all_units_volume_tier),
            ("Below Tier Threshold Logic", self._test_below_tier_threshold),
            ("Incremental Volume Tier Logic", self._test_incremental_volume_tier),
            ("Multi-Objective Functionality", self._test_multi_objective),
            ("RAC Contract Logic", self._test_rac_contract),
            ("Cost Calculation Validation", self._test_cost_calculations)
        ]

        # Run all tests
        passed_tests = 0
        total_tests = len(test_scenarios)

        for test_name, test_func in test_scenarios:
            print(f"\n🔍 Testing: {test_name}")
            print("-" * 40)

            try:
                result = test_func()
                if result['passed']:
                    print(f"✅ PASSED: {result['summary']}")
                    passed_tests += 1
                else:
                    print(f"❌ FAILED: {result['summary']}")
                    if result.get('details'):
                        for detail in result['details']:
                            print(f"   - {detail}")

                self.test_results.append({
                    'test_name': test_name,
                    'passed': result['passed'],
                    'result': result
                })

            except Exception as e:
                print(f"💥 ERROR: {test_name} crashed - {str(e)}")
                print(f"   {traceback.format_exc()}")
                self.test_results.append({
                    'test_name': test_name,
                    'passed': False,
                    'result': {'error': str(e), 'traceback': traceback.format_exc()}
                })

        # Summary
        print(f"\n📊 VERIFICATION SUMMARY")
        print("=" * 50)
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED - Optimizer verification successful!")
        else:
            print("⚠️  Some tests failed - Review results above")

        # Save detailed results
        self._save_verification_report()

        return {
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'all_passed': passed_tests == total_tests,
            'test_results': self.test_results
        }

    def _test_basic_assignment(self) -> Dict[str, Any]:
        """Test basic assignment constraint logic."""
        precomputed_data, config_path = self.generator.create_test_scenario_1_basic_assignment()
        expected = self.generator.get_expected_results("scenario_1_basic_assignment")

        # Run optimization
        optimizer = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        results = optimizer.run_optimization()

        # Verify results
        passed = True
        details = []

        if results['status'] != 'optimal':
            passed = False
            details.append(f"Expected optimal solution, got: {results['status']}")

        # Check cost within tolerance
        if abs(results.get('total_annual_cost', 0) - expected['expected_total_cost']) > 0.01:
            passed = False
            details.append(f"Cost mismatch: expected R{expected['expected_total_cost']:.2f}, got R{results.get('total_annual_cost', 0):.2f}")

        # Check allocations against expectations (supplier + option type)
        expected_allocations = expected.get('expected_allocations', [])
        actual_allocations = results.get('allocations', [])

        if len(actual_allocations) != len(expected_allocations):
            passed = False
            details.append(f"Expected {len(expected_allocations)} allocations, got {len(actual_allocations)}")

        actual_by_depot = {alloc['customer_depot_id']: alloc for alloc in actual_allocations}

        depot_allocation_counts = {}
        for alloc in actual_allocations:
            depot_id = alloc['customer_depot_id']
            depot_allocation_counts[depot_id] = depot_allocation_counts.get(depot_id, 0) + 1

        for expected_alloc in expected_allocations:
            depot_id = expected_alloc['depot_id']
            actual = actual_by_depot.get(depot_id)
            if not actual:
                passed = False
                details.append(f"Depot {depot_id} missing allocation")
                continue

            if actual['supplier_depot_id'] != expected_alloc['supplier_depot_id']:
                passed = False
                details.append(
                    f"Depot {depot_id}: expected supplier depot {expected_alloc['supplier_depot_id']}, "
                    f"got {actual['supplier_depot_id']}"
                )

            if actual['option_type'] != expected_alloc['option']:
                passed = False
                details.append(
                    f"Depot {depot_id}: expected option {expected_alloc['option']}, got {actual['option_type']}"
                )

        # Check for multiple allocations per depot
        for depot_id, count in depot_allocation_counts.items():
            if count != 1:
                passed = False
                details.append(f"Depot {depot_id} has {count} allocations, expected exactly 1")

        return {
            'passed': passed,
            'summary': f"Basic assignment working correctly" if passed else "Assignment constraint violations detected",
            'details': details,
            'actual_cost': results.get('total_annual_cost'),
            'expected_cost': expected['expected_total_cost']
        }

    def _test_capacity_constraints(self) -> Dict[str, Any]:
        """Test capacity constraint enforcement."""
        precomputed_data, config_path = self.generator.create_test_scenario_2_capacity_constraint()
        expected = self.generator.get_expected_results("scenario_2_capacity_constraint")

        # Run optimization
        optimizer = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        results = optimizer.run_optimization()

        # Verify results
        passed = True
        details = []

        if results['status'] != 'optimal':
            passed = False
            details.append(f"Expected optimal solution, got: {results['status']}")

        expected_allocations = expected.get('expected_allocations', [])
        actual_allocations = results.get('allocations', [])

        if len(actual_allocations) != len(expected_allocations):
            passed = False
            details.append(f"Expected {len(expected_allocations)} allocations, got {len(actual_allocations)}")

        actual_by_depot = {alloc['customer_depot_id']: alloc for alloc in actual_allocations}

        for expected_alloc in expected_allocations:
            depot_id = expected_alloc['depot_id']
            actual = actual_by_depot.get(depot_id)
            if not actual:
                passed = False
                details.append(f"Depot {depot_id} missing allocation")
                continue

            if actual['supplier_depot_id'] != expected_alloc['supplier_depot_id']:
                passed = False
                details.append(
                    f"Depot {depot_id}: expected supplier depot {expected_alloc['supplier_depot_id']}, "
                    f"got {actual['supplier_depot_id']}"
                )

            if actual['option_type'] != expected_alloc['option']:
                passed = False
                details.append(
                    f"Depot {depot_id}: expected option {expected_alloc['option']}, got {actual['option_type']}"
                )

        # Verify supplier usage matches expectation (within tolerance)
        expected_usage = expected.get('expected_supplier_usage', {})
        utilization = results.get('supplier_depot_utilization', {})
        for supplier_id, expected_volume in expected_usage.items():
            actual_volume = utilization.get(supplier_id, {}).get('used_volume')
            if actual_volume is None:
                passed = False
                details.append(f"Supplier depot {supplier_id} usage missing in results")
            elif abs(actual_volume - expected_volume) > 1e-3:
                passed = False
                details.append(
                    f"Supplier depot {supplier_id}: expected {expected_volume:.0f}L, got {actual_volume:.0f}L"
                )

        # Validate total cost
        expected_cost = expected.get('expected_total_cost')
        actual_cost = results.get('total_annual_cost', 0)
        if expected_cost is not None and abs(actual_cost - expected_cost) > 0.01:
            passed = False
            details.append(f"Cost mismatch: expected R{expected_cost:,.2f}, got R{actual_cost:,.2f}")

        return {
            'passed': passed,
            'summary': f"Capacity constraints enforced correctly" if passed else "Capacity constraint violations",
            'details': details,
            'utilization': utilization,
            'actual_cost': actual_cost,
            'expected_cost': expected.get('expected_total_cost')
        }

    def _test_infeasible_capacity(self) -> Dict[str, Any]:
        """Test infeasible capacity detection."""
        precomputed_data, config_path = self.generator.create_test_scenario_3_infeasible_capacity()

        # Run optimization
        optimizer = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        results = optimizer.run_optimization()

        # Verify results
        passed = True
        details = []

        # Should detect infeasibility
        if results['status'] == 'optimal':
            passed = False
            details.append(f"Expected infeasible solution due to insufficient capacity, got optimal")

        # Should be infeasible or no solution
        if results['status'] not in ['no_solution', 'infeasible']:
            passed = False
            details.append(f"Expected 'no_solution' or 'infeasible' status, got: {results['status']}")

        return {
            'passed': passed,
            'summary': f"Infeasibility detected correctly" if passed else "Failed to detect infeasible problem",
            'details': details,
            'status': results['status']
        }

    def _test_all_units_volume_tier(self) -> Dict[str, Any]:
        """Test all-units volume tier logic."""
        precomputed_data, config_path = self.generator.create_test_scenario_4_all_units_volume_tier()
        expected = self.generator.get_expected_results("scenario_4_all_units_tier")

        # Run optimization
        optimizer = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        results = optimizer.run_optimization()

        # Verify results
        passed = True
        details = []

        if results['status'] != 'optimal':
            passed = False
            details.append(f"Expected optimal solution, got: {results['status']}")

        # Should choose tier option (cheaper)
        allocations = results.get('allocations', [])
        if not allocations:
            passed = False
            details.append("No allocations found")
        else:
            chosen_option = allocations[0]['option_type']
            if 'tier_' not in chosen_option:
                passed = False
                details.append(f"Expected tier option, got: {chosen_option}")

        # Check cost matches tier cost
        if abs(results.get('total_annual_cost', 0) - expected['expected_total_cost']) > 1000:
            passed = False
            details.append(f"Cost mismatch: expected R{expected['expected_total_cost']:,.2f}, got R{results.get('total_annual_cost', 0):,.2f}")

        # Check active tiers
        active_tiers = results.get('active_tiers', [])
        if not active_tiers:
            passed = False
            details.append("No active tiers found, expected tier activation")

        return {
            'passed': passed,
            'summary': f"All-units tier logic working correctly" if passed else "All-units tier logic failed",
            'details': details,
            'chosen_option': allocations[0]['option_type'] if allocations else None,
            'active_tiers': active_tiers
        }

    def _test_below_tier_threshold(self) -> Dict[str, Any]:
        """Test below tier threshold logic."""
        precomputed_data, config_path = self.generator.create_test_scenario_5_below_tier_threshold()
        expected = self.generator.get_expected_results("scenario_5_below_threshold")

        # Run optimization
        optimizer = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        results = optimizer.run_optimization()

        # Verify results
        passed = True
        details = []

        if results['status'] != 'optimal':
            passed = False
            details.append(f"Expected optimal solution, got: {results['status']}")

        # Should choose base option (doesn't qualify for tier)
        allocations = results.get('allocations', [])
        if not allocations:
            passed = False
            details.append("No allocations found")
        else:
            chosen_option = allocations[0]['option_type']
            if 'tier_' in chosen_option:
                passed = False
                details.append(f"Expected base option (below threshold), got tier option: {chosen_option}")

        # Check no active tiers
        active_tiers = results.get('active_tiers', [])
        if active_tiers:
            passed = False
            details.append(f"Expected no active tiers (below threshold), got: {active_tiers}")

        return {
            'passed': passed,
            'summary': f"Below threshold logic working correctly" if passed else "Below threshold logic failed",
            'details': details,
            'chosen_option': allocations[0]['option_type'] if allocations else None
        }

    def _test_incremental_volume_tier(self) -> Dict[str, Any]:
        """Test incremental volume tier logic."""
        precomputed_data, config_path = self.generator.create_test_scenario_6_incremental_tiers()
        expected = self.generator.get_expected_results("scenario_6_incremental_tiers")

        # Run optimization
        optimizer = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        results = optimizer.run_optimization()

        # Verify results
        passed = True
        details = []

        if results['status'] != 'optimal':
            passed = False
            details.append(f"Expected optimal solution, got: {results['status']}")

        # Check cost is between all-base and all-tier costs
        expected_cost = expected['expected_total_cost']
        actual_cost = results.get('total_annual_cost', 0)

        # Allow 1% tolerance for incremental cost calculations
        if abs(actual_cost - expected_cost) > expected_cost * 0.01:
            passed = False
            details.append(f"Cost mismatch: expected R{expected_cost:,.2f}, got R{actual_cost:,.2f}")

        # Ensure band allocations match expectations
        band_details = results.get('band_volume_details', {})
        option_band_details = band_details.get('1_101_coc_cash')

        if option_band_details is None:
            passed = False
            details.append("Missing band allocation details for incremental option")
        else:
            expected_bands = expected.get('band_allocations', {})
            for band_name, expected_volume in expected_bands.items():
                actual_volume = option_band_details.get(band_name)
                if actual_volume is None or abs(actual_volume - expected_volume) > 1.0:  # 1 litre tolerance
                    passed = False
                    details.append(
                        f"Band {band_name}: expected {expected_volume:,.0f}L, "
                        f"got {0 if actual_volume is None else actual_volume:,.0f}L"
                    )

            # Ensure no unexpected volume appears in other bands
            actual_total = sum(option_band_details.values())
            expected_total = sum(expected_bands.values())
            if abs(actual_total - expected_total) > 1.0:
                passed = False
                details.append(
                    f"Total band volume mismatch: expected {expected_total:,.0f}L, got {actual_total:,.0f}L"
                )

        return {
            'passed': passed,
            'summary': f"Incremental tier logic working correctly" if passed else "Incremental tier logic failed",
            'details': details,
            'expected_cost': expected_cost,
            'actual_cost': actual_cost,
            'band_allocations': option_band_details
        }

    def _test_multi_objective(self) -> Dict[str, Any]:
        """Test multi-objective functionality."""
        precomputed_data, config_path = self.generator.create_test_scenario_7_multi_objective()
        expected = self.generator.get_expected_results("scenario_7_multi_objective")

        passed = True
        details = []

        # Test cost-only mode
        optimizer_cost = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        optimizer_cost.prepare_data().create_decision_variables()
        optimizer_cost.set_objective(objective_mode="cost_only")
        optimizer_cost.add_constraints()
        results_cost = optimizer_cost.solve()

        if results_cost['status'] == 'optimal':
            cost_supplier = results_cost['allocations'][0]['supplier_name']
            if cost_supplier != expected['cost_only']['expected_supplier']:
                passed = False
                details.append(f"Cost-only mode: expected {expected['cost_only']['expected_supplier']}, got {cost_supplier}")
        else:
            passed = False
            details.append(f"Cost-only mode failed: {results_cost['status']}")

        # Test strategic-only mode
        optimizer_strategic = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        optimizer_strategic.prepare_data().create_decision_variables()
        optimizer_strategic.set_objective(objective_mode="strategic_only")
        optimizer_strategic.add_constraints()
        results_strategic = optimizer_strategic.solve()

        if results_strategic['status'] == 'optimal':
            strategic_supplier = results_strategic['allocations'][0]['supplier_name']
            if strategic_supplier != expected['strategic_only']['expected_supplier']:
                passed = False
                details.append(f"Strategic-only mode: expected {expected['strategic_only']['expected_supplier']}, got {strategic_supplier}")
        else:
            passed = False
            details.append(f"Strategic-only mode failed: {results_strategic['status']}")

        # Test epsilon-constraint mode
        optimizer_epsilon = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        optimizer_epsilon.prepare_data().create_decision_variables()
        optimizer_epsilon.set_objective(objective_mode="epsilon_constraint", strategic_constraint=0.8)
        optimizer_epsilon.add_constraints()
        results_epsilon = optimizer_epsilon.solve()

        if results_epsilon['status'] == 'optimal':
            epsilon_supplier = results_epsilon['allocations'][0]['supplier_name']
            if epsilon_supplier != expected['epsilon_constraint_0_8']['expected_supplier']:
                passed = False
                details.append(f"ε-constraint mode: expected {expected['epsilon_constraint_0_8']['expected_supplier']}, got {epsilon_supplier}")
        else:
            passed = False
            details.append(f"ε-constraint mode failed: {results_epsilon['status']}")

        return {
            'passed': passed,
            'summary': f"Multi-objective functionality working correctly" if passed else "Multi-objective functionality failed",
            'details': details,
            'cost_mode_result': cost_supplier if results_cost['status'] == 'optimal' else results_cost['status'],
            'strategic_mode_result': strategic_supplier if results_strategic['status'] == 'optimal' else results_strategic['status'],
            'epsilon_mode_result': epsilon_supplier if results_epsilon['status'] == 'optimal' else results_epsilon['status']
        }

    def _test_rac_contract(self) -> Dict[str, Any]:
        """Test RAC contract logic."""
        precomputed_data, config_path = self.generator.create_test_scenario_8_rac_contract()
        expected = self.generator.get_expected_results("scenario_8_rac_contract")

        # Run optimization
        optimizer = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        results = optimizer.run_optimization()

        # Verify results
        passed = True
        details = []

        if results['status'] != 'optimal':
            passed = False
            details.append(f"Expected optimal solution, got: {results['status']}")

        # Should choose RAC penalty option (below threshold)
        allocations = results.get('allocations', [])
        if not allocations:
            passed = False
            details.append("No allocations found")
        else:
            chosen_option = allocations[0]['option_type']
            if not chosen_option.startswith('rac_'):
                passed = False
                details.append(f"Expected RAC option (below threshold), got: {chosen_option}")

        # Check cost matches penalty cost
        expected_cost = expected['expected_total_cost']
        actual_cost = results.get('total_annual_cost', 0)
        if abs(actual_cost - expected_cost) > 100:
            passed = False
            details.append(f"Cost mismatch: expected R{expected_cost:,.2f}, got R{actual_cost:,.2f}")

        return {
            'passed': passed,
            'summary': f"RAC contract logic working correctly" if passed else "RAC contract logic failed",
            'details': details,
            'chosen_option': allocations[0]['option_type'] if allocations else None
        }

    def _test_cost_calculations(self) -> Dict[str, Any]:
        """Test cost calculation accuracy."""
        precomputed_data, config_path = self.generator.create_test_scenario_1_basic_assignment()

        # Run optimization
        optimizer = FuelDepotOptimizerDocplex(precomputed_data, config_path)
        results = optimizer.run_optimization()

        # Verify results
        passed = True
        details = []

        if results['status'] != 'optimal':
            passed = False
            details.append(f"Expected optimal solution, got: {results['status']}")
            return {'passed': passed, 'summary': 'Optimization failed', 'details': details}

        # Manual cost calculation verification
        manual_total_cost = 0
        for allocation in results.get('allocations', []):
            depot_volume = allocation['annual_volume']
            cost_per_litre = allocation['cost_per_litre']
            calculated_cost = depot_volume * cost_per_litre

            if abs(calculated_cost - allocation['total_cost']) > 0.01:
                passed = False
                details.append(f"Cost calculation error for depot {allocation['customer_depot_id']}: "
                             f"expected R{calculated_cost:.2f}, got R{allocation['total_cost']:.2f}")

            manual_total_cost += calculated_cost

        # Compare manual total with optimizer total
        optimizer_total = results.get('total_annual_cost', 0)
        if abs(manual_total_cost - optimizer_total) > 0.01:
            passed = False
            details.append(f"Total cost mismatch: manual R{manual_total_cost:.2f}, optimizer R{optimizer_total:.2f}")

        return {
            'passed': passed,
            'summary': f"Cost calculations accurate" if passed else "Cost calculation errors detected",
            'details': details,
            'manual_total': manual_total_cost,
            'optimizer_total': optimizer_total
        }

    def _save_verification_report(self):
        """Save detailed verification report."""
        report_path = self.output_dir / "verification_report.json"

        report = {
            'verification_suite': 'Fuel Optimizer Verification',
            'timestamp': str(Path().cwd()),
            'summary': {
                'total_tests': len(self.test_results),
                'passed_tests': sum(1 for t in self.test_results if t['passed']),
                'failed_tests': sum(1 for t in self.test_results if not t['passed']),
                'success_rate': (sum(1 for t in self.test_results if t['passed']) / len(self.test_results)) * 100 if self.test_results else 0
            },
            'test_results': self.test_results
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Detailed verification report saved: {report_path}")


def main():
    """Run fuel optimizer verification suite."""
    print("Starting Fuel Optimizer Verification Suite...")

    # Create and run verification suite
    suite = OptimizerVerificationSuite()
    results = suite.run_all_verification_tests()

    # Exit with appropriate code
    exit_code = 0 if results['all_passed'] else 1

    print(f"\nVerification complete. Exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
