#!/usr/bin/env python3
"""
Migration script to restructure the final_version project.

This script will:
1. Create new directory structure
2. Move all files to new locations
3. Update imports in Python files
4. Update output paths in scripts
5. Create __init__.py files
6. Update .gitignore
7. Generate migration report

Run with: python restructure_migration.py
"""

import os
import shutil
import re
from pathlib import Path
from datetime import datetime
import json

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = PROJECT_ROOT / f"backup_before_restructure_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Migration tracking
migration_log = {
    "timestamp": datetime.now().isoformat(),
    "moves": [],
    "updates": [],
    "errors": []
}


def log_move(source, destination, status="success"):
    """Log a file move operation"""
    migration_log["moves"].append({
        "source": str(source),
        "destination": str(destination),
        "status": status
    })


def log_update(file_path, update_type, details):
    """Log a file update operation"""
    migration_log["updates"].append({
        "file": str(file_path),
        "type": update_type,
        "details": details
    })


def log_error(operation, error):
    """Log an error"""
    migration_log["errors"].append({
        "operation": operation,
        "error": str(error)
    })


def create_backup():
    """Create backup of current state"""
    print(f"\n📦 Creating backup at {BACKUP_DIR}...")
    try:
        BACKUP_DIR.mkdir(exist_ok=True)

        # Backup all files and directories (except venv, .git, __pycache__)
        for item in PROJECT_ROOT.iterdir():
            if item.name in ['venv', '.git', '__pycache__', '.claude', '.context-sync'] or item.name.startswith('backup_'):
                continue

            dest = BACKUP_DIR / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

        print(f"✅ Backup created successfully")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        log_error("create_backup", e)
        return False


def create_directory_structure():
    """Create new directory structure"""
    print("\n📁 Creating new directory structure...")

    directories = [
        "src",
        "src/visualization",
        "scripts/data_preparation/extractors",
        "scripts/export",
        "tools",
        "tests/unit",
        "tests/debug",
        "tests/verification/test_scenarios",
        "tests/verification/verification_results",
        "data/databases",
        "data/config",
        "outputs/optimization_results",
        "outputs/visualizations",
        "outputs/thesis_exports",
        "docs/input_specs",
        "docs/output_specs/data_prep_docs",
        "docs/personal_notes",
        "docs/verification_research",
        "docs/chapters_copy",
        "archive/delete"
    ]

    for directory in directories:
        dir_path = PROJECT_ROOT / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created {directory}")

    log_update("directory_structure", "created", {"directories": directories})


def move_file(source, destination):
    """Safely move a file"""
    try:
        source_path = PROJECT_ROOT / source
        dest_path = PROJECT_ROOT / destination

        if not source_path.exists():
            print(f"  ⚠ Skipping {source} (not found)")
            log_move(source, destination, "skipped_not_found")
            return False

        # Create parent directory if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(source_path), str(dest_path))
        print(f"  ✓ Moved {source} → {destination}")
        log_move(source, destination, "success")
        return True
    except Exception as e:
        print(f"  ❌ Error moving {source}: {e}")
        log_error(f"move_file: {source}", e)
        return False


def move_all_files():
    """Move all files to new locations"""
    print("\n📦 Moving files to new locations...")

    # Define all file movements
    moves = [
        # Core src files
        ("fuel_optimizer_docplex.py", "src/fuel_optimizer_docplex.py"),
        ("precomputation.py", "src/precomputation.py"),
        ("pareto_front_generator.py", "src/pareto_front_generator.py"),
        ("strategic_supplier_scoring.py", "src/strategic_supplier_scoring.py"),

        # Scripts - data preparation
        ("create_supplier_tables.py", "scripts/data_preparation/create_supplier_tables.py"),
        ("extractors/diesel_price_extractor.py", "scripts/data_preparation/extractors/diesel_price_extractor.py"),
        ("extractors/excel_to_sqlite.py", "scripts/data_preparation/extractors/excel_to_sqlite.py"),

        # Scripts - export
        ("export_costs.py", "scripts/export/export_costs.py"),
        ("export_baseline_summaries.py", "scripts/export/export_baseline_summaries.py"),

        # Visualization (kept importable by core under src)
        ("optimization_map.py", "src/visualization/optimization_map.py"),

        # Tests - unit
        ("test_debug/test_volume_tiers.py", "tests/unit/test_volume_tiers.py"),
        ("test_debug/test_transport_costs.py", "tests/unit/test_transport_costs.py"),
        ("test_debug/test_coc_equipment_costs.py", "tests/unit/test_coc_equipment_costs.py"),
        ("test_debug/test_del_simplification.py", "tests/unit/test_del_simplification.py"),
        ("test_debug/test_indicators_refactor.py", "tests/unit/test_indicators_refactor.py"),
        ("test_debug/test_tier_columns.py", "tests/unit/test_tier_columns.py"),
        ("test_debug/test_multi_objective.py", "tests/unit/test_multi_objective.py"),

        # Tests - debug
        ("test_debug/debug_costs.py", "tests/debug/debug_costs.py"),
        ("test_debug/debug_validation_stats.py", "tests/debug/debug_validation_stats.py"),
        ("test_debug/transport_cost_comparison.py", "tests/debug/transport_cost_comparison.py"),

        # Tests - verification
        ("verification_validation_sensitivity/optimizer_verification_suite.py", "tests/verification/optimizer_verification_suite.py"),
        ("verification_validation_sensitivity/test_data_generator.py", "tests/verification/test_data_generator.py"),

        # Data files
        ("fuel_data.db", "data/databases/fuel_data.db"),
        ("fuel_data_backup.db", "data/databases/fuel_data_backup.db"),
        ("optimization_config.json", "data/config/optimization_config.json"),

        # Output files
        ("pareto_fuel_solutions.csv", "outputs/optimization_results/pareto_fuel_solutions.csv"),
        ("pareto_fuel_solutions.json", "outputs/optimization_results/pareto_fuel_solutions.json"),
        ("complete_export.json", "outputs/optimization_results/complete_export.json"),
        ("complete_export.xlsx", "outputs/optimization_results/complete_export.xlsx"),
        ("complete_export_flattened.csv", "outputs/optimization_results/complete_export_flattened.csv"),
        ("pareto_front_fuel_optimization.png", "outputs/visualizations/pareto_front_fuel_optimization.png"),
        ("optimization_allocation_map.html", "outputs/visualizations/optimization_allocation_map.html"),
    ]

    for source, dest in moves:
        move_file(source, dest)

    # Move test scenarios (multiple files)
    print("\n  Moving test scenarios...")
    test_scenarios_source = PROJECT_ROOT / "verification_validation_sensitivity/test_scenarios"
    if test_scenarios_source.exists():
        for file in test_scenarios_source.iterdir():
            if file.is_file():
                move_file(f"verification_validation_sensitivity/test_scenarios/{file.name}",
                         f"tests/verification/test_scenarios/{file.name}")

    # Move verification results
    print("\n  Moving verification results...")
    ver_results_source = PROJECT_ROOT / "verification_validation_sensitivity/verification_results"
    if ver_results_source.exists():
        for file in ver_results_source.iterdir():
            if file.is_file():
                move_file(f"verification_validation_sensitivity/verification_results/{file.name}",
                         f"tests/verification/verification_results/{file.name}")

    # Move verification research notes
    print("\n  Moving verification research notes...")
    research_notes_source = PROJECT_ROOT / "verification_validation_sensitivity/research_notes"
    if research_notes_source.exists():
        for file in research_notes_source.iterdir():
            if file.is_file():
                move_file(f"verification_validation_sensitivity/research_notes/{file.name}",
                         f"docs/verification_research/{file.name}")

    # Move docs folders (entire directories)
    print("\n  Moving documentation folders...")
    if (PROJECT_ROOT / "input_specs").exists():
        shutil.move(str(PROJECT_ROOT / "input_specs"), str(PROJECT_ROOT / "docs/input_specs"))
        print(f"  ✓ Moved input_specs/ → docs/input_specs/")
        log_move("input_specs/", "docs/input_specs/", "success")

    if (PROJECT_ROOT / "output_specs").exists():
        shutil.move(str(PROJECT_ROOT / "output_specs"), str(PROJECT_ROOT / "docs/output_specs"))
        print(f"  ✓ Moved output_specs/ → docs/output_specs/")
        log_move("output_specs/", "docs/output_specs/", "success")

    if (PROJECT_ROOT / "personal_notes").exists():
        shutil.move(str(PROJECT_ROOT / "personal_notes"), str(PROJECT_ROOT / "docs/personal_notes"))
        print(f"  ✓ Moved personal_notes/ → docs/personal_notes/")
        log_move("personal_notes/", "docs/personal_notes/", "success")

    # Move chapters_copy files
    print("\n  Moving chapters_copy files...")
    chapters_source = PROJECT_ROOT / "chapters_copy"
    if chapters_source.exists():
        for file in chapters_source.iterdir():
            if file.is_file():
                # Thesis exports (CSV/TEX) go to outputs/thesis_exports
                if file.suffix in ['.csv', '.tex']:
                    dest = f"outputs/thesis_exports/{file.name}"
                else:
                    # Everything else goes to docs/chapters_copy
                    dest = f"docs/chapters_copy/{file.name}"
                move_file(f"chapters_copy/{file.name}", dest)

    # Move nested chapters_copy files if they exist
    nested_chapters = PROJECT_ROOT / "final_version/chapters_copy"
    if nested_chapters.exists():
        for file in nested_chapters.iterdir():
            if file.is_file():
                if file.suffix in ['.csv', '.tex']:
                    move_file(f"final_version/chapters_copy/{file.name}",
                             f"outputs/thesis_exports/{file.name}")

    # Move delete folder to archive
    if (PROJECT_ROOT / "delete").exists():
        shutil.move(str(PROJECT_ROOT / "delete"), str(PROJECT_ROOT / "archive/delete"))
        print(f"  ✓ Moved delete/ → archive/delete/")
        log_move("delete/", "archive/delete/", "success")


def update_imports_in_file(file_path):
    """Update imports in a Python file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        original_content = content
        updates = []

        # Choose replacement strategy depending on whether file is inside src
        rel_path = file_path.relative_to(PROJECT_ROOT)
        inside_src = str(rel_path).startswith('src/')

        if inside_src:
            # Use package-relative imports for modules within src
            replacements = [
                (r'from\s+precomputation\s+import', 'from .precomputation import'),
                (r'from\s+fuel_optimizer_docplex\s+import', 'from .fuel_optimizer_docplex import'),
                (r'from\s+pareto_front_generator\s+import', 'from .pareto_front_generator import'),
                (r'from\s+strategic_supplier_scoring\s+import', 'from .strategic_supplier_scoring import'),
                (r'from\s+optimization_map\s+import', 'from .visualization.optimization_map import'),
                (r'(^|\n)import\s+precomputation(\s|$)', r'\1from . import precomputation as precomputation\2'),
                (r'(^|\n)import\s+fuel_optimizer_docplex(\s|$)', r'\1from . import fuel_optimizer_docplex as fuel_optimizer_docplex\2'),
                (r'(^|\n)import\s+pareto_front_generator(\s|$)', r'\1from . import pareto_front_generator as pareto_front_generator\2'),
                (r'(^|\n)import\s+strategic_supplier_scoring(\s|$)', r'\1from . import strategic_supplier_scoring as strategic_supplier_scoring\2'),
                (r'(^|\n)import\s+optimization_map(\s|$)', r'\1from .visualization import optimization_map as optimization_map\2'),
            ]
        else:
            # External scripts/tests should import from src package root
            replacements = [
                (r'from\s+precomputation\s+import', 'from src.precomputation import'),
                (r'from\s+fuel_optimizer_docplex\s+import', 'from src.fuel_optimizer_docplex import'),
                (r'from\s+pareto_front_generator\s+import', 'from src.pareto_front_generator import'),
                (r'from\s+strategic_supplier_scoring\s+import', 'from src.strategic_supplier_scoring import'),
                (r'from\s+optimization_map\s+import', 'from src.visualization.optimization_map import'),
                (r'(^|\n)import\s+precomputation(\s|$)', r'\1import src.precomputation as precomputation\2'),
                (r'(^|\n)import\s+fuel_optimizer_docplex(\s|$)', r'\1import src.fuel_optimizer_docplex as fuel_optimizer_docplex\2'),
                (r'(^|\n)import\s+pareto_front_generator(\s|$)', r'\1import src.pareto_front_generator as pareto_front_generator\2'),
                (r'(^|\n)import\s+strategic_supplier_scoring(\s|$)', r'\1import src.strategic_supplier_scoring as strategic_supplier_scoring\2'),
                (r'(^|\n)import\s+optimization_map(\s|$)', r'\1import src.visualization.optimization_map as optimization_map\2'),
            ]

        for pattern, replacement in replacements:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                updates.append(f"{pattern} → {replacement}")

        # Write updated content if changes were made
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)

            if updates:
                print(f"  ✓ Updated imports in {file_path.relative_to(PROJECT_ROOT)}")
                log_update(file_path, "imports", updates)
            return True

        return False
    except Exception as e:
        print(f"  ❌ Error updating {file_path}: {e}")
        log_error(f"update_imports: {file_path}", e)
        return False


def update_all_imports():
    """Update imports in all Python files"""
    print("\n🔄 Updating imports in Python files...")

    # Find all Python files in new locations
    python_files = []
    for directory in ['src', 'scripts', 'tests', 'tools']:
        dir_path = PROJECT_ROOT / directory
        if dir_path.exists():
            python_files.extend(dir_path.rglob('*.py'))

    updated_count = 0
    for py_file in python_files:
        if update_imports_in_file(py_file):
            updated_count += 1

    print(f"\n  ✅ Updated imports in {updated_count} files")


def update_output_paths():
    """Update output paths in scripts"""
    print("\n📝 Updating output paths in scripts...")

    # Scripts that need path updates
    scripts_to_update = [
        "scripts/export/export_baseline_summaries.py",
        "scripts/visualization/optimization_map.py",
        "scripts/export/export_costs.py",
    ]

    for script_rel_path in scripts_to_update:
        script_path = PROJECT_ROOT / script_rel_path
        if not script_path.exists():
            print(f"  ⚠ Skipping {script_rel_path} (not found)")
            continue

        try:
            with open(script_path, 'r') as f:
                content = f.read()

            original_content = content
            updates = []

            # Update common path patterns
            # Example: here / "chapters_copy" → here.parent.parent / "outputs/thesis_exports"

            # For export_baseline_summaries.py - change output to outputs/thesis_exports
            if "export_baseline_summaries" in script_path.name:
                if 'chapters_copy' in content:
                    # Update to use outputs/thesis_exports
                    content = content.replace('here / "chapters_copy"', 'here.parent.parent / "outputs/thesis_exports"')
                    content = content.replace('"chapters_copy"', '"outputs/thesis_exports"')
                    updates.append("Changed output to outputs/thesis_exports/")

            # For optimization_map.py - output to outputs/visualizations
            if "optimization_map" in script_path.name:
                # Add path configuration at top if not exists
                if 'OUTPUT_DIR' not in content and 'output_dir' not in content:
                    # This will need manual review, just flag it
                    updates.append("MANUAL REVIEW: Add output path to outputs/visualizations/")

            # Update database and config paths (variable assignment style)
            content = re.sub(r'db_path\s*=\s*["\']fuel_data\.db["\']',
                             'db_path = str(here.parent.parent / "data/databases/fuel_data.db")',
                             content)
            content = re.sub(r'config_path\s*=\s*["\']optimization_config\.json["\']',
                             'config_path = str(here.parent.parent / "data/config/optimization_config.json")',
                             content)

            # Update Path(...) builds like: here / "fuel_data.db"
            content = re.sub(r'here\s*/\s*["\']fuel_data\.db["\']',
                             'here.parent.parent / "data/databases/fuel_data.db"',
                             content)
            content = re.sub(r'here\s*/\s*["\']optimization_config\.json["\']',
                             'here.parent.parent / "data/config/optimization_config.json"',
                             content)

            # Update chapters_copy outputs to outputs/thesis_exports
            content = re.sub(r'Path\(\s*["\']final_version/chapters_copy["\']\s*\)',
                             'Path(__file__).resolve().parent.parent / "outputs/thesis_exports"',
                             content)

            if content != original_content:
                with open(script_path, 'w') as f:
                    f.write(content)
                print(f"  ✓ Updated paths in {script_rel_path}")
                log_update(script_path, "output_paths", updates)

        except Exception as e:
            print(f"  ❌ Error updating {script_rel_path}: {e}")
            log_error(f"update_paths: {script_rel_path}", e)


def create_init_files():
    """Create __init__.py files in all packages"""
    print("\n📄 Creating __init__.py files...")

    packages = [
        "src",
        "src/visualization",
        "scripts",
        "scripts/data_preparation",
        "scripts/data_preparation/extractors",
        "scripts/export",
        "tools",
        "tests",
        "tests/unit",
        "tests/debug",
        "tests/verification",
    ]

    for package in packages:
        init_file = PROJECT_ROOT / package / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            print(f"  ✓ Created {package}/__init__.py")
            log_update(init_file, "created", "Package initialization file")


def update_core_defaults():
    """Update default config/db paths and mapper imports inside src core modules."""
    print("\n🧩 Updating core module defaults and mapper imports...")

    core_files = [
        PROJECT_ROOT / 'src/fuel_optimizer_docplex.py',
        PROJECT_ROOT / 'src/precomputation.py',
        PROJECT_ROOT / 'src/pareto_front_generator.py',
        PROJECT_ROOT / 'src/strategic_supplier_scoring.py',
    ]

    for path in core_files:
        if not path.exists():
            print(f"  ⚠ Skipping {path} (not found)")
            continue

        try:
            with open(path, 'r') as f:
                content = f.read()

            original = content

            # Ensure Path import for modules that use it in defaults
            if 'Path(' in content and 'from pathlib import Path' not in content:
                content = content.replace('\nimport logging', '\nimport logging\nfrom pathlib import Path')

            # Update default constructor args for config/db to project-root data paths
            # fuel_optimizer_docplex & precomputation & pareto_front_generator
            content = re.sub(
                r'config_path:\s*str\s*=\s*["\']optimization_config\.json["\']',
                'config_path: str = str(Path(__file__).resolve().parents[1] / "data/config/optimization_config.json")',
                content
            )
            content = re.sub(
                r'db_path:\s*str\s*=\s*["\']fuel_data\.db["\']',
                'db_path: str = str(Path(__file__).resolve().parents[1] / "data/databases/fuel_data.db")',
                content
            )

            # strategic_supplier_scoring: __init__(self, db_path: str = "fuel_data.db")
            content = re.sub(
                r'db_path:\s*str\s*=\s*["\']fuel_data\.db["\']',
                'db_path: str = str(Path(__file__).resolve().parents[1] / "data/databases/fuel_data.db")',
                content
            )

            # Map import in optimizer to new location under src/visualization
            content = re.sub(
                r'from\s+optimization_map\s+import\s+OptimizationMapper',
                'from .visualization.optimization_map import OptimizationMapper',
                content
            )

            if content != original:
                with open(path, 'w') as f:
                    f.write(content)
                print(f"  ✓ Updated defaults/imports in {path.relative_to(PROJECT_ROOT)}")
                log_update(path, "core_defaults", "Updated default paths and mapper import")
        except Exception as e:
            print(f"  ❌ Error updating {path}: {e}")
            log_error(f"update_core_defaults: {path}", e)


def update_gitignore():
    """Update .gitignore with new paths"""
    print("\n📝 Updating .gitignore...")

    gitignore_path = PROJECT_ROOT / ".gitignore"

    new_gitignore = """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
venv/
*.egg-info/

# IDE / Editor
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Outputs (entire directory - all generated files)
outputs/

# Data files (databases only, keep config tracked)
data/databases/*.db
data/databases/*.db-journal

# Keep config tracked
!data/config/*.json

# Logs
*.log
.aider*

# AI Context Sync (internal tooling)
.context-sync/

# Claude Code
.claude/

# Backup directories
backup_before_restructure_*/
"""

    try:
        with open(gitignore_path, 'w') as f:
            f.write(new_gitignore)
        print("  ✓ Updated .gitignore")
        log_update(gitignore_path, "updated", "New ignore patterns for restructured project")
    except Exception as e:
        print(f"  ❌ Error updating .gitignore: {e}")
        log_error("update_gitignore", e)


def cleanup_old_directories():
    """Remove empty old directories"""
    print("\n🧹 Cleaning up old directories...")

    dirs_to_remove = [
        "test_debug",
        "verification_validation_sensitivity",
        "extractors",
        "test_scenarios",
        "verification_results",
        "chapters_copy",
        "final_version",  # Nested duplicate
    ]

    for dir_name in dirs_to_remove:
        dir_path = PROJECT_ROOT / dir_name
        if dir_path.exists():
            try:
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    print(f"  ✓ Removed empty directory: {dir_name}")
                elif dir_path.is_dir():
                    print(f"  ⚠ Skipping {dir_name} (not empty - manual review needed)")
            except Exception as e:
                print(f"  ⚠ Could not remove {dir_name}: {e}")


def generate_migration_report():
    """Generate migration report"""
    print("\n📊 Generating migration report...")

    report_path = PROJECT_ROOT / "migration_report.json"

    try:
        with open(report_path, 'w') as f:
            json.dump(migration_log, f, indent=2)

        print(f"\n✅ Migration report saved to: {report_path}")

        # Print summary
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        print(f"Files moved: {len([m for m in migration_log['moves'] if m['status'] == 'success'])}")
        print(f"Files skipped: {len([m for m in migration_log['moves'] if m['status'].startswith('skipped')])}")
        print(f"Files updated: {len(migration_log['updates'])}")
        print(f"Errors: {len(migration_log['errors'])}")

        if migration_log['errors']:
            print("\n⚠️  ERRORS ENCOUNTERED:")
            for error in migration_log['errors']:
                print(f"  - {error['operation']}: {error['error']}")

        print("="*60)

    except Exception as e:
        print(f"❌ Error generating report: {e}")


def main():
    """Main migration function"""
    print("="*60)
    print("FINAL_VERSION PROJECT RESTRUCTURING")
    print("="*60)

    print(f"\nProject root: {PROJECT_ROOT}")

    # Confirm before proceeding
    response = input("\n⚠️  This will restructure your project. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return

    # Step 1: Create backup
    if not create_backup():
        print("\n❌ Migration aborted due to backup failure")
        return

    # Step 2: Create directory structure
    create_directory_structure()

    # Step 3: Move files
    move_all_files()

    # Step 4: Update imports
    update_all_imports()

    # Step 5: Update output paths
    update_output_paths()

    # Step 5a: Update core module defaults/imports
    update_core_defaults()

    # Step 6: Create __init__.py files
    create_init_files()

    # Step 7: Update .gitignore
    update_gitignore()

    # Step 8: Cleanup
    cleanup_old_directories()

    # Step 9: Generate report
    generate_migration_report()

    print("\n" + "="*60)
    print("✅ MIGRATION COMPLETE!")
    print("="*60)
    print(f"\nBackup saved at: {BACKUP_DIR}")
    print("\nNext steps:")
    print("1. Review migration_report.json for any errors")
    print("2. Test your scripts: python scripts/export/export_costs.py")
    print("3. Run verification: python tests/verification/optimizer_verification_suite.py")
    print("4. If everything works, you can delete the backup directory")
    print("\nIf you need to rollback, restore from the backup directory.")
    print("="*60)


if __name__ == "__main__":
    main()
