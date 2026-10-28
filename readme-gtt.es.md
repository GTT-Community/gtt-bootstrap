# GTT Bootstrap

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

**GTT — Governance Through Thinking.** Tú decides qué debe ser el sistema; el agente de IA lo construye
con libertad dentro de ese diseño; GTT mantiene separadas las dos cosas.

> **El razonamiento del agente ≠ autorización de cambio.**

🇺🇸 [English](readme-gtt.md) · Guía completa: [.gtt/docs/guide.es.md](.gtt/docs/guide.es.md) · Apache-2.0

## Cómo funciona

1. **Setup** - `gtt init`: eliges los ADEs que usas (Claude Code, Kiro, Copilot, Cursor, Antigravity,
   OpenHands, Codex), cuánto puede hacer GTT sin preguntarte (perfil de autonomía: Light, Medium, Hard,
   Team) y cómo se organiza la solución (método de desarrollo, p. ej. Vertical Slice).
2. **Diseño** - abre el proyecto en tu ADE y escribe cualquier cosa. Parte de tu documento de diseño o te
   entrevista con el Cuestionario de Diseño Inicial. El stack y el datastore siempre los decides tú.
3. **Freeze** - `gtt freeze`: ratificas el diseño. Pasa a ser la autoridad.
4. **Construcción** - el agente implementa, refactoriza, prueba y escribe Stories sin pedir permiso.
5. **Observación** - GTT compara el trabajo con el diseño congelado. Un datastore, framework o módulo nuevo
   que el diseño no declara, o una regla de dependencias rota, se reporta; solo se detiene lo que tú
   declaraste BLOCKING.
6. **Cambio** - escribe lo que quieres cambiar en `gtt-domain/change-request.md`; el agente propone;
   `gtt promote <set>` aplica tu decisión y vuelve a congelar. `gtt undo` lo revierte.

## Los comandos que usas

| Comando | Qué hace |
|---|---|
| `gtt status` | Dónde está el proyecto: freeze, observaciones, qué espera GTT |
| `gtt validate` | Todos los chequeos deterministas de gobierno (también en CI) |
| `gtt freeze` | Ratificar el diseño (solo una persona, en una terminal) |
| `gtt change`, `gtt proposals`, `gtt promote`, `gtt undo` | El flujo de cambios |
| `gtt check` | ¿El código respeta las reglas de dependencias del método? |
| `gtt autonomy` | Ver o cambiar el perfil de autonomía |

## Dónde está cada cosa

| Ruta | Qué |
|---|---|
| `gtt-domain/context/` | El diseño gobernado (visión, arquitectura, stack, restricciones...) - solo tú lo cambias |
| `gtt-domain/backlog.md` | Epics (tuyos) y Stories (el plan de trabajo del agente) |
| `gtt-domain/change-request.md` | Lo que quieres cambiar |
| `gtt-domain/proposals/` | Lo que propone el agente |
| `AGENTS.md` | El contrato que lee todo agente (unido al tuyo si ya tenías uno) |
| `.gtt/` | El motor: scripts, contratos, documentación |

Más: [la guía completa](.gtt/docs/guide.es.md) · [índice de documentación](.gtt/docs/index.md) ·
[métodos de desarrollo](.gtt/methods/README.md) · [el canon de GTT](https://github.com/GTT-Community/gtt-method)
