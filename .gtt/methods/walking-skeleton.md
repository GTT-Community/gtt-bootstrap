---
id: walking-skeleton
name: Walking Skeleton
kind: decomposition-strategy
question: start
recommended: true
requires_adr: false
compatible_with: [vertical-slice, layered, ddd, hexagonal, event-first]
incompatible_with: []
verification: partial
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Walking Skeleton · Method Pack

## Qué es

Antes de construir funcionalidades se construye la versión más delgada del sistema que funciona de punta a punta:
una entrada, una regla mínima, un dato guardado, desplegada y con su prueba. Después, cada Epic agrega carne a ese
esqueleto en vez de inventar la estructura sobre la marcha.

## Conviene si

El stack, el despliegue o las integraciones tienen riesgo y quieres descubrir los problemas en la primera semana, no al final.

## What it is

Before building features, build the thinnest version of the system that works end to end: one input, one
minimal rule, one stored datum, deployed and tested. Each later Epic then puts flesh on that skeleton instead
of inventing the structure as it goes.

## Fits when

The stack, the deployment or the integrations carry risk and you want to find the problems in the first week, not at the end.

## Qué descarta

- Empezar por una capa completa (todo el modelo de datos, toda la API) antes de que algo funcione de punta a punta.
- Dejar el despliegue y la integración continua para el final.
- Un esqueleto que no se despliega o que no tiene una prueba de punta a punta.

## Efecto en el diseño

### Cómo se cortan los Epics

El primer Epic del backlog es obligatoriamente el esqueleto y lo declara (`**Kind:** skeleton`). Atraviesa todos
los componentes del stack con la funcionalidad mínima. Los demás Epics vienen después y se apoyan en él.

### Cómo se estructura el diseño por Epic

Solo el diseño del Epic esqueleto recibe la plantilla de abajo, en su sección 1: el recorrido de punta a punta,
los componentes que atraviesa, cómo se despliega y su prueba.

### Qué va en architecture.md (Architectural style)

Una línea: el desarrollo empieza por un Walking Skeleton (el primer Epic). Es una estrategia de descomposición,
no un estilo arquitectónico: no lleva ADR.

### Qué reglas agrega a stack.md, vista 5

Ninguna. Su control es del backlog, no de las dependencias del código.

## Plantilla de diseño por Epic

`gtt-design.sh scaffold` inserta este bloque solo en el diseño del Epic esqueleto (`**Kind:** skeleton`, o el
primer Epic del backlog si ninguno lo declara).

```gtt-epic-template
### Walking skeleton

- **Recorrido de punta a punta:** <the one request that travels the whole system, from entry to stored data and back> (#F-n)
- **Componentes que atraviesa:** <every component of stack.md section 2 it touches>
- **Despliegue:** <where and how the skeleton is deployed, through the real pipeline>
- **Prueba de punta a punta:** <the test that proves the path works> (#E-n)
```

## Verificación

### Reglas

No agrega reglas de dependencia.

```gtt-method-rules
WS-1 | first Epic | - | - | audit: the skeleton crosses every component and is deployed through the real pipeline
```

### Qué se chequea en el freeze

```gtt-method-checks
first-epic-kind: skeleton
first-epic-design-fields: Recorrido de punta a punta, Componentes que atraviesa, Despliegue, Prueba de punta a punta
```

- El primer Epic del backlog (el de número más bajo que no está `Cancelled`) tiene `**Kind:** skeleton`.
- Si su diseño está aprobado, tiene el recorrido, los componentes, el despliegue y la prueba.

### Qué se chequea en gtt check / CI

Nada del código: es una estrategia de inicio.

### Qué queda solo para audit

WS-1: que el esqueleto atraviese de verdad todos los componentes y se despliegue por el pipeline real.
