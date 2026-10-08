# Working inside a governed project

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Part of the agent contract. `AGENTS.md` points here, and what this file says binds exactly as if it
were written there. A section named in *italics* that is not in this file is a section of
`AGENTS.md` or of another file in this directory.

## Working without unnecessary interruption

> The developer decides what only the developer can decide. GTT does everything else.

Lower friction never means less governance. The policy is data -
`.gtt/contract/profiles.json` -> `developer_experience` - and applies in every
Method Plan; what is automatic, confirmed or proposed for each kind of operation is
the selected plan's own `plan.policy`.

**Before asking the human anything**, check whether the answer already follows from
governed context, the selected plan, project policies and working agreements, the
actual state of the project, or a deterministic rule. If it does: act, validate the
result, continue. If it does not: name the decision, explain it briefly, ask once.

**Do, do not ask.** Never turn these into a question:

- ordinary work - implementing, refactoring, testing, and writing, splitting or
  closing Stories (*The two planes*);
- an observation that is not `BLOCKING` - report it once, in one line, and continue;
- an occupied id - take the next free one: `bash .gtt/scripts/gtt-project.sh next-id --kind adr|epic|story`
  (it never reuses a retired id; under a plan whose id resolution is `propose_confirm`
  or `team_policy` the human confirms the number when reviewing the package, not in a
  separate question);
- rebuilding the index, syncing the GTTGuard registry, validating - after any
  operation run `bash .gtt/scripts/gtt-maintain.sh`, which does all three and reports
  in a few lines;
- continuing to the next planned task after a step succeeded;
- a policy the plan or a working agreement already defines.

**Protected and governed operations use one promotion, never a recipe.** When an operation
needs human authorization (approve, promote, advance a governed stage, copy, move,
delete, overwrite, modify a governed or protected artifact), stage the full content of
every file it touches as one promotion set - `bash .gtt/scripts/gtt-stage.sh <name>
--reason "<one line>" <staged file>=<destination> ...` - and give the one command the
human runs: `bash .gtt/scripts/gtt-promote.sh <name>`. **Never write an application
script by hand**, and never ask the human to reconstruct a command. You never run the
promotion: see *Human Promotion Boundary*. Once the human has run it, it has already
validated the result (`gtt-maintain.sh`); continue.

**STOP is not a general precaution.** Stop only for: a genuine architectural or
semantic conflict; a boundary the governed state declares `BLOCKING`, or an
observation the developer rejected; a decision only the developer can make; explicit authorization
required for a protected or governed operation; a safety or integrity condition that
prevents continuing safely; unresolved evidence required to continue correctly.
Reaching an intermediate mechanical step is never a reason to stop, and neither is an
observation that is not blocking.

**Say when it is GTT speaking.** Every message in which you speak on behalf of GTT
opens with `@gtt · <what this is>`, so the human always knows it is the method and not
the assistant's ordinary conversation: a question the method needs answered; a
confirmation or a choice (ADE participation, Method Plan, Confirmation A, Confirmation
B, an Epic's approval); an observation; the Initial Design Questionnaire, in every turn of the
interview; a proposal, a finding, a conflict or a STOP; a request for authorization;
a report. For example `@gtt · Method Plan`, `@gtt · Initial Design Questionnaire`,
`@gtt · Authorization required`, `@gtt · Observation`, `@gtt · Report`. Ordinary work GTT did not raise -
explaining code, answering a question, implementing a Story - carries no marker. The
marker is data (`developer_experience.dialogue.marker`) and identifies who is
speaking: it is never a decision, an approval or evidence.

**Report in at most 12 lines, in the user's language:**
1. One line: what is done and what is not.
2. The `gtt review` block when files changed - do not restate the files or diffs it shows.
3. `Decide:` only what the human must decide - numbered, at most three, each with its exact command.
4. `Next:` one line.
No step-by-step narration, no tables unless asked, no repeated content, no unrequested Git suggestions, at most one question. Give details when asked.

Detail is never withheld: give it when asked, or point to it (`gtt-review.sh --files`,
`gtt-maintain.sh --verbose`, `gtt-status.sh`, `gtt-query.sh`, the full output of a check).

```text
@gtt · Authorization required
Changes: AGENTS.md, .claude/settings.json - <one-line reason>
Run: bash .gtt/scripts/gtt-promote.sh <name>
Nothing was applied; it is your decision.
```

## Protected artifacts (GTTGuard)

GTTGuard is a lightweight, language-agnostic mechanism for marking a file,
class, or method so an AI coding agent may read, analyze, and propose a
change to it, but may never modify it autonomously. It is a **sibling** to
L0/L1 governance, not a restatement of it: it protects arbitrary L3 code
the developer opts into protecting, never `gtt-domain/context/` or `gtt-domain/adr/`, and
it must never be conflated with the Human Promotion Boundary of `AGENTS.md` — the
two are deliberately different weights of ceremony for different things.

**Core rule:** User proposes the protection → GTT implements it → Agent
respects it.

A developer marks a declaration with `@GTTGuard` (Java, Python), `[GTTGuard]`
(C#), or a `// @GTTGuard` / `# @GTTGuard` comment (other languages),
optionally with `reason=`/`source=`. `.gtt/scripts/gtt-guard-sync.sh`
detects every marker, resolves the file/class/method it protects
deterministically (never by LLM judgment), and regenerates
`.gtt/protection/registry.yaml` — a **derived artifact**, like a lockfile:
never hand-edit it, since `.gtt/scripts/gtt-check-protection.sh` fails the
build the moment the committed file drifts from what the markers in source
actually declare. Placing or removing the marker is an ordinary L3 edit —
it is the Solution Designer's proposal, not a protected change itself.

On Claude Code, `.claude/hooks/protect-guard.py` (a PreToolUse hook,
registered alongside `protect-l0.py`) blocks an autonomous edit to a
protected artifact in real time, resolving each protected symbol's exact
span live against the file on disk so an unprotected method next to a
protected one stays freely editable — and failing safe to whole-file
blocking whenever that resolution is ambiguous. Kiro, Codex, and GitHub
Copilot have no equivalent real-time block, the same honest limitation
already documented for the two-regime `gtt-domain/context/`/`gtt-domain/adr/` condition —
`gtt-check-protection.sh` in CI is the enforcement there, backed by an
instruction-plane note in each adapter. No ADE is credited with a guarantee
it does not actually have.

**Changing a protected artifact:** draft a proposal with `gtt-propose-change`
(form 5). Once the Solution Designer approves **in conversation** — not a
script run — implement the change directly, update or remove the marker,
and re-sync the registry. This promotion model is deliberately lighter than
the Human Promotion Boundary of `AGENTS.md` (no ADR, no `apply-*.sh` script):
GTTGuard protects L3 code the developer chose to flag, not L0/L1 governed
context, and the proposal that introduced this mechanism is explicit that
it "should not create a second, unrelated approval model."

Full procedure: `.claude/skills/gtt-guard/SKILL.md` (marking/unmarking) and
`.claude/skills/gtt-propose-change/SKILL.md` (form 5, changing a protected
artifact).

## Session continuity

Run `.gtt/scripts/gtt-status.sh` to regenerate `gtt-domain/session.md`: a
deterministic snapshot (freeze state and baseline, backlog focus, what observation found,
pending proposals, protected-artifact count, artifact identity and index state) derived from repository
artifacts, never from any ADE's private conversation memory — the same
project resumes the same way whether the next session is Claude Code,
Codex, Kiro, or Copilot. Treat it as operational context only: never
architectural authority, never evidence, never a substitute for an ADR or
decision record. An agent must never invent this state from memory instead
of running the script.

When a session starts with no GTT context injected - the ADE has no session hook, or it did
not fire - the first step is `bash .gtt/scripts/gtt-review.sh`: twelve lines that say what
changed, what it touches, what the human must decide and what comes next, computed from the
repository. `gtt-domain/session.md` opens with that same block. At the end of a turn
`bash .gtt/scripts/gtt-checkpoint.sh` refreshes it; a checkpoint is never a commit.

`gtt-domain/session.md` also reports the ADE integration state (Primary ADE,
participating ADEs, integration health, read from `.gtt/ade.json` through
`.gtt/scripts/gtt-ade.sh state`). It is portable across ADEs and records no "last
active ADE": several ADEs may run at once and would overwrite each other's entry,
and no deterministic source for it exists. It is operational state, never a
second memory architecture and never authority.

Working preferences are defined in *Provenance, gaps, sources and working agreements*; keep them in
an artifact separate from session state — they are not Canon, architecture,
evidence, or decisions, sit below governed gtt-domain/context/constraints in
precedence, must never silently override them, and no agent may author its
own preferences.

## Artifact identity and technical index

Every governed Markdown artifact has a stable identity (`.gtt/index/artifacts.json`)
independent of its path: a move or rename is reconciled, never treated as delete
+ create. Reference an artifact as `[[ID]]` (e.g. `[[ADR-007]]`) so the reference
survives moves. `.gtt/index/technical-index.json` is a DERIVED accelerator - for
locating concepts and sections (`.gtt/scripts/gtt-query.sh`) - never a source of
truth, never evidence in itself; the Markdown it points to is authoritative.
Regenerate it with `.gtt/scripts/gtt-index.sh`; never hand-edit it. After any move
run `.gtt/scripts/gtt-reconcile.sh` (dry-run first). `.gtt/scripts/gtt-check-integrity.sh`
(part of `gtt-validate.sh`) fails on unreconciled moves, duplicate logical identity,
broken or old-path references, unresolved `[[ID]]`, and a stale index. Agents
operate through these scripts and MUST NOT own an artifact's identity or authority,
and never rewrite frozen `gtt-domain/context/` or `gtt-domain/adr/` files to fix a reference.

## Validation

`.gtt/scripts/gtt-validate.sh` runs every deterministic check script
(`gtt-check-backlog.sh`, `gtt-check-adapter.sh`, `gtt-check-protection.sh`,
`gtt-check-stack.sh`, `gtt-check-provenance.sh`) and reports pass/fail/cannot-determine.
A Session Memory adapter is checked only for an ADE that participates: `adapter_status`
describes the Bootstrap catalog, not the project, so the adapter of an ADE the human did
not choose is skipped, never failed. Every ADE therefore validates on its own.
It also runs `gtt-observe.sh check`, which fails only on what the governed state says must
stop - a `BLOCKING` boundary, an observation the human rejected - and, where the Method Plan's
gate says so, on a `GOVERNANCE` observation nobody decided. Drift that is not blocking never
fails validation.
`.gtt/scripts/gtt-status.sh` reports what is current, governed, pending,
proposed, observed, blocked, and frozen. Both are read-only and deterministic;
neither substitutes for a human architectural judgment.

`gtt-check-adapter.sh` validates every participating ADE against
`.gtt/ade.json`: a missing or inconsistent integration FAILS, a detected ADE that
does not participate is a WARN, never a pass (`gtt-ade.sh validate` reports the
same per ADE). Without `.gtt/ade.json` it falls back to the single-ADE matrix of
projects that predate multi-ADE support.

## Provenance, gaps, sources and working agreements

One deterministic gate — `.gtt/scripts/gtt-check-provenance.sh`, part of `gtt-validate.sh` and of
`gtt-freeze.sh` — checks the four mechanisms below. It makes no architectural judgment and is never
authority; `gtt-status.sh` and `gtt-query.sh --governance <open|blocking|resolved|conflicts|sources|agreements>`
report them from the governed artifacts themselves. A project that has adopted none of them is unchanged.

- **Provenance.** In governed context and ADRs a claim is one of: `[FUENTE: ref]` (evidence from a declared
  source id, or a repo path with an optional `:line`), `[VACÍO: GAP-id]` (the authorised sources do not
  determine it; classified by a gap), `[CONFLICTO: a vs b]` (named sources disagree), or a
  `[PROPUESTA]`, which is reasoning output and **never** appears inside governed context (it stays in
  `gtt-domain/proposals/`). An unclassified `[VACÍO]`, a `[FUENTE]` that does not resolve, or a `[CONFLICTO]`
  that does not name its sources is a finding. The evidence boundary stays as stated in *Agent roles*:
  grounding retrieves, cites, declares absence and exposes conflicts; reasoning works on that dossier and
  proposes; neither decides.
- **Gaps: OPEN and BLOCKING.** The register is the `gtt-gaps` block in `gtt-domain/context/stack.md`
  (section 8). A **BLOCKING** gap must be decided before freeze: freeze is refused while one is pending, and a
  frozen design cannot carry one. An **OPEN** gap is known, undecided and not needed for the current design: it
  has an explicit `scope:`, crosses freeze, stays visible in status and query, and is **never an authorisation**
  — resolving it, or changing anything outside its scope, follows the normal path (change request → proposal →
  human decision → promotion → new freeze). A resolved gap is not deleted: it becomes an append-only
  `RESOLVED` line citing the ADR that resolved it.
- **Sources.** When there is more than one design source, or a provenance policy is wanted, they are declared in
  `gtt-domain/context/sources.md` (`gtt-sources` block): id, path, version, authority, precedence, status, and
  `policy: provenance=advisory|required`. Precedence must be unambiguous and is never decided by reading order.
  It orders sources for interpreting a conflict and never erases the conflict. After freeze `SOURCE-BRIEF.*` is
  evidence and history, never an authority; the governed context wins over it.
- **Working agreements.** Team agreements live in `gtt-domain/working-agreements.md` (versioned, reviewed);
  a person's own preferences in `.gtt/local/preferences.md` (local, never committed). Both sit below governed
  context, are not Session Memory, never override a governed decision (the gate rejects one that tries), and no
  agent authors its own.
