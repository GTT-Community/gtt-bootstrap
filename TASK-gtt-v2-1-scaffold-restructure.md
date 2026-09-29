# Tarea --- Reestructuración profesional del Scaffold GTT v2.1

> Canon GTT:
> https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

## Objetivo

Reestructurar `gtt-bootstrap` a partir de la versión más reciente del
producto, separando claramente:

1.  GTT Engine.
2.  Project Governance.
3.  GTT Documentation.
4.  ADE Overlay.

La migración debe mejorar la claridad del producto, su mantenibilidad y
la futura implementación de `gtt init`, **sin perder ninguna conexión,
referencia, índice, validación, protección, integración o funcionalidad
existente**.

No inventar arquitectura ni funcionalidades. La estructura objetivo debe
derivarse del repositorio real y de la arquitectura GTT ya existente.

------------------------------------------------------------------------

# 1. Baseline obligatorio

Trabajar exclusivamente sobre la versión más reciente disponible de
`gtt-bootstrap`.

Antes de modificar cualquier archivo:

-   inspeccionar la estructura real;
-   identificar el estado actual de Git;
-   identificar el estado de freeze;
-   identificar los índices actuales;
-   identificar las referencias actuales;
-   identificar todos los componentes existentes;
-   preservar el comportamiento funcional actual.

No asumir que una ruta, archivo o componente existe solamente porque
aparece en documentación.

La realidad del repositorio es la fuente para la migración.

------------------------------------------------------------------------

# 2. Estructura objetivo

La estructura final debe quedar conceptualmente así:

``` text
gtt-bootstrap/
│
├── gtt/                              ← GTT ENGINE
│   ├── scripts/
│   ├── index/
│   ├── protection/
│   ├── session-adapters/
│   └── scaffold/
│       └── manifest.yaml
│
├── context/                          ← PROJECT GOVERNANCE
├── adr/
├── proposals/
├── backlog.md
├── change-request.md
├── session.md                        ← DERIVED OPERATIONAL STATE
├── .frozen
│
├── docs/                             ← GTT DOCUMENTATION
│   ├── index.md
│   ├── installation.md
│   ├── installation.es.md
│   ├── usage.md
│   ├── usage.es.md
│   ├── gtt-completion.md
│   ├── evidence.md
│   └── ...
│
├── agents.md
├── readme-gtt.md
├── readme-gtt.es.md
│
├── .claude/                          ← ADE OVERLAY
├── .kiro/
└── .copilot/
```

## Regla de nombres

La estructura objetivo utiliza nombres de archivos y directorios en
**lowercase**.

Ejemplos:

-   `change-request.md`
-   `session.md`
-   `index.md`
-   `installation.md`
-   `installation.es.md`
-   `usage.md`
-   `gtt-completion.md`
-   `evidence.md`
-   `agents.md`
-   `readme-gtt.md`

No realizar un renombrado masivo de archivos únicamente por estética
fuera del alcance de esta migración.

La regla aplica a los elementos que formen parte de la nueva estructura
objetivo.

------------------------------------------------------------------------

# 3. Frontera arquitectónica

## 3.1 GTT Engine

Debe permanecer dentro de:

``` text
gtt/
├── scripts/
├── index/
├── protection/
├── session-adapters/
└── scaffold/
```

El Engine contiene la implementación de los servicios de GTT.

No mover estos componentes fuera de `gtt/`.

------------------------------------------------------------------------

## 3.2 Project Governance

Debe quedar directamente en el proyecto:

``` text
context/
adr/
proposals/
backlog.md
change-request.md
session.md
.frozen
```

Estos elementos representan el estado y los artefactos gobernados del
proyecto.

No tratarlos como simple documentación.

------------------------------------------------------------------------

## 3.3 GTT Documentation

La documentación propia de GTT debe quedar en:

``` text
docs/
```

Los README y `agents.md` permanecen en el nivel raíz cuando corresponda
a la experiencia de entrada al producto.

No mezclar documentación de producto con artefactos de governance.

------------------------------------------------------------------------

## 3.4 ADE Overlay

Los ADE específicos permanecen fuera del Engine:

``` text
.claude/
.kiro/
.copilot/
```

Si existe otro ADE soportado actualmente, conservarlo según la realidad
del repositorio.

El ADE no define el Scaffold.

------------------------------------------------------------------------

# 4. Regla fundamental del Scaffold

El Scaffold es **canónico de GTT**.

Debe existir una única definición estructural de Scaffold.

Los ADE únicamente aportan su integración específica mediante un
overlay.

Modelo:

``` text
GTT CANONICAL SCAFFOLD
        │
        ├── ENGINE
        ├── PROJECT GOVERNANCE
        ├── DOCUMENTATION
        │
        └── ADE OVERLAY
              ├── Claude
              ├── Kiro
              ├── Copilot
              └── otros ADE soportados
```

No crear un Scaffold independiente por ADE.

No duplicar la lógica de GTT dentro de los adapters.

Mantener el principio:

> GTT Core provides the service. ADE adapters provide the integration.

------------------------------------------------------------------------

# 5. Scaffold Manifest

Crear:

``` text
gtt/scaffold/manifest.yaml
```

Este archivo será la definición declarativa del Scaffold.

Debe permitir expresar, como mínimo:

-   versión del Scaffold;
-   componentes del Engine;
-   componentes de Project Governance;
-   componentes de Documentation;
-   overlays ADE;
-   elementos requeridos;
-   elementos opcionales cuando corresponda.

El manifest debe ser declarativo.

No debe contener lógica operacional compleja.

No duplicar en el manifest la lógica que ya pertenece al Engine.

No implementar todavía un nuevo `gtt init` si no existe como parte de
esta tarea.

El objetivo es dejar preparada la fuente canónica que `gtt init` podrá
consumir posteriormente.

------------------------------------------------------------------------

# 6. No crear arquitectura artificial

No crear carpetas únicamente para representar conceptos metodológicos.

No crear:

``` text
gtt/engine/
gtt/governance/
gtt/think/
gtt/grounding/
gtt/workers/
gtt/dossier/
```

si esos módulos no existen actualmente.

Conceptos como Grounding, Reasoning, Workers, THINK, Evidence Boundary,
etc. siguen siendo conceptos operativos/metodológicos cuando no exista
una implementación física correspondiente.

------------------------------------------------------------------------

# 7. FASE 1 --- AUDITORÍA PREVIA

Esta fase es obligatoria y debe ejecutarse antes de cualquier
movimiento.

No modificar archivos durante esta fase.

## 7.1 Inventario

Identificar:

-   todos los directorios;
-   todos los archivos;
-   scripts;
-   hooks;
-   adapters;
-   manifests;
-   índices;
-   documentación;
-   configuración;
-   archivos derivados;
-   archivos de estado;
-   archivos de protección;
-   archivos relacionados con Session Memory;
-   archivos relacionados con Artifact Identity;
-   archivos relacionados con Technical Index.

## 7.2 Dependencias de rutas

Buscar todas las referencias a:

``` text
gtt/context
gtt/adr
gtt/proposals
gtt/backlog.md
gtt/CHANGE-REQUEST.md
gtt/SESSION.md
gtt/docs
gtt/INDEX.md
gtt/INSTALLATION
gtt/USAGE
gtt/GTT-COMPLETION
gtt/EVIDENCE
```

y cualquier otra ruta real que vaya a cambiar.

La búsqueda debe incluir:

-   `.sh`
-   `.py`
-   `.json`
-   `.yaml`
-   `.yml`
-   `.md`
-   `.toml`
-   `.ini`
-   `.conf`
-   configuración de ADE;
-   hooks;
-   scripts;
-   índices;
-   manifests;
-   documentación.

No limitar la búsqueda a Markdown.

## 7.3 Dependencias funcionales

Identificar qué componentes dependen de esas rutas.

Especial atención a:

-   Artifact Identity;
-   Artifact Reconciliation;
-   Technical Index;
-   Session Memory;
-   SessionStart;
-   adapters;
-   protection hooks;
-   freeze;
-   validation;
-   `gtt-status`;
-   `gtt-session-context`;
-   `gtt-validate`;
-   checks de integridad;
-   checks de protección;
-   checks de adapters.

## 7.4 Referencias derivadas e históricas

Distinguir:

1.  referencia funcional activa;
2.  referencia derivada;
3.  referencia histórica legítima;
4.  referencia stale;
5.  referencia rota.

No eliminar referencias históricas legítimas automáticamente.

------------------------------------------------------------------------

# 8. FASE 2 --- MIGRACIÓN

Ejecutar los movimientos de acuerdo con la estructura objetivo.

Como mínimo, evaluar estos movimientos:

``` text
gtt/context/             → context/
gtt/adr/                 → adr/
gtt/proposals/           → proposals/
gtt/backlog.md           → backlog.md
gtt/CHANGE-REQUEST.md    → change-request.md
gtt/SESSION.md           → session.md
```

Mover la documentación GTT correspondiente:

``` text
gtt/docs/                → docs/
```

y cualquier documentación equivalente que actualmente esté mezclada en
`gtt/` y corresponda realmente a Documentation.

Mantener dentro de `gtt/`:

``` text
gtt/scripts/
gtt/index/
gtt/protection/
gtt/session-adapters/
```

y crear:

``` text
gtt/scaffold/
```

No ejecutar movimientos ciegos.

Si el repositorio real difiere de esta estructura, adaptar el movimiento
al estado real y documentar la diferencia.

------------------------------------------------------------------------

# 9. Conservación de conexiones

Esta es una condición crítica.

**No debe perderse ninguna conexión entre archivos o componentes como
consecuencia de la migración.**

Actualizar todas las referencias necesarias en:

-   scripts;
-   hooks;
-   adapters;
-   validators;
-   manifests;
-   configuración;
-   índices;
-   Artifact Identity;
-   Technical Index;
-   Session Memory;
-   protección L0;
-   freeze;
-   documentación;
-   README;
-   instrucciones para agentes;
-   archivos de ADE;
-   cualquier lookup de archivos;
-   cualquier ruta usada por `gtt init` o bootstrap existente.

Si una ruta está embebida en código, configuración o documentación, debe
analizarse y actualizarse cuando corresponda.

No asumir que una referencia es irrelevante porque esté fuera de `gtt/`.

------------------------------------------------------------------------

# 10. Artifact Identity e índices

Después de los movimientos:

1.  actualizar la definición de identidad si corresponde;
2.  reconstruir/reconciliar Artifact Identity;
3.  regenerar Technical Index;
4.  comprobar que todos los artefactos actuales tengan identidad
    coherente;
5.  comprobar que los artefactos retirados sigan correctamente marcados
    si corresponde;
6.  comprobar que no aparezcan duplicados;
7.  comprobar que no existan artefactos faltantes;
8.  comprobar que no existan referencias rotas.

Los índices siguen siendo derivados.

No convertir ningún índice en fuente de verdad.

------------------------------------------------------------------------

# 11. Session Memory

La migración no debe romper:

``` text
session.md
gtt-status.sh
gtt-session-context.sh
SessionStart
```

Verificar que:

-   `session.md` pueda reconstruirse correctamente;
-   las rutas nuevas sean reconocidas;
-   no se convierta en evidencia de governance;
-   no se incorpore accidentalmente al grounding;
-   el servicio continúe siendo ADE-agnostic;
-   los adapters sigan siendo thin.

------------------------------------------------------------------------

# 12. Protection y Freeze

La migración no puede debilitar la protección existente.

Verificar:

-   protección L0;
-   rutas protegidas;
-   normalización de paths;
-   Windows paths;
-   PowerShell;
-   Bash;
-   Write;
-   Edit;
-   NotebookEdit;
-   cualquier mecanismo actualmente soportado.

Comprobar también:

``` text
.frozen
```

y cualquier lógica que dependa de su ubicación.

No eliminar ni relajar controles de protección para facilitar la
migración.

------------------------------------------------------------------------

# 13. ADE Adapters

Mantener el contrato común existente.

Verificar que:

``` text
gtt/session-adapters/
```

continúe siendo ADE-agnostic.

Verificar los overlays:

``` text
.claude/
.kiro/
.copilot/
```

y cualquier otro adapter realmente existente.

No mover lógica de GTT al ADE.

No crear lógica duplicada.

No hacer que el Core detecte directamente detalles específicos de un ADE
si actualmente el contrato de adapters permite evitarlo.

------------------------------------------------------------------------

# 14. Documentación

Actualizar toda la documentación afectada por la nueva estructura.

La documentación debe explicar claramente:

``` text
gtt/                 → GTT Engine
context/             → Project Governance
adr/                 → Project Governance
proposals/           → Project Governance
docs/                → GTT Documentation
.claude/.kiro/...    → ADE Overlay
```

La explicación debe ser consistente en todos los idiomas y documentos
afectados.

No introducir definiciones contradictorias.

------------------------------------------------------------------------

# 15. Lowercase

Verificar que los nombres correspondientes a la nueva estructura sean
lowercase.

Ejemplos:

``` text
change-request.md
session.md
index.md
installation.md
installation.es.md
usage.md
usage.es.md
gtt-completion.md
evidence.md
agents.md
readme-gtt.md
readme-gtt.es.md
```

No crear nuevos nombres con mayúsculas dentro de la estructura objetivo.

------------------------------------------------------------------------

# 16. Limpieza

Durante la migración detectar:

-   `__pycache__`;
-   archivos temporales;
-   probes;
-   staging residual;
-   ZIPs internos;
-   scripts de aplicación de cambios ya ejecutados;
-   archivos de pruebas descartables;
-   artefactos stale.

No eliminar archivos legítimos del producto.

Todo elemento eliminado debe poder clasificarse claramente como:

-   temporal;
-   generado;
-   staging;
-   retired;
-   stale;
-   o no perteneciente al producto.

No eliminar contenido funcional por simplificación.

------------------------------------------------------------------------

# 17. Validación obligatoria

Después de completar la migración ejecutar todas las validaciones
disponibles.

Como mínimo:

``` text
gtt-check-integrity.sh
gtt-check-protection.sh
gtt-check-session-adapter.sh
gtt-validate.sh
```

Además:

-   validación de Artifact Identity;
-   validación de Technical Index;
-   validación de Session Memory;
-   validación del estado de freeze;
-   validación de adapters;
-   cualquier check adicional existente en el repositorio.

Todos los checks que actualmente puedan ejecutarse deben ejecutarse.

No declarar PASS solamente porque el código parezca correcto.

------------------------------------------------------------------------

# 18. Búsqueda final de referencias antiguas

Realizar una búsqueda completa por las rutas anteriores.

Como mínimo:

``` text
gtt/context
gtt/adr
gtt/proposals
gtt/backlog.md
gtt/CHANGE-REQUEST.md
gtt/SESSION.md
gtt/docs
```

También buscar los nombres antiguos de documentación.

Cada resultado debe clasificarse como:

``` text
VALID
HISTORICAL
DERIVED
STALE
ERROR
```

No dejar referencias funcionales antiguas sin resolver.

------------------------------------------------------------------------

# 19. Validación del Scaffold

Comprobar que la estructura final pueda ser interpretada de forma
inequívoca:

``` text
ENGINE
PROJECT GOVERNANCE
DOCUMENTATION
ADE OVERLAY
```

y que:

``` text
gtt/scaffold/manifest.yaml
```

represente la definición canónica del Scaffold.

El manifest no debe convertirse en una segunda fuente contradictoria con
el repositorio.

------------------------------------------------------------------------

# 20. Criterios de aceptación

La tarea solamente se considera terminada si:

-   la nueva estructura está implementada;
-   no se perdió ningún archivo funcional;
-   no se rompieron referencias;
-   no se rompieron scripts;
-   no se rompieron hooks;
-   no se rompieron adapters;
-   no se rompió Session Memory;
-   no se rompió Artifact Identity;
-   no se rompió Technical Index;
-   no se debilitó Protection;
-   no se rompió Freeze;
-   no se rompió `gtt-validate.sh`;
-   no quedan referencias funcionales a las rutas antiguas;
-   los índices fueron regenerados;
-   el Scaffold Manifest existe;
-   el Scaffold es canónico de GTT;
-   los ADE solamente aportan overlays;
-   no se creó arquitectura artificial;
-   los nombres de la nueva estructura cumplen lowercase;
-   las validaciones disponibles terminan correctamente.

------------------------------------------------------------------------

# 21. Restricciones

NO:

-   cambiar la versión de GTT;
-   cambiar la semántica de governance;
-   rediseñar GTT;
-   crear módulos metodológicos artificiales;
-   duplicar lógica entre Core y adapters;
-   inventar funcionalidades;
-   implementar todavía un nuevo `gtt init`;
-   convertir índices en fuente de verdad;
-   eliminar evidencia histórica legítima;
-   hacer commit;
-   hacer push;
-   modificar el Canon GTT.

La tarea es una **reestructuración controlada del Scaffold**, no una
nueva versión de la metodología.

------------------------------------------------------------------------

# 22. Informe final requerido

Al terminar, entregar un informe conciso pero verificable con:

## Estructura

Árbol final.

## Migración

Lista de archivos/directorios movidos.

## Referencias

Resumen de referencias actualizadas.

## Scaffold

Ubicación y contenido funcional del manifest.

## Integridad

Resultado de Artifact Identity y Technical Index.

## Session

Resultado de Session Memory.

## Protection

Resultado de protection/freeze.

## Adapters

Resultado de cada adapter/check disponible.

## Validation

Resultado de:

``` text
gtt-check-integrity.sh
gtt-check-protection.sh
gtt-check-session-adapter.sh
gtt-validate.sh
```

## Referencias antiguas

Resultado de la búsqueda final y clasificación de cualquier coincidencia
restante.

## Limpieza

Archivos stale/temporales eliminados, si los hubo.

## Gaps

Cualquier problema que permanezca debe declararse explícitamente.

No ocultar warnings ni convertir un SKIP en PASS.

------------------------------------------------------------------------

# Resultado esperado

El producto debe quedar conceptualmente así:

``` text
                 GTT CANONICAL SCAFFOLD
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
      ENGINE          GOVERNANCE          DOCS
        │                 │
        │                 │
        └────────────┬────┘
                     │
                ADE OVERLAY
          ┌──────────┼──────────┐
        Claude      Kiro      Copilot
```

La estructura física debe ser simple para el usuario, mientras que las
relaciones internas deben continuar siendo técnicamente completas,
trazables y verificables.

**Principio final:**

> Reestructurar la forma sin romper el comportamiento.

No realizar commit ni push al finalizar.
