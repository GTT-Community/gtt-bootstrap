# GTT Bootstrap — Method Plans

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

A **Method Plan** answers one question: *how much of the operational work do you
delegate to GTT?* You choose an intention — Light, Medium, Hard or Team — and GTT
derives the technical policies from it. You are never asked to configure an index
policy, an identity policy or a validation policy one by one.

This page is the human-readable rendering of `.gtt/contract/profiles.json`. That
file is the single definition; if the two ever disagree, the contract is right and
the disagreement is a defect to report.

## What a plan is, and what it is not

- A plan is an **operating and collaboration profile**. It sets how often GTT stops
  to ask you, and what a team must have in place.
- A plan is **not a quality level**. Light is not "worse" and Hard is not "better":
  they fit different situations.
- A plan **never turns governance off**. The rules in the next section hold in all
  four.

## What no plan changes

These hold in every plan. No selection, ADE or automation level weakens them, and
the contract check fails if a plan tries.

| Rule | What it means for you |
|---|---|
| Human decision authority | Agents prepare; only a human decides, ratifies and freezes. |
| Governed decisions are always confirmed | A change to `gtt-domain/context/`, `gtt-domain/adr/`, the structure of the backlog, a GTTGuard-protected artifact or the freeze always needs your explicit decision. |
| Destructive operations are always confirmed | Nothing that cannot be regenerated is removed or overwritten without asking. |
| Proposals are never decisions | A `[PROPUESTA]` never appears inside governed context. |
| Conflicts stay visible | A conflict between sources is exposed, never silently resolved. |
| Freeze is a ratification | There is no unfreeze shortcut; frozen context changes only through the governed path. |
| Protected artifacts | GTTGuard-protected code and frozen context are never modified autonomously. |

## Vocabulary

The plans are described with four terms. Each has one meaning:

| Term | Meaning | Examples |
|---|---|---|
| Deterministic operation | The result follows entirely from the repository and the declared policy; no judgment is involved. | Allocating the next free id, rebuilding the index, regenerating the GTTGuard registry, running validation |
| Relevant change | An automated operation that rewrites files people or ADEs read, rather than derived ones. | Updating references across documents after a move, synchronising ADE context files |
| Destructive operation | Removes or overwrites something that cannot be regenerated. | `clean`, removing an ADE, overwriting a file |
| Governed decision | Changes L0/L1, the structure of the backlog, a protected artifact or the freeze. | Changing the stack, accepting an ADR, freezing |

## Choosing a plan

The Bootstrap asks. It does not choose for you, and it does not infer a plan from
the project, the ADE or a previous project.

```text
Select GTT Method Plan

[1] Light Method
    Maximum safe automation and the fewest interruptions, for one developer or a governed prototype.

[2] Medium Method
    Automation with confirmation of relevant changes, for an individual project or a small team.

[3] Hard Method
    Explicit human authorization of every governed operation, for production and critical systems.

[4] Team Method
    Collaborative governance: the Hard gates plus CI, actor traceability and shared team policy.
```

The one-line descriptions are the `summary` of each plan in the contract, shown as
written.

Until you choose, the project reports its plan as **not selected**. Validation still
runs, using the Medium gates as a fallback — the behaviour GTT had before plans
existed. That fallback is not a selection: the status says `not selected` in plain
words, and the Bootstrap still has to ask.

## The four plans

### Light Method

**For:** an individual developer, a personal project, a governed prototype, a POC or
a spike — wherever the lowest operational load is wanted.

**GTT does without asking:** allocates ids, updates references, rebuilds the index,
validates, and synchronises ADE context when nothing you wrote would be overwritten.

**You are asked for:** governed decisions and destructive operations. Nothing else.

**What Light relaxes — stated exactly, because it is the only plan that relaxes
anything:**

| Control | In Light |
|---|---|
| Documentation depth | `solution-vision`, `stack` and `constraints` must be real before freeze; `architecture`, `principles` and `glossary` may stay minimal, but must not contain template placeholders. |
| ADR expectations | An ADR is expected only for a change that alters frozen governed context. |
| The two confirmations | Confirmation A (source) and Confirmation B (context) may be asked in one exchange; each still needs its own explicit answer. |
| Audit cadence | `gtt-audit` is not scheduled; run it on demand. |

**Machine-enforced gates:** provenance advisory; warnings do not block freeze.

### Medium Method

**For:** normal development — features, integrations, internal services — by an
individual or a small team that wants automation but prefers to confirm relevant
changes.

**GTT does without asking:** allocates ids, rebuilds the index, validates.

**You are asked for:** relevant changes (reference updates, ADE context
synchronisation), governed decisions and destructive operations.

**Requires:** all six governed context files real before freeze; an ADR for every
architectural decision that changes governed context; `gtt-audit` before a release
or after a large merge. CI is recommended.

**Machine-enforced gates:** provenance advisory; warnings do not block freeze.

### Hard Method

**For:** production, critical or security-sensitive systems, high-consequence
architecture, regulated work.

Hard does not mean manual work. It means **explicit control over governed
operations**: GTT still prepares everything; it waits for you before applying.

**GTT does without asking:** rebuilds the index and validates — derived state only.

**You are asked for:** ids (GTT proposes one, you confirm), relevant changes,
governed decisions and destructive operations.

**Requires:** all six context files real, every technology row cited, a source
manifest; an ADR for every change to governed context, including small ones;
rollback and blast radius in every proposal; `gtt-audit` before every promotion.
CI is recommended.

**Machine-enforced gates:** provenance required; a source manifest required for
freeze; every OPEN gap must carry `affects`; warnings block freeze.

### Team Method

**For:** teams and collaborative projects — several people, or several ADEs,
changing the same governed project.

**GTT does without asking:** rebuilds the index and validates. For ids, reference
updates and ADE synchronisation it follows what the team declares in
`gtt-domain/working-agreements.md`; where the team has declared nothing, GTT
proposes and waits for confirmation, as in Hard.

**You are asked for:** governed decisions and destructive operations, always; the
rest as the team's policy says.

**Requires:** everything Hard requires, plus: validation running in CI on every
change; a second person reviewing each proposal and promotion script; the acting
person recorded for confirmations, ADRs and evidence; the base revision checked at
promotion so a concurrent change is detected rather than overwritten.

**Machine-enforced gates:** the same as Hard.

> **Status: baseline.** Today Team is the Hard gates plus the collaboration
> requirements above. Dedicated team plans are planned and will refine this
> definition. Until they ship, nothing beyond what is written here is promised.

## Side by side

| | Light | Medium | Hard | Team |
|---|---|---|---|---|
| GTT structure | yes | yes | yes | yes |
| Invariants | all | all | all | all |
| Relaxed controls | four, listed above | none | none | none |
| Automation | high | medium-high | controlled | high, by team policy |
| Id resolution | automatic | automatic | proposed, then confirmed | team policy |
| Reference updates | automatic | confirmed | confirmed | team policy |
| ADE context sync | automatic when safe | confirmed | confirmed | team policy |
| Index and validation | automatic | automatic | automatic | automatic |
| Governed decisions | confirmed | confirmed | confirmed | confirmed |
| Destructive operations | confirmed | confirmed | confirmed | confirmed |
| CI | optional | recommended | recommended | required |
| Multi-user | optional | optional | possible | central |
| Traceability | standard | standard | standard | reinforced (actor recorded) |
| Provenance gate | advisory | advisory | required | required |
| Warnings block freeze | no | no | yes | yes |

## What is enforced, and by what

A plan is honest about where each of its rules is enforced:

| Part of the plan | Enforced by | Verified by the Bootstrap? |
|---|---|---|
| Gates (provenance, source manifest, `affects`, warnings) | `gtt-check-provenance.sh`, in `gtt-validate.sh` and `gtt-freeze.sh` | Yes — deterministic |
| Invariants | Hooks, scripts and gates, as each one states in the contract | Yes, where a gate or hook exists |
| Semantics (proposal rigor, documentation depth, ADR and audit expectations) | Instructions to agents (`AGENTS.md`, the bootstrap skill) | No — nothing verifies that an ADE follows them |
| Operating policy (what is automatic, what is confirmed, CI, actor traceability) | The GTT CLI, which reads it from the contract | No — the Bootstrap declares it; the CLI executes it |

The Bootstrap and the CLI do not implement the same rule twice: the Bootstrap
defines what a plan means, the CLI reads that definition and acts on it.

## Selecting and changing a plan

A plan can be selected or changed at any time without recreating the project. Only
`.gtt/methodology.json` is written; governed context, ADRs, proposals, backlog,
index and history are untouched.

```bash
bash .gtt/scripts/gtt-project.sh profile get                          # what is selected
bash .gtt/scripts/gtt-project.sh profile set --profile light          # dry run: shows the change
bash .gtt/scripts/gtt-project.sh profile set --profile light --apply  # writes it
```

A CLI does the same through the declared operations `methodology.profile.get` and
`methodology.profile.set`. The operations keep the name *profile* for compatibility
with the 1.0 contract; *profile* and *plan* are the same thing.

**In a frozen project**, moving to a *less* strict plan is refused: it is a governed
change and follows the normal path (change request → proposal → human decision).
Moving to a stricter one is allowed. The order is Light < Medium < Hard < Team.

## What the Bootstrap deliberately does not add

- **No second configuration file.** The selection lives in `.gtt/methodology.json`
  and the meaning in `.gtt/contract/profiles.json`. There is no `.gtt/config.yaml`.
- **No separate agent registry.** Which ADEs take part is already recorded in
  `.gtt/ade.json` and declared in `.gtt/scaffold/manifest.yaml`; an ADE never joins
  merely because it is installed on the machine.
