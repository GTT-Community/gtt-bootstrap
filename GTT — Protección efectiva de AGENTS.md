# GTT — Tarea de corrección: protección efectiva de `AGENTS.md`

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

## Objetivo

Corregir exclusivamente la discrepancia detectada durante la implementación de `GTT_BOOTSTRAP_CLAUDE_EXECUTION_DIRECTIVE.md`:

`gtt/docs/DOCS.md` declara que `AGENTS.md` pertenece al machinery/protected governance, pero la protección efectiva actual no lo cubre mediante `protect-l0.py` ni mediante `permissions.deny`.

El objetivo es que **la protección declarada y la protección realmente aplicada queden alineadas**.

---

## Autoridad

La autoridad para esta tarea es:

```text
GTT-CANONICAL-v2.1.md
        ↓
esta directriz
        ↓
implementación existente de GTT Bootstrap
```

Claude ejecuta esta corrección.

No debe rediseñar GTT ni modificar otras áreas de la implementación.

---

# 1. Inspección obligatoria

Antes de modificar cualquier archivo, revisar el estado real de:

```text
AGENTS.md
gtt/docs/DOCS.md
protect-l0.py
permissions.deny
cualquier mecanismo actual de GTTGuard
hooks relacionados
scripts de protección
```

También identificar cómo están protegidos actualmente los demás artefactos que `DOCS.md` clasifica como machinery/protected governance.

No asumir nombres, rutas ni mecanismos que no existan.

---

# 2. Verificar la discrepancia

Confirmar explícitamente:

```text
DOCS.md
   ↓
declara AGENTS.md como machinery/protegido

pero

enforcement actual
   ↓
¿AGENTS.md realmente está protegido?
```

La conclusión debe basarse en el código real del repositorio.

---

# 3. Aplicar la corrección mínima

Si se confirma que `AGENTS.md` está declarado como protegido pero no está efectivamente protegido:

- incorporar `AGENTS.md` al mecanismo de protección existente;
- utilizar el mismo mecanismo que ya utiliza GTT para artefactos equivalentes;
- no crear un segundo sistema de protección;
- no duplicar lógica;
- no modificar innecesariamente `DOCS.md` si su declaración actual es correcta.

La solución debe integrarse con el mecanismo existente de:

```text
GTTGuard
protect-l0.py
permissions.deny
hooks
```

según corresponda al diseño real encontrado.

---

# 4. No ampliar el alcance

Esta tarea NO autoriza:

- rediseñar GTTGuard;
- rediseñar `protect-l0.py`;
- cambiar la arquitectura de agentes;
- modificar Session Continuity;
- modificar `gtt-status.sh`;
- modificar `gtt-validate.sh`;
- crear nuevos agentes;
- cambiar ADE adapters;
- modificar el Canon;
- introducir nuevas reglas metodológicas;
- proteger archivos adicionales que no estén justificados por el mecanismo existente.

Si durante la inspección aparece otro archivo potencialmente problemático, **no corregirlo automáticamente**.

Reportarlo como:

```text
OUT OF SCOPE FINDING
<archivo>
<problema>
```

---

# 5. Regla específica para `AGENTS.md`

La protección debe garantizar que un agente no pueda modificar `AGENTS.md` por una ruta que contradiga el modelo de protección existente.

La solución debe considerar el mecanismo efectivo, no solamente documentación.

Debe verificarse al menos:

```text
Agent
  ↓
intenta modificar AGENTS.md
  ↓
GTT protection
  ↓
DENIED
```

si `AGENTS.md` efectivamente pertenece al conjunto de artefactos protegidos declarado por el repositorio.

---

# 6. Staging / mecanismo existente

Si el mecanismo actual exige staging, generación de propuesta, hook u otra ruta controlada para modificar artefactos protegidos:

- conservar ese flujo;
- no crear una excepción para `AGENTS.md`;
- no permitir escritura directa simplemente porque el archivo es un Markdown.

La protección debe ser consistente con los artefactos equivalentes.

---

# 7. Validación obligatoria

Ejecutar los checks existentes relacionados con protección.

Como mínimo, revisar y ejecutar los mecanismos reales disponibles en el repositorio para:

```text
protection
GTTGuard
permissions
hooks
validation
```

Además realizar una prueba concreta de que `AGENTS.md` no puede ser modificado por la ruta que la protección pretende bloquear.

No basta con verificar que el archivo aparece en una lista.

Debe comprobarse el enforcement real.

---

# 8. Documentación

Si después de la corrección `DOCS.md` ya describe correctamente el comportamiento:

**no modificarlo innecesariamente.**

Si existe una diferencia entre la implementación corregida y la documentación:

- corregir únicamente la documentación necesaria;
- mantener la terminología existente;
- no introducir nueva metodología.

---

# 9. Resultado esperado

Al finalizar debe cumplirse:

```text
DOCS.md
   │
   │ declara
   ▼
AGENTS.md = protected machinery
   │
   ▼
actual enforcement
   │
   ▼
AGENTS.md realmente protegido
```

No debe existir una contradicción entre:

```text
declaración
vs.
enforcement
```

---

# 10. Reporte obligatorio

Entregar al finalizar:

## Inspected

Archivos/mecanismos revisados.

## Changed

Archivos modificados.

## Added

Archivos nuevos, si los hubiera.

## Protection behavior

Explicar exactamente cómo queda protegido `AGENTS.md`.

## Validation

Indicar:

```text
comando
resultado
```

para cada validación ejecutada.

## Test of enforcement

Explicar cómo se verificó que una modificación no autorizada de `AGENTS.md` queda bloqueada.

## Out of scope findings

Cualquier otro problema encontrado pero no modificado.

## Decision Required

Si surgió una decisión metodológica no definida por esta directriz o por el Canon:

```text
DECISION REQUIRED
<detalle>
```

Si no existe ninguna:

```text
Decision Required: None
```

---

# Restricción final

Esta es una **tarea de corrección puntual**.

No convertirla en una revisión general del bootstrap.

No realizar mejoras adicionales "porque parecen convenientes".

No introducir decisiones metodológicas nuevas.

La condición de éxito es simple:

> **Si `AGENTS.md` está declarado como machinery/protegido, el enforcement real debe protegerlo de acuerdo con el mecanismo existente de GTT.**