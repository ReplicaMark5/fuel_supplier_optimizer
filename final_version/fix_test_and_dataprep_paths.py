#!/usr/bin/env python3
"""
Post-migration fix script to update:
1. Test file paths to use new data/config and data/databases locations
2. Data preparation script defaults to write to data/databases/
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def fix_test_paths():
    """Update hardcoded paths in test files to new structure"""
    print("\n🔧 Fixing test file paths...")

    test_files = [
        "tests/unit/test_del_simplification.py",
        "tests/unit/test_coc_equipment_costs.py",
        "tests/unit/test_transport_costs.py",
        "tests/unit/test_tier_columns.py",
        "tests/debug/transport_cost_comparison.py",
    ]

    for test_file_rel in test_files:
        test_file = PROJECT_ROOT / test_file_rel
        if not test_file.exists():
            print(f"  ⚠ Skipping {test_file_rel} (not found)")
            continue

        try:
            with open(test_file, 'r') as f:
                content = f.read()

            original_content = content

            # Replace hardcoded config path
            content = re.sub(
                r"config_path\s*=\s*['\"](?:/home/blake/projects/demo5/)?final_version/optimization_config\.json['\"]",
                "config_path=str(Path(__file__).resolve().parents[2] / 'data/config/optimization_config.json')",
                content
            )

            # Replace hardcoded db path
            content = re.sub(
                r"db_path\s*=\s*['\"](?:/home/blake/projects/demo5/)?final_version/fuel_data\.db['\"]",
                "db_path=str(Path(__file__).resolve().parents[2] / 'data/databases/fuel_data.db')",
                content
            )

            # Ensure Path import exists
            if 'Path(__file__)' in content and 'from pathlib import Path' not in content:
                # Add Path import after sys imports
                if 'import sys' in content:
                    content = content.replace('import sys', 'import sys\nfrom pathlib import Path')
                else:
                    # Add at top after docstring
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('from ') or line.startswith('import '):
                            lines.insert(i, 'from pathlib import Path')
                            break
                    content = '\n'.join(lines)

            if content != original_content:
                with open(test_file, 'w') as f:
                    f.write(content)
                print(f"  ✓ Fixed paths in {test_file_rel}")
            else:
                print(f"  • No changes needed in {test_file_rel}")

        except Exception as e:
            print(f"  ❌ Error fixing {test_file_rel}: {e}")


def fix_dataprep_defaults():
    """Update data preparation scripts to use new data/databases location"""
    print("\n🔧 Fixing data preparation script defaults...")

    dataprep_files = [
        ("scripts/data_preparation/create_supplier_tables.py", "db_path", "fuel_data.db"),
        ("scripts/data_preparation/extractors/excel_to_sqlite.py", "db_path", "fuel_data.db"),
        ("scripts/data_preparation/extractors/diesel_price_extractor.py", "DB_PATH", "fuel_data.db"),
    ]

    for file_rel, var_name, old_default in dataprep_files:
        file_path = PROJECT_ROOT / file_rel
        if not file_path.exists():
            print(f"  ⚠ Skipping {file_rel} (not found)")
            continue

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            original_content = content

            # Replace default parameter in function definition
            content = re.sub(
                rf'({var_name}\s*=\s*)["\']fuel_data\.db["\']',
                rf'\1str(Path(__file__).resolve().parents[2] / "data/databases/fuel_data.db")',
                content
            )

            # Replace direct assignment like DB_PATH = "fuel_data.db"
            content = re.sub(
                rf'^({var_name}\s*=\s*)["\']fuel_data\.db["\']',
                rf'\1str(Path(__file__).resolve().parents[2] / "data/databases/fuel_data.db")',
                content,
                flags=re.MULTILINE
            )

            # Ensure Path import exists
            if 'Path(__file__)' in content and 'from pathlib import Path' not in content:
                # Add after other imports
                if 'import pandas as pd' in content:
                    content = content.replace('import pandas as pd', 'import pandas as pd\nfrom pathlib import Path')
                elif 'import sqlite3' in content:
                    content = content.replace('import sqlite3', 'import sqlite3\nfrom pathlib import Path')
                else:
                    # Add at top
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            lines.insert(i, 'from pathlib import Path')
                            break
                    content = '\n'.join(lines)

            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"  ✓ Fixed defaults in {file_rel}")
            else:
                print(f"  • No changes needed in {file_rel}")

        except Exception as e:
            print(f"  ❌ Error fixing {file_rel}: {e}")


def main():
    print("="*60)
    print("POST-MIGRATION PATH FIXES")
    print("="*60)
    print(f"\nProject root: {PROJECT_ROOT}")

    # Fix test paths
    fix_test_paths()

    # Fix data-prep defaults
    fix_dataprep_defaults()

    print("\n" + "="*60)
    print("✅ PATH FIXES COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Run a test: python tests/unit/test_del_simplification.py")
    print("2. Test data-prep: python scripts/data_preparation/create_supplier_tables.py --help")
    print("="*60)


if __name__ == "__main__":
    main()