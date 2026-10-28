---
id: event-first
name: Event-First
kind: architecture-style
question: development
recommended: false
requires_adr: true
compatible_with: [ddd, vertical-slice, hexagonal, layered, walking-skeleton]
incompatible_with: []
verification: partial
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

# Event-First · Method Pack

## Qué es

El diseño parte de los hechos del negocio: los eventos que ocurren ("pedido confirmado", "pago rechazado"), los
comandos que los provocan y las políticas que reaccionan a ellos. Los módulos se comunican publicando y
consumiendo eventos, no llamándose por dentro.

## Conviene si

El negocio es un flujo de pasos que ocurren en el tiempo, con varias partes que reaccionan a lo mismo o procesos que tardan.

## What it is

Design starts from the facts of the business: the events that happen ("order confirmed", "payment rejected"),
the commands that cause them and the policies that react to them. Modules talk by publishing and consuming
events, not by calling into each other.

## Fits when

The business is a flow of steps over time, with several parts reacting to the same thing or long-running processes.

## Qué descarta

- Que un módulo cambie el estado de otro llamando a su código interno.
- Eventos con nombre de acción técnica ("UpdateRow") en lugar de un hecho del negocio en pasado.
- Diseñar las pantallas o las tablas antes que el flujo de eventos.

## Efecto en el diseño

### Cómo se cortan los Epics

Cada Epic cubre un tramo del flujo de eventos del negocio, de un comando a los eventos que produce y a las
políticas que reaccionan. El orden de los Epics sigue el orden del flujo.

### Cómo se estructura el diseño por Epic

El diseño del Epic conserva sus ocho secciones. En la sección 1 se agregan los eventos, los comandos, las
políticas y las vistas de lectura del Epic, con la plantilla de abajo.

### Qué va en architecture.md (Architectural style)

"Event-First", con el mecanismo de publicación (en proceso, cola, broker), dónde viven los contratos de eventos
y la razón. La tabla *Modules and boundaries* declara la carpeta de cada módulo y la de los contratos.

### Qué reglas agrega a stack.md, vista 5

- EF-1: un módulo no depende del código interno de otro módulo; solo de los contratos de eventos.

## Plantilla de diseño por Epic

```gtt-epic-template
### Events

- **Eventos de dominio:** <facts in the past tense, who publishes each one and its payload> (#I-n)
- **Comandos:** <what a user or a system asks for, and the event it produces> (#F-n)
- **Políticas:** <when event X happens, then command Y> (#R-n)
- **Vistas de lectura:** <what is projected from the events to be shown or queried>
```

## Verificación

### Reglas

Formato neutro: `ID | FROM | MUST NOT DEPEND ON | MAY DEPEND ON | CHECK`.

```gtt-method-rules
EF-1 | module | the internal code of another module | event contracts | dependency
EF-2 | module | - | - | audit: events are named as business facts in the past tense
```

### Qué se chequea en el freeze

```gtt-method-checks
epic-forbidden-kind: layer
design-fields: Eventos de dominio, Comandos, Políticas
```

- Ningún Epic es una capa técnica.
- Cada diseño aprobado declara sus eventos, comandos y políticas.
- EF-1 está en stack.md, vista 5, con las rutas reales.

### Qué se chequea en gtt check / CI

EF-1, con la herramienta de dependencias del lenguaje mediante un adaptador. Sin adaptador, `declared-only`.

### Qué queda solo para audit

EF-2: que los eventos sean hechos del negocio y que ningún módulo cambie el estado de otro sin un evento.
