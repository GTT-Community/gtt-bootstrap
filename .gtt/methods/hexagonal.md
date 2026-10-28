---
id: hexagonal
name: Hexagonal (Ports and Adapters)
kind: architecture-style
question: development
recommended: false
requires_adr: true
compatible_with: [ddd, vertical-slice, event-first, walking-skeleton]
incompatible_with: [layered]
verification: partial
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v3.0.md

# Hexagonal (Ports and Adapters) · Method Pack

## Qué es

El dominio queda en el centro y no conoce la tecnología. Se comunica con el exterior por puertos (interfaces que
él define), y los adaptadores conectan esos puertos con la base de datos, la web, las colas o los servicios
externos. Cambiar una tecnología es cambiar un adaptador.

## Conviene si

La lógica de negocio debe sobrevivir a cambios de base de datos, framework o proveedores, y quieres probarla sin infraestructura.

## What it is

The domain sits at the centre and knows nothing of technology. It talks to the outside through ports
(interfaces it defines), and adapters connect those ports to the database, the web, queues or external
services. Changing a technology is changing an adapter.

## Fits when

The business logic must outlive changes of database, framework or providers, and you want to test it without infrastructure.

## Qué descarta

- Que el dominio importe el framework, el ORM, el cliente HTTP o el SDK de un proveedor.
- Que un adaptador contenga reglas de negocio.
- Capas apiladas donde el dominio depende de la persistencia (Layered).

## Efecto en el diseño

### Cómo se cortan los Epics

Cada Epic es un resultado de negocio. Integrar un proveedor nuevo es un adaptador dentro de un Epic de negocio,
no un Epic por sí mismo.

### Cómo se estructura el diseño por Epic

El diseño del Epic conserva sus ocho secciones. En la sección 1 se agregan los puertos de entrada (casos de uso),
los puertos de salida y los adaptadores que el Epic necesita, con la plantilla de abajo.

### Qué va en architecture.md (Architectural style)

"Hexagonal (Ports and Adapters)", con dónde vive el dominio, dónde los puertos y dónde los adaptadores, y la
razón. La tabla *Modules and boundaries* declara esas carpetas con sus rutas reales.

### Qué reglas agrega a stack.md, vista 5

- HX-1: el dominio no depende de adaptadores, de infraestructura ni del framework.
- HX-2: la aplicación (casos de uso) no depende de adaptadores; solo del dominio y de los puertos.

## Plantilla de diseño por Epic

```gtt-epic-template
### Ports and adapters

- **Puertos de entrada:** <use cases this Epic exposes, and who calls them> (#F-n)
- **Puertos de salida:** <what the domain needs from outside, as interfaces it owns> (#I-n)
- **Adaptadores:** <the technology behind each port: database, web, queue, provider>
```

## Verificación

### Reglas

Formato neutro: `ID | FROM | MUST NOT DEPEND ON | MAY DEPEND ON | CHECK`.

```gtt-method-rules
HX-1 | domain | adapters, infrastructure, framework | - | dependency
HX-2 | application | adapters | domain, ports | dependency
HX-3 | adapters | - | - | audit: no business rule lives in an adapter
```

### Qué se chequea en el freeze

```gtt-method-checks
epic-forbidden-kind: layer
design-fields: Puertos de entrada, Puertos de salida, Adaptadores
```

- Ningún Epic es una capa técnica.
- Cada diseño aprobado declara sus puertos y adaptadores.
- HX-1 y HX-2 están en stack.md, vista 5, con las rutas reales.

### Qué se chequea en gtt check / CI

HX-1 y HX-2, con la herramienta de dependencias del lenguaje mediante un adaptador. Sin adaptador, `declared-only`.

### Qué queda solo para audit

HX-3: que los adaptadores no tengan reglas de negocio y que los puertos estén definidos en términos del dominio.
