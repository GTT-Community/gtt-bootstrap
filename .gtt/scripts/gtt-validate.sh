#!/usr/bin/env bash
# GTT - validate. Deterministic aggregator over the existing CI gates:
# backlog structural integrity, ADE-adapter matrix, GTTGuard registry, the
# stack map, the markdown canonical-reference gate, and artifact identity /
# repository integrity (broken references, duplicate identity, stale index),
# and Session Memory adapter conformance (one line per declared adapter). Reuses each check
# script's own logic rather than reimplementing it - this script only runs
# them and summarizes.
#
# Adapter check, two regimes. When .gtt/ade.json exists (an installed project
# with declared participating ADEs) every participating ADE's integration is
# validated against it - a missing or inconsistent integration FAILS, a detected
# ADE that does not participate is a WARN. Without it (a project that predates
# multi-ADE, or this source repository, the catalog) the check is skipped, not
# failed, when zero or more than one adapter is present: the catalog legitimately
# ships every adapter, which is not the "wrong adapter installed" violation
# gtt-check-adapter.sh exists to catch. Run `.gtt/scripts/gtt-check-adapter.sh
# <ade>` by hand there if needed, or `gtt-ade.sh adopt` to declare the state.
#
# The result is remembered in .gtt/local/last-validation.json against the state it
# was computed for, so the review surface can say when it stopped being current.
# A change over the review threshold of gtt-domain/workflow.md is a WARN line: it
# informs and never changes the exit code.
#
# Usage:
#   .gtt/scripts/gtt-validate.sh
#   .gtt/scripts/gtt-validate.sh --review    the checks, then the review gate
#
# Exit 0 = every check passed or was skipped, 1 = at least one check failed
# (with --review: or a BLOCKING condition is open).

set -uo pipefail

REVIEW=0
for arg in "$@"; do
  case "$arg" in
    --review) REVIEW=1 ;;
    *) echo "usage: gtt-validate.sh [--review]" >&2; exit 2 ;;
  esac
done

FAIL=0
PASSED=0
SKIPPED=0
FAILED=0
report() {
  # $1=label $2=exit-code (2 means "cannot determine", not a failure)
  case "$2" in
    0) echo "PASS               $1"; PASSED=$((PASSED + 1)) ;;
    2) echo "CANNOT-DETERMINE   $1" ;;
    *) echo "FAIL               $1"; FAIL=1; FAILED=$((FAILED + 1)) ;;
  esac
}
run_check() {
  # $1=label, the rest is the command; its output is shown only when it fails
  local label="$1" out rc
  shift
  out="$("$@" 2>&1)"
  rc=$?
  report "$label" "$rc"
  [ "$rc" -ne 0 ] && printf '%s\n' "$out" | sed 's/^/                   /'
  return 0
}

bash .gtt/scripts/gtt-check-backlog.sh >/tmp/gtt-validate-backlog.$$ 2>&1
BACKLOG_RC=$?
report "gtt-check-backlog.sh" "$BACKLOG_RC"
[ "$BACKLOG_RC" -ne 0 ] && cat /tmp/gtt-validate-backlog.$$
rm -f /tmp/gtt-validate-backlog.$$

# The Core does not enumerate ADE names or paths itself. It discovers the
# set of known ADEs from .gtt/session-adapters/*.json - the same declaration
# registry the Session Memory loop below already uses - and asks
# gtt-check-adapter.sh (the one script whose contract is to know per-ADE
# paths) whether each one matches this workspace. Adding
# .gtt/session-adapters/<new-ade>.json tomorrow is picked up here with no
# edit to this file.
known_ades=()
for manifest in .gtt/session-adapters/*.json; do
  [ -f "$manifest" ] || continue
  known_ades+=("$(basename "$manifest" .json)")
done

if [ -f .gtt/ade.json ]; then
  adapter_out="$(bash .gtt/scripts/gtt-check-adapter.sh 2>&1)"
  adapter_rc=$?
  report "gtt-check-adapter.sh (participating ADEs, .gtt/ade.json)" "$adapter_rc"
  printf '%s
' "$adapter_out" | sed 's/^/                   /'
else
  matched_ades=()
  for ade in "${known_ades[@]}"; do
    bash .gtt/scripts/gtt-check-adapter.sh "$ade" >/dev/null 2>&1 && matched_ades+=("$ade")
  done

  if [ "${#matched_ades[@]}" -eq 1 ]; then
    report "gtt-check-adapter.sh ${matched_ades[0]}" 0
  else
    SKIPPED=$((SKIPPED + 1))
    echo "SKIPPED            gtt-check-adapter.sh (${#matched_ades[@]} of ${#known_ades[@]} declared adapters match this workspace and there is no .gtt/ade.json - catalog repo or ambiguous; run 'gtt-ade.sh adopt' to declare the participating ADEs)"
  fi
fi

bash .gtt/scripts/gtt-check-protection.sh >/tmp/gtt-validate-protection.$$ 2>&1
PROTECTION_RC=$?
report "gtt-check-protection.sh" "$PROTECTION_RC"
[ "$PROTECTION_RC" -ne 0 ] && cat /tmp/gtt-validate-protection.$$
rm -f /tmp/gtt-validate-protection.$$

bash .gtt/scripts/gtt-check-stack.sh >/tmp/gtt-validate-stack.$$ 2>&1
STACK_RC=$?
report "gtt-check-stack.sh" "$STACK_RC"
[ "$STACK_RC" -ne 0 ] && cat /tmp/gtt-validate-stack.$$
rm -f /tmp/gtt-validate-stack.$$

bash .gtt/scripts/gtt-check-markdown.sh >/tmp/gtt-validate-markdown.$$ 2>&1
MARKDOWN_RC=$?
report "gtt-check-markdown.sh" "$MARKDOWN_RC"
[ "$MARKDOWN_RC" -ne 0 ] && cat /tmp/gtt-validate-markdown.$$
rm -f /tmp/gtt-validate-markdown.$$

if [ -f .gtt/scripts/gtt-check-provenance.sh ]; then
  bash .gtt/scripts/gtt-check-provenance.sh >/tmp/gtt-validate-provenance.$$ 2>&1
  PROVENANCE_RC=$?
  report "gtt-check-provenance.sh" "$PROVENANCE_RC"
  [ "$PROVENANCE_RC" -ne 0 ] && cat /tmp/gtt-validate-provenance.$$
  rm -f /tmp/gtt-validate-provenance.$$
fi

if [ -f .gtt/scripts/gtt-check-contract.sh ]; then
  bash .gtt/scripts/gtt-check-contract.sh >/tmp/gtt-validate-contract.$$ 2>&1
  CONTRACT_RC=$?
  report "gtt-check-contract.sh" "$CONTRACT_RC"
  [ "$CONTRACT_RC" -ne 0 ] && cat /tmp/gtt-validate-contract.$$
  rm -f /tmp/gtt-validate-contract.$$
fi

# Design Assessment or questionnaire working copy (present only during bootstrap THINK): whatever
# the THINK Depth, the floor is assessed and a design below it is POOR, and the
# depth is the human's choice. Nothing to check once the copy is gone.
if { [ -f gtt-domain/proposals/bootstrap/design-assessment.md ] || [ -f gtt-domain/proposals/bootstrap/initial-design-questionnaire.md ]; } \
   && [ -f .gtt/scripts/gtt-project.sh ]; then
  bash .gtt/scripts/gtt-project.sh think >/tmp/gtt-validate-think.$$ 2>&1
  THINK_RC=$?
  report "gtt-project.sh think (THINK Depth)" "$THINK_RC"
  [ "$THINK_RC" -ne 0 ] && cat /tmp/gtt-validate-think.$$
  rm -f /tmp/gtt-validate-think.$$
fi

# Observation: the work against the frozen governed state. This fails only on what
# the governed state itself says must stop - a boundary ratified as BLOCKING, an
# observation the human rejected - and, under a Method Plan that says so, on a
# GOVERNANCE observation nobody has decided. Everything else is recorded, not failed.
# Read-only here (--dry-run): validating never rewrites the governance backlog.
if [ -f .gtt/scripts/gtt-observe.sh ]; then
  bash .gtt/scripts/gtt-observe.sh check --dry-run >/tmp/gtt-validate-observe.$$ 2>&1
  OBSERVE_RC=$?
  report "gtt-observe.sh check" "$OBSERVE_RC"
  [ "$OBSERVE_RC" -ne 0 ] && cat /tmp/gtt-validate-observe.$$
  rm -f /tmp/gtt-validate-observe.$$
fi

# The agent contract: its governance sections start where every ADE still reads (Codex cuts at 32 KiB).
if [ -f .gtt/scripts/gtt-check-agents.sh ]; then
  bash .gtt/scripts/gtt-check-agents.sh >/tmp/gtt-validate-agents.$$ 2>&1
  AGENTS_RC=$?
  report "gtt-check-agents.sh" "$AGENTS_RC"
  [ "$AGENTS_RC" -ne 0 ] && cat /tmp/gtt-validate-agents.$$
  rm -f /tmp/gtt-validate-agents.$$
fi

# Sources and designs: a registered source still matches its hash, and every Epic's design is
# complete - the same in every Method Plan and at every THINK Depth.
if [ -f .gtt/scripts/gtt_design.py ]; then
  run_check "gtt-source.sh verify (sources are immutable)" bash .gtt/scripts/gtt-source.sh verify
  bash .gtt/scripts/gtt-check-design.sh >/tmp/gtt-validate-design.$$ 2>&1
  DESIGN_RC=$?
  report "gtt-check-design.sh" "$DESIGN_RC"
  if [ "$DESIGN_RC" -ne 0 ]; then cat /tmp/gtt-validate-design.$$; else grep -E '^WARN ' /tmp/gtt-validate-design.$$ || true; fi
  rm -f /tmp/gtt-validate-design.$$
fi

# Continuity, review and Git: the workflow file is valid, the session state can be derived,
# nothing in GTT writes Git history, every overlay carries the same Git rules as the contract,
# and the GTT-AR rules are in the contract.
if [ -f .gtt/scripts/gtt_flow.py ]; then
  FLOW="bash .gtt/scripts/gtt-run-python.sh .gtt/scripts/gtt_flow.py"
  run_check "gtt-workflow.sh check (gtt-domain/workflow.md)" $FLOW workflow check
  run_check "gtt-status.sh --check (the session state can be derived)" bash .gtt/scripts/gtt-status.sh --check
  run_check "no GTT script or hook writes Git history" $FLOW check no-commits
  run_check "Git and workflow section identical in every overlay" $FLOW check overlay-block
  run_check "GTT-AR-01 to GTT-AR-10 in the contract" $FLOW check ar-rules
  # Size informs and never blocks: a WARN line, no effect on the exit code.
  OVER="$($FLOW review --gate 2>/dev/null | sed -n 's/^Human review: RECOMMENDED - //p')"
  [ -n "$OVER" ] && echo "WARN  change over the review threshold ($OVER): a human review is recommended"
fi

# Instruction plane, installed projects only (.gtt/ade.json exists; the catalog never has it): the
# protection engine must refuse a write to the engine itself. This asks the engine, so it proves the
# rule is live - a path list that looks right in a diff proves nothing. It says nothing about any
# ADE's own hook, which is verified inside that ADE or not at all.
if [ -f .gtt/ade.json ] && [ -f .gtt/scripts/gtt_protect.py ]; then
  bash .gtt/scripts/gtt-run-python.sh .gtt/scripts/gtt_protect.py decide --file .gtt/scripts/gtt-validate.sh >/tmp/gtt-validate-plane.$$ 2>&1
  PLANE_RC=$?
  if [ "$PLANE_RC" -eq 2 ] && grep -q "instruction-plane" /tmp/gtt-validate-plane.$$; then
    report "instruction plane protected (installed project)" 0
  else
    report "instruction plane protected (installed project)" 1
    echo "                   the protection engine allowed a write to .gtt/scripts/ in an installed project:"
    sed 's/^/                   /' /tmp/gtt-validate-plane.$$
  fi
  rm -f /tmp/gtt-validate-plane.$$
fi

bash .gtt/scripts/gtt-check-integrity.sh >/tmp/gtt-validate-integrity.$$ 2>&1
INTEGRITY_RC=$?
report "gtt-check-integrity.sh" "$INTEGRITY_RC"
[ "$INTEGRITY_RC" -ne 0 ] && cat /tmp/gtt-validate-integrity.$$
rm -f /tmp/gtt-validate-integrity.$$

# Session Memory adapter conformance: one result per declared adapter. The
# check is static and needs no ADE; runtime verification by the real ADE is
# never run here, so each line carries the DECLARED runtime status instead of
# implying it was proven. A staged (not yet promoted) adapter is labelled so.
#
# adapter_status describes the Bootstrap catalog, not this project: an adapter
# declared "installed" is checked against its native paths, which exist only
# where that ADE participates. With .gtt/ade.json, an ADE the human did not
# choose is therefore skipped, never failed. Without it (the catalog, or a
# project that predates multi-ADE) every declaration is checked, as before.
PARTICIPATING=""
if [ -f .gtt/ade.json ]; then
  PARTICIPATING="$(bash .gtt/scripts/gtt-ade.sh state --json 2>/dev/null \
    | bash .gtt/scripts/gtt-run-python.sh -c 'import json,sys; print(" ".join(json.load(sys.stdin).get("participating") or []))' 2>/dev/null || true)"
fi
for manifest in .gtt/session-adapters/*.json; do
  [ -f "$manifest" ] || continue
  ade="$(basename "$manifest" .json)"
  if [ -n "$PARTICIPATING" ]; then
    case " $PARTICIPATING " in
      *" $ade "*) ;;
      *) echo "SKIPPED            gtt-check-session-adapter.sh $ade (ADE not participating)"; SKIPPED=$((SKIPPED + 1)); continue ;;
    esac
  fi
  out="$(bash .gtt/scripts/gtt-check-session-adapter.sh "$ade" 2>&1)"
  rc=$?
  summary="$(printf '%s
' "$out" | grep '^SUMMARY ' | sed 's/^SUMMARY //')"
  if [ "$rc" -eq 0 ]; then
    echo "PASS               gtt-check-session-adapter.sh $ade  [$summary]"
    PASSED=$((PASSED + 1))
  elif [ "$rc" -eq 2 ]; then
    echo "CANNOT-DETERMINE   gtt-check-session-adapter.sh $ade"
    printf '%s
' "$out"
  else
    echo "FAIL               gtt-check-session-adapter.sh $ade"
    FAIL=1
    FAILED=$((FAILED + 1))
    printf '%s
' "$out" | grep -E '^(FAIL|SUMMARY)'
  fi
done

if [ -f .gtt/scripts/gtt_flow.py ]; then
  bash .gtt/scripts/gtt-run-python.sh .gtt/scripts/gtt_flow.py record-validation \
    --exit "$FAIL" --passed "$PASSED" --skipped "$SKIPPED" --failed "$FAILED" >/dev/null 2>&1 || true
fi

echo
GATE=0
if [ "$REVIEW" -eq 1 ] && [ -f .gtt/scripts/gtt-review.sh ]; then
  bash .gtt/scripts/gtt-review.sh --gate || GATE=1
  echo
fi
if [ "$FAIL" -ne 0 ]; then
  echo "gtt-validate: FAILED - see the FAIL line(s) above."
  exit 1
fi
if [ "$GATE" -ne 0 ]; then
  echo "gtt-validate: checks OK - the review gate stops on a BLOCKING condition."
  exit 1
fi
echo "gtt-validate: OK"
exit 0
