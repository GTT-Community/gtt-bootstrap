# GTT v2.1 — Technical Closure & ADE Support Checklist

> **GTT Canonical Governance Reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

**Estado:** Draft — not a decision  
**Rama:** `dev`  
**Propósito:** Checklist operativo para Claude Code para cerrar técnicamente GTT v2.1 y verificar su soporte portable entre ADEs.

## 1. Reglas

- No abrir nuevas funcionalidades.
- No rediseñar arquitectura salvo inconsistencia demostrada.
- No inventar runtime verification.
- No ejecutar `apply-*` sin autorización.
- No hacer freeze ni ratificación.
- No hacer commit/push hasta autorización.
- GTT Core debe ser ADE-agnostic.
- La lógica común vive en GTT Core; cada ADE usa un adapter.
- Los adapters no duplican lógica GTT.
- Todo Markdown nuevo usa exclusivamente el Canon indicado arriba.

## 2. Arquitectura objetivo

```text
                         GTT CORE
                            |
              +-------------+-------------+
              |                           |
       Session Memory             GTT Services
              |                  Identity / Index /
       gtt-session-context.sh    Reconciliation / Integrity
              |
        Adapter Contract
              |
    +---------+---------+---------+
    |         |         |         |
 Claude     Codex    Copilot    Kiro
 Adapter    Adapter   Adapter    Adapter
```

Regla fundamental:

> **GTT Core provides the service. ADE adapters provide the integration.**

## 3. Checkpoint inicial

- [ ] Confirmar rama `dev`
- [ ] `git pull origin dev`
- [ ] `git status`
- [ ] Confirmar checkpoint esperado
- [ ] `bash gtt/scripts/gtt-validate.sh`
- [ ] Registrar commit y resultado inicial



## 3A. AUDITORÍA DE EXISTENCIA Y COMPLETITUD

Antes de ejecutar cambios, Claude debe comprobar que **todo lo que este checklist afirma que GTT v2.1 debe tener realmente existe en el repositorio y está conectado**.

No asumir que algo existe porque aparece documentado.

### 3A.1 Servicios y scripts principales

Verificar existencia, ejecutabilidad y relación funcional de:

- [ ] `gtt/scripts/gtt_artifacts.py`
- [ ] `gtt/scripts/gtt-index.sh`
- [ ] `gtt/scripts/gtt-reconcile.sh`
- [ ] `gtt/scripts/gtt-check-integrity.sh`
- [ ] `gtt/scripts/gtt-query.sh`
- [ ] `gtt/scripts/gtt-run-python.sh`
- [ ] `gtt/scripts/gtt-status.sh`
- [ ] `gtt/scripts/gtt-session-context.sh`
- [ ] `gtt/scripts/gtt-validate.sh`
- [ ] `gtt/scripts/gtt-check-adapter.sh`
- [ ] `gtt/scripts/gtt_guard.py`

Para cada uno indicar:

```text
EXISTS:
EXECUTABLE:
USED BY:
PURPOSE:
TESTED:
STATUS:
```

### 3A.2 Artifact Identity

Verificar que existan y estén conectados:

- [ ] `gtt/index/artifacts.json`
- [ ] Implementación de identity registry
- [ ] Registro de identidad lógica
- [ ] Route history
- [ ] Alias
- [ ] Reconciliation
- [ ] Integrity validation

Responder:

```text
Artifact Identity implementation:
Registry:
Reconciliation:
Integrity:
All connected:
```

### 3A.3 Technical Index

Verificar:

- [ ] `gtt/index/technical-index.json`
- [ ] Generador del índice
- [ ] Section ranges
- [ ] Concepts
- [ ] References
- [ ] Referenced-by
- [ ] Provenance
- [ ] Authority
- [ ] Version
- [ ] Query/retrieval
- [ ] Rebuild capability

Responder:

```text
Index exists:
Generator exists:
Query exists:
Rebuild verified:
Current:
```

### 3A.4 Session Memory

Verificar que exista la cadena completa:

```text
Repository state
      ↓
gtt-status.sh
      ↓
SESSION.md
      ↓
gtt-session-context.sh
      ↓
ADE adapter
      ↓
ADE session context
```

Checklist:

- [ ] `gtt-status.sh` genera/actualiza estado
- [ ] `SESSION.md` existe
- [ ] `gtt-session-context.sh` consume estado
- [ ] Session Memory no es autoridad
- [ ] Session Memory no es grounding evidence
- [ ] Session Memory es derivada del estado real
- [ ] La cadena funciona independientemente del ADE

Responder:

```text
Session Memory service:
SESSION.md:
Context generator:
End-to-end:
```

### 3A.5 Adapter Contract

Verificar que existan:

- [ ] `gtt/docs/SESSION-ADAPTER-CONTRACT.md`
- [ ] `gtt/session-adapters/`
- [ ] Declaración Claude
- [ ] Declaración Codex
- [ ] Declaración Copilot
- [ ] Declaración Kiro
- [ ] `gtt-check-session-adapter.sh`
- [ ] implementación/validador del contrato
- [ ] propuestas o mecanismos de aplicación cuando correspondan

Para cada ADE:

```text
Adapter declaration:
Schema:
Contract validation:
Runtime integration:
Runtime evidence:
Coverage:
```

### 3A.6 Integración Claude

Verificar la cadena real:

```text
Claude SessionStart
      ↓
Claude adapter/hook
      ↓
gtt-session-context.sh
      ↓
additionalContext
      ↓
Claude session
```

No basta con encontrar los archivos: comprobar que están conectados.

### 3A.7 Integración Codex

Verificar:

```text
Codex SessionStart
      ↓
Codex adapter
      ↓
gtt-session-context.sh
      ↓
additionalContext
```

Si runtime no puede verificarse, distinguir claramente:

```text
IMPLEMENTATION PRESENT
RUNTIME NOT VERIFIED
```

### 3A.8 Integración Copilot

Verificar:

```text
Copilot sessionStart
      ↓
Copilot adapter
      ↓
gtt-session-context.sh
      ↓
additionalContext
```

Distinguir:

```text
CLI
Cloud Agent
```

cuando corresponda.

### 3A.9 Integración Kiro

Verificar:

```text
Kiro session event
      ↓
Kiro adapter
      ↓
gtt-session-context.sh
      ↓
Kiro context
```

Si Kiro no está instalado:

```text
IMPLEMENTATION PRESENT
RUNTIME NOT VERIFIED — Kiro not installed
```

### 3A.10 Documentación y governance artifacts

Verificar existencia y coherencia de:

- [ ] Canonical governance references
- [ ] `AGENTS.md`
- [ ] `gtt/docs/SESSION-ADAPTER-CONTRACT.md`
- [ ] documentación de Session Memory
- [ ] documentación de Artifact Identity / Technical Index
- [ ] proposals relevantes
- [ ] ADR existente, si ya fue creado
- [ ] Epic/Stories, si ya fueron creados

No asumir que la ausencia de un ADR/Epic/Story es un error: indicar simplemente:

```text
PRESENT / NOT YET CREATED / OUT OF SCOPE
```

### 3A.11 Matriz de existencia

Claude debe terminar esta auditoría con una matriz:

| Componente | Existe | Conectado | Validado | Estado |
|---|---:|---:|---:|---|
| Artifact Identity | | | | |
| Artifact Registry | | | | |
| Reconciliation | | | | |
| Technical Index | | | | |
| Query/Retrieval | | | | |
| Session Memory | | | | |
| Session Context | | | | |
| Adapter Contract | | | | |
| Claude Adapter | | | | |
| Codex Adapter | | | | |
| Copilot Adapter | | | | |
| Kiro Adapter | | | | |
| Integrity | | | | |
| Validation | | | | |
| AGENTS.md | | | | |
| Governance docs | | | | |

### Regla de esta auditoría

Si un componente:

- está documentado pero no existe → **MISSING**
- existe pero no está conectado → **INCOMPLETE**
- existe y está conectado pero no tiene prueba → **UNVERIFIED**
- existe, está conectado y tiene evidencia → **PASS**

No convertir `UNVERIFIED` en `PASS`.


## 4. Artifact Identity

- [ ] Identidad lógica independiente del path
- [ ] `gtt/index/artifacts.json` consistente
- [ ] Rutas actuales correctas
- [ ] Route history preservada
- [ ] Alias preservados
- [ ] Moves detectados como moves
- [ ] No delete+create incorrecto
- [ ] Duplicados detectados
- [ ] Nuevos artefactos registrados
- [ ] Sin prefijos de identidad específicos de ADE
- [ ] `gtt_artifacts.py` sin lógica funcional dependiente del ADE

## 5. Repository Reconciliation

- [ ] Move detection
- [ ] Dry-run
- [ ] Reconciliation
- [ ] Route history
- [ ] Relative links
- [ ] Old-path references detectadas
- [ ] Integrity detecta moves no reconciliados
- [ ] No ejecutar `apply-*`

## 6. Technical Index

- [ ] `technical-index.json` existe
- [ ] Índice corresponde al repo
- [ ] Documentos/secciones/rangos correctos
- [ ] Concepts/references/referenced-by correctos
- [ ] Provenance/authority/version correctos
- [ ] Rebuild reproducible
- [ ] No es fuente de verdad
- [ ] Section retrieval funciona
- [ ] `gtt-query.sh` funciona

## 7. Session Memory

- [ ] `gtt-status.sh`
- [ ] `gtt-session-context.sh`
- [ ] `gtt-run-python.sh`
- [ ] `SESSION.md` derivado del estado real
- [ ] No es autoridad
- [ ] No es evidencia
- [ ] No entra al grounding corpus
- [ ] Core sin lógica ADE específica
- [ ] Claude SessionStart sigue funcionando
- [ ] Startup Claude runtime verified
- [ ] Resume Claude runtime verified
- [ ] Clear/compact/fork solo marcar si fueron realmente probados
- [ ] No-authority markers presentes

## 8. Adapter Contract

Cada adapter debe:

1. Detectar el evento propio del ADE.
2. Invocar únicamente `gtt-session-context.sh`.
3. Recibir el contexto.
4. Inyectarlo usando el mecanismo propio del ADE.
5. Declarar cobertura.
6. Reportar errores según el ADE.
7. No duplicar lógica GTT.

Nunca debe reconstruir Session Memory, Identity, Index o Governance.

## 9. ADE — Claude Code

Estado esperado:

```text
STATIC: PASS
RUNTIME: VERIFIED
```

Checklist:

- [ ] Adapter válido
- [ ] `SessionStart`
- [ ] `gtt-session-context.sh`
- [ ] `additionalContext`
- [ ] Startup verified
- [ ] Resume verified
- [ ] No-authority markers
- [ ] Sin lógica GTT duplicada

No modificar salvo regresión demostrada.

## 10. ADE — Codex

Checklist estático:

- [ ] Declaración válida
- [ ] Schema válido
- [ ] SessionStart
- [ ] `gtt-session-context.sh`
- [ ] `additionalContext`
- [ ] Limitaciones documentadas
- [ ] Windows/`commandWindows` si aplica
- [ ] Sin lógica GTT duplicada
- [ ] No runtime claim falso

Runtime, solo si puede probarse legítimamente:

- [ ] Startup
- [ ] Resume
- [ ] Clear
- [ ] Compact

Si requiere aprobación interactiva:

```text
RUNTIME: NOT VERIFIED — human approval required
```

No usar bypass para fabricar evidencia.

## 11. ADE — GitHub Copilot

Checklist:

- [ ] Declaración válida
- [ ] Schema válido
- [ ] `sessionStart`
- [ ] `gtt-session-context.sh`
- [ ] `additionalContext`
- [ ] CLI interactive distinguido
- [ ] Cloud agent distinguido
- [ ] Limitaciones documentadas
- [ ] Sin lógica GTT duplicada
- [ ] No runtime claim falso

Runtime:

- [ ] CLI sessionStart
- [ ] Context injected
- [ ] No-authority markers

Si no hay sesión interactiva:

```text
RUNTIME: NOT VERIFIED — interactive session required
```

## 12. ADE — Kiro

Checklist:

- [ ] Declaración válida
- [ ] Schema válido
- [ ] Evento soportado documentado
- [ ] `gtt-session-context.sh`
- [ ] Mecanismo de contexto documentado
- [ ] CLI/IDE distinguido cuando corresponda
- [ ] Sin lógica GTT duplicada
- [ ] No runtime claim falso

Runtime:

- [ ] Startup/session event
- [ ] Context loaded
- [ ] No-authority markers

Si Kiro no está instalado:

```text
RUNTIME: NOT VERIFIED — Kiro not installed
```

## 13. Core ADE-Agnostic

Buscar referencias ADE en:

```text
gtt/scripts/
gtt/index/
gtt/docs/
```

Clasificar:

**A — ADE knowledge:** el Core cambia comportamiento según ADE → eliminar/mover al adapter layer.

**B — Repository artifact scope:** indexa/protege una ruta de herramientas como cualquier artefacto → puede permanecer.

**C — Documentation:** referencia documental → puede permanecer si no crea dependencia funcional.

No eliminar referencias B automáticamente.

## 14. `gtt-validate.sh` — pendiente conocido

Revisar la detección directa de `.claude`, `.kiro`, `.copilot`.

Objetivo:

```text
gtt-validate.sh
        |
        +--> gtt-check-adapter.sh
                    |
                    +--> determina su propio contexto
```

No queremos que `gtt-validate.sh` conozca ADEs.

- [ ] Analizar
- [ ] Confirmar dependencia real
- [ ] Diseñar corrección mínima
- [ ] Aplicar solo si no amplía alcance
- [ ] Validar nuevamente

Si requiere cambios mayores: detener y reportar.

## 15. AGENTS.md

Aplicar el cambio manual definido en:

```text
gtt/proposals/PROPOSAL-artifact-identity-followups.md
```

Sección `§2d`.

- [ ] Revisar fragmento
- [ ] Aplicar cambio
- [ ] No alterar governance adicional
- [ ] Ejecutar `gtt-index.sh`
- [ ] Verificar Technical Index
- [ ] Integrity check

## 16. Validación final

Ejecutar:

```bash
bash gtt/scripts/gtt-validate.sh
bash gtt/scripts/gtt-check-integrity.sh
```

Registrar:

```text
Artifact Identity:
Repository Reconciliation:
Technical Index:
Session Memory:
Adapter Contract:
Claude:
Codex:
Copilot:
Kiro:
ADE-agnostic Core:
gtt-validate:
AGENTS.md:
Integrity:
Global:
```

## 17. Gobernanza — posterior

No ejecutar todavía:

```text
ADR
  ↓
Epic
  ↓
Stories
  ↓
Human Review
  ↓
Ratification
  ↓
Freeze
```

Todo permanece:

```text
Draft — not a decision
```

## 18. Definition of Done — Technical

- [ ] Artifact Identity PASS
- [ ] Reconciliation PASS
- [ ] Technical Index PASS
- [ ] Session Memory PASS
- [ ] Claude runtime VERIFIED
- [ ] Codex adapter STATIC PASS
- [ ] Copilot adapter STATIC PASS
- [ ] Kiro adapter STATIC PASS
- [ ] Runtime no verificado declarado honestamente donde corresponda
- [ ] Core ADE-agnostic PASS
- [ ] `gtt-validate.sh` sin dependencia ADE, o pendiente explícitamente documentado
- [ ] AGENTS.md actualizado
- [ ] Technical Index regenerado
- [ ] Integrity PASS
- [ ] Sin secretos/temporales/artefactos accidentales
- [ ] Working tree revisado

## 19. Definition of Done — Governance

Posterior a la revisión técnica:

- [ ] ADR
- [ ] Epic
- [ ] Stories
- [ ] Human Review
- [ ] Ratification
- [ ] Freeze
- [ ] Release/version final

## 20. Reporte obligatorio de Claude

Entregar tabla:

| Área | Estado | Evidencia | Pendiente |
|---|---|---|---|
| Artifact Identity | | | |
| Reconciliation | | | |
| Technical Index | | | |
| Session Memory | | | |
| Claude | | | |
| Codex | | | |
| Copilot | | | |
| Kiro | | | |
| ADE-agnostic Core | | | |
| gtt-validate | | | |
| AGENTS.md | | | |
| Integrity | | | |
| Governance | | | |

Después indicar:

### Bloqueadores reales

Solo aquello que impide cerrar técnicamente.

### Pendientes no bloqueantes

Aquello que puede quedar para gobernanza o runtime posterior.

### Cambios realizados

Archivos modificados.

### Cambios no realizados

Qué se decidió no tocar y por qué.

### Estado final

Usar únicamente uno:

```text
TECHNICAL READY
TECHNICAL BLOCKED
GOVERNANCE READY
```

No usar `FINAL`, `RATIFIED` o `FROZEN` salvo ratificación humana explícita.
