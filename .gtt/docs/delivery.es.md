# Planificación de entrega

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

GTT gobierna **qué** se construye. La planificación de entrega suma **cuánto tarda y con cuántas manos**, antes de
empezar y mientras se trabaja. Lo calcula `.gtt/scripts/gtt-delivery.sh` desde los archivos: el agente explica y
propone, tú decides, y medir no gasta tokens.

GTT planifica y vigila los frentes. No lanza ni orquesta agentes: eso le corresponde a tu ADE.

## La skill

La skill `gtt-delivery` (estimar, comprar o construir, frentes, propuestas cuando se abre una señal) llega a cada ADE que lee skills, desde una sola fuente: `.gtt/scaffold/skills/gtt-delivery/SKILL.md`. Claude Code lee `.claude/skills/`, Codex `.agents/skills/`, Copilot `.github/skills/` y Kiro `.kiro/steering/` (incluida por su descripción). Las copias las genera `bash .gtt/scripts/gtt-skills.sh sync --apply` y `validate` falla si una se desvía o falta para un ADE participante.

## Las preguntas

Se hacen al inicio (`gtt init` hace D1-D3; el cuestionario inicial, sección 4.7, las confirma y hace D4-D6). Una por
turno; "Aún no sé" es válida y nunca se inventa nada.

| Id | Pregunta |
|---|---|
| D1 | ¿Quién va a construir esto? (yo con un agente / yo con varios / un equipo) |
| D2 | ¿Cuántos frentes en paralelo puedes sostener? Depende de los límites de uso de tu plan del agente. |
| D3 | ¿Para cuándo necesitas una primera versión usable? (días / 1-2 semanas / un mes o más / sin fecha) |
| D4 | ¿Qué priorizas? (rapidez / equilibrio / todo propio) |
| D5 | ¿Puedes usar servicios de terceros para lo genérico (login, cobros, correo, archivos)? |
| D6 | Tope por Epic antes de que GTT avise (8 horas de agente por defecto) |

La respuesta queda en `.gtt/delivery.json`. Es operación, no arquitectura: se puede cambiar en cualquier momento con
`gtt delivery set` (o `gtt-delivery.sh select --apply`).

## Estimar

Las estimaciones son **horas de agente más puntos de decisión humana**, nunca semanas de persona: `Estimate: 6h + 2 decisions`.
Mientras haya menos de tres Stories medidas, el plan dice **sin calibrar**.

| Entrada | Campos |
|---|---|
| Epic (se aprueban con el Epic) | `Estimate`, `Depends on`, `Lane`, `Owner` (Team profile), `Touches`, `Build` (`own` or `integrate (ADR-NNN)`), `Budget` |
| Story (del agente) | `Estimate`, `Owner` (`agent` o `human`; tus acciones son Stories con `Owner: human`) |

`Budget` es `ok`, `over - accepted: <razón> - <quién> - <AAAA-MM-DD>`, u `over - split | cut | integrate`.
Comprar un servicio en vez de construir es una decisión de arquitectura: `Build: integrate (ADR-NNN)` exige ese ADR.

## Antes de empezar: el plan

`gtt plan` imprime el plan por frente, la cadena más larga, la fecha estimada y, si no cabe, las palancas (frentes
paralelos, comprar en vez de construir, tajada vertical) con las horas que ahorra cada una. Toda palanca es una
`[PROPUESTA]`. `gtt plan --lanes` imprime un resumen por frente (Epics, rutas que puede tocar, interfaces de las que
depende, su `Done when`) y los comandos `git worktree add` para copiar. No crea nada.

Dos Epics de frentes distintos no deben compartir `Touches`, salvo que uno dependa del otro a través de una interfaz.

## Mientras se trabaja: el registro y las señales

`gtt-domain/delivery-log.jsonl` es solo de agregado. Cada cambio de estado de una Story o un Epic queda con su hora,
actor y frente, escrito por `gtt-delivery.sh log`, que lee el backlog: el agente no le pasa argumentos y el archivo está
protegido contra escritura. En Claude Code lo corre un hook tras cada escritura al backlog; en los demás ADEs, al iniciar
la sesión y en `gtt status` (resolución menor). No depende de Git.

La calibración es la mediana de real/estimado de las Stories cerradas. La fecha estimada es lo que falta por esa razón,
siguiendo la cadena de dependencias más larga.

| Señal | Condición |
|---|---|
| DLV-STORY-OVER | Story In Progress por más de 1.5× su estimación |
| DLV-EPIC-BUDGET | Epic sobre su tope sin decisión en `Budget` |
| DLV-FORECAST | Fecha estimada posterior al plazo |
| DLV-HUMAN-WAIT | Acción tuya esperando más de 24 h |
| DLV-LANE-CROSS | Epics de frentes distintos con `Touches` cruzados |
| DLV-NO-VALUE | Ningún Epic `Kind: slice` o `skeleton` (solo con método declarado) |
| DLV-UNCALIBRATED | Menos de 3 Stories medidas |
| DLV-NO-PLAN | 8 o más Stories abiertas y menos de la mitad con duración (su `Estimate` o el de su Epic). Se dispara **aunque nunca se haya declarado la planificación**: nadie puede decir cuánto dura el backlog |
| DLV-STALE-STATUS | Una Story que no está `Done` mientras un commit reciente ya la cierra por nombre (`closes STORY-168`) |
| DLV-GROWTH | Las Stories abiertas (o las horas estimadas) crecieron `growth_pct` (50% de partida) o más desde el tamaño de referencia tomado cuando declaraste el plan |
| DLV-OVER-TARGET | Las horas estimadas que faltan superan el tope que **tú** declaraste con `--scope-cap` |
| DLV-PACE-DRIFT | Un documento de plan habla en otro ritmo que el `pace` declarado (`día N`, `jornada`, `cronograma` bajo `flow`) |

### Qué tan grande es el proyecto y cómo cambiar de idea

GTT mide; **tú** decides qué es demasiado. `gtt delivery review` (o `gtt-delivery.sh size`) reporta las Stories abiertas, las horas de
agente que faltan (o «no medible» si las Épicas no tienen `Estimate`: nunca 0), la capacidad hasta tu fecha, el crecimiento desde el
tamaño de referencia y tu propio tope. GTT solo juzga contra números que tú declaraste:

- `gtt delivery review --scope-cap <horas|none>`: cuántas horas de agente son demasiadas para este proyecto.
- `gtt delivery set --growth-pct <n>`: cuánto puede crecer el backlog antes de que GTT avise.
- `gtt delivery review --keep`: mantenerlo como está; el tamaño de hoy pasa a ser la referencia.
- `gtt delivery review --single-pass`: una sola pasada continua: sin fecha y sin cronograma por días.
- Para adelgazar, GTT muestra las palancas (recortar, unir, comprar hecho); recortar una Épica es una propuesta que tú decides.
- En una terminal `gtt delivery review` pregunta qué hacer, incluso cambiar quién construye, los frentes, la fecha y el ritmo.

`pace` es `days` o `flow` (flujo continuo). Se declara una vez con `gtt delivery set --pace flow`; cambiarlo después es el mismo
comando, en un solo lugar, y DLV-PACE-DRIFT lista cada documento que aún habla distinto. Las tres señales solo avisan:
nunca detienen un proyecto que no declaró planificación.

Qué significa cada una depende de tu Autonomy Profile (`profiles.json`, `delivery`). `gtt report [--epic EPIC-NNN] [--json]`
muestra % por Epic, real contra estimado, la razón, la fecha estimada y las señales abiertas.

## En el freeze

`gtt-delivery.sh check --pre-freeze` corre dentro de `gtt-freeze.sh` y `gtt-validate.sh`: cada Epic Planned tiene
Estimate; un Epic sobre su tope trae su decisión; con más de un frente cada Epic tiene `Lane` y `Touches` y los frentes
no se cruzan; cada `integrate` apunta a un ADR que existe; cada fuente externa `[FUENTE: url, consultado AAAA-MM-DD]`
tiene menos de 90 días. Light solo avisa, Medium exige las decisiones, Hard y Team bloquean. Un proyecto que nunca
declaró planificación de entrega no se obstruye.
