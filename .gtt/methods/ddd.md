---
id: ddd
name: Domain-Driven Design
kind: architecture-style
question: development
recommended: false
requires_adr: true
compatible_with: [vertical-slice, hexagonal, layered, event-first, walking-skeleton]
incompatible_with: []
verification: partial
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Domain-Driven Design · Method Pack

## Qué es

El sistema se divide en bounded contexts: zonas del negocio con su propio modelo y su propio lenguaje. Cada
contexto es dueño de sus datos y reglas, y los demás lo usan solo por su contrato público. Se combina bien con
Vertical Slice: DDD define los Epics y Vertical Slice los corta.

## Conviene si

El negocio es complejo, tiene áreas con reglas y vocabulario propios, y equivocarse en el modelo cuesta caro.

## What it is

The system is divided into bounded contexts: areas of the business with their own model and language. Each
context owns its data and rules, and the others use it only through its public contract. It combines well with
Vertical Slice: DDD defines the Epics and Vertical Slice cuts them.

## Fits when

The business is complex, has areas with their own rules and vocabulary, and getting the model wrong is costly.

## Qué descarta

- Un modelo único compartido por todo el sistema (la misma entidad `Cliente` para ventas, facturación y soporte).
- Que un contexto lea o escriba el modelo interno o las tablas de otro.
- Términos del dominio con un significado distinto según quién los use dentro de un mismo contexto.

## Efecto en el diseño

### Cómo se cortan los Epics

Cada Epic pertenece a un bounded context y lo declara (`**Bounded context:**` en el backlog). Un Epic que
atraviesa varios contextos se divide, o declara cuál es su dueño y qué contratos usa de los demás.

### Cómo se estructura el diseño por Epic

El diseño del Epic conserva sus ocho secciones. En la sección 1 se agrega el contexto, sus agregados, el
lenguaje ubicuo y los contratos con otros contextos, con la plantilla de abajo.

### Qué va en architecture.md (Architectural style)

"Domain-Driven Design", con el mapa de contextos (cuáles hay, quién es dueño de qué y cómo se relacionan) y la
razón. La tabla *Modules and boundaries* declara la carpeta de cada contexto con su ruta real.

### Qué reglas agrega a stack.md, vista 5

- DDD-1: un bounded context no accede al modelo interno de otro; solo a su contrato público.

## Plantilla de diseño por Epic

```gtt-epic-template
### Domain

- **Bounded context:** <the context this Epic belongs to, as architecture.md names it>
- **Agregados:** <aggregates it creates or changes, and their invariants> (#R-n)
- **Lenguaje ubicuo:** <terms of this context, as glossary.md defines them>
- **Contratos con otros contextos:** <what it uses from or offers to other contexts> (#I-n)
```

## Verificación

### Reglas

Formato neutro: `ID | FROM | MUST NOT DEPEND ON | MAY DEPEND ON | CHECK`.

```gtt-method-rules
DDD-1 | bounded context | the internal model of another bounded context | the public contract of another bounded context | dependency
DDD-2 | bounded context | - | - | audit: one model and one language per context, as glossary.md defines it
```

### Qué se chequea en el freeze

```gtt-method-checks
epic-required-fields: Bounded context
design-fields: Bounded context, Agregados, Lenguaje ubicuo, Contratos con otros contextos
```

- Cada Epic aprobado declara su bounded context.
- Cada diseño aprobado tiene contexto, agregados, lenguaje y contratos.
- DDD-1 está en stack.md, vista 5, con las rutas reales.

### Qué se chequea en gtt check / CI

DDD-1, con la herramienta de dependencias del lenguaje mediante un adaptador. Sin adaptador, `declared-only`.

### Qué queda solo para audit

DDD-2: que los límites de los contextos sean los del negocio, que el lenguaje ubicuo se respete y que los
agregados protejan sus invariantes.
