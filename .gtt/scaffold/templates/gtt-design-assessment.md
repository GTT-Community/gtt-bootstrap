# GTT Design Assessment

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

The Think stage starts here. Before a design document is used as the source of
the governed context, the ADE reads it — every document, when there is more
than one — and writes down **how good it is**: what it establishes, what it
leaves thin, what it does not say, and whether it is enough to design from.

This is an assessment, written so it can be reviewed and shared; it is not a
conversation, not a decision, and not governed context. The human reads it and
decides what to do with it.

## Operating contract for the ADE

1. Read every candidate document completely before rating anything.
2. Rate what the documents **say**, citing where: `[FUENTE: file:line]`. Never
   rate from what you assume the author meant.
3. Do not complete, correct or improve the documents here. Improving the
   design is the strengthening step, and it is the human who decides it.
4. Every option you suggest is a `[PROPUESTA]`, with its trade-offs. A proposal
   is never a decision, and you never fill a `Human decision` for the human.
5. Where documents disagree, write `[CONFLICTO: a vs b]`. Never pick a winner.
6. Open every message about this assessment with `@gtt · Design assessment`.
7. Work at the THINK Depth the human selected (below). The depth changes how
   far you dig; it never changes a rule. You never raise or lower it yourself.

## THINK Depth

How deep THINK goes for this design. The human selects it — ask once, showing
the three levels; never infer it from the project, the Method Plan or the ADE.
Left empty it is **not selected**, and `STANDARD` applies as a fallback.

```text
THINK Depth:
Selected by:
Date:
```

| | `QUICK` | `STANDARD` | `DEEP` |
|---|---|---|---|
| For | simple or small designs | ordinary projects | complex, critical or highly uncertain systems |
| Assessment (section 3) | the floor areas always, and the areas the documents make relevant; an area left out is written `not assessed (QUICK)`, never `SOLID` | every area, with its evidence | every area, exhaustively; architecture, non-functional requirements, security, data, integrations, deployment, observability, development architecture and constraints in depth |
| Focus | critical gaps | every `THIN` or `MISSING` area | alternatives, dependencies, risks, conflicts and gaps, each explicit |
| Stack (section 6.1) | options only for an undecided floor layer: one recommendation and its main trade-off | reasonable alternatives per undecided or unjustified layer, trade-offs, a recommendation | stack **and** architectural alternatives, trade-offs explicit (sections 6.1 and 6.3) |
| Questionnaire (section 7) | reduced: only what the floor or a critical gap needs | adaptive: what was `THIN` or `MISSING` | deep and iterative: earlier answers revisited as later rounds change them |

**THINK Depth is not a level of governance, and it is not the Method Plan**
(the two are independent and chosen separately). At every depth:
section 4 is assessed line by line and a design below the floor is `POOR`;
every option is a `[PROPUESTA]`; unknowns stay `[VACÍO]` and disagreements
`[CONFLICTO]`; the human decides; the original documents are not modified;
and freeze works exactly the same.

### Escalation log

When what you find justifies a deeper level, propose it — one level at a time,
with the evidence — and keep working at the current depth until the human
decides. A decision is `accepted` or `declined`, with who and when. Only an
accepted row changes the `THINK Depth` above.

| From | To | Evidence `[FUENTE]` | Human decision (accepted / declined — who — date) |
|---|---|---|---|

## 1. Documents assessed

| Id | Path | What it is | Version / date |
|---|---|---|---|
| <SRC-1> | <path> | <design doc / requirements / notes> | <version or date, or unknown> |

## 2. More than one document

Fill this section only when section 1 lists more than one document.

Overlaps and disagreements between the documents:

- <topic> — `[CONFLICTO: SRC-1 vs SRC-2]` <what each one says, with `[FUENTE]`>

How the documents will be used — **the human chooses; the ADE never does**:

| Option | What happens |
|---|---|
| `CONSOLIDATE` | The ADE drafts one design document from all of them, every statement carrying the `[FUENTE]` it came from and every disagreement left visible as `[CONFLICTO]` for the human to resolve. After the human's review it is the single source document. The originals are not modified. |
| `KEEP_AS_SOURCES` | Each document stays as it is and is declared in the source manifest with an authority and an unambiguous precedence. All of them are context during design; a disagreement stays a `[CONFLICTO]` until the human decides — precedence orders the reading, it never erases the conflict. |

```text
Human decision:
```

## 3. Assessment by area

Rating: `SOLID` (decided and specific enough to build from), `THIN` (mentioned,
but vague, partial or undecided), `MISSING` (not addressed).

| Area | Rating | Evidence | What is thin or missing |
|---|---|---|---|
| Vision — problem, who it is for, what success is |  |  |  |
| Scope — in, out, boundaries |  |  |  |
| Users and consumers |  |  |  |
| Main capabilities and functional requirements |  |  |  |
| Non-functional requirements — performance, availability, scale, compliance |  |  |  |
| Architecture — style, modules and boundaries, integration strategy |  |  |  |
| **Technology stack** — language and runtime, framework, compute model |  |  |  |
| **Data** — datastore, data model and ownership, lifecycle |  |  |  |
| Security — identity, authentication, authorization, secrets |  |  |  |
| Integrations and external systems |  |  |  |
| Deployment and infrastructure — environments, IaC, CI/CD |  |  |  |
| Development architecture — repository layout, layering, testing strategy, conventions |  |  |  |
| Observability |  |  |  |
| Constraints — platform, regulatory, budget |  |  |  |

## 4. Minimum floor

A design cannot be governed below this floor. Each line is `MET` or `NOT MET`.

| Floor | State |
|---|---|
| The problem and who it is for are stated (Vision is not `MISSING`) |  |
| What is in scope and out of scope is stated (Scope is not `MISSING`) |  |
| **The technology stack is decided: language and runtime, framework, compute model** (Technology stack is `SOLID`) |  |
| **The datastore is decided, or the design states that it needs none** (Data is not `MISSING`) |  |
| The architectural style is stated (Architecture is not `MISSING`) |  |

## 5. Verdict

```text
Verdict:
```

| Value | Meaning | What follows |
|---|---|---|
| `STRONG` | The floor is met and no area that matters for this project is `THIN` or `MISSING` | Strengthening is offered; the human may skip it |
| `ADEQUATE` | The floor is met; some areas are `THIN` or `MISSING` | Strengthening is offered and recommended for the areas listed |
| `POOR` | The floor is not met | The design is strengthened before it is used as a source. It is not mapped into governed context as it is |

The ADE must explain the verdict in two or three sentences.

## 6. Strengthening plan

What would make this design better, most important first. For each item: the
area, what is missing, and — where a choice is open — the options.

### 6.1 Technology stack

The stack is where a weak design costs most. For every layer that is not
decided, or that is decided without a reason, give the options that fit **this**
project — its requirements, constraints, team and scale as the documents state
them — never a generic favourite.

| Layer | What the documents say | Options `[PROPUESTA]` | Trade-offs of each | Recommendation `[PROPUESTA]` and why | Human decision |
|---|---|---|---|---|---|
| Language and runtime |  |  |  |  |  |
| Framework |  |  |  |  |  |
| Compute model |  |  |  |  |  |
| Datastore |  |  |  |  |  |
| Messaging / integration |  |  |  |  |  |
| Identity and secrets |  |  |  |  |  |
| IaC and CI/CD |  |  |  |  |  |
| Observability |  |  |  |  |  |
| Testing |  |  |  |  |  |

A recommendation states what it optimises for and what it gives up. When the
documents do not say enough to recommend, say so and ask — do not recommend
from nothing.

### 6.2 Other areas

| Area | What is missing | Question for the human, or options `[PROPUESTA]` with trade-offs | Human decision |
|---|---|---|---|
|  |  |  |  |

### 6.3 Architecture alternatives, dependencies and risks

Filled at `DEEP`; at `STANDARD` only where an architectural choice is open; not
at `QUICK`.

| Topic | Alternatives `[PROPUESTA]` | Trade-offs of each | Depends on | Risk if wrong | Human decision |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 7. How the design is strengthened

The strengthened design is written, not talked about. The ADE carries what the
documents establish into the Initial Design Questionnaire — the Bootstrap's one
instrument for reaching a Minimum Viable Governed Design — each statement with
the `[FUENTE]` it came from, and conducts the interview only for what section 3
found `THIN` or `MISSING`. The decisions the human takes in section 6 are
recorded there as human decisions; an option nobody decided stays a
`[PROPUESTA]` and maps to nothing in governed context.

The original documents are never rewritten. After the human's review
(Confirmation A) the strengthened design is the source document.

```text
Human decision (strengthen / use as it is):
```

## 8. Status

This assessment is source material for the bootstrap. It governs nothing, and
completing it decides nothing.
