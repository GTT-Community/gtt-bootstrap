# PROPOSAL — Soporte de Google Antigravity como ADE propio

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Fecha del análisis: 2026-10-05. Bootstrap 1.3.0, scaffold layout 2.

**Nota de cierre (2026-10-06, Bootstrap 1.3.1).** Las condiciones de esta propuesta que piden aprobar
cada Story y escribirlas como `Ready` (más abajo, en *Estado* y en *Listo para implementación*) quedan
sin efecto: la arquitectura de dos planos las reemplazó y nadie aprueba una Story. El soporte v1 que
describía la STORY-001 está implementado - la entrada `antigravity` de `.gtt/scaffold/manifest.yaml`, el
overlay bajo `.agents/`, el formato en `gtt_protect.py` y el escenario `antigravity` de la suite de
aceptación. La verificación dentro de Antigravity (CLI, IDE, escritorio) sigue pendiente: el registro lo
declara `realtime-hook-unverified`. Los cambios de `AGENTS.md` de esta propuesta se entregan en el
paquete `apply-bootstrap-1.3.1-closure.sh`; `AGENTS-antigravity.patch` y su script quedan reemplazados
por él y no deben ejecutarse después.

**Estado: revisión 2.** El Solution Designer aprobó la revisión 1 "con cambios, como diseño
base" en conversación el 2026-10-05, con diez correcciones y la instrucción expresa de no
implementar todavía. Esta revisión las incorpora. Sigue sin autorizar implementación: eso
requiere la aprobación de cada Story (ver paquete).

## Paquete

| Archivo | Qué es |
|---|---|
| `PROPOSAL-antigravity-ade-support.md` | este documento: diseño |
| `AGENTS-antigravity.patch` | diff de las cinco modificaciones de `AGENTS.md`; comprobado con `git apply --check` |
| `apply-AGENTS-antigravity.sh` | script que aplica ese diff; lo ejecuta el Solution Designer, nunca el agente |
| `PROPOSAL-backlog-antigravity-epic.md` | Epic, tres Stories y criterios de aceptación |
| `PROPOSAL-session-memory-consolidation.md` | deuda transversal de sesión, separada |

## Correcciones de la revisión 2

| # | Corrección pedida | Dónde queda |
|---|---|---|
| 1 | id propio `antigravity`, nunca alias de `codex` | §5, §9; STORY-001 |
| 2 | Niveles de soporte v1; "Supported" = integración de GTT, no enforcement garantizado | *Recommendation* |
| 3 | `.agents/` compartido; conflicto con `hooks.json` documentado; sin fusión | §8, §11, §19 |
| 4 | Sesión/handoff separado | §15; propuesta aparte |
| 5 | Sin modelo de capacidades nuevo | §16: el modelo actual lo expresa; no hay gap |
| 6 | Diff de `AGENTS.md` preparado, sin aplicar; regla corta | §10; `AGENTS-antigravity.patch` |
| 7 | Verificación práctica como requisito de implementación | §12; STORY-002 y STORY-003 |
| 8 | Epic y Stories | `PROPOSAL-backlog-antigravity-epic.md` |
| 9 | Sin código | no se tocó ningún archivo fuera de `gtt-domain/proposals/` |
| 10 | Recomendación sobre el paso a implementación | *Listo para implementación* al final |

Además, la revisión 2 corrige un dato de la revisión 1: el límite de tamaño de las reglas (§3, §10).

```text
Proposed Architecture Change

Current decision:   El registro de ADEs (overlays: en .gtt/scaffold/manifest.yaml:120-125) declara
                    seis ADEs: claude, kiro, copilot, cursor, openhands, codex. Antigravity no existe
                    para GTT: no se detecta, no se puede instalar, ni ser participante ni Primary.
Suggested change:   Añadir el ADE `antigravity` con overlay propio de tres archivos bajo .agents/
                    (dos reglas y hooks.json), un formato `antigravity` en gtt_protect.py y
                    enforcement `realtime-hook-unverified`. Sin cambio de modelo del registro.
Reason:             Antigravity lee AGENTS.md, así que hoy trabaja en un proyecto GTT semi-instruido
                    pero invisible: sin registro, sin validación, sin bloqueo y sin poder declararse
                    Primary. Declararlo como `codex` falsea el registro.
Impact:             1 línea de manifest, ~45 líneas en gtt_protect.py, 3 archivos de overlay nuevos,
                    ~10 aserciones de test que enumeran los ADEs, documentación en 8 archivos
                    (incluido AGENTS.md, que es del Solution Designer). gtt_ade.py, gtt_manifest.py,
                    gtt-check-adapter.sh y gtt-validate.sh no cambian.
Risk:               (1) Hook no verificado: en IDE y escritorio puede no dispararse, así que el
                    bloqueo real sería solo CI. (2) AGENTS.md pesa 59 KB y supera el límite por
                    archivo que Antigravity documenta (24 KB); si no lo carga entero, se pierde
                    parte del contrato. (3) .agents/ es compartido con OpenHands.
                    Detección: tests de aceptación + verificación práctica por superficie (§12).
Affected files:     ver §22.
Alternatives considered: ver §21 y "Alternativas" al final.

Status: Requires Architect approval
```

Esta propuesta no toca ninguna fila de `gtt-domain/context/stack.md`: en este repositorio el
contexto gobernado sigue siendo la plantilla (pre-freeze, sin stack decidido). Lo que cambia es
el producto Bootstrap: maquinaria de `.gtt/`, el catálogo de overlays y `AGENTS.md`.

---

## 1. Estado actual

| Hecho | Evidencia |
|---|---|
| Antigravity no está en el registro | `.gtt/scaffold/manifest.yaml:120-125`; ninguna mención a "antigravity" ni "gemini" en el repo |
| `detect` no lo propone | `gtt-ade.sh detect` lista seis candidatos, ninguno Antigravity |
| `install` lo rechaza | `gtt-ade: unknown ADE id(s) ... antigravity (registry: claude, codex, copilot, cursor, kiro, openhands)` — `gtt_ade.py:385-388` |
| El motor de protección no lo conoce | `gtt_protect.py:232` — `FORMATS = {"cursor": cursor, "openhands": openhands}` |
| Sin declaración de sesión | `.gtt/session-adapters/` contiene claude, codex, copilot, kiro |
| `.agents/` ya está en uso | `.agents/skills/gtt/SKILL.md` es del overlay de OpenHands (`manifest.yaml:124`) |

## 2. Cómo funciona GTT hoy

**El registro es dato, el motor es genérico.** `gtt_ade.py` no contiene ningún nombre de ADE.
Todo lo que sabe sale de la sección `overlays:` del manifest, leída por `gtt_manifest.overlays()`
(`gtt_manifest.py:110-137`), que normaliza cada entrada a diez claves: `id`, `name`, `path`,
`entry`, `owned`, `detect`, `enforcement`, `scaffold`, `version`, `role`.

| Aspecto | Mecanismo real |
|---|---|
| Detección | `detect_rows` (`gtt_ade.py:312-325`): existe alguna ruta de `detect`, o el binario `ade_binary` de `.gtt/session-adapters/<id>.json` está en el PATH. Solo produce candidatos. |
| Instalación | `cmd_install` (`gtt_ade.py:405-465`): copia los archivos de `owned` desde el catálogo, registra sha256 en `.gtt/ade.json`, dry-run sin `--apply`, transaccional con rollback. |
| Conflicto | Si un archivo de `owned` ya existe en el host: `CONFLICT`, no se escribe nada (`gtt_ade.py:436-448`). No fusiona nunca. |
| Participación / Primary | `.gtt/ade.json`: `participating`, `primary`, `excluded`, `installed`. Primary debe ser uno de los participantes (`gtt_ade.py:243`). Nada condiciona Primary al nivel de enforcement. |
| Propiedad | El ledger atribuye cada archivo a **un** ADE. `remove` y `update` solo tocan archivos del ledger sin modificar. No hay propiedad compartida de un archivo. |
| Validación | `validate` (`gtt_ade.py:219-281`): existen `path` y `entry`, existen los archivos del ledger, WARN por ADE detectado no participante. `gtt-check-adapter.sh` sin argumento delega aquí. |
| Hooks | Claude: hooks propios en `.claude/hooks/`. Cursor y OpenHands: un `hooks.json` cada uno que apunta al motor neutral `gtt_protect.py hook --format <ade>`. Kiro, Copilot, Codex: sin bloqueo, solo CI. |
| Sesión | Servicio neutral `gtt-session-context.sh` → `gtt-status.sh` → `gtt-domain/session.md`. Ver §14. |
| Skills | Solo Claude tiene skills nativas de GTT. OpenHands tiene un SKILL.md que remite a secciones de `AGENTS.md`. El resto sigue `AGENTS.md` directamente. |

**Patrón de adapter establecido.** No existe un directorio `.gtt/<ade>/`. Un adapter es:

1. una línea en `overlays:`;
2. sus archivos en las rutas nativas del ADE, presentes en el catálogo;
3. opcionalmente un formato en `gtt_protect.py`;
4. opcionalmente una declaración `.gtt/session-adapters/<id>.json`.

Cursor y OpenHands (los dos últimos añadidos) siguen exactamente 1-3 y omiten 4.

## 3. Cómo funciona Antigravity respecto al contrato GTT

Fuentes: documentación oficial de Antigravity (hooks, skills) y guías de terceros. Nada de esto
fue ejecutado dentro de Antigravity en este análisis.

| Capacidad | Antigravity | Evidencia |
|---|---|---|
| Lee `AGENTS.md` | Sí, desde el IDE 1.20.5 | documentado por terceros |
| Reglas de workspace | `.agents/rules/*.md`, directorio plano; `.agent/rules/` sigue funcionando | documentado |
| Activación de una regla | frontmatter `trigger: always_on \| model_decision \| glob \| manual`, con `globs:` para `glob` | documentación oficial |
| Límite por archivo de reglas | 24 KB según la documentación oficial; 12.000 caracteres según guías de terceros | **las fuentes no coinciden** |
| Presupuesto agregado | 20.000 tokens entre todas las reglas globales y `always_on` | documentación oficial |
| Tratamiento de `AGENTS.md` | se trata como contenido `always_on`, "sujeto a las mismas restricciones de tamaño" | documentación oficial; qué ocurre al excederlas no está dicho |
| Precedencia | `~/.gemini/GEMINI.md` global gana sobre `AGENTS.md`; `.agents/rules/` se aplica al final | documentado por terceros |
| Skills | `.agents/skills/<nombre>/SKILL.md` | documentado (estándar Agent Skills, mayo 2026) |
| Workflows | `.agents/workflows/<nombre>.md`; en migración hacia skills | documentado |
| Hooks | `.agents/hooks.json`; eventos `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop` | documentado |
| Denegar una herramienta | salida JSON `{"decision": "deny", "reason": ...}` | documentado |
| Evento de inicio de sesión | No existe. `PreInvocation` se dispara antes de **cada** llamada al modelo | documentado |
| Superficies que ejecutan hooks | La doc dice CLI, IDE y 2.0. Un reporte de la comunidad (agosto 2026, IDE 2.1.1 y escritorio 2.5.0) midió cero invocaciones fuera de la CLI `agy`; sin respuesta de Google | **contradictorio** |
| Códigos de salida, timeout, directorio de trabajo del hook | No documentados | **vacío** |

## 4. Gap analysis

| Área | Hoy | Falta |
|---|---|---|
| Registro | ausente | entrada `antigravity` |
| Detección | ausente | señales específicas que no colisionen con OpenHands |
| Instalación / ledger | rechazada | resuelto por el registro, sin código nuevo |
| Participación / Primary | imposible | resuelto por el registro, sin código nuevo |
| Instrucciones | `AGENTS.md` por lectura nativa, sin garantía de lectura completa | regla always-on corta en `.agents/rules/` |
| Protección en tiempo real | ninguna | `.agents/hooks.json` + formato en `gtt_protect.py` |
| Sesión | el agente debe ejecutar el servicio por instrucción | instrucción explícita en la regla (N3) |
| Skills | ninguna | nada en v1 (ver §16) |
| Validación | invisible | resuelto por el registro |
| CI | `gtt-check-protection.sh` ya es agnóstico | nada |
| Tests | no cubren | ver §18 |
| Documentación | no lo menciona | ver §19 |

## 5. Arquitectura propuesta

Antigravity entra como un overlay más, con el mismo patrón que Cursor y OpenHands. El contrato
sigue siendo `AGENTS.md`; el overlay no lo duplica.

```text
                    GTT (AGENTS.md + .gtt/ + gtt-domain/)
                                   │
   ┌──────────┬──────────┬─────────┼──────────┬───────────┬──────────────┐
 claude     kiro     copilot    cursor    openhands     codex      antigravity
 .claude/   .kiro/   .copilot/  .cursor/  .agents/skills/gtt/      .agents/rules/gtt*.md
                                 (3 arch.) .openhands/hooks.json   .agents/hooks.json
                                    └──────────┴───────────────────────┘
                                       gtt_protect.py (un motor, un formato por ADE)
```

**ID propio, no alias de Codex.** Comparten una sola cosa: `AGENTS.md` como punto de entrada.
Difieren en todo lo demás:

| | Codex | Antigravity |
|---|---|---|
| Archivos propios | ninguno (`owned: []`) | tres |
| Reglas adicionales | no | `.agents/rules/` |
| Hook pre-herramienta | no en el overlay | sí, documentado |
| Enforcement | `ci-gate` | `realtime-hook-unverified` |
| Límite de tamaño de instrucciones | no evaluado aquí | por archivo y agregado (§3) |

## 6. Adapter propuesto

No hace falta un directorio `.gtt/.../antigravity/`: el patrón del repo no lo usa y crearlo sería
una estructura nueva sin consumidor. El adapter son tres archivos en el catálogo:

| Archivo | Contenido |
|---|---|
| `.agents/rules/gtt.md` | Regla always-on. Mismo contenido que `.cursor/rules/gtt.mdc` adaptado: leer `AGENTS.md` completo con la herramienta de lectura, rutas gobernadas, nunca ejecutar `apply-*.sh`, marcador `@gtt ·`, y la instrucción de sesión de §14. Bajo 12.000 caracteres (la de Cursor pesa 2.590 bytes). |
| `.agents/rules/gtt-implementation.md` | Espejo de `.cursor/rules/gtt-implementation.mdc`, activada por glob `src/**`, `lib/**`, `tests/**`. |
| `.agents/hooks.json` | Un hook con nombre `gtt-protect`, evento `PreToolUse`. |

`.agents/hooks.json` propuesto:

```json
{
  "gtt-protect": {
    "PreToolUse": [
      {
        "matcher": "run_command|write_to_file|replace_file_content|multi_replace_file_content",
        "hooks": [
          { "type": "command",
            "command": "bash .gtt/scripts/gtt-run-python.sh .gtt/scripts/gtt_protect.py hook --format antigravity",
            "timeout": 20 }
        ]
      }
    ]
  }
}
```

Frontmatter de las reglas, según la documentación oficial: `trigger: always_on` para `gtt.md`;
`trigger: glob` con `globs:` para `gtt-implementation.md`.

La regla es corta por diseño: remite a `AGENTS.md` y no copia ninguna de sus secciones.

## 7. Detection

Propuesta: `detect: [.agents/rules/, .agents/hooks.json, .agents/workflows/, .agent/]`.

| Señal candidata | ¿Se usa? | Por qué |
|---|---|---|
| `.agents/rules/` | sí | específica de Antigravity |
| `.agents/hooks.json` | sí | específica de Antigravity |
| `.agents/workflows/` | sí | específica de Antigravity |
| `.agent/` (singular) | sí | ubicación heredada de Antigravity |
| `.agents/` | **no** | compartida: el overlay de OpenHands la crea. `docs.md:834-836` ya descarta esta señal por la misma razón. |
| `.agents/skills/` | **no** | estándar Agent Skills, la usan OpenHands y otros |
| `AGENTS.md` | **no** | es el núcleo portable de GTT; estaría siempre presente |
| `GEMINI.md` | **no** | en la raíz del proyecto es de Gemini CLI; el de Antigravity es global (`~/.gemini/`) |
| binario `agy` | solo si hay declaración de sesión | `detect_rows` toma el binario de `.gtt/session-adapters/<id>.json`; Cursor y OpenHands tampoco lo tienen |

Los tres estados que pide el encargo ya están separados en el motor y no requieren cambio:

| Estado | Dónde vive |
|---|---|
| ADE detectado | `gtt-ade.sh detect` — observación, nunca se guarda |
| Integración GTT instalada | `.gtt/ade.json` → `installed` (ledger con hashes) |
| ADE participante | `.gtt/ade.json` → `participating` |

Lo que GTT no sabe, y no debe fingir saber, es qué ADE está activo en este momento:
`AGENTS.md` lo prohíbe expresamente ("records no last active ADE").

## 8. Installation

Sin código nuevo. Con la entrada en el registro y los tres archivos en el catálogo:

```bash
bash .gtt/scripts/gtt-ade.sh install --from <catálogo> --participating antigravity --primary antigravity          # dry run
bash .gtt/scripts/gtt-ade.sh install --from <catálogo> --participating antigravity --primary antigravity --apply
```

| Operación | Comportamiento (ya implementado) |
|---|---|
| Instalar | copia los 3 archivos, registra hashes |
| Actualizar | `update`: UPDATE si no se modificó localmente, CONFLICT si se modificó y el catálogo cambió |
| Desinstalar | `remove antigravity`: borra solo archivos del ledger sin modificar; el resto de `.agents/` queda |
| Archivo preexistente | CONFLICT, no se escribe nada |

**Limitación heredada que aquí pesa más.** Un conflicto en un archivo aborta la instalación de
todo el ADE. Si el host ya tiene su propio `.agents/hooks.json`, Antigravity no se puede
instalar, ni siquiera las reglas. Con Cursor pasa lo mismo hoy con `.cursor/hooks.json`. El
formato de Antigravity (hooks con nombre en un mismo archivo) invita a fusionar, pero el modelo
actual de GTT no fusiona nunca y esta propuesta no lo cambia.

Lo que sí se hace en v1 es documentarlo: la sección de Antigravity en `.gtt/docs/docs.md`, los
dos READMEs y `AGENTS.md` dirán que un `.agents/hooks.json` preexistente es un conflicto que se
reporta, y que la salida es que el humano añada a mano la entrada `gtt-protect` a su archivo o
renuncie al hook. La fusión automática queda fuera de v1.

## 9. Manifest

Línea propuesta, con las claves exactas del modelo actual:

```yaml
  - { id: antigravity, name: Google Antigravity, path: .agents/rules/gtt.md, entry: AGENTS.md, owned: [.agents/rules/gtt.md, .agents/rules/gtt-implementation.md, .agents/hooks.json], detect: [.agents/rules/, .agents/hooks.json, .agents/workflows/, .agent/], enforcement: realtime-hook-unverified, scaffold: 2, version: 1, kind: file, required: false, role: Antigravity overlay - AGENTS.md is its entry point; two workspace rules add the Antigravity-specific notes and a hooks file adds the write block (.gtt/scripts/gtt_protect.py); the hook is documented for the CLI, the IDE and the desktop app but reported to run only in the CLI; GTT owns only these three files, never the rest of the host's .agents/ }
```

`entry: AGENTS.md` sigue el precedente de OpenHands (`manifest.yaml:124`). `path` es el ancla
que `validate` exige que exista.

## 10. AGENTS.md

Sigue siendo el contrato portable principal. `.agents/rules/gtt.md` no lo copia: remite a él y
añade solo lo específico de Antigravity, igual que la regla de Cursor.

La regla es necesaria por una razón concreta, no por simetría: `AGENTS.md` mide 59.249 bytes.
La documentación oficial de Antigravity da un límite de 24 KB por archivo, dice que `AGENTS.md`
está sujeto a él, y añade un presupuesto de 20.000 tokens para todo el contenido `always_on`.
`AGENTS.md` supera el primero con holgura y por sí solo consume la mayor parte del segundo. Qué
hace Antigravity al excederlos (truncar, omitir, avisar) no está documentado ni verificado. La
regla corta garantiza que el mínimo vinculante llegue siempre y ordena leer el archivo entero
con la herramienta de lectura.

El tamaño de `AGENTS.md` frente a los límites de los ADEs es un hallazgo transversal: no es de
Antigravity y no se resuelve aquí.

**Las cinco modificaciones de `AGENTS.md`** están en `AGENTS-antigravity.patch` (21 inserciones,
12 eliminaciones). No se aplicaron.

| # | Sección | Cambio |
|---|---|---|
| 1 | *Required workspace* (diagrama, dos apariciones, y fila *ADE Overlay* de la tabla) | añade `.agents/rules/`; la fila pasa a nombrar también los archivos propios bajo `.cursor/`, `.agents/` y `.openhands/`, que hoy omite |
| 2 | *Adapters vs. portable core* | añade Antigravity y sus tres archivos; dice que `.agents/` es compartido |
| 3 | *Multi-ADE participation* | el párrafo de hooks incluye Antigravity, aclara que no tiene evento de inicio de sesión, que ninguna de sus tres superficies está probada, y que un `hooks.json` del host es conflicto y no fusión |
| 4 | *Conflict policy* | añade los tres archivos a la lista |
| 5 | *Bootstrap documentation vs. installed project layout* | añade los archivos a la lista de overlays y a la frase final |

Se aplica con `bash gtt-domain/proposals/apply-AGENTS-antigravity.sh`, que el Solution Designer
ejecuta después de STORY-001: el script se niega a correr si el registro aún no tiene el
overlay, para que el contrato no describa algo que no existe.

## 11. `.agents/` — ownership

GTT posee archivos, no el directorio. Ya es así: `owned` lista archivos concretos, el ledger
atribuye cada uno a un ADE y `export-policy.json:17` ya incluye `.agents/` en `never_by_name`.

| Archivo en `.agents/` | Dueño |
|---|---|
| `skills/gtt/SKILL.md` | GTT, overlay `openhands` |
| `rules/gtt.md`, `rules/gtt-implementation.md`, `hooks.json` | GTT, overlay `antigravity` (propuesto) |
| cualquier otro | el host |

Coexistencia OpenHands + Antigravity:

- No hay colisión de archivos: los conjuntos `owned` son disjuntos, así que ambos se instalan
  sin CONFLICT.
- **Lectura cruzada.** Antigravity carga skills desde `.agents/skills/`, de modo que con ambos
  participando leerá el SKILL.md de OpenHands, que habla de `.openhands/hooks.json`. No rompe
  nada (el contenido remite a `AGENTS.md`), pero el título dice "OpenHands integration".
  Compartir un único SKILL.md neutral no es posible hoy: el ledger no admite un archivo con dos
  dueños y el segundo `install` daría CONFLICT.
- `remove openhands` no toca los archivos de Antigravity y viceversa. `Txn.delete` borra
  directorios padre solo si quedan vacíos (`gtt_ade.py:183-190`).

## 12. Hooks

| Operación | Herramienta de Antigravity | Argumento relevante | Interceptable |
|---|---|---|---|
| Crear / sobrescribir archivo | `write_to_file` | `TargetFile` | sí, documentado |
| Editar un fragmento | `replace_file_content` | `TargetFile`, `TargetContent` | sí, documentado |
| Editar varios fragmentos | `multi_replace_file_content` | `TargetFile`, `ReplacementChunks` | sí, documentado |
| Ejecutar comando | `run_command` | `CommandLine`, `Cwd` | sí, documentado |

Clasificación por superficie, según la evidencia disponible hoy:

| Superficie | Clasificación | Base |
|---|---|---|
| CLI `agy` | **unverified** | documentado, y un tercero reporta que se dispara en cada llamada; GTT no lo ha ejecutado |
| IDE | **unverified**, con evidencia en contra | documentado; un tercero midió cero invocaciones |
| Escritorio 2.0 | **unverified**, con evidencia en contra | ídem |

Ninguna superficie puede declararse `verified` sin una ejecución real por parte de GTT, igual
que se hizo con Claude (`.gtt/session-adapters/claude.json:24`). La CLI es el camino barato
para conseguir la primera verificación.

**Verificación práctica: requisito de implementación.** La documentación y los reportes de la
comunidad no son evidencia de soporte verificado. Cada punto se observa en una ejecución real y
se anota en `.gtt/docs/evidence.md` con versión, fecha y quién lo ejecutó.

| # | Qué se observa | Por qué importa | Story |
|---|---|---|---|
| 1 | Directorio en que se ejecuta el hook | el comando usa rutas relativas a la raíz del proyecto | STORY-002 |
| 2 | Comportamiento al denegar con código 2 y con código 0 | el motor sale con 2; no se sabe si Antigravity lee el JSON de un hook que no sale con 0 | STORY-002 |
| 3 | Payload real que recibe el hook, por herramienta | el formato se escribe contra el payload documentado | STORY-002 |
| 4 | Comportamiento en la CLI | única superficie con indicios de que el hook corre | STORY-002 |
| 5 | Comportamiento en el IDE | hay un reporte de cero invocaciones | STORY-003 |
| 6 | Comportamiento en el escritorio, si aplica | ídem | STORY-003 |

En esta máquina no hay binario `agy` ni `antigravity` en el PATH: estas observaciones necesitan
un equipo con Antigravity instalado y un humano que las ejecute o supervise.

Punto abierto adicional: el matcher es una lista cerrada de cuatro herramientas. Si Antigravity
tiene otras que escriben (borrado, notebooks, MCP), no pasan por el hook. STORY-002 registra las
que aparezcan.

## 13. Protection — cambios exactos en `gtt_protect.py`

| Punto | Cambio |
|---|---|
| Nuevo formato | función `antigravity(event)` y `FORMATS["antigravity"]`. `argparse` toma las opciones de `FORMATS`, así que el CLI no cambia. |
| Raíz del proyecto | `event["workspacePaths"][0]`, con `os.getcwd()` como reserva. |
| Tipo de evento | El payload no trae nombre de evento. Se distingue por forma: `toolCall` presente = pre-herramienta. Cualquier otra forma: salir 0 sin respuesta. |
| Archivo | `toolCall.args.TargetFile` → `decide_file`. `TargetFile` no está en `PATH_KEYS` (`gtt_protect.py:176`); se lee directamente en la función. |
| Extensión de la edición (GTTGuard) | `replace_file_content`: `TargetContent` como `old_string`. `multi_replace_file_content`: evaluar cada fragmento de `ReplacementChunks`; si su forma no es la esperada, pasar `None`, que ya falla seguro a archivo completo (`gtt_protect.py:124-126`). `write_to_file`: `None`. |
| Comando | `toolCall.args.CommandLine` → `decide_shell`. |
| Respuesta | `{"decision": "deny", "reason": <motivo>}`: la misma forma que OpenHands. Sale con 2, como los otros dos formatos; STORY-002 lo corrige si Antigravity no lo respeta (§12, punto 2). |
| Maquinaria | añadir `\.agents/hooks\.json` a `MACHINERY` (`gtt_protect.py:42`) para que el agente no pueda desarmar su propio bloqueo. |
| Errores | sin cambio: payload ilegible o excepción → salida 0 (`gtt_protect.py:236-240`). |
| Docstring | actualizar líneas 16 y 21-22. |

Compatibilidad hacia atrás: todo es aditivo. `cursor()` y `openhands()` no se tocan; la única
línea compartida que cambia es la expresión regular `MACHINERY`, que solo gana una alternativa.

Limitación conocida que se hereda: `decide_shell` resuelve rutas relativas contra la raíz, no
contra `Cwd`. Un `run_command` con `Cwd` dentro de `gtt-domain/context/` y una ruta relativa
corta no se detectaría. Afecta igual a Cursor y OpenHands; no se propone arreglarlo aquí.

Sin inyección de contexto de sesión en este formato: ver §14.

## 14. Session

**Lo que ya existe.** GTT ya tiene estado de sesión portable e independiente del ADE:

- `gtt-status.sh` genera `gtt-domain/session.md` solo desde artefactos del repo: estado de
  freeze, Stories en curso y bloqueadas, propuestas pendientes, ADRs, GTTGuard, estado de ADEs,
  gaps, plan, rama, rutas sin commitear y últimos commits.
- No lee memoria de ningún ADE ni la reemplaza. No registra "último ADE activo".
- El archivo está versionado en git, así que viaja entre máquinas.
- `gtt-session-context.sh` lo regenera y lo imprime con los marcadores de no-autoridad.

El diagrama del encargo (sesión nativa del ADE más estado de sesión de GTT, en paralelo) describe
lo que el repo ya hace.

**Cómo llega al agente** — niveles del contrato (`.gtt/docs/session-adapter-contract.md:67-73`):

| ADE | Entrega hoy |
|---|---|
| Claude | N1, verificado en ejecución |
| Codex, Copilot, Kiro | N1 declarado pero *staged* en `gtt-domain/proposals/session-adapters/`, sin promover; Codex probado y **no** funcionó |
| Cursor, OpenHands | inyección por `sessionStart` vía `gtt_protect.py`, sin declaración en `.gtt/session-adapters/` |
| Antigravity (propuesto) | **N3**: la regla always-on ordena ejecutar `bash .gtt/scripts/gtt-session-context.sh` al empezar |

Antigravity no tiene evento de inicio de sesión. `PreInvocation` puede inyectar un mensaje, pero
se dispara antes de cada llamada al modelo; ejecutar ahí el servicio regeneraría `session.md` en
cada paso. Hacerlo solo en la primera invocación depende de la semántica de `invocationNum`, que
no está documentada. Por eso v1 es N3 y la inyección por `PreInvocation` queda en *Future*.

No se propone crear `.gtt/session-adapters/antigravity.json` en v1. El esquema exige `files`,
`registration` y `command` de un hook (`gtt_session_adapter.py:118-121`), que un adapter N3 no
tiene, y el contrato entero está marcado "Draft — not a decision"
(`session-adapter-contract.md:5`). Cursor y OpenHands tampoco la tienen.

## 15. Memory / handoff — cambio transversal, separado

El escenario "día 1 Claude → día 2 Antigravity" ya funciona para todo lo derivable. Lo que falta
no es de Antigravity:

| Hueco | Naturaleza |
|---|---|
| **Dos mecanismos de sesión en paralelo.** El contrato dice que todo adapter usa el servicio, falla de forma visible y nunca sale con 2. `gtt_protect.py:170-173` entrega contexto a Cursor y OpenHands tragándose el fallo, sin declaración y sin pasar por `gtt-check-session-adapter.sh`. | inconsistencia existente |
| **Tres adapters sin promover** (Codex, Copilot, Kiro) desde `apply-session-adapters.sh`. | decisión pendiente del Solution Designer |
| **Sin checkpoint al terminar.** `session.md` se regenera al empezar una sesión; si el ADE no tiene hook de inicio, depende de que el agente obedezca. Ningún ADE usa un evento `Stop`. | capacidad ausente |
| **Intención no derivable.** "Estaba a mitad de X, lo siguiente es Y" no está en git ni en el backlog si no se actualizó *Current Focus*. `session.md` es, por diseño, estado derivado y nunca notas del agente. | decisión de diseño: ¿se admite un artefacto de handoff escrito por el agente, y con qué rango? |

Queda como propuesta propia: `PROPOSAL-session-memory-consolidation.md`. Un comando tipo
`gtt session checkpoint` sería un envoltorio fino sobre `gtt-status.sh`; la pregunta real es la
cuarta fila, que toca un principio del método y no debe resolverse de paso.

Esta propuesta no depende de aquella y no toca nada de sesión: Antigravity queda en N3 con lo
que hay, y `gtt-domain/session.md` sigue siendo derivado, independiente del ADE y sin autoridad.

## 16. Capabilities, skills y workflows

**Modelo de capacidades.** El registro ya no es "ADE = nombre". Cada ADE declara punto de
entrada, archivos propios, señales de detección y nivel de enforcement en el manifest, y
cobertura de sesión, eventos y verificación en su declaración de sesión. Reestructurarlo ahora
en un árbol de capacidades sería sobreingeniería: Antigravity cabe en el modelo actual sin una
sola clave nueva.

**No hay gap que proponer por separado.** `realtime-hook-unverified` ya es uno de los tres
valores de `enforcement` (`manifest.yaml:115-118`), lo usan Cursor y OpenHands, y
`gtt_ade.py:275` lo imprime en cada validación. El modelo actual lo expresa sin cambios.

El único matiz es que `enforcement` tiene un solo valor por ADE y en Antigravity el
comportamiento puede variar por superficie. Se resuelve dentro del modelo: el valor que es
cierto para todas (`realtime-hook-unverified`) y el detalle por superficie en `role` y en la
documentación. Una clave `surfaces:` solo se justificaría si el detalle por superficie tuviera
que ser legible por máquina; hoy nada lo consume.

**Skills y workflows.** Nada específico en v1. El contrato común ya existe: los procedimientos
están en `AGENTS.md` y cinco de los seis ADEs los siguen desde ahí. Antigravity tiene skills y
workflows nativos, pero portar las siete skills de Claude sería duplicar el método en otro
formato y mantenerlo dos veces. La regla always-on incluye la misma tabla "situación → sección
de `AGENTS.md`" que el SKILL.md de OpenHands.

## 17. Primary / participating

`gtt-ade.sh install --participating antigravity --primary antigravity` y
`gtt-ade.sh set-primary antigravity` funcionan en cuanto el id está en el registro. Ningún
punto del motor condiciona Primary al enforcement, y no debe: Primary es un identificador de
flujo de trabajo sin autoridad.

La limitación queda visible sin esfuerzo adicional: `validate` y `gtt-domain/session.md`
imprimen `integration valid (enforcement: realtime-hook-unverified)` para cada participante.

## 18. Tests

Todos en `.gtt/tests/bootstrap-acceptance.py`, sobre copias desechables.

**Regresión — aserciones existentes que enumeran los ADEs y hay que actualizar:**

| Línea | Aserción |
|---|---|
| 246 | lista ordenada de ids del registro |
| 258 | `excluded` tras instalar claude + codex |
| 300 | `excluded` tras instalar cursor + openhands |
| 611 | bucle `any_ade_alone` |

El resto de `ade`, `cursor_and_openhands`, `protection_hooks` y `export_and_clean` debe pasar
sin modificación: es la prueba de que los seis ADEs actuales no cambian.

**Nuevos — positivos:**

| Área | Test |
|---|---|
| Registro | `antigravity` aparece con `owned_paths` exactos y `instruction_entry` = `AGENTS.md` |
| Detección | un host con `.agents/rules/x.md` lo da como candidato, nunca participante |
| Instalación | dry-run no escribe; `--apply` copia tres archivos y los registra |
| Primary | Antigravity solo, como Primary, valida |
| Participación | `antigravity,openhands` juntos instalan sin CONFLICT y validan |
| Solo | entra en `any_ade_alone`: install → reconcile → index → validation.run |
| Hooks | `write_to_file` a `AGENTS.md` denegado con `decision: deny`; a `src/app.py` permitido; a `gtt-domain/proposals/` permitido |
| Hooks | `run_command` con `bash gtt-domain/proposals/apply-x.sh` denegado; `cat AGENTS.md` permitido; `rm .agents/hooks.json` denegado |
| Hooks | régimen de freeze: escritura en `gtt-domain/context/` permitida antes de `.frozen`, denegada después |
| Hooks | `replace_file_content` dentro del tramo de un símbolo `@GTTGuard` denegado, fuera permitido |
| Propiedad | `export-policy` excluye los tres archivos y no `.agents/` |
| Sesión | la regla instalada nombra `gtt-session-context.sh` |
| Tamaño | `.agents/rules/gtt.md` pesa menos de 12.000 caracteres |

**Nuevos — negativos:**

| Caso | Resultado esperado |
|---|---|
| id desconocido (`--participating antigravty`) | salida 2, nada escrito |
| host con `.agents/hooks.json` propio | CONFLICT, nada escrito, archivo intacto |
| host con `.agents/rules/gtt.md` propio | CONFLICT, nada escrito |
| host con `.agents/rules/team.md` y `.agents/skills/otro/` propios | instala; ambos intactos; `remove` no los toca |
| solo OpenHands instalado | Antigravity **no** aparece como candidato (`.agents/skills/` no es señal) |
| `remove antigravity` con OpenHands participando | `.agents/skills/gtt/SKILL.md` sigue |
| evento sin `toolCall` (p. ej. forma de `PreInvocation`) | salida 0, sin respuesta |
| evento malformado: no JSON, `toolCall` sin `args`, `ReplacementChunks` no lista | salida 0, sin excepción |
| `multi_replace_file_content` de forma desconocida sobre archivo con símbolo protegido | denegado (falla seguro a archivo completo) |
| herramienta desconocida (`read_file`) | salida 0 |

**Fuera de los tests automáticos:** la verificación en `agy` de §12. Su resultado se anota en la
documentación, no en un test.

## 19. Documentación

Ubicaciones canónicas existentes; no se crea ningún documento nuevo.

| Archivo | Qué cambia |
|---|---|
| `AGENTS.md` | cinco menciones (§10) — del Solution Designer |
| `readme-gtt.md` / `readme-gtt.es.md` | línea 73, tabla de soporte (≈180), tabla de archivos por ADE (≈191), párrafo de enforcement (≈198, ≈228), ancla del enlace (832) |
| `.gtt/docs/docs.md` | título y ancla de *Portability* (14, 643), tabla de capacidades (≈676), nueva subsección `### Antigravity` junto a `### OpenHands` (822) con las superficies y los tres puntos sin verificar |
| `.gtt/docs/index.md` | línea 49 y filas de archivos (146-149) |
| `.gtt/docs/installation.md` / `.es.md` | línea 26 |
| `.gtt/docs/evidence.md` | la afirmación sobre el hook, clasificada por nivel de verificación |
| `.gtt/scaffold/manifest.yaml` | comentario de `enforcement` si se menciona la variación por superficie |

Ayuda del CLI: `gtt-ade.sh list` se genera del registro; no requiere cambio. Cambiar el título
de *Portability* rompe el ancla que usan `readme-gtt.md:832` y `docs.md:14`: actualizar los tres
a la vez o `gtt-check-integrity.sh` fallará.

Los archivos Markdown del overlay pueden necesitar identidad en `.gtt/index/artifacts.json`
(hoy solo `.copilot/copilot-instructions.md` la tiene entre los overlays no-Claude);
`gtt-maintain.sh` lo dirá tras añadirlos.

## 20. Riesgos

| Riesgo | Qué rompe si ocurre | Cómo se detecta | Mitigación |
|---|---|---|---|
| El hook no se dispara en IDE / escritorio | escrituras en rutas gobernadas pasan sin bloqueo | prueba manual; CI lo atrapa después | valor `realtime-hook-unverified`, regla vinculante por sí misma, CI |
| `AGENTS.md` no se carga entero (supera los 24 KB documentados) | el agente ignora parte del contrato | pedirle que cite la última regla no negociable (STORY-002, STORY-003) | regla corta always-on con el mínimo vinculante |
| Salida 2 al denegar se interpreta como error del hook | la denegación se pierde o bloquea toda herramienta | STORY-002 | corregir el formato en STORY-002; no anunciar el soporte antes |
| Nadie dispone de Antigravity para verificar | STORY-002 y STORY-003 no se cierran y el Epic queda abierto | el backlog lo muestra | el overlay sigue rotulado `unverified`; no se afirma nada más |
| `~/.gemini/GEMINI.md` del usuario contradice GTT | instrucción global gana | no detectable por GTT | documentarlo; CI |
| Host con `.agents/hooks.json` propio | Antigravity no se puede instalar | CONFLICT explícito | documentar; *Future* |
| Lectura cruzada del SKILL.md de OpenHands | confusión menor de nombres | inspección | documentar |
| Antigravity renombra herramientas o rutas | el matcher deja de coincidir, sin error | ninguna automática | `version` del overlay; nota en `evidence.md` |
| Regresión en los seis ADEs | instalaciones existentes fallan | suite de aceptación | cambios solo aditivos |

## 21. Must / Should / Future

**A. Must have** — mínimo para "soportado oficialmente":

1. Entrada `antigravity` en `overlays:`.
2. `.agents/rules/gtt.md` en el catálogo, con la instrucción de sesión N3.
3. `.agents/hooks.json` y formato `antigravity` en `gtt_protect.py`, con `.agents/hooks.json` en `MACHINERY`.
4. Tests de §18 y actualización de las cuatro aserciones.
5. Documentación de §19, con las superficies y lo no verificado dicho tal cual.
6. Verificación práctica de los seis puntos de §12, por superficie (STORY-002 y STORY-003).
7. Las cinco modificaciones de `AGENTS.md`, aplicadas por el Solution Designer.

**B. Should have:**

1. `.agents/rules/gtt-implementation.md`.
2. Comprobación empírica de si `AGENTS.md` se carga entero, por superficie.
3. Tabla "situación → sección de `AGENTS.md`" dentro de la regla.

**C. Future** — depende de evidencia o de la evolución de Antigravity:

1. Subir a `realtime-hook` cuando el hook esté verificado en las tres superficies.
2. Inyección de sesión por `PreInvocation` cuando se conozca la semántica de `invocationNum`.
3. Clave `surfaces:` en el registro si otro ADE lo necesita.
4. Instalación parcial o fusión cuando el host ya tiene `hooks.json`.
5. Skills nativas de Antigravity, si se decide mantener el método en más de un formato.
6. SKILL.md neutral compartido entre ADEs que leen `.agents/skills/` (requiere propiedad compartida en el ledger).

## 22. Archivos que cambiarían

| Archivo | Cambio | Quién lo aplica |
|---|---|---|
| `.gtt/scaffold/manifest.yaml` | +1 línea | agente, tras aprobación |
| `.gtt/scripts/gtt_protect.py` | +~45 líneas, 1 regex | agente, tras aprobación |
| `.agents/rules/gtt.md` | nuevo | agente |
| `.agents/rules/gtt-implementation.md` | nuevo | agente |
| `.agents/hooks.json` | nuevo | agente |
| `.gtt/tests/bootstrap-acceptance.py` | 4 aserciones + función nueva | agente |
| `readme-gtt.md`, `readme-gtt.es.md` | secciones de ADEs | agente |
| `.gtt/docs/docs.md`, `index.md`, `installation.md`, `installation.es.md`, `evidence.md` | §19 | agente |
| `AGENTS.md` | cinco menciones | **Solution Designer** (borrador preparado bajo `gtt-domain/proposals/`) |
| `.gtt/index/*` | regenerados por `gtt-maintain.sh` | derivado |

No cambian: `gtt_ade.py`, `gtt_manifest.py`, `gtt-check-adapter.sh`, `gtt-validate.sh`,
`gtt-status.sh`, `.gtt/contract/*.json`, `.gtt/session-adapters/`, ningún overlay existente.

Complejidad: baja en código (el motor ya es genérico), media en documentación (ocho archivos,
dos idiomas). El trabajo con incertidumbre real es la verificación en `agy`.

## 23. Propuesta de change request

Texto para `gtt-domain/change-request.md`, que solo el Solution Designer escribe:

```text
Añadir Google Antigravity como ADE soportado con id propio `antigravity`.
Overlay de tres archivos bajo .agents/ (rules/gtt.md, rules/gtt-implementation.md, hooks.json),
entry AGENTS.md, enforcement realtime-hook-unverified. Formato `antigravity` en gtt_protect.py.
Sesión por instrucción (N3). Sin skills nativas, sin cambio del modelo del registro.
La consolidación de Session Memory y el checkpoint de sesión van en un cambio aparte.
Detalle: gtt-domain/proposals/PROPOSAL-antigravity-ade-support.md
```

La línea de desarrollo está en `PROPOSAL-backlog-antigravity-epic.md`: EPIC-001 y tres Stories
con su definición completa y criterios de aceptación. Cada Story se aprueba por separado.

---

## Alternativas

| Alternativa | Por qué pierde |
|---|---|
| Declarar Antigravity como `codex` | El registro mentiría sobre el ADE real y no habría overlay, hook ni detección. |
| Solo registro, con `owned: []` como Codex | Funciona y es trivial, pero renuncia a un hook que el ADE documenta y deja el riesgo de truncado de `AGENTS.md` sin mitigar. |
| Overlay completo con skills y workflows nativos | Duplica el método en un segundo formato; contradice "mismo contrato, distintos adapters". |
| Evolucionar el registro a un modelo de capacidades antes de añadirlo | Antigravity cabe en el modelo actual; sería rediseñar sin un caso que lo exija. |
| Esperar a que Google aclare las superficies de hooks | El contrato portable y el CI no dependen del hook; no hay motivo para dejar al ADE invisible mientras tanto. |

# Recommendation

**¿Debe GTT soportar Antigravity?** Sí. El coste es bajo porque el motor de ADEs ya es
genérico, y la situación actual es la peor de las posibles: Antigravity ya opera sobre
proyectos GTT leyendo `AGENTS.md`, pero sin registro, sin validación y sin que nadie pueda
declararlo participante.

**Nivel recomendado para la primera versión:** ADE propio, gobernado por instrucciones y CI, con
bloqueo en tiempo real entregado pero no acreditado. El mismo nivel que Cursor y OpenHands hoy.

**Qué significa "Supported" aquí:** que GTT soporta la integración — la instala, la registra, la
valida y la mantiene. No significa que Antigravity garantice el enforcement en tiempo real. Lo
único que bloquea con garantía una escritura no gobernada desde Antigravity es el gate de CI.

| Nivel | Qué | Por qué |
|---|---|---|
| **Supported** | registro con id propio; detección como candidato; instalación, actualización y remoción con ledger; participating; Primary; contrato mediante `AGENTS.md` más regla específica; validación; CI | Todo se apoya en mecanismos de GTT que no dependen de Antigravity y quedan cubiertos por tests deterministas. |
| **Partially supported** | sesión (el agente ejecuta el servicio porque la regla lo dice) y procedimientos (por secciones de `AGENTS.md`) | Funcionan solo si el modelo obedece la instrucción. |
| **Unverified** | hooks en tiempo real, en cualquier superficie; carga completa de `AGENTS.md`; comportamiento del código de salida del hook | Hay documentación del proveedor y ninguna ejecución de GTT; para IDE y escritorio existe además un reporte en contra. |
| **Unsupported** | inyección automática de contexto al inicio; fusión de `hooks.json`; skills nativas | El ADE no tiene el evento, o el modelo actual de GTT no lo hace y no se cambia en v1. |

El cambio de Session Memory (§15) es transversal y va por separado.

# Listo para implementación

**Sí para STORY-001, con tres condiciones. No todavía para cerrar el Epic ni para anunciar el soporte.**

El diseño está completo para STORY-001: no queda ninguna decisión abierta que impida escribir
el código, y todo lo que no se sabe de Antigravity está rotulado como no verificado en lugar de
resuelto por suposición.

Condiciones antes de empezar:

1. El Solution Designer aprueba STORY-001 (y, por separado, STORY-002 y STORY-003).
2. Las Stories aprobadas se escriben en `gtt-domain/backlog.md` como `Ready`.
3. Se acepta de forma expresa la propuesta de salir con código 2 al denegar, sabiendo que
   STORY-002 puede cambiarlo.

Lo que impide cerrar:

| Qué | Por qué |
|---|---|
| STORY-002 y STORY-003 | necesitan Antigravity instalado; en esta máquina no está. Sin ellas no hay ninguna observación real. |
| `apply-AGENTS-antigravity.sh` | lo ejecuta el Solution Designer, después de STORY-001. |

Si no hay acceso a Antigravity a corto plazo, STORY-001 se puede implementar igualmente: el
resultado es un overlay correcto según el contrato documentado y honestamente rotulado
`realtime-hook-unverified`. Lo que no se debe hacer es publicarlo como soporte de Antigravity
sin la verificación en la CLI.
