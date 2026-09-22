#!/usr/bin/env bash
# GTT - validate. Deterministic aggregator over the existing CI gates:
# backlog structural integrity, ADE-adapter matrix, GTTGuard registry, and
# the stack map. Reuses each check script's own logic rather than
# reimplementing it - this script only runs them and summarizes.
#
# Adapter check is skipped (not failed) when zero or more than one adapter
# is present: this source repository is the catalog and legitimately ships
# every adapter, which is not the "wrong adapter installed" violation
# gtt-check-adapter.sh exists to catch on an installed project. Run
# `gtt/scripts/gtt-check-adapter.sh <ade>` by hand there if needed.
#
# Usage:
#   gtt/scripts/gtt-validate.sh
#
# Exit 0 = every check passed or was skipped, 1 = at least one check failed.

set -uo pipefail

FAIL=0
report() {
  # $1=label $2=exit-code (2 means "cannot determine", not a failure)
  case "$2" in
    0) echo "PASS               $1" ;;
    2) echo "CANNOT-DETERMINE   $1" ;;
    *) echo "FAIL               $1"; FAIL=1 ;;
  esac
}

bash gtt/scripts/gtt-check-backlog.sh >/tmp/gtt-validate-backlog.$$ 2>&1
BACKLOG_RC=$?
report "gtt-check-backlog.sh" "$BACKLOG_RC"
[ "$BACKLOG_RC" -ne 0 ] && cat /tmp/gtt-validate-backlog.$$
rm -f /tmp/gtt-validate-backlog.$$

adapters=()
[ -d ".claude" ] && adapters+=("claude")
[ -d ".kiro" ] && adapters+=("kiro")
[ -f ".copilot/copilot-instructions.md" ] && adapters+=("copilot")

if [ "${#adapters[@]}" -eq 1 ]; then
  bash gtt/scripts/gtt-check-adapter.sh "${adapters[0]}" >/tmp/gtt-validate-adapter.$$ 2>&1
  ADAPTER_RC=$?
  report "gtt-check-adapter.sh ${adapters[0]}" "$ADAPTER_RC"
  [ "$ADAPTER_RC" -ne 0 ] && cat /tmp/gtt-validate-adapter.$$
  rm -f /tmp/gtt-validate-adapter.$$
else
  echo "SKIPPED            gtt-check-adapter.sh (zero or multiple adapters present - catalog repo or ambiguous; run manually with an explicit ADE if this is an installed project)"
fi

bash gtt/scripts/gtt-check-protection.sh >/tmp/gtt-validate-protection.$$ 2>&1
PROTECTION_RC=$?
report "gtt-check-protection.sh" "$PROTECTION_RC"
[ "$PROTECTION_RC" -ne 0 ] && cat /tmp/gtt-validate-protection.$$
rm -f /tmp/gtt-validate-protection.$$

bash gtt/scripts/gtt-check-stack.sh >/tmp/gtt-validate-stack.$$ 2>&1
STACK_RC=$?
report "gtt-check-stack.sh" "$STACK_RC"
[ "$STACK_RC" -ne 0 ] && cat /tmp/gtt-validate-stack.$$
rm -f /tmp/gtt-validate-stack.$$

echo
if [ "$FAIL" -ne 0 ]; then
  echo "gtt-validate: FAILED - see the FAIL line(s) above."
  exit 1
fi
echo "gtt-validate: OK"
exit 0
