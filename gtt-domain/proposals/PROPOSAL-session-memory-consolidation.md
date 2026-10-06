# PROPOSAL — Session Memory: consolidación de adapters y checkpoint

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Borrador, no decisión. Fecha: 2026-10-05.
Separada a propósito de `PROPOSAL-antigravity-ade-support.md`: es deuda transversal, no de un
ADE. El soporte de Antigravity no depende de nada de lo que hay aquí.

Este documento registra el problema y las decisiones que hacen falta. No propone todavía un
diseño: tres de los cuatro puntos necesitan primero una decisión del Solution Designer.

```text
Context Conflict Detected

Context file:        .gtt/docs/session-adapter-contract.md (Status: Draft — not a decision)
What the context says:
    Todo adapter de sesión usa solo el servicio gtt-session-context.sh, falla de forma visible,
    nunca sale con código 2, y se declara en .gtt/session-adapters/<ade>.json, que
    gtt-check-session-adapter.sh comprueba (líneas 51-79).
What the implementation does:
    Cursor y OpenHands entregan el contexto de sesión por gtt_protect.py (líneas 170-173, 193-195,
    216-218): sin declaración, sin pasar por la comprobación, y devolviendo "sin contexto" en
    silencio cuando el servicio falla.
Where they diverge:
    Hay dos mecanismos de entrega de sesión. Solo uno está bajo el contrato.
Possible resolutions:
    (a) Llevar Cursor y OpenHands al contrato: declaración por ADE y fallo visible.
    (b) Cambiar el contrato para admitir la entrega por el motor de protección, con sus reglas.
    (c) Dejarlo como está y documentar la excepción.

Status: Requires human review
```

## Lo que ya funciona y no debe cambiar

`gtt-domain/session.md` lo genera `gtt-status.sh` solo desde artefactos del repositorio (freeze,
backlog, propuestas, ADRs, GTTGuard, estado de ADEs, gaps, plan, git). No nombra ningún ADE, no
lee la memoria de ninguno, está versionado y lleva los marcadores de no-autoridad. Un proyecto
se retoma igual desde cualquier ADE.

Restricción para cualquier diseño futuro: debe seguir siendo derivado, independiente del ADE,
complementario a la memoria nativa de cada uno, y nunca una segunda fuente de autoridad.

## Deuda detectada

| # | Hecho | Evidencia | Qué necesita |
|---|---|---|---|
| 1 | Dos mecanismos de entrega de sesión | arriba | decisión (a), (b) o (c) |
| 2 | Los adapters de Codex, Copilot y Kiro llevan *staged* sin promover; el de Codex se probó y no se ejecutó | `.gtt/session-adapters/codex.json:5,24`; `gtt-domain/proposals/apply-session-adapters.sh` | decisión: promoverlos, corregirlos o retirarlos |
| 3 | El contrato de adapters es un borrador sin ADR ni Story, y su diagrama lista cuatro ADEs de seis | `session-adapter-contract.md:5,25-29` | ratificarlo o reescribirlo |
| 4 | No hay checkpoint al terminar una sesión: `session.md` se regenera al empezar, y en un ADE sin evento de inicio depende de que el agente obedezca | `gtt-session-context.sh`; ningún overlay usa un evento de fin | diseño, después de 1-3 |
| 5 | La intención en curso no es derivable: "estaba a mitad de X" no está en git ni en el backlog si nadie actualizó *Current Focus* | `gtt-status.sh` solo lee artefactos | **decisión de método**, abajo |

## La decisión que no es técnica

Un comando `gtt session checkpoint` es trivial si solo vuelve a ejecutar `gtt-status.sh`: no
añade información, solo frescura.

Para llevar además la intención en curso hay dos caminos, y son distintos en principio:

| Camino | Qué implica |
|---|---|
| Solo derivado | El handoff es lo que ya dicen el backlog (*Current Focus*, Stories `In Progress`) y git. La disciplina es mantener el backlog al día. No cambia ningún principio. |
| Notas de handoff escritas por el agente | Un artefacto nuevo, por debajo de `session.md` en precedencia, que un agente escribe y otro lee. Hoy `session.md` excluye expresamente las notas de agente; admitirlas es un cambio del método y necesita su propia regla de no-autoridad. |

No recomiendo ninguno aquí: es una decisión del Solution Designer sobre qué admite GTT como
memoria operativa.

## Alternativas

| Alternativa | Por qué no ahora |
|---|---|
| Resolverlo dentro del soporte de Antigravity | Mezcla un cambio de un ADE con un cambio del método; el Solution Designer pidió separarlos. |
| Añadir ya el comando de checkpoint | Sin decidir la fila 5 solo sería un alias de `gtt-status.sh`. |

## Siguiente paso

Decidir las filas 1, 2 y 5. Con eso se puede redactar una propuesta de diseño y, si procede, su
Epic.
