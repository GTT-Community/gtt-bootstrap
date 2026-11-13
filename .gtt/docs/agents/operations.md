# Working inside a governed project

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

Part of the agent contract. `AGENTS.md` points here, and what this file says binds exactly as if it
were written there. A section named in *italics* that is not in this file is a section of
`AGENTS.md` or of another file in this directory.

## Working without unnecessary interruption

> The developer decides what only the developer can decide. GTT does everything else.

Lower friction never means less governance. The policy is data -
`.gtt/contract/profiles.json` -> `developer_experience` - and applies in every
Autonomy Profile; what is automatic, confirmed or proposed for each kind of operation is
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
confirmation or a choice (ADE participation, Autonomy Profile, Confirmation A, Confirmation
B, an Epic's approval); an observation; the Initial Design Questionnaire, in every turn of the
interview; a proposal, a finding, a conflict or a STOP; a request for authorization;
a report. For example `@gtt · Autonomy Profile`, `@gtt · Initial Design Questionnaire`,
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

**Handing a human act over.** Whatever the human must run, the message is one and the same, built by a script so
that the command is exact: `bash .gtt/scripts/gtt-handoff.sh promote <set> | approve <EPIC-NNN> | accept|reject|defer <OBS-NNNN> | freeze | run <n>`.
It prints `@gtt · For you` (`@gtt · Para ti` in Spanish), what is asked, what it changes, what it blocks and the command, and it refuses
(exit 1, saying why) when the set, the Epic, the observation or the plan does not exist, so a command that cannot work
is never shown. Show its output as it is. Nothing was applied; it is the human's decision.

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
stop - a `BLOCKING` boundary, an observation the human rejected - and, where the Autonomy Profile's
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

## The change flow during development

The human can drive a governed change from the CLI as well as by editing files; both reach the same
artifacts, through `.gtt/scripts/gtt-change.sh` (operations `change.*`, `proposal.*`, `promotion.*`).

- **Request.** `gtt change` writes `gtt-domain/change-request.md` with an `Id: CR-...`. While no proposal
  cites that id, the session's `## Next action` tells every ADE to process it on the first turn:
  `gtt-propose-change`, with `Request: CR-...` in the proposal. You draft; you never apply.
- **Proposals.** `gtt proposals` lists the drafts, ADR drafts and staged promotion sets, with their state.
  A draft the human withdraws is archived in `gtt-domain/proposals/withdrawn/`, never deleted; do not
  revive it unless the human asks.
- **Promotion.** `gtt promote <set>` is the human's act, exactly as `gtt-promote.sh`.
- **One step back.** `gtt undo` puts back what the last promotion replaced, only while its files are as it
  left them. If that promotion recorded a freeze, a new freeze records the earlier state: there is still
  no unfreeze, and the history keeps every baseline. Anything older is a change request.

## Observation

During work GTT observes; it does not approve. `.gtt/scripts/gtt-observe.sh`
compares the project with the frozen governed state - Git, the filesystem,
dependency manifests, the GTTGuard registry, the freeze baseline: computed facts,
never a model's opinion - and keeps every meaningful deviation in the governance
backlog (`gtt-domain/governance-backlog.json`). The boundaries it watches are
declared in the `gtt-boundaries` block of `gtt-domain/context/stack.md`, which the
human ratifies at freeze.

| Level | What it is | What you do |
|---|---|---|
| `NOTICE` | informational | nothing - it is recorded |
| `WARNING` | meaningful drift | say it in one line and keep working |
| `GOVERNANCE` | a boundary of the design was crossed | say it and keep working; if the design itself must change, draft the proposal |
| `BLOCKING` | a state the governed design prohibits | stop the affected operation, fix it or tell the human; everything else continues |

The levels are named, never numbered: L0 and L1 already mean the governed context
and the ADRs.

- **Continue unless blocking.** Only a `BLOCKING` observation, or one the human
  explicitly rejected, interrupts work. An observation that is not blocking is
  never a reason to stop, to ask for approval or to wait.
- **Blocking is explicit.** Something stops only because the governed state says
  so - a boundary declared `BLOCKING`, a rejected observation, a governed path, a
  GTTGuard artifact - and the block names its rule. Never treat something as
  blocking because it looks unusual.
- **Run it; do not reason it.** Observe by running the script - after a meaningful
  change, and it also runs whenever `gtt-status.sh` does - never by judging the
  diff yourself. A fact a script can compute is not established by an agent's
  opinion, and no agent supervises another agent as governance.
- **Silent by default.** No signal, no message. Report an observation once, when
  it is new.
- **The decisions are the human's.** `gtt-observe.sh accept | reject | defer`,
  `gtt-freeze.sh` and `gtt-git-hook.sh install | remove --apply` are run by the human,
  never by an agent, and an agent never writes `gtt-domain/.frozen` or
  `gtt-domain/governance-backlog.json` itself. Accepting an observation
  ratifies nothing: if the governed design must change, that is still a change
  request and a new freeze.
- **A proposal is not an approval request.** Write one when something may need a
  governance decision - never to ask permission for ordinary work.

`.gtt/scripts/gtt-git-hook.sh install` (the human's choice) runs the same check
before each commit: Git is the first control every ADE shares, whatever hooks an
ADE has or lacks. It is not the guaranteed one - a local pre-commit hook is skipped
with `git commit --no-verify`, which an agent never does while the hook is installed.
The guaranteed layer is CI: `gtt-validate.sh` and `gtt-check-stack.sh` on the pull
request, which also fail when the freeze marker was removed or its history rewritten.

The architecture as data: `.gtt/contract/profiles.json` -> `two_planes`.

## Backlog in detail

**What keeps Stories honest is observation, not approval.** If the work behind a
Story crosses a boundary of the frozen design - a new backbone technology, a
changed contract - observation reports it whatever the Story said, and that is
where governance enters (*The two planes*).

**Work the human asks for directly needs no Epic first.** Do it, and record it
under *General Development Work*, or as a Story if it is worth resuming. If
defined Epics exist elsewhere (a requirements document, an issue tracker) but
are missing from the backlog, report the gap. Never invent business Epics and
present them as user-defined requirements: a proposed Epic stays `Proposed`
until the human approves it.

**Fields Sonar reads.** A Story may carry, besides `Status`, `Estimate`, `Done when` and `Closed`: `Release:` (which
release it belongs to: `v1`, `v1.1`; a name or note that says `post-`, `out of scope` or `deferred` leaves it out of the
in-scope progress), `Frente:` / `Front:` / `Lane:` (the front that carries it) and `Blocked by:` (why it waits, in one
line, in your own words; `—` means nothing). Write them as you work: Sonar shows the progress by release and by hours, what
is in progress by front, and the reason of each blocked Story, without anyone asking in the chat.

**Project health.** A check the project already runs (an audit, a pace or coverage script) can leave its result in
`.gtt/local/health/<id>.json` as `{"title": "...", "status": "ok|warn|fail", "detail": "...", "at": "YYYY-MM-DDTHH:MM:SSZ"}`;
Sonar only reads these files (it never runs a command of the project) and marks one older than 48 hours as out of date.

An Epic is `Completed` only when every one of its Stories is `Done` or
`Cancelled`. `.gtt/scripts/gtt-check-backlog.sh` keeps the structure sound -
unique ids, the status vocabulary, an Epic that is `Planned`, `In Progress` or
`Completed` carries its `Goal` and its `Approved`, a `Completed` Epic has no
open Story - and reports, without failing, a `Done` Story with no `Closed` and
Stories being worked under an Epic that is still `Proposed`. It approves
nothing; whether an Epic is real and current is a judgment for the `gtt-audit`
skill.

## Delivery planning

GTT plans and watches delivery time; it does not launch agents. In `.gtt/docs/delivery.md`.

- Estimate in agent hours plus human decision points; never in weeks of a person.
- While fewer than 3 Stories are measured, the plan is uncalibrated: say it.
- An Epic over its cap is proposed (split, integrate, cut or accept), never decided: `Budget`, `Owner` and `.gtt/delivery.json` are the human's.
- Work only inside the `Touches` of your front; if you need another front's paths, report it.
- A backlog must be sizeable: when you write an Epic or its Stories, give each Epic an `Estimate` (or its Stories theirs) in the same turn. `DLV-NO-PLAN` says when it is not, even if planning was never declared; say it in one line and size the backlog.
- Close in the same turn: when a commit completes a Story, set `Status: Done` and `Closed:` (date and commit) before you go on. `DLV-STALE-STATUS` names the ones left behind.
- One rhythm: read `pace` (`gtt-delivery.sh get`) before you write a plan, status or order, and speak only in it (`days`, or `flow` = agent hours, no "day N"). `DLV-PACE-DRIFT` lists the documents that disagree. Changing the pace is the human's `gtt delivery set --pace`, one place, never a rewrite by hand.
- At the start of a session the context may end with `## Tell the human`: say those lines in one line each in your first report (never every turn) and offer `gtt delivery review`. A plan under the minimum the human set (`DLV-UNDER-TARGET`) is made fuller by you (detail, split and estimate Stories: no approval); a new Epic or a wider scope is a proposal.
- Size is the human's judgement: report it (`gtt-delivery.sh size`), never decide that a project is too big or too small. On `DLV-GROWTH` or `DLV-OVER-TARGET` say it in one line with the numbers and point to `gtt delivery review` (keep, set a cap, one pass, slim down). Cutting or merging an Epic is a proposal (`gtt-propose-change`, form 4), never done on your own.
- Run `.gtt/scripts/gtt-delivery.sh` for the plan, the forecast and the report; never estimate by judgment what it computes. `gtt-domain/delivery-log.jsonl` is written only by `gtt-delivery.sh log`.

## Simple execution

When the human has to execute something, give them one line saying what it does and one command, never a sequence to assemble.

- **Threshold.** A governed act (promote, freeze, approve) keeps its own command: `gtt promote <set>`. Anything that changes state, or takes two or more commands, is a run plan. A single read-only command may be given inline.
- **The plan.** `bash .gtt/scripts/gtt-run.sh new <slug> --apply` creates `gtt-domain/run/RUN-NNN-<slug>.md`. Fill in *What it does*, *Why*, *Changes* (`none | environment | data | code`) and the `gtt-run` block (`check:`, `step: <title> | <command>`, `next:`). You write the plan, never the script.
- **The script.** `bash .gtt/scripts/gtt-run.sh generate RUN-NNN --apply` makes the script from a fixed template, seals it with the plan's sha256 and reviews it (RUN-01 to RUN-12: no writes to governed paths, no Git history unless `commits: allowed`, no `rm -rf` outside temporary folders, no download piped into a shell; `sudo` and network are warnings; the script must parse, name only files that exist, and, when it changes only code or nothing and every step is a script of the project or a basic file utility, it is rehearsed in a throwaway copy: it must exit 0 and leave `gtt-validate.sh` no worse; any other tool is not rehearsed, and that never blocks). If the review fails, fix the plan and generate again; do not hand it over.
- **The hand-over.** Say exactly the message `generate` prints (`@gtt · To run`, what it does, `gtt run <n>`). `gtt run` lists what is pending.
- **Never** edit a generated script, run `gtt run <n>` or `gtt-run.sh execute` (the hook denies it), or write `gtt-domain/run/done/` or `log.jsonl`. A hand-edited script is refused (RUN-05). The human's run is logged and, when it succeeds, archived in `gtt-domain/run/done/` (the last 20 are kept).

## Pending events

What waits for the human is one small file per event in `gtt-domain/pending/`, and only that. Normally the folder is empty. Only `.gtt/scripts/gtt-pending.sh` writes it.

- **Settle it yourself first.** (1) If governed context, the design or a project rule settles it, decide and continue. (2) If it is a simple, reversible question, take the simplest option and continue, with no event. (3) Only a decision that is the human's (an account, a key, money, a legal matter, a product matter, a governed file) and that cannot be undone easily becomes an event.
- **Two kinds.** A question (`ASK`) is a decision only the human can take, and it is rare: it is asked only when something cannot continue without the answer (a product or governed question must name the Story or Epic it blocks with `--blocks`; at most 4 are open at once; never the same one twice). Questions reach the human in the chat, never as a pointer to a file: show the open ones as one batch (up to four) by running `bash .gtt/scripts/gtt-pending.sh show` and pasting its output under `@gtt · Needs you (N)`; the event file is the silent record, so do not announce files and mention one only for a proposal or something to review outside the chat. Its form is always the same, exactly as the file reads: `--header` (the topic, up to 24 characters), the question with what the answer closes, 2 or 3 `--option "short answer | what I will do if you choose it"` with the recommended one first, and the engine adds the two closing lines (something else, talk about it in the chat). `gtt-pending.sh ask --type <account|key|money|legal|product|governed> --question "...?" --why "..." --option "..." --option "..." --recommended N [--blocks STORY-NNN] --apply`. A decision (`DEC`) is something you decided that changes scope, time, cost, security or the design: `gtt-pending.sh decide --affects <scope|time|cost|security|design> --title "..." --what "..." --why "..." --where <path|STORY-NNN|ADR-NNN> --apply`. Anything else is not an event: ordinary technical detail goes in the code, an agreement between fronts in the contract, a change of the governed design through `gtt promote`.
- **Plain words.** At most 12 lines per file and 120 characters per line; the question is one line ending in «?»; 2 or 3 options, one recommended; the type or `Affects` is one of the list. The engine refuses a file that does not fit: shorten it, split it in two events, or put the detail in the code.
- **The answer is the human's.** They answer in the chat («14: 1», «ok to all»), in the file after `Answer:` or with `gtt answer 14 1`. You never write it. If they answered in the chat, write it down with `gtt-pending.sh record <n> <answer> --quote "<their exact words>" --apply` (`record all ok` for «ok» to every decision); the engine checks the quote against their last 10 messages and refuses anything else. An answer that looks like a key is refused: keys go in `.env.local`. `gtt answer` and `gtt-pending.sh answer` are denied to you.
- **Apply it, cite it, mark it.** When an answer exists, apply it where it belongs (the backlog, the code or a proposal), cite it there, then `gtt-pending.sh done <n> --in <where> --apply`. A decision answered «ok» is marked by the engine. The next session deletes what is marked and the decisions nobody objected to in 7 days; an answered event that is not marked is never deleted. An answer never ratifies the governed design: that stays `gtt promote`.
- **Do not stop.** With no answer, use the recommended option and keep working on everything that does not depend on it.
- **Tell the human once.** If something is pending, end your report with `@gtt · Needs you`: print `bash .gtt/scripts/gtt-pending.sh notice --report` (it prints nothing the second time in a turn). A decision shows as «For your information».
- **Sonar shows the rest; the chat does not repeat it.** `gtt sonar` draws everything that waits for the human (questions with one command per option, Stories that are `Blocked`, Epics to approve) from the files, at no token cost. So: (1) whatever waits for the human is recorded where Sonar reads it, never only in the chat: a decision or a key as an event (`--blocks STORY-NNN` when it holds a Story), a Story that cannot continue as `Blocked` in the backlog; (2) after the batch has been shown once, do not list or tabulate pending items again in later reports: say in one line that `gtt sonar` has them; (3) never build a table of what the human owes in the chat; (4) a decision the human owes is an event the moment it appears, not a line in a later summary: what lives only in the conversation Sonar cannot show and the next session loses; (5) the session context carries a `## Sonar` line: say it once, in your first report, as it reads (it tells where the page is and how many things wait), never again. This changes where the information lives, not who decides: Sonar only copies commands, and the answer stays the human's.

## Agent roles and the evidence boundary

GTT distinguishes four responsibilities. No skill or script may collapse
them into one:

| Role | Does | Never does | This repo's mechanism |
|---|---|---|---|
| Grounding | Retrieves and exposes governed evidence faithfully | Decide architecture | `gtt-bootstrap`, `gtt-audit` reading `gtt-domain/context/`, `gtt-domain/adr/`, `gtt-domain/backlog.md` |
| Reasoning | Analyzes evidence, drafts gtt-domain/proposals/ADRs | Authorize its own draft | `gtt-propose-change`, `gtt-adr`, `gtt-drift-response` |
| Validation | Runs deterministic structural checks | Make an architectural judgment | `.gtt/scripts/gtt-check-*.sh`, `gtt-validate.sh` |
| Observation | Computes what the work did against the frozen governed state and records it | Approve, decide or block without an explicit rule | `.gtt/scripts/gtt-observe.sh` |

The chain is: Sources → Grounding → Evidence Dossier (governed context as
read) → Reasoning → Proposal → Human Decision → Freeze. A reasoning step
must never receive raw sources "for context" in a way that bypasses
grounding — read `.gtt/docs/docs.md` → *Governance model* for the full
rationale. Producing output, of any kind, never grants an agent decision
authority.
