---
name: gtt-propose-change
description: Produce a GTT change proposal instead of applying a governance change directly. Use to triage the inbox (ideas and requests the human wrote), when the user says to process a request, when an architectural change is required, when a governed context file under gtt-domain/context/ is wrong or outdated, when implementation code conflicts with the governed context, when an Epic must be added, removed or its goal or scope materially changed, when the ratified development method (the Method Lock) must change, or when a change is requested to a GTTGuard-protected file/class/method. Triggers on any request to change architecture, paradigm, module boundaries, frameworks, cloud services, or infrastructure tooling, on any request to change an Epic, and whenever a permission denial points at gtt-domain/context/, gtt-domain/adr/, gtt-domain/proposals/, or a GTTGuard-protected artifact, and when the session's Next action says there are untriaged inbox entries (IDEA-NNN). NOT for ordinary work - implementing, refactoring, testing, or writing and closing Stories needs no proposal and no approval.
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

# GTT change proposal

> **Speaking for GTT.** Every message this skill raises to the human — a
> question, a confirmation, a proposal, a finding, a request for
> authorization, a report — opens with `@gtt · <what this is>`
> (e.g. `@gtt · Proposal`). The marker says who is speaking; it is never a decision.

Governed context is owned by the Solution Designer. You produce proposals; a
human decides. Do not implement the change, do not partially apply it, and do
not create the ADR yourself.

## Triage (the first thing to do with an inbox entry)

The human writes `IDEA-NNN` (an idea, or a request with fields) in `docs/ideas/`; you write `PROP-NNN`.
Triage is yours: you read each entry that is in stage `new` and give it one result. Do it at a cut point
(the session start, or when you have no Story of your own `In Progress`), never in the middle of a Story;
an entry written with `--now`, or an accepted urgent one without a package, goes in your first answer.
List them with `bash .gtt/scripts/gtt-inbox.sh list` and read one with `gtt-inbox.sh show IDEA-n`.

| Result | When | What you do | REV? |
|---|---|---|---|
| `work` | It fits in an approved Epic and does not touch the design | Write the Story (with `- **Origin:** IDEA-n`), then `gtt-inbox.sh triage IDEA-n --result work --to STORY-m` | No |
| `covered` | An Epic, idea or proposal already covers it | Cite the ref: `triage --result covered --to EPIC-n\|IDEA-n\|PROP-n` (opens an informative DEC) | No |
| `scope` | It asks for a new Epic, removing one, or changing an Epic's goal | Write a PROP with Form 4 | Yes |
| `spec` | It changes an Epic's design, the glossary, the vision or the principles | Write a PROP with Form 2 or 4 | Yes |
| `arch` | It touches architecture, constraints, the map or a technology | Write a PROP with Form 1, 2, 3, 6 or 7 | Yes |
| `non-goal` | It clashes with a non-goal of `solution-vision.md` | Write a closing PROP | Yes |
| `ask` | A fact only the human has is missing | Open an ASK, then `triage --result ask --to ASK-n` | No |
| `incorporated` | Before the freeze | Carry it into the design draft: `triage --result incorporated --to <file>` | No |

**Level rule:** when two levels are plausible, choose the higher one. The engine corrects it at the end
(it records a CHANGE, not an ADR, when no architecture file is touched). The human confirms the level in the REV.

A level `work` entry needs no proposal and no question. For `scope`, `spec`, `arch` and `non-goal`,
write the proposal (below) and register it; the triage line is added by `propose` itself.

## Registering a proposal

1. Write your draft in `gtt-domain/proposals/drafts/<slug>.md`, in the form of this skill that fits.
2. Register it:

   ```bash
   bash .gtt/scripts/gtt-inbox.sh propose --file gtt-domain/proposals/drafts/<slug>.md \
     --level arch|spec|scope|work --form <1-7> [--origin IDEA-n|OBS-n|STORY-n]
   ```

   The engine validates the form, writes `gtt-domain/proposals/PROP-NNN-<slug>.md`, opens the `REV-NNN`
   in `gtt-domain/pending/` and stores the sha256 of what the human will see. From then on the PROP is the
   engine's: you cannot edit it.
3. To correct it, or to re-triage after the human answers "this is architecture, not spec", write a new draft
   and run `gtt-inbox.sh supersede PROP-n --file <draft>`: it closes the open REV and opens another.
4. State the REV in chat as the session asks (`@gtt · Necesito tu decisión`), and stop. You never accept,
   reject, park, reopen or change the priority of an entry: those are the human's (`gtt answer`,
   `gtt inbox park|reopen|reject|priority`). When the human answers in chat ("15: 1"), record their exact words
   with `gtt-pending.sh record --quote`.

Once accepted, build the package (see the end of this skill) with `gtt-stage.sh ... --origin PROP-n`; after the
freeze it refuses to stage a set that touches `gtt-domain/context/` or `gtt-domain/adr/` without an `--origin`
that is in stage `accepted`.

## First: is this governance at all?

A proposal means "this may need a governance decision". It is never a request
for permission to do ordinary work (`AGENTS.md` → *The two planes*).

| The change | What to do |
|---|---|
| Implementation: a refactor, a bug fix, tests, an internal reorganisation, an optimisation | Do it. No proposal. |
| A Story: creating, splitting, rewriting, closing one | Edit `gtt-domain/backlog.md`. No proposal. |
| The governed design: architecture, a boundary, a governed technology, an API contract, a constraint, an Epic's goal or scope, a protected artifact | A proposal - this skill. |

If you are about to write a proposal for the first two rows, stop: you would be
putting the human back into the loop of ordinary work.

## Where the request comes from

The Solution Designer's intent reaches you as an inbox entry: `IDEA-NNN` in `docs/ideas/` (`Tipo: idea`, or
`Tipo: solicitud` when it carries the fields Change, Reason, Trigger, Scope, Impact, Risk and Priority), or
whatever the user just described. `gtt-domain/change-request.md` is retired as a desk: `gtt change` is a shortcut
for `gtt idea add --type solicitud`, and a leftover request is migrated into an `IDEA` by `gtt update`
(`gtt-inbox.sh migrate`). Read the entry for what it actually decides; a raw pasted paragraph is valid input, do
not ask for the fields first. An empty one is not a request: say so and stop, do not invent one.

Several requests can wait at once. A `--now` one is processed in your first answer, whatever the first message
says. Processing is triage and drafting; the decision stays the human's. Never edit the text of an `IDEA`.

## Where the output goes

Your drafts go to `gtt-domain/proposals/drafts/<slug>.md` (free). The registered `PROP-NNN-<slug>.md` is written
only by `gtt-inbox.sh propose`. Before the freeze there are no proposals: write the governed context directly
(`proposals/bootstrap/`, as THINK does) and triage ideas as `incorporated`.

## Before writing

Read what the change actually touches: `gtt-domain/context/stack.md` always, plus the
relevant context files and any ADR the affected stack rows point to in their
"Locked by" column. A proposal that ignores the decision it overturns is not a
proposal.

If the request is about an Epic instead - a new one, removing one, or a
material change to its goal or scope - read `gtt-domain/backlog.md` first, and
check whether it contradicts governed context or an accepted ADR before
drafting (see *Precedence* in `AGENTS.md` → *Backlog*). Stories are not a change
request at all: they are the working plan and are edited directly.

If the request changes the development method - another Method Pack, a pack
added to or dropped from the combination, a different start, or an `OPEN` method
being decided after the freeze - use Form 6: it is an architecture change with a
mandatory impact analysis, never a direct edit of the `gtt-method` block, and never
a new run of the setup questionnaire. Read the Method Lock
(`bash .gtt/scripts/gtt-method.sh get`) and both packs (`gtt-method.sh show <id>`)
first.

If the request is a change to a file, class, or method carrying a
`@GTTGuard` marker — check `.gtt/protection/registry.yaml` — use Form 5
below; it is neither an architecture change nor a backlog change.

## Forms

Pick the one that matches the situation.

## 1. Architecture change

Use when the solution needs a different architectural direction, style,
paradigm, module boundary, integration strategy, deployment strategy, framework,
runtime, datastore, or cloud service.

```text
Proposed Architecture Change

Current decision:
Suggested change:
Reason:
Impact:
Risk:
Affected files:
Alternatives considered:

Status: Requires Architect approval
```

## 2. Context change

Use when a file under `gtt-domain/context/` is inaccurate, stale, or contradicts
reality — and the fix is to the document, not the code.

```text
Proposed Context Change

File:
Current statement:
Suggested change:
Reason:
Impact:
Risk:

Status: Requires Solution Designer approval
```

## 3. Context conflict

Use when implementation and governed context disagree and you cannot tell which
one is correct. Do not resolve it yourself and do not pick the code by default.

```text
Context Conflict Detected

Context file:
What the context says:
What the implementation does:
Where they diverge:
Possible resolutions:

Status: Requires human review
```

## 4. Epic change

Use when `gtt-domain/backlog.md` needs an Epic added, removed, or its goal or
scope materially changed. An Epic is intent and scope - the one part of the
backlog the human decides. Not for Stories: those are the working plan and are
never proposed or approved.

```text
Proposed Epic Change

Kind: <new Epic / remove / material change of goal or scope>
Epic ID: <EPIC-NNN, or "new" if not yet assigned>
Current state: <what gtt-domain/backlog.md says today, or "none" if new>
Goal:
Scope:
Out of Scope:
Reason:
Contradicts governed context or an ADR?: <no / yes — cite file:line>
Impact:
Risk:

Status: Requires Solution Designer approval
```

If the request would contradict governed context or an accepted ADR, say so
explicitly rather than quietly aligning the Epic to the architecture - that
contradiction is exactly what the Solution Designer needs to see and decide.

Write the Epic into `gtt-domain/backlog.md` as `Proposed`, with
`**Design:** gtt-domain/context/design/EPIC-NNN.md`, and draft that design
(`bash .gtt/scripts/gtt-design.sh scaffold EPIC-NNN --apply`): the complete specification of the
Epic, carried over from the sources and cited. After the freeze the draft lands under
`gtt-domain/proposals/` and reaches its place through a promotion set - a specification change, no ADR.
The human approves the Epic and its design together with `bash .gtt/scripts/gtt-approve.sh EPIC-NNN`;
you never write `Approved`. The Stories under it are yours and need no approval, in this format:

```markdown
##### STORY-NNN — <title>
- **Status:** Planned
- **Implements:** design/EPIC-NNN#R-2, #F-1, #E-1 · ADR-NNN
- **Done when:** E-1 passes (Given … when … then …) · <test file>
```

A Story cites the design; it never cites a source directly and never decides.

## 5. Protected artifact change (GTTGuard)

Use when the requested change touches a file, class, or method that
`.gtt/protection/registry.yaml` lists with `protection: HUMAN_APPROVAL`.
This is not an architecture change and not a backlog change — GTTGuard is a
sibling mechanism protecting L3 code the developer opted into protecting,
not `gtt-domain/context/` or `gtt-domain/adr/`. See `AGENTS.md` → *Protected artifacts
(GTTGuard)* before using this form.

```text
Protected Artifact Change

Artifact: <file path>
Symbol: <ClassName, ClassName.method, or "whole file">
Current behavior:
Suggested change:
Reason:
Source (if any, e.g. an ADR or ticket the protection traces to):
Impact:
Risk:
Alternatives considered:

Status: Requires Solution Designer approval
```

**Promotion is lighter here than Forms 1-3.** There is no ADR and no
promotion set — GTTGuard is deliberately not a second, unrelated
approval model; it reuses this proposal mechanism, nothing heavier. Once
the Solution Designer approves
**in conversation**, implement the change directly, update or remove the
`@GTTGuard` marker as appropriate, and run `.gtt/scripts/gtt-guard-sync.sh`
so the registry reflects it. Do not treat this approval as covering any
other protected artifact, and do not confuse this with the L0/L1 Human
Promotion Boundary — that one still requires the Solution Designer to run a
script themselves, this one does not.

## 6. Development method change

Use when the ratified development method must change: the Method Lock in
`gtt-domain/context/architecture.md` (block `gtt-method`) names other packs, a
pack is added to or dropped from the combination, the start strategy changes, or a
method left `OPEN` at the freeze is now decided. The method was ratified with the
design, so this is a governed change - an architecture change when a pack requires
an ADR (`requires_adr: true`), and always with an impact analysis. `select` is
refused after the freeze and `gtt init` does not ask again: this form is the only
way.

```text
Proposed Development Method Change

Current method: <the Method Lock as `gtt-method.sh get` prints it - style, start, locked_by, verification>
Proposed method: <style, start - Method Pack ids>
Reason:
Incompatibilities: <pairs the packs declare incompatible, or "none" (gtt-method.sh select --style ... dry run says)>

Impact analysis (all four are required):
- Slices or modules reorganised: <which folders, Epics and Epic designs change shape, and how>
- Rules of stack.md that change: <section 5 rows removed (ids), rows added (ids, with real paths)>
- ADR replaced: <ADR-NNN that locks the current method -> the new ADR that supersedes it, or "none">
- Backlog and designs: <Epics re-cut, `Kind` fields that change, designs whose section 1 changes template>

Verification level: <current -> proposed (the weakest of the proposed packs)>
Risk:
Alternatives considered:

Status: Requires Solution Designer approval
```

Never fill the impact analysis with "to be determined": a method change that
cannot say what moves cannot be decided. Once approved, it is recorded with the
`gtt-adr` skill like Forms 1-3: the promotion set carries the new ADR (superseding
the old one), the new `gtt-method` block and the `Development method` row, the
changed section 5 rules and the map change log row; the human promotes it and runs a
new freeze, whose `gtt-method.sh check --pre-freeze` verifies the result. The
re-cut of Epics and designs follows as specification changes (no ADR), and the
code moves as ordinary work afterwards.

## 7. Autonomy Profile change (frozen project)

Use when the human wants a *less* strict Autonomy Profile after the freeze (Hard -> Medium, Medium -> Light, and so on) because
the method feels like too much, or a *stricter* one is wanted but you were asked to record it formally. Stricter changes
need no proposal: `gtt autonomy set <plan>` is allowed. A less strict plan is refused after the freeze, so this form is the
only way. Never recommend the change yourself: you write this proposal only when the human asked for the change.

Read `bash .gtt/scripts/gtt-contract.sh show profiles`, the `relaxes` and `semantics` of both plans, so the impact is the
contract's words, not yours.

```text
Proposed Autonomy Profile Change

Current plan: <id>
Proposed plan: <id>
Reason: <what the human finds heavy, in their words>
Controls that relax: <the `relaxes` of the proposed plan and every `semantics` entry that differs, as the contract states them>
Unchanged in every plan: human decision authority, governed decisions confirmed, destructive operations confirmed, freeze
Risk: <what the project loses in oversight and how it would be noticed>
Alternatives considered: <staying, or a single stricter-but-lighter step>

Status: Requires Solution Designer approval
```

Once approved, record it with the `gtt-adr` skill: the ADR must contain the exact line `Autonomy Profile: <current> -> <proposed>`
and `Status: Accepted`. The human promotes it, then applies it with
`bash .gtt/scripts/gtt-project.sh profile set --profile <proposed> --adr ADR-NNN --apply` (or
`gtt autonomy set <proposed> --adr ADR-NNN`), and runs a new freeze. The agent never runs that command.

## Quality bar

A proposal is only useful if it can be decided without a follow-up question.

- Name the specific decision being changed, not the general area.
- Impact means blast radius: which modules, which interfaces, which deployments.
- Risk means what breaks if this is wrong, and how it would be detected.
- List at least one alternative and say why it loses.
- If you cannot fill a field honestly, say so rather than inventing it.

## After writing

Register the proposal (`gtt-inbox.sh propose`), then summarize it in two or three lines in chat, with the REV the
engine opened, so the decision can be made without opening the file. Then stop.

Once the human accepts (`gtt answer N 1`, or "N: 1" in chat), you build the package. For architecture, context,
conflict, method and autonomy proposals (forms 1-3, 6 and 7) the decision is recorded with the `gtt-adr` skill, which
stages the ADR, the affected context files and an executable promotion script together, with
`--origin PROP-n`; the human runs `gtt promote` (a new freeze follows), and the agent never applies the change itself
(the Human Promotion Boundary, `AGENTS.md`). A specification change (an Epic's design) is staged the same way,
without an ADR: the engine records a CHANGE. An Epic proposal (form 4) is accepted by the human, who then approves it
with `gtt approve EPIC-n` (after the freeze, `gtt run n` carries both the design promotion and the approval). A
protected-artifact proposal (form 5) is approved in conversation - once the Solution Designer says so, implement it
directly, update the marker, and re-sync the registry; no ADR, no script, and never treat it as approval for a
different protected artifact. Work derived from an accepted entry is written as Stories with `- **Origin:** PROP-n`.
