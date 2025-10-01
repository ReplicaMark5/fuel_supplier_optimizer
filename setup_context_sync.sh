#!/usr/bin/env bash
set -euo pipefail

# Universal AI agent context sync setup
#
# Usage:
#   ./setup_context_sync.sh                    # Safe: backs up existing files, imports to CONTEXT.md
#   ./setup_context_sync.sh --auto             # Fully automated: no review step, immediate sync
#   ./setup_context_sync.sh --ai               # AI agent mode: setup + guided review handoff
#   ./setup_context_sync.sh --force            # Skip review: immediately overwrite targets
#   ./setup_context_sync.sh --targets FILE1,FILE2,FILE3  # Custom target files
#
# What it does:
#   1. Creates CONTEXT.md as single source of truth
#   2. Backs up existing target files safely
#   3. Creates manual_sync_context.sh (one-time sync)
#   4. Creates watch_context.sh (auto-sync on save)
#   5. Write-protects target files to prevent accidental edits

force=false
auto=false
ai=false
targets_csv="CLAUDE.md,AGENTS.md,GEMINI.md"

# AI/CI detection
if [ "${AI_RUNNER:-}" = "1" ] || [ "${CI:-}" = "1" ]; then
  auto=true
  ai=true
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --force) force=true ;;
    --auto) auto=true ;;
    --ai) auto=true; ai=true ;;
    --targets) shift; targets_csv="${1:-$targets_csv}" ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac; shift || true
done
IFS=, read -r -a targets <<<"$targets_csv"

# OS detection
uname_s="$(uname -s 2>/dev/null || echo unknown)"
is_wsl=false; is_linux=false; is_macos=false; is_windows_native=false

case "$uname_s" in
  Linux)
    is_linux=true
    grep -qi microsoft /proc/version 2>/dev/null && is_wsl=true
    ;;
  Darwin) is_macos=true ;;
  MINGW*|MSYS*|CYGWIN*) is_windows_native=true ;;  # Git Bash / MSYS
  *) [ "${OS:-}" = "Windows_NT" ] && is_windows_native=true ;;
esac

# Portable helpers
hash256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

sed_inplace() {
  if sed --version >/dev/null 2>&1; then sed -i "$@"
  else sed -i '' "$@"; fi
}

# Helper for AI breadcrumbs
ai_emit() { printf 'AI_TODO::%s\n' "$*"; }

echo "Setting up AI agent context sync..."
src="CONTEXT.md"
ts="$(date +%Y%m%dT%H%M%S)"
sync_dir=".context-sync"
bdir="$sync_dir/.backups/$ts"
mkdir -p "$bdir"
mkdir -p "$sync_dir"

# 1) Seed or preserve CONTEXT.md
if [[ ! -f "$src" ]]; then
  echo "• No $src found. Seeding from legacy files if present."
  {
    echo "<!-- Edit ONLY this file (CONTEXT.md). Targets like CLAUDE.md / AGENTS.md / GEMINI.md are read only and generated. (after edits to the CONTEXT.MD run <bash .context-sync/manual_sync_context.sh> to make the changes sync across to the target files DO NOT RUN <bash ./setup_context_sync.sh>) -->"
    echo
    echo "# Project Context"
    echo
    echo "**Name:** <PROJECT_NAME>"
    echo "**One-liner:** <WHAT_IT_DOES>"
    echo "**Stack:** <LANGS/FRAMEWORKS>"
    echo
    echo "## Quick Start"
    echo "1. <install_cmd>"
    echo "2. <dev_cmd>"
    echo "3. Open <entry_point>"
    echo "4. Key files: <list_files>"
    echo
    echo "## Commands"
    echo "**Common:**"
    echo "- \`npm install\` / \`pip install -r requirements.txt\`"
    echo "- \`npm run dev\` / \`uvicorn app:app --reload\`"
    echo "- \`npm test\` / \`pytest\`"
    echo "- \`npm run lint\` / \`ruff check .\`"
    echo "- \`npm run build\`"
    echo "- 'tree -a -I \".git|__pycache__|*.pyc|archive|outputs|data/databases/*.db\" > project_tree.txt' # use this command to see project tree"
    echo
    echo "**ast-grep (sg):** Available for structural code search/refactor. Use for: API migrations, large-scale renames, logging standardization, security hardening, error-handling policy changes, test modernization, config normalization. Workflow: \`sg run -p 'pattern' --lang python src/\` (preview) → \`-i\` (interactive) → \`-U\` (batch). Always set \`--lang\`. Use \`sg scan --config sgconfig.yml\` for repeatable repo policies."
    echo
    echo "## Architecture Notes"
    echo "- <KEY_PATTERNS_OR_PRINCIPLES>"
    echo "- <IMPORTANT_ABSTRACTIONS>"
    echo "- <GOTCHAS_OR_CONVENTIONS>"
    echo
    echo "## Project Structure"
    echo "\`\`\`"
    echo "├── example.py          # example....."
    echo "├── example2.py         # ....."
    echo "└── folder/             # ....."
    echo "    ├── example3.py"
    echo "    ├── example4.py"
    echo "\`\`\`"
    echo
    echo "## Standards"
    echo "- Format and lint before PR"
    echo "- Prefer types where available"
    echo "- Small, focused functions"
    echo "- Tests for new behavior"
    echo
    echo "## Agent Guide"
    echo "**Before coding:** read this file + README, locate existing patterns, plan minimal change."
    echo "**When coding:** follow conventions, add tests, update docs if API changes."
    echo "**Before submitting:** run format, lint, types, unit tests. Provide minimal diff."
    echo "**Don't:** edit generated targets, add deps without reason, break public APIs."
    echo
    echo "## Install Policy"
    echo "- **Default: no sudo**. Use user-space installs (venv, pipx, nvm)"
    echo "- **sudo only** for OS packages (\`apt install git\`)"
    echo "- **Never** \`sudo pip\` or \`sudo npm\`"
    echo "- Agents must ask before using sudo"
    echo
    echo "## Current Focus"
    echo "[Describe current development priorities]"
    echo
    echo "---"
    echo "_Generated on ${ts}_"
  } > "$src"
fi

# 2) Collect legacy content (non-destructive)
legacy_found=false
for t in "${targets[@]}"; do
  if [[ -f "$t" ]]; then
    legacy_found=true
    cp -f "$t" "$bdir/$t"
  fi
done

# If legacy exists, import into CONTEXT.md once (guard via marker)
marker="<!-- LEGACY_IMPORT_$ts -->"
if $legacy_found; then
  if ! grep -q "LEGACY_IMPORT_" "$src" 2>/dev/null; then
    {
      echo
      echo "$marker"
      echo "## Legacy Context Imports ($ts)"
      for t in "${targets[@]}"; do
        if [[ -f "$bdir/$t" ]]; then
          echo
          echo "### From $t"
          echo '```md'
          cat "$bdir/$t"
          echo '```'
        fi
      done
    } >> "$src"
    echo "• Imported legacy content into $src and backed up to $bdir"
  else
    echo "• Legacy content appears already imported. Skipping import."
  fi
fi

# 3) Write sync script (checksum + write-protect)
cat > "$sync_dir/manual_sync_context.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Portable SHA-256 helper
hash256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

# Auto-detect if we're in .context-sync/ or project root
if [[ "$(basename "$PWD")" == ".context-sync" ]]; then
    src="../CONTEXT.md"
    target_prefix="../"
else
    src="CONTEXT.md"
    target_prefix=""
fi
targets=__TARGETS__
[ -f "$src" ] || { echo "Error: $src not found"; exit 1; }
sum_src="$(hash256 "$src")"
updated=false
for t in "${targets[@]}"; do
  target_file="${target_prefix}$t"
  [ -f "$target_file" ] && chmod +w "$target_file" 2>/dev/null || true
  sum_t="$( [ -f "$target_file" ] && hash256 "$target_file" || echo "" )"
  if [ "$sum_src" != "$sum_t" ] || [ ! -f "$target_file" ]; then
    tmp="${target_prefix}$t.tmp.$$"
    cp "$src" "$tmp"
    mv -f "$tmp" "$target_file"
    echo "✓ $t"
    updated=true
  fi
  chmod a-w "$target_file"
done
if [ "$updated" = true ]; then echo "Sync complete"; else echo "All files up to date"; fi
EOF
chmod +x "$sync_dir/manual_sync_context.sh"
# Write targets list for cross-platform use
printf "%s\n" "${targets[@]}" > "$sync_dir/targets.txt"

targets_str=$(printf '"%s" ' "${targets[@]}")
targets_str=${targets_str%% }  # remove trailing space
sed_inplace "s/__TARGETS__/(${targets_str})/" "$sync_dir/manual_sync_context.sh"

# 3.5) Windows PowerShell helpers (if on native Windows)
if $is_windows_native; then
  # manual sync (PowerShell)
  cat > "$sync_dir/manual_sync_context.ps1" <<'PS1'
param()
$ErrorActionPreference = 'Stop'

# Handle both root and .context-sync launch
$pwdBase = Split-Path -Leaf (Get-Location)
if ($pwdBase -eq '.context-sync') {
  $src = Join-Path .. 'CONTEXT.md'
  $targetPrefix = '..'
} else {
  $src = 'CONTEXT.md'
  $targetPrefix = '.'
}
if (!(Test-Path $src)) { Write-Error 'Error: CONTEXT.md not found' }

# Load targets from file
$targetsPath = Join-Path $targetPrefix '.context-sync/targets.txt'
if (!(Test-Path $targetsPath)) { Write-Error ('targets.txt not found at {0}' -f $targetsPath) }
$targets = Get-Content $targetsPath | Where-Object { $_ -ne '' }

# Hash source
$sha256 = (Get-FileHash -Path $src -Algorithm SHA256).Hash
$updated = $false

foreach ($t in $targets) {
  $targetFile = Join-Path $targetPrefix $t
  if (Test-Path $targetFile) {
    Attrib -R $targetFile 2>$null
    $tHash = (Get-FileHash -Path $targetFile -Algorithm SHA256).Hash
  } else {
    $tHash = ''
  }

  if ($sha256 -ne $tHash) {
    $tmp = ('{0}.tmp.{1}' -f $targetFile, $PID)
    Copy-Item $src $tmp -Force
    Move-Item $tmp $targetFile -Force
    Write-Host ('Updated {0}' -f $t)
    $updated = $true
  }
  Attrib +R $targetFile 2>$null
}

if ($updated) { Write-Host 'Sync complete' } else { Write-Host 'All files up to date' }
PS1

  # watcher (PowerShell)
  cat > "$sync_dir/watch_context.ps1" <<'PS1'
param()
$ErrorActionPreference = 'Stop'

# Resolve paths
$pwdBase = Split-Path -Leaf (Get-Location)
if ($pwdBase -eq '.context-sync') {
  $src = Join-Path .. 'CONTEXT.md'
  $syncScriptDefault = '.\manual_sync_context.ps1'
} else {
  $src = 'CONTEXT.md'
  $syncScriptDefault = Join-Path '.context-sync' 'manual_sync_context.ps1'
}
$syncScript = if ($env:SYNC_SCRIPT) { $env:SYNC_SCRIPT } else { $syncScriptDefault }
if (!(Test-Path $syncScript)) { Write-Error ('Sync script not found: {0}' -f $syncScript) }

# Single-instance lock
$lock = Join-Path $env:TEMP 'watch_context.lock'
if (Test-Path $lock) {
  $pid = Get-Content $lock -ErrorAction SilentlyContinue
  if ($pid -and (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
    Write-Host ('Watcher already running (pid {0})' -f $pid); exit 0
  }
}
$PID | Out-File -FilePath $lock -Encoding ascii
$cleanup = { if (Test-Path $lock) { Remove-Item $lock -Force } }
Register-EngineEvent PowerShell.Exiting -Action $cleanup | Out-Null

# FileSystemWatcher
if (!(Test-Path $src)) { Write-Error ('Source not found: {0}' -f $src) }
$full = (Resolve-Path $src).Path
$dir  = Split-Path $full -Parent
$file = Split-Path $full -Leaf

$fsw = New-Object System.IO.FileSystemWatcher $dir, $file
$fsw.NotifyFilter = [System.IO.NotifyFilters]'LastWrite'
$action = {
  Start-Sleep -Milliseconds 250
  & $using:syncScript | Out-Null
}
$reg = Register-ObjectEvent $fsw Changed -Action $action
Write-Host ('Watching {0} (Ctrl+C to stop)' -f $full)
try {
  while ($true) { Start-Sleep -Seconds 3600 }
} finally {
  Unregister-Event -SourceIdentifier $reg.Name -ErrorAction SilentlyContinue
  $fsw.EnableRaisingEvents = $false
  $fsw.Dispose()
  & $cleanup
}
PS1

  echo "• Windows helpers created: $sync_dir/manual_sync_context.ps1, $sync_dir/watch_context.ps1"
fi

# 4) Watcher (Linux/macOS)
cat > "$sync_dir/watch_context.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Auto-detect if we're in .context-sync/ or project root
if [[ "$(basename "$PWD")" == ".context-sync" ]]; then
    src="../CONTEXT.md"
    sync_script_default="./manual_sync_context.sh"
else
    src="CONTEXT.md"
    sync_script_default=".context-sync/manual_sync_context.sh"
fi

# Allow override via environment variable
sync_script="${SYNC_SCRIPT:-${sync_script:-$sync_script_default}}"

# Sanity checks
if [ ! -x "$sync_script" ]; then
  echo "Making $sync_script executable"; chmod +x "$sync_script"
fi
if ! command -v inotifywait >/dev/null 2>&1 && ! command -v fswatch >/dev/null 2>&1; then
  if [ "${OS:-}" = "Windows_NT" ] || [[ "${MSYSTEM:-}" =~ MINGW|MSYS|CYGWIN ]]; then
    # Delegate to PowerShell watcher if present
    if [ -f ".context-sync/watch_context.ps1" ]; then
      echo "No Linux/macOS watcher found. Delegating to PowerShell."
      exec powershell.exe -NoProfile -File ".context-sync\\watch_context.ps1" || {
        echo "PowerShell watcher failed. Run: powershell.exe -NoProfile -File .context-sync\\watch_context.ps1"; exit 1; }
    fi
  fi
  echo "No watcher found. Install: inotify-tools (Linux), fswatch (macOS), or use watch_context.ps1 on Windows."
  exit 1
fi
lock="/tmp/watch_context.lock"
if [ -e "$lock" ] && kill -0 "$(cat "$lock")" 2>/dev/null; then
  echo "Watcher already running (pid $(cat "$lock"))"; exit 0; fi
echo $$ > "$lock"; trap 'rm -f "$lock"' EXIT
echo "Watching $src (Ctrl+C to stop)"
if command -v inotifywait >/dev/null 2>&1; then
  while inotifywait -e close_write "$src" >/dev/null 2>&1; do sleep 0.25; "$sync_script"; done
elif command -v fswatch >/dev/null 2>&1; then
  fswatch -o "$src" | while read _; do sleep 0.25; "$sync_script"; done
else
  echo "No watcher found. Install: inotify-tools (Linux) or fswatch (macOS)"; exit 1
fi
EOF
chmod +x "$sync_dir/watch_context.sh"

# 5) Add to .gitignore
if [[ -f ".gitignore" ]]; then
  if ! grep -q "^\.context-sync/" ".gitignore" 2>/dev/null; then
    echo "" >> .gitignore
    echo "# AI Context Sync (internal tooling)" >> .gitignore
    echo ".context-sync/" >> .gitignore
    echo "• Added .context-sync/ to .gitignore"
  else
    echo "• .context-sync/ already in .gitignore"
  fi
else
  cat > .gitignore << 'EOF'
# AI Context Sync (internal tooling)
.context-sync/
EOF
  echo "• Created .gitignore with .context-sync/"
fi

# 5.5) Add pre-commit guards for AI mode
if [ "$ai" = true ]; then
  mkdir -p .git/hooks
  cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

# Enforce review completion
if [ -f ".context-sync/REVIEW_NEEDED" ]; then
  echo "❌ Review not completed. Remove .context-sync/REVIEW_NEEDED after merging CONTEXT.md."
  exit 1
fi

# Check for remaining placeholders
if grep -E '<PROJECT_NAME>|<WHAT_IT_DOES>|<LANGS/FRAMEWORKS>|<NAMES>' CONTEXT.md >/dev/null 2>&1; then
  echo "❌ Placeholders remain in CONTEXT.md. Complete the review process."
  exit 1
fi

# Check for unmerged legacy imports
if grep "Legacy Context Imports" CONTEXT.md >/dev/null 2>&1; then
  echo "❌ Remove 'Legacy Context Imports' section after merging content."
  exit 1
fi

# Keep targets in sync
if [ -x ".context-sync/manual_sync_context.sh" ]; then
  if ! .context-sync/manual_sync_context.sh >/dev/null 2>&1; then
    echo "❌ Context sync failed. Fix CONTEXT.md and try again."
    exit 1
  fi
  # Check if sync created changes
  if ! git diff --quiet --exit-code CLAUDE.md AGENTS.md GEMINI.md 2>/dev/null; then
    echo "⚠️  Targets updated from CONTEXT.md. Stage changes and commit again."
    git add CLAUDE.md AGENTS.md GEMINI.md 2>/dev/null || true
    exit 1
  fi
fi
HOOK
  chmod +x .git/hooks/pre-commit
  echo "• Added pre-commit guards for review enforcement"
fi

# 6) First sync: safe by default
if $legacy_found && [ "$force" = false ] && [ "$auto" = false ]; then
  echo ""
  echo "🔍 FOUND EXISTING FILES"
  echo "   • Backed up to: $bdir"
  echo "   • Imported content into CONTEXT.md under 'Legacy Context Imports'"
  echo ""
  echo "📝 WHAT'S NEXT:"
  echo "   1. Review CONTEXT.md - merge/clean up the imported sections"
  echo "   2. Run: .context-sync/manual_sync_context.sh (copies CONTEXT.md to targets)"
  echo "   3. Run: .context-sync/watch_context.sh (auto-sync on file saves)"
  echo ""
  echo "🚀 SKIP REVIEW:"
  echo "   • To immediately overwrite targets: ./setup_context_sync.sh --force"
  echo "   • For AI agents, use: ./setup_context_sync.sh --auto"
  echo ""
else
  # Run sync from the sync directory (cross-platform)
  if $is_windows_native && [ -f "$sync_dir/manual_sync_context.ps1" ]; then
    powershell.exe -NoProfile -File "$sync_dir\\manual_sync_context.ps1"
  else
    (cd "$sync_dir" && ./manual_sync_context.sh)
  fi
  echo ""

  # AI mode: create review handoff
  if [ "$ai" = true ]; then
    echo "REVIEW_PENDING" > "$sync_dir/REVIEW_NEEDED"

    cat > AI_REVIEW_TASKS.md <<'EOF'
# AI Review Tasks

## Understanding the Context Sync System

**What this does:**
This setup creates a single source of truth (CONTEXT.md) that syncs to multiple AI agent config files:
- CONTEXT.md → CLAUDE.md (Claude Code agent)
- CONTEXT.md → AGENTS.md (other agent tools)
- CONTEXT.md → GEMINI.md (Gemini agents)

**Why this matters:**
- You only edit CONTEXT.md (never the target files)
- All AI agents see the same consistent context
- Changes sync automatically when you run the sync script
- Target files are write-protected to prevent accidental edits

**Your job:**
Create a comprehensive, well-structured CONTEXT.md that will serve as the definitive project context for ALL AI agents working on this codebase.

## Read and Analyze
- Open CONTEXT.md
- Locate "Legacy Context Imports" section (bottom of file)
- Identify template placeholders: <PROJECT_NAME>, <WHAT_IT_DOES>, <LANGS/FRAMEWORKS>, <NAMES>
- Understand that the legacy content was imported from existing agent files

## Merge and Structure
- Replace ALL placeholders with real values from imported sections and repo analysis
- Move valuable content from "Legacy Context Imports" into appropriate template sections
- Ensure the result is a complete, coherent project context document
- Delete the entire "Legacy Context Imports" section after merging

## Cross-check Against Repository
- Infer tech stack from: package.json, requirements.txt, pyproject.toml, source files
- Infer project owners from: CODEOWNERS, git log, README
- Update "Project Structure" section using actual file structure
- Verify all information is accurate and current

## Quality Check
- Ensure no placeholder text remains (<PROJECT_NAME> etc.)
- Verify the context is comprehensive enough for any AI agent
- Check that content flows logically and is well-organized
- Confirm the context accurately represents the project

## Finalise
- Run: .context-sync/finish_review.sh (syncs to all target files and removes sentinel)
- Verify target files (CLAUDE.md, AGENTS.md, GEMINI.md) are updated
- Confirm the review process is complete
EOF

    # Light heuristics to help the agent
    name_guess="$(grep -m1 -E '^\*\*Name:\*\*|^# ' CONTEXT.md | sed 's/\*\*Name:\*\* //;s/^# //' || echo 'unknown')"
    stack_guess="$(find . -name 'package.json' -o -name 'requirements.txt' -o -name 'pyproject.toml' | head -1 || echo 'unknown')"
    echo "Guesses: name=${name_guess}, stack_file=${stack_guess}" > "$sync_dir/REVIEW_HINTS.txt"

    # Create finish helper for agents
    cat > "$sync_dir/finish_review.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "🔄 Running final sync..."
.context-sync/manual_sync_context.sh
echo "🗑️  Cleaning up review files..."
rm -f .context-sync/REVIEW_NEEDED
rm -f AI_REVIEW_TASKS.md
rm -f .context-sync/REVIEW_HINTS.txt
rm -f .context-sync/finish_review.sh
echo "✅ Review finished, synced, and cleaned up."
EOF
    chmod +x "$sync_dir/finish_review.sh"

    # Emit machine-readable steps for agents
    ai_emit "READ::AI_REVIEW_TASKS.md::Follow checklist"
    ai_emit "READ::CONTEXT.md::Review template and legacy imports"
    ai_emit "INSPECT::repo::Derive stack from package.json/requirements.txt"
    ai_emit "EDIT::CONTEXT.md::Merge content and remove legacy section"
    ai_emit "RUN::.context-sync/finish_review.sh"
    ai_emit "REPORT::Context review and merge completed"

    echo "🤖 AI REVIEW HANDOFF CREATED"
    echo "   • Review checklist: AI_REVIEW_TASKS.md"
    echo "   • Sentinel file: .context-sync/REVIEW_NEEDED"
    echo "   • Follow the AI_TODO breadcrumbs above"
    echo ""
    exit 42  # Nonzero exit to keep agent active
  fi

  if [ "$auto" = true ]; then
    echo "✅ AUTOMATED SETUP COMPLETE"
    echo "   • CONTEXT.md created and synced to targets"
    echo "   • Legacy content imported and synced automatically"
    echo "   • Review CONTEXT.md to clean up imported sections if needed"
    if $is_windows_native; then
      echo "   • Start auto-sync: powershell.exe -NoProfile -File .context-sync\\watch_context.ps1"
    else
      echo "   • Start auto-sync: .context-sync/watch_context.sh"
    fi
  else
    echo "✅ SETUP COMPLETE"
    echo "   • CONTEXT.md created and synced to targets"
    if $is_windows_native; then
      echo "   • Start auto-sync: powershell.exe -NoProfile -File .context-sync\\watch_context.ps1"
    else
      echo "   • Start auto-sync: .context-sync/watch_context.sh"
    fi
  fi
  echo ""
fi

echo "💡 HOW IT WORKS:"
echo "   • Edit ONLY CONTEXT.md (single source of truth)"
echo "   • Target files (CLAUDE.md, AGENTS.md, etc.) are auto-generated"
echo "   • Scripts work from project root OR .context-sync/ directory:"
if $is_windows_native; then
  echo "     - .context-sync/watch_context.ps1 (auto-sync on save) - PowerShell"
  echo "     - .context-sync/manual_sync_context.ps1 (one-time sync) - PowerShell"
  echo "     - .context-sync/watch_context.sh (auto-sync on save) - Bash fallback"
  echo "     - .context-sync/manual_sync_context.sh (one-time sync) - Bash fallback"
  echo ""
  echo "📋 WINDOWS TIP:"
  echo "   • If PowerShell scripts are blocked, run once:"
  echo "     Set-ExecutionPolicy -Scope CurrentUser RemoteSigned"
else
  echo "     - .context-sync/watch_context.sh (auto-sync on save)"
  echo "     - .context-sync/manual_sync_context.sh (one-time sync)"
fi
echo ""
echo "🧹 CLEANUP:"
echo "   • You can now delete this setup script: rm setup_context_sync.sh"
echo "   • All sync tools are in .context-sync/ folder (hidden from AI agents)"
echo "   • .context-sync/ added to .gitignore automatically"