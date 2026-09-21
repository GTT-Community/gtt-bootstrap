# GTT Bootstrap — Guía de uso

GTT gobierna el contexto que guía el desarrollo asistido por IA.

El ciclo normal es:

```text
Contexto → Decisión → Propuesta → Aprobación → Implementación → Verificación
```

## Flujo normal

### 1. Comenzar desde el contexto gobernado

Antes de tomar una decisión de implementación, el agente debe leer el contexto gobernado aplicable.

No se busca cargar toda la documentación en cada sesión. GTT separa deliberadamente las restricciones que deben estar siempre disponibles del contexto que solo se necesita para una tarea específica.

### 2. Trabajar en la implementación

El trabajo rutinario pertenece a la capa de implementación.

El agente puede modificar código, pruebas, pipelines e infraestructura según las reglas del proyecto.

El trabajo rutinario no requiere un `gtt/CHANGE-REQUEST.md`.

### 3. Detectar un cambio arquitectónico

Si una solicitud afecta una decisión arquitectónica, una tecnología, una regla de dependencias, la topología de despliegue, la observabilidad u otra decisión gobernada, no se debe modificar silenciosamente el mapa.

Utiliza:

```text
gtt/CHANGE-REQUEST.md
```

### 4. Proponer el cambio

El agente crea una propuesta revisable en:

```text
gtt/proposals/
```

Debe explicar:

- decisión actual
- cambio solicitado
- motivo
- disparador
- alcance
- impacto
- riesgo
- alternativas
- filas afectadas del mapa arquitectónico

### 5. Aprobar

La persona responsable revisa la propuesta.

La aprobación es una decisión de gobernanza, no un detalle de implementación.

### 6. Registrar la decisión

El cambio aprobado se convierte en un **paquete de promoción**, preparado bajo:

```text
gtt/proposals/
```

— el borrador del ADR, el texto completo de cada archivo afectado bajo
`gtt/context/` (incluyendo el `gtt/context/stack.md` actualizado), y un
script ejecutable:

```text
gtt/proposals/apply-ADR-NNN-<slug>.sh
```

El agente nunca lo ejecuta. Revisa el paquete y ejecútalo tú mismo desde la
raíz del proyecto:

```bash
bash gtt/proposals/apply-ADR-NNN-<slug>.sh
```

Pide una confirmación final, aplica todos los archivos afectados juntos, y
falla con claridad en lugar de dejar el mapa a medio actualizar. Solo esta
ejecución humana explícita escribe realmente en `gtt/adr/` y
`gtt/context/stack.md` — ver el Límite Humano de Promoción en `AGENTS.md`.

### 7. Verificar

Ejecuta los mecanismos de auditoría/check correspondientes.

El CI gate:

```text
gtt/scripts/gtt-check-stack.sh
```

debe fallar cuando el mapa arquitectónico y las decisiones gobernadas dejan de estar sincronizados.

---

## El mapa arquitectónico

`gtt/context/stack.md` proporciona siete vistas:

1. stack
2. componentes
3. despliegue
4. observabilidad
5. reglas de dependencias
6. historial de cambios del mapa
7. señales de drift — rutas fuera de `gtt/` que cargan peso arquitectónico, vigiladas por `detect-drift.py`

Utiliza este mapa como primer punto de orientación arquitectónica.

Si una entrada del stack no tiene un ADR en `Locked by`, debe investigarse como una decisión no gobernada.

---

## El backlog

`gtt/backlog.md` es la línea de desarrollo: Epics, Stories, foco actual y
próximo trabajo. Es un artefacto de planificación, no arquitectura — la
precedencia es contexto gobernado → ADR → backlog → implementación, y una
Story nunca sobrescribe una decisión arquitectónica.

Antes de trabajar en desarrollo, establecé la Epic/Story aplicable desde el
backlog. Agregar, eliminar, o cambiar materialmente una va por
`gtt/CHANGE-REQUEST.md`, igual que un cambio de arquitectura. Actualizar el
estado de una Story o las listas de Current Focus / Next Work / Blocked
durante trabajo ya aprobado es una edición directa, no una solicitud de
cambio.

Corré `gtt/scripts/gtt-check-backlog.sh` para la integridad estructural
(IDs únicos, valores de estado válidos); corré `gtt-audit` para reconciliar
el backlog contra lo que realmente está definido y realmente se hizo.

---

## Ejemplo de solicitud de cambio

La solicitud debe comunicar intención, no imponer ciegamente una implementación.

```text
¿Qué debe cambiar?
Reemplazar la tecnología actual de caché.

¿Por qué?
La tecnología actual ya no cumple las restricciones operativas acordadas.

Disparador:
Nuevos requisitos de despliegue.

Alcance:
Capa de caché y observabilidad relacionada.

Impacto:
Arquitectura, despliegue, configuración y documentación operativa.

Riesgo:
Compatibilidad de migración e invalidación de caché.

Prioridad:
Alta.
```

El agente debe convertir esto en una propuesta, no editar directamente el mapa arquitectónico.

---

## Capas de contexto

### L0 — contexto gobernado

```text
gtt/context/
```

Contiene la comprensión gobernada actual de la solución.

### L1 — decisiones arquitectónicas

```text
gtt/adr/
```

Contiene decisiones aceptadas y su justificación.

### L2 — documentación

```text
gtt/docs/
```

Contiene material de referencia humana y documentación metodológica.

### L3 — implementación

```text
src/
tests/
pipelines/
IaC/
```

Contiene la implementación gobernada por las capas superiores.

---

## Freeze y modelo de dos regímenes

GTT distingue:

### Régimen de bootstrap

Antes del freeze:

- el contexto puede ser poblado por el procedimiento de bootstrap;
- el diseño todavía está siendo confirmado;
- el contexto aún no está ratificado.

### Régimen gobernado

Después de:

```text
gtt/.frozen
```

el contexto gobernado queda protegido.

Los cambios arquitectónicos deben seguir el flujo de solicitud/propuesta/ADR.

---

## Mantener útil el contexto

Mantén pequeño el contexto que se carga siempre.

`constraints.md` debe contener únicamente restricciones que realmente necesiten estar disponibles continuamente.

Las explicaciones detalladas, metodología, migraciones y material de referencia deben permanecer en `gtt/docs/`.

No conviertas cada instrucción en una regla permanentemente cargada.

---

## Adaptadores por herramienta

GTT proporciona un adaptador por cada ADE soportado. Un proyecto instala
exactamente el que corresponde al ADE que ejecutó su bootstrap — nunca más
de uno — resuelto automáticamente, no elegido copiando archivos después.

- Claude Code utiliza `.claude/`.
- Kiro utiliza `.kiro/`.
- Codex utiliza `AGENTS.md` y la configuración aplicable, sin archivo adicional.
- GitHub Copilot utiliza `.copilot/copilot-instructions.md` más `AGENTS.md`.

**Nunca elimines `AGENTS.md`.**

---

## Checklist operativo

Antes de implementar:

- [ ] Leer el contexto gobernado aplicable.
- [ ] Establecer la Epic/Story aplicable desde `gtt/backlog.md`, si existe una.
- [ ] Determinar si la tarea es rutinaria o arquitectónica.
- [ ] Si es arquitectónica, o una Epic/Story nueva/modificada, crear/procesar una solicitud de cambio.

Durante la implementación:

- [ ] Mantener la implementación alineada con el contexto.
- [ ] No modificar silenciosamente decisiones gobernadas.
- [ ] Actualizar el estado de la Story y el Current Focus a medida que avanza el trabajo real.
- [ ] Preservar la estructura del proyecto anfitrión.

Antes del merge:

- [ ] Confirmar que existen ADR para los cambios arquitectónicos.
- [ ] Confirmar que el mapa refleja las decisiones aceptadas.
- [ ] Ejecutar el stack check.
- [ ] Revisar el diff resultante.

---

## Principio rector

> **El contexto es la Fuente de Verdad.**

GTT no intenta impedir que la IA modifique software. Establece un límite gobernado alrededor de las decisiones que definen qué debe ser el software.

### Destino del despliegue: repositorio Bootstrap vs. proyecto anfitrión

`README-GTT.md`, `README-GTT.es.md` y `AGENTS.md` permanecen en la **raíz
del proyecto** — los puntos de entrada canónicos, leídos antes que
cualquier otra cosa. Todo lo demás que posee GTT, incluyendo este archivo,
vive bajo `gtt/`, tanto en el repositorio Bootstrap como en cualquier
proyecto anfitrión donde se instale.

Cuando un agente despliega GTT dentro de un proyecto anfitrión, DEBE reorganizar el workspace instalado para que el contenido propio de GTT quede bajo `gtt/`:

```text
/
├── AGENTS.md
├── README-GTT.md
├── README-GTT.es.md
├── SOURCE-BRIEF.*                # si existió documento fuente
└── gtt/
    ├── README.md
    ├── INDEX.md
    ├── CHANGE-REQUEST.md
    ├── GTT-COMPLETION.md
    ├── backlog.md
    ├── INSTALLATION.md
    ├── INSTALLATION.es.md
    ├── USAGE.md
    ├── USAGE.es.md
    ├── adr/
    ├── context/
    ├── docs/
    ├── proposals/
    └── scripts/
```

El único adaptador resuelto — `.claude/`, `.kiro/`, o `.copilot/copilot-instructions.md` — permanece en la raíz del proyecto anfitrión. Solo ese se instala.

El agente debe preservar los archivos existentes del proyecto, no sobrescribir conflictos silenciosamente y no ejecutar automáticamente el freeze. La revisión y confirmación humana deben ocurrir antes del freeze.
