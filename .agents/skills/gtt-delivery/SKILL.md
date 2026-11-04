---
name: gtt-delivery
description: Use during THINK, before the freeze, to fill the Delivery Assessment (estimates in agent hours, buy-or-build with dated sources, fronts, the vertical slice, pending decisions); and after the freeze when observation opens a DLV-* signal (an Epic over its cap, a forecast past the deadline, fronts that overlap) to propose a new plan with options and the hours each saves. Proposes only and never decides a Budget, an Owner or the delivery answers.
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

# GTT delivery

> **Speaking for GTT.** Every message this skill raises to the human opens with `@gtt · <what this is>`
> (e.g. `@gtt · Delivery plan`). The marker says who is speaking; it is never a decision.

GTT knows **what** is built; this skill helps the human see **how long it takes and with how many hands**.
Measuring, calculating the plan and raising signals are scripts (`.gtt/scripts/gtt-delivery.sh`): run them, never
estimate their result by judgment. What is left for you is explaining and proposing. The human decides.

**You never** write `.gtt/delivery.json` (the human's answers, recorded with `gtt-delivery.sh select` only when they
give them), decide a `Budget`, assign an `Owner`, or launch agents. GTT does not orchestrate agents: that is the ADE's job.

Estimate in **agent hours plus human decision points** (`Estimate: 6h + 2 decisions`), never in weeks of a person.
Until three Stories have been measured the plan is *uncalibrated*: say it.

## Before the freeze (THINK)

1. `bash .gtt/scripts/gtt-delivery.sh get` - who builds, fronts, deadline. If `OPEN`, ask (questionnaire 4.7).
2. Fill section 9, *Delivery Assessment*, of the design assessment at the selected THINK Depth:
   - **Estimate per Epic**: Stories foreseen, agent hours, decision points, whether it passes the cap.
   - **Buy or build**: for each generic capability (login, payments, email, files) the cost of building, an integration
     option with `[FUENTE: url, consultado AAAA-MM-DD]`, integration hours, recurring cost, lock-in, clash with
     `constraints.md`. No source means it stays a `[PROPUESTA]`, never a fact. A source older than 90 days is verified again
     before the freeze. Buying is an architecture decision: it needs an ADR (`Build: integrate (ADR-NNN)`).
   - **Fronts**: owner, Epics, `Touches`, dependencies through an interface. Two fronts never share `Touches` unless one
     depends on the other through an interface (I-n) of its design.
   - **Vertical slice**: the first flow that delivers value, and what stays outside it.
   - **Pending decisions**: what is undecided, what each blocks, your recommended option - so the human decides all in one session.
3. Write the Epic fields as suggestions (`Estimate`, `Depends on`, `Lane`, `Touches`, `Build`, `Budget`); the human approves them with the Epic.
4. Run `bash .gtt/scripts/gtt-delivery.sh plan` and give the human the summary it computes, e.g. "With 3 fronts: ~N h of agent,
   finish X, deadline Y -> does not fit. To fit: integrate identity (-5 Stories), cut EPIC-008 (-4 Stories)". Every lever is a `[PROPUESTA]`.

## At any time (even if planning was never declared)

`bash .gtt/scripts/gtt-delivery.sh check` and `summary` report three signals with or without a declaration: `DLV-NO-PLAN` (many open
Stories and almost none with an `Estimate`: size the Epics now), `DLV-STALE-STATUS` (a commit already closed a Story still not `Done`: set
`Done` and `Closed`) and `DLV-PACE-DRIFT` (a plan document speaks in another rhythm than `pace`). Say each in one line and fix the part
that is yours (Stories, estimates, plan documents); the pace itself is the human's (`gtt delivery set --pace days|flow`).

`bash .gtt/scripts/gtt-delivery.sh size` reports how big the backlog is as facts (never "too big": the human declares the cap and the growth
that matter). On `DLV-GROWTH` or `DLV-OVER-TARGET` say the numbers in one line and offer `gtt delivery review`: keep it, set a cap, one
pass, or slim down (levers from `plan`; cutting or merging an Epic is a proposal for the human).

## After the freeze

When observation opens a `DLV-*` signal (`bash .gtt/scripts/gtt-observe.sh backlog`), say it in one line and keep working. For
`GOVERNANCE` signals propose, in `gtt-domain/proposals/`, which lever to use (split, integrate, cut, add a front, accept) and how many
hours it saves, from `gtt-delivery.sh plan` and `report`. The human decides. Work only inside the `Touches` of your front; if you need
another front's paths, report it.
