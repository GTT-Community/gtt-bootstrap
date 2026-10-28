---
id: layered
name: Layered
kind: architecture-style
question: development
recommended: false
requires_adr: true
compatible_with: [walking-skeleton, ddd, event-first]
incompatible_with: [vertical-slice, hexagonal]
verification: partial
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

# Layered · Method Pack

## Qué es

El sistema se organiza en capas técnicas apiladas: presentación, aplicación y datos. Cada capa usa solo la de
abajo y no conoce las de arriba. Es la forma más conocida y la que la mayoría de los frameworks trae por defecto.

## Conviene si

Tu equipo y tu framework ya trabajan por capas y el sistema es sobre todo formularios y datos con poca lógica de negocio.

## What it is

The system is organised in stacked technical layers: presentation, application and data. Each layer uses only
the one below and knows nothing of those above. It is the best-known form and the one most frameworks ship with.

## Fits when

Your team and framework already work in layers and the system is mostly forms and data with little business logic.

## Qué descarta

- Que una capa inferior conozca a una superior (datos que llaman a presentación, aplicación que importa la UI).
- Que la presentación salte la aplicación y vaya directo a los datos (capas cerradas).
- Organizar el código por funcionalidad: una funcionalidad se reparte entre las capas.
- Combinarlo con Vertical Slice o Hexagonal: cortan el sistema en otra dirección.

## Efecto en el diseño

### Cómo se cortan los Epics

Cada Epic sigue siendo un resultado de negocio (nunca "la capa de datos"); su diseño dice qué aporta cada capa.

### Cómo se estructura el diseño por Epic

El diseño del Epic conserva sus ocho secciones. En la sección 1 se agrega qué agrega o cambia el Epic en cada
capa, con la plantilla de abajo.

### Qué va en architecture.md (Architectural style)

"Layered", con las capas, su orden, si son cerradas y la razón de la elección. La tabla *Modules and
boundaries* declara la carpeta de cada capa con su ruta real.

### Qué reglas agrega a stack.md, vista 5

- L-1: aplicación no depende de presentación.
- L-2: datos no depende de aplicación ni de presentación.
- L-3: presentación no depende de datos (capas cerradas: pasa por aplicación).

## Plantilla de diseño por Epic

```gtt-epic-template
### By layer

- **Capa de presentación:** <screens, endpoints or commands this Epic adds or changes> (#I-n)
- **Capa de aplicación:** <use cases and rules it adds> (#R-n, #F-n)
- **Capa de datos:** <entities, tables and queries it adds or changes>
```

## Verificación

### Reglas

Formato neutro: `ID | FROM | MUST NOT DEPEND ON | MAY DEPEND ON | CHECK`.

```gtt-method-rules
L-1 | application layer | presentation layer | data layer | dependency
L-2 | data layer | application layer, presentation layer | - | dependency
L-3 | presentation layer | data layer | application layer | dependency
```

### Qué se chequea en el freeze

```gtt-method-checks
epic-forbidden-kind: layer
design-fields: Capa de presentación, Capa de aplicación, Capa de datos
```

- Ningún Epic es una capa (`**Kind:** layer`): un Epic es un resultado de negocio en cualquier método.
- Cada diseño aprobado dice qué aporta en cada capa.
- L-1, L-2 y L-3 están en stack.md, vista 5, con las rutas reales.

### Qué se chequea en gtt check / CI

L-1, L-2 y L-3, con la herramienta de dependencias del lenguaje mediante un adaptador. Sin adaptador, `declared-only`.

### Qué queda solo para audit

Que la lógica de negocio viva en la capa de aplicación y no se filtre a la presentación ni a los datos.
