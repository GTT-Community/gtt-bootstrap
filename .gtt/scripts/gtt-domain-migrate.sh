#!/usr/bin/env bash
# GTT - bring a project's gtt-domain up to the format of the Bootstrap it now runs, without losing anything.
#
# A thin wrapper: the logic is in gtt_domain_migrate.py. See that file for the usage.
#
# Usage (from the project root):
#   .gtt/scripts/gtt-domain-migrate.sh status [--json] | check [--apply] | begin [--to DIR] | verify [--json] | done | restore [--apply]
#
# Exit 0 = ok, 1 = verify refused or nothing to restore, 2 = cannot run.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/gtt-run-python.sh" "$HERE/gtt_domain_migrate.py" "$@"
