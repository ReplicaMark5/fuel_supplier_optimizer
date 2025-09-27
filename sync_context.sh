#!/usr/bin/env bash
set -euo pipefail

# Sync shared context to all AI agent config files
source_file="shared_context.md"
target_files=("CLAUDE.md" "AGENTS.md" "GEMINI.md")

if [[ ! -f "$source_file" ]]; then
    echo "Error: $source_file not found"
    exit 1
fi

echo "Syncing $source_file to agent config files..."

for target in "${target_files[@]}"; do
    cp "$source_file" "$target"
    echo "  ✓ $target"
done

echo "Sync complete: ${target_files[*]}"