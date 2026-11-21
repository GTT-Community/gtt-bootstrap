#!/usr/bin/env python3
"""A large, invented backlog in the shape an older Bootstrap left: no business, no real project, deterministic.

  build(epics=10, stories=8) -> text of a whole backlog.md (the Epics section replaced inside a given template)

It mixes what real backlogs hold: every Story status, Stories with no `Implements`, `Implements: (none)`, Spanish and English,
accents and symbols, long Context lines, closed Stories with their evidence, blocked Stories, Epics Proposed / Planned /
In Progress / Done, approved and not, and Epics with a Design line and without. Used by domain-migration.py (scale) and by
the end-to-end run of `gtt update` from an old tag.
"""
import re

AREAS = ["Facturación", "Inventory", "Catálogo", "Notifications", "Reportes", "Onboarding", "Búsqueda", "Audit trail",
         "Permisos", "Integración de pagos", "Sincronización", "Exportación"]
VERBS = ["Registrar", "List", "Calcular", "Validate", "Archivar", "Send", "Importar", "Reconcile", "Editar", "Show"]
STATUS_CYCLE = ["Done", "Done", "In Progress", "Planned", "Planned", "Blocked", "Planned", "Done"]
EPIC_STATUS = ["Completed", "In Progress", "In Progress", "Planned", "Planned", "Proposed", "Proposed", "Planned", "Completed", "Proposed"]


def epic_text(n, stories, legacy=True):
    area = AREAS[(n - 1) % len(AREAS)]
    status = EPIC_STATUS[(n - 1) % len(EPIC_STATUS)]
    approved = status != "Proposed"
    lines = [f"### EPIC-{n:03d} — {area}", "",
             f"**Status:** {status}",
             f"**Goal:** Que el equipo pueda operar {area.lower()} sin pasos manuales — línea {n}, con acentos: ñ, é, ü.",
             f"**Scope:** el flujo principal de {area.lower()}, sus reglas y sus errores · lo que el cliente ve.",
             f"**Out of Scope:** reportes históricos anteriores a 2020 · migración de datos de terceros."]
    if n % 3 == 0:
        lines.append("**Kind:** slice")
    lines.append(f"**Design:** gtt-domain/context/design/EPIC-{n:03d}.md")
    if approved:
        lines.append(f"**Approved:** ana — 2026-0{1 + n % 9}-1{n % 9}")
    lines += ["", "#### Stories", ""]
    for s in range(1, stories + 1):
        sid = (n - 1) * stories + s
        verb = VERBS[(sid - 1) % len(VERBS)]
        st = STATUS_CYCLE[(sid - 1) % len(STATUS_CYCLE)]
        if status == "Proposed" and st == "Done":
            st = "Planned"
        if status == "Completed":
            st = "Done"
        lines += [f"##### STORY-{sid:03d} — {verb} {area.lower()} (paso {s})", "", f"- **Status:** {st}"]
        shape = sid % 4 if legacy else (1 if sid % 3 else 2)   # legacy=False: every Story cites its design, as a valid old project did
        if shape == 0:
            lines.append("- **Implements:** (none)")
        elif shape == 1:
            lines.append(f"- **Implements:** design/EPIC-{n:03d}#R-{s}, #F-1 · ADR-00{1 + n % 3}")
        elif shape == 2:
            lines.append(f"- **Implements:** design/EPIC-{n:03d}#R-{s}")
            lines.append(f"- **Context:** {verb} requiere la regla R-{s} — «cantidad ≥ 1», símbolos: <>&\"' y una línea larga "
                         + "que sigue " * 12 + f"(#R-{s}).")
        if st == "Done" or (not legacy and st != "Blocked"):
            lines.append(f"- **Done when:** E-{s} passes (Given a cliente, when {verb.lower()}, then queda registrado) · tests/test_{sid}.py")
        if st == "Done":
            lines.append(f"- **Closed:** 2026-0{1 + sid % 9}-0{1 + sid % 8} — a1b2c{sid:03d} — 12 tests passed")
        elif st == "Blocked":
            lines.append("- **Blocked by:** decisión del cliente sobre el formato")
        lines.append("")
    return "\n".join(lines)


def design_text(n, stories):
    """The Epic's design, with every anchor its Stories cite (rules R-n, flow F-1, examples E-n)."""
    rules = "\n".join(f"- **R-{s}** regla {s} de {AREAS[(n - 1) % len(AREAS)].lower()} — «cantidad ≥ 1»" for s in range(1, stories + 1))
    examples = "\n".join(f"- **E-{s}** Given a cliente, when actúa, then queda registrado ({s})" for s in range(1, stories + 1))
    return f"# EPIC-{n:03d} design\n\n## Rules\n\n{rules}\n\n## Flows\n\n- **F-1** el flujo principal\n\n## Examples\n\n{examples}\n"


def write_designs(root, epics=10, stories=8):
    """The design files and the ADRs a backlog built here cites, under a project root."""
    import glob
    import os
    for n in range(1, epics + 1):
        path = os.path.join(root, f"gtt-domain/context/design/EPIC-{n:03d}.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(design_text(n, stories))
    for a in (1, 2, 3):
        if not glob.glob(os.path.join(root, f"gtt-domain/adr/ADR-00{a}*.md")):    # the catalog already ships ADR-001..: never duplicate one
            path = os.path.join(root, f"gtt-domain/adr/ADR-00{a}-synthetic-{a}.md")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").write(f"# ADR-00{a} decision {a}\n\nStatus: Accepted\n")


def build(template, epics=10, stories=8, legacy=True):
    """The template is a backlog.md; its `## Epics` section (up to `## General Development Work`) is replaced."""
    body = "## Epics\n\n" + "\n".join(epic_text(n, stories, legacy) for n in range(1, epics + 1)) + "\n---\n\n"
    return re.sub(r"## Epics\n.*?(?=## General Development Work)", lambda m: body, template, count=1, flags=re.S)


def counts(text):
    return {"epics": len(re.findall(r"^### EPIC-", text, re.M)), "stories": len(re.findall(r"^##### STORY-", text, re.M))}


if __name__ == "__main__":
    import sys
    print(build(open(sys.argv[1], encoding="utf-8").read(), *(int(a) for a in sys.argv[2:4])), end="")
