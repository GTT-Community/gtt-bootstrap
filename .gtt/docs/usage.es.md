# GTT Bootstrap — Guía de uso

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

GTT gobierna el contexto que guía el desarrollo asistido por IA.

El ciclo normal es:

```text
Gobierno   Contexto → Decisión → Propuesta → Decisión humana → Freeze
Trabajo    Freeze → el ADE trabaja por su cuenta → GTT observa → el trabajo continúa
```

La línea de arriba solo se recorre cuando cambia el diseño gobernado mismo:
la arquitectura, un límite, una restricción, el objetivo o el alcance de una
Epic. El trabajo ordinario nunca pasa por ella: con el diseño congelado, la
implementación no necesita aprobación.

## Flujo normal

### 1. Comenzar desde el contexto gobernado

Antes de tomar una decisión de implementación, el agente debe leer el contexto gobernado aplicable.

No se busca cargar toda la documentación en cada sesión. GTT separa deliberadamente las restricciones que deben estar siempre disponibles del contexto que solo se necesita para una tarea específica.

### 2. Trabajar en la implementación

El trabajo rutinario pertenece a la capa de implementación.

El agente puede modificar código, pruebas, pipelines e infraestructura según las reglas del proyecto.

El trabajo rutinario no requiere un `gtt-domain/change-request.md`.

### 3. Detectar un cambio arquitectónico

Si una solicitud afecta una decisión arquitectónica, una tecnología, una regla de dependencias, la topología de despliegue, la observabilidad u otra decisión gobernada, no se debe modificar silenciosamente el mapa.

Utiliza:

```text
gtt-domain/change-request.md
```

### 4. Proponer el cambio

El agente crea una propuesta revisable en:

```text
gtt-domain/proposals/
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
gtt-domain/proposals/
```

— el borrador del ADR, el texto completo de cada archivo afectado bajo
`gtt-domain/context/` (incluyendo el `gtt-domain/context/stack.md` actualizado), y un
script ejecutable:

```text
gtt-domain/proposals/staged/ADR-NNN-<slug>/
```

El agente nunca lo ejecuta. Revisa el paquete y ejecútalo tú mismo desde la
raíz del proyecto:

```bash
bash .gtt/scripts/gtt-promote.sh ADR-NNN-<slug>
```

Pide una confirmación final, aplica todos los archivos afectados juntos, y
falla con claridad en lugar de dejar el mapa a medio actualizar. Solo esta
ejecución humana explícita escribe realmente en `gtt-domain/adr/` y
`gtt-domain/context/stack.md` — ver el Límite Humano de Promoción en `AGENTS.md`.

### 7. Verificar

Ejecuta los mecanismos de auditoría/check correspondientes.

El CI gate:

```text
.gtt/scripts/gtt-check-stack.sh
```

debe fallar cuando el mapa arquitectónico y las decisiones gobernadas dejan de estar sincronizados.

---

## El mapa arquitectónico

`gtt-domain/context/stack.md` proporciona siete vistas:

1. stack
2. componentes
3. despliegue
4. observabilidad
5. reglas de dependencias
6. historial de cambios del mapa
7. límites — dónde un cambio en el código significa que el diseño pudo haber cambiado, y qué tan serio es; los vigila `gtt-observe.sh`

Utiliza este mapa como primer punto de orientación arquitectónica.

Si una entrada del stack no tiene un ADR en `Locked by`, debe investigarse como una decisión no gobernada.

---

## El backlog

`gtt-domain/backlog.md` es la línea de desarrollo: Epics, Stories, foco actual y
próximo trabajo. Es un artefacto de planificación, no arquitectura — la
precedencia es contexto gobernado → ADR → backlog → implementación, y una
Story nunca sobrescribe una decisión arquitectónica.

El backlog tiene dos clases de entrada, gobernadas de forma distinta:

- **Una Epic la decides tú.** Es intención y alcance: su objetivo, qué
  incluye, dónde termina. La apruebas (`**Approved:** quién — AAAA-MM-DD`) y
  solo entonces deja de estar `Proposed`. Agregar, eliminar o cambiar
  materialmente una es tu decisión (`gtt-propose-change`, formulario 4).
- **Una Story es el plan de trabajo del agente.** El agente crea, divide,
  reescribe, implementa y cierra Stories por su cuenta. No apruebas ninguna, y
  una Story nunca es una compuerta delante del trabajo.

Las Stories no se mantienen honestas firmándolas. Lo hace GTT, observando el
trabajo (sección siguiente): si lo que una Story produce cruza un límite del
diseño que congelaste, te enteras, diga lo que diga la Story.

El trabajo que pides directamente no necesita una Epic primero. Cuando una
Story se termina se marca `Done` con `Closed` (fecha, commit o PR, tests que
pasaron), y una Epic está `Completed` solo cuando todas sus Stories están
`Done` o `Cancelled`.

Ejecuta `.gtt/scripts/gtt-check-backlog.sh` para la integridad estructural
(IDs únicos, valores de estado válidos, una Epic aprobada lleva su objetivo y
quién la aprobó); ejecuta `gtt-audit` para reconciliar el backlog contra lo que
realmente está definido y realmente se hizo.

---

## Trabajar: el agente trabaja, GTT observa

Con el diseño congelado no estás en el ciclo del trabajo ordinario. El agente
implementa, refactoriza, prueba y commitea sin pedir permiso. El freeze no
impide que el código cambie; hace que el diseño que aprobaste sea la
autoridad.

Mientras el agente trabaja, GTT compara el proyecto con ese diseño congelado
y te avisa solo lo que importa:

```text
@gtt · Observation
⚠ OBS-0003 WARNING    B-003  package.json#kafkajs
    new dependency `kafkajs`
    guards: Stack at a glance (section 1)
    work continues
```

| Nivel | Qué significa para ti |
|---|---|
| `NOTICE` | Nada. Queda registrado |
| `WARNING` | Se te avisa una vez. El trabajo continúa |
| `GOVERNANCE` | Se te avisa una vez. El trabajo continúa. Decide antes del próximo freeze |
| `BLOCKING` | La operación afectada se detuvo: una regla que ratificaste dice que esto no debe pasar |

Lo que puedes hacer, cuando quieras:

```bash
bash .gtt/scripts/gtt-observe.sh backlog                              # qué está abierto
bash .gtt/scripts/gtt-observe.sh accept OBS-0003 --by <tú> --apply   # queda así
bash .gtt/scripts/gtt-observe.sh reject OBS-0003 --by <tú> --apply   # la validación falla hasta que desaparezca
bash .gtt/scripts/gtt-observe.sh defer  OBS-0003 --by <tú> --apply   # más adelante
```

Aceptar una observación no cambia el diseño. Si el diseño mismo tiene que
cambiar — el bus de eventos ahora sí es parte de la arquitectura — eso es una
solicitud de cambio, un ADR y después un **nuevo freeze**:
`bash .gtt/scripts/gtt-freeze.sh` registra una nueva línea base y conserva la
anterior como historial. No existe el unfreeze.

Lo que GTT vigila es lo que declaraste en la sección 7 de
`gtt-domain/context/stack.md` (`gtt-boundaries`). Mantenlo corto, y reserva
`BLOCKING` para lo que nunca debe pasar sin una decisión.

El primer control que comparten todos los agentes y todas las personas es el
hook de pre-commit de Git: `bash .gtt/scripts/gtt-git-hook.sh install --apply`.
Se puede saltar con `git commit --no-verify`, así que la capa garantizada es
el CI: ejecuta `gtt-validate.sh` y `gtt-check-stack.sh` sobre el pull request.

---

## Artefactos protegidos (GTTGuard)

Algo de código L3 merece una regla más estricta que "libremente editable":
un archivo, clase o método que un desarrollador marcó explícitamente para
que un agente pueda leerlo y proponer cambios, pero nunca modificarlo por
su cuenta. Eso es GTTGuard — un mecanismo hermano de la gobernanza L0/L1,
no parte de ella.

**Marcar algo como protegido** es una edición de código normal, no un
cambio gobernado: agrega `@GTTGuard` (Java/Python), `[GTTGuard]` (C#), o
`// @GTTGuard` / `# @GTTGuard` (lenguajes basados en comentarios),
opcionalmente con `reason="..."`/`source="..."`, justo arriba de la
declaración — o como primera línea del archivo para proteger todo el
archivo. Usa la skill `gtt-guard` para esto, y después ejecuta:

```bash
bash .gtt/scripts/gtt-guard-sync.sh
```

para regenerar `.gtt/protection/registry.yaml` desde cada marcador en el
código. El registro es derivado, nunca editado a mano —
`gtt-check-protection.sh` hace fallar el build si se desincroniza de lo
que los marcadores realmente declaran.

**Cambiar algo ya protegido** pasa por el formulario 5 de
`gtt-propose-change`, no por una edición directa. Una vez que apruebas la
propuesta **en la conversación**, el agente implementa el cambio
directamente y vuelve a sincronizar el registro — sin ADR, sin script de
promoción. Esto es deliberadamente más liviano que el Límite Humano de
Promoción de arriba: GTTGuard protege código L3 que tú decidiste
proteger, no `gtt-domain/context/` ni `gtt-domain/adr/`, y los dos modelos de promoción
nunca deben confundirse.

En Claude Code, `.claude/hooks/protect-guard.py` bloquea una edición
protegida en tiempo real, resolviendo el tramo de línea actual de cada
símbolo protegido en vivo contra el archivo en disco, de modo que un
método sin proteger junto a uno protegido sigue siendo editable. Kiro,
Codex y GitHub Copilot no tienen un bloqueo equivalente en tiempo real; el
enforcement ahí es `.gtt/scripts/gtt-check-protection.sh` en CI más una
nota en el plano de instrucciones, el mismo respaldo honesto que ya usa la
condición de dos regímenes de `gtt-domain/context/`/`gtt-domain/adr/`.

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
gtt-domain/context/
```

Contiene la comprensión gobernada actual de la solución.

### L1 — decisiones arquitectónicas

```text
gtt-domain/adr/
```

Contiene decisiones aceptadas y su justificación.

### L2 — documentación

```text
.gtt/docs/
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
gtt-domain/.frozen
```

el contexto gobernado queda protegido.

Los cambios arquitectónicos deben seguir el flujo de solicitud/propuesta/ADR.

---

## Mantener útil el contexto

Mantén pequeño el contexto que se carga siempre.

`constraints.md` debe contener únicamente restricciones que realmente necesiten estar disponibles continuamente.

Las explicaciones detalladas, metodología, migraciones y material de referencia deben permanecer en `.gtt/docs/`.

No conviertas cada instrucción en una regla permanentemente cargada.

---

## Adaptadores por herramienta

GTT proporciona un adaptador por cada ADE soportado. Un proyecto instala el
adaptador de cada ADE que su humano eligió que participe, con exactamente uno
declarado Primario (un identificador de flujo que no tiene autoridad) — elegido en
el bootstrap y registrado en `.gtt/ade.json`, no copiando archivos después. Varios
ADE pueden trabajar en el proyecto a la vez: los mismos artefactos gobernados y la
misma Frontera de Promoción Humana rigen para todos.

- Claude Code utiliza `.claude/`.
- Kiro utiliza `.kiro/`.
- Codex utiliza `AGENTS.md` y la configuración aplicable, sin archivo adicional.
- GitHub Copilot utiliza `.github/instructions/gtt.instructions.md` más `AGENTS.md`.

Gestiona el conjunto con `.gtt/scripts/gtt-ade.sh` (ensayo hasta `--apply`): `state` muestra
el Primario, los ADE participantes y la salud de cada integración, `validate` falla cuando una
integración participante está rota, `install`/`remove`/`set-primary`/`update` cambian el
conjunto, y `owned` lista exactamente los archivos que GTT instaló para los ADE — lo único que
un clean o un `export --clean` puede eliminar. `gtt-domain/session.md` lleva el mismo estado, de
modo que cualquier ADE que retome el proyecto lo ve.

**Nunca elimines `AGENTS.md`.**

---

## Checklist operativo

Antes de implementar:

- [ ] Leer el contexto gobernado aplicable.
- [ ] Determinar si la tarea es trabajo ordinario o un cambio al diseño gobernado.
- [ ] Trabajo ordinario: hacerlo. Ninguna Story necesita aprobación previa.
- [ ] Un cambio al diseño gobernado, o una Epic nueva/modificada: crear/procesar una solicitud de cambio.

Durante la implementación:

- [ ] Mantener la implementación alineada con el contexto.
- [ ] No modificar silenciosamente decisiones gobernadas.
- [ ] Si un archivo/clase/método tiene un marcador `@GTTGuard`, usar `gtt-propose-change` (formulario 5) en lugar de editarlo directamente.
- [ ] Mantener la Story al día sobre la marcha: es el plan de trabajo, así que cuando aparece algo no escrito se actualiza y se continúa; nadie la aprueba.
- [ ] Actualizar el estado de la Story y el Current Focus a medida que avanza el trabajo real.
- [ ] Al terminar, marcar la Story `Done` con `Closed` (fecha, commit o PR, tests que pasaron); marcar la Epic `Completed` cuando todas sus Stories lo estén.
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

`readme-gtt.md`, `readme-gtt.es.md` y `AGENTS.md` permanecen en la **raíz
del proyecto** — los puntos de entrada canónicos, leídos antes que
cualquier otra cosa. Todo lo demás sigue el mismo scaffold en el repositorio Bootstrap y en cualquier
proyecto anfitrión donde se instale: el Motor (con la Documentación, incluyendo
este archivo) en `.gtt/`, y el dominio gobernado en `gtt-domain/`.


Cuando un agente despliega GTT dentro de un proyecto anfitrión, DEBE reorganizar el workspace instalado para que coincida con el scaffold de GTT:

```text
/
├── AGENTS.md                     # contrato portable del agente (archivo de descubrimiento del ADE)
├── readme-gtt.md
├── readme-gtt.es.md
├── SOURCE-BRIEF.*                # si existió documento fuente
│
├── .gtt/                         # MOTOR DE GTT-METHOD (maquinaria, estado derivado, documentación propia de GTT)
│   ├── README.md
│   ├── index/
│   ├── protection/
│   ├── ade.json                  #   estado de ADE del proyecto: participantes, primario, registro de instalación (proyectos instalados)
│   ├── scaffold/manifest.yaml    #   también el registro de ADE (overlays:) y las templates: que posee el Bootstrap
│   ├── scaffold/templates/       #   plantillas propiedad del Bootstrap (el Cuestionario Inicial de Diseño)
│   ├── scripts/
│   ├── session-adapters/
│   └── docs/                     #   documentación propia de GTT: index, installation, usage, docs, evidence,
│                                 #   gtt-completion, session-adapter-contract
│
├── gtt-domain/                   # EL DOMINIO GOBERNADO POR GTT-METHOD
│   ├── context/                  #   contexto gobernado L0
│   ├── adr/                      #   decisiones aceptadas L1
│   ├── proposals/                #   borradores gobernados pendientes de decisión humana
│   ├── backlog.md
│   ├── change-request.md
│   ├── session.md                #   estado operativo derivado (nunca autoridad)
│   └── .frozen                   #   marcador de freeze, escrito por gtt-freeze.sh
│
└── .claude/ | .kiro/ | .github/instructions/ # OVERLAYS DE ADE - uno por ADE participante; exactamente un ADE es Primario
```

El adaptador de cada ADE participante — `.claude/`, `.kiro/`, o `.github/instructions/gtt.instructions.md` — permanece en la raíz del proyecto anfitrión. Solo se instalan los adaptadores de los ADE participantes.

El agente debe preservar los archivos existentes del proyecto, no sobrescribir conflictos silenciosamente y no ejecutar automáticamente el freeze. La revisión y confirmación humana deben ocurrir antes del freeze.
