#!/usr/bin/env bash
# Create or update the branch rulesets in .github/rulesets/ (issue 0029).
#
#   scripts/apply_rulesets.sh [owner/repo]        default: gtech-mulearn/mulearnbackend
#
# Needs a gh login with admin rights on the repository. Run it only once dev-architecture has
# merged into dev: the rulesets require the "unit", "legacy", "mysql (8.0)", "mysql (8.4)" and
# "two reviewers" checks, which only the new CI produces. Applied earlier, they block every pull
# request into dev. A ruleset with the same name is updated in place, so re-running is safe.
set -euo pipefail

repo="${1:-gtech-mulearn/mulearnbackend}"
here="$(cd "$(dirname "$0")/.." && pwd)"

for file in "$here"/.github/rulesets/*.json; do
  name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$file")"
  id="$(gh api "repos/$repo/rulesets" --paginate -q ".[] | select(.name == \"$name\") | .id" | head -n 1)"
  if [ -n "$id" ]; then
    gh api --method PUT "repos/$repo/rulesets/$id" --input "$file" > /dev/null
    echo "updated ruleset $name ($id)"
  else
    gh api --method POST "repos/$repo/rulesets" --input "$file" > /dev/null
    echo "created ruleset $name"
  fi
done
