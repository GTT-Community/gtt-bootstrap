---
id: vertical-slice
name: Vertical Slice
kind: architecture-style
question: development
recommended: true
requires_adr: true
compatible_with: [walking-skeleton, ddd, hexagonal, event-first]
incompatible_with: [layered]
verification: partial
---

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

# Vertical Slice · Method Pack

## Qué es

El sistema se organiza por funcionalidades completas, no por capas técnicas. Cada slice es un caso de uso
que atraviesa todo lo que necesita (entrada, lógica, datos) y vive junto en su propia carpeta. Agregar una
funcionalidad es agregar un slice, no tocar cinco capas.

## Conviene si

Vas a entregar funcionalidades de punta a punta, una a la vez, y quieres que cada cambio quede contenido en un solo lugar.

## What it is

The system is organised by complete features, not by technical layers. Each slice is one use case that
crosses everything it needs (input, logic, data) and lives together in its own folder. Adding a feature is
adding a slice, not touching five layers.

## Fits when

You will deliver end-to-end features one at a time and want each change contained in one place.

## Qué descarta

- Epics horizontales: "modelo de datos", "API", "backend", "frontend", "base de datos" no son Epics.
- Capas compartidas por todo el sistema (un `services/` o `repositories/` global del que dependen todos).
- Que un slice llame al código interno de otro slice. Lo que dos slices comparten va a un kernel mínimo.
- La abstracción anticipada: no se generaliza hasta que dos slices lo necesitan de verdad.

## Efecto en el diseño

### Cómo se cortan los Epics

Cada Epic es un resultado de negocio y se corta en slices de punta a punta. Ningún Epic es una capa técnica:
el backlog no tiene "modelo de datos", "API" ni "frontend" como Epics. El primer slice de cada Epic es el más
delgado que atraviesa todo el stack.

### Cómo se estructura el diseño por Epic

El diseño del Epic (`gtt-domain/context/design/EPIC-NNN.md`) conserva sus ocho secciones. En la sección 1 se
agrega una subsección por slice (`### S-n`), con la plantilla de abajo. Las reglas, flujos, interfaces y
ejemplos de las secciones 2 a 6 se citan desde los slices (`R-n`, `F-n`, `I-n`, `E-n`).

### Qué va en architecture.md (Architectural style)

"Vertical Slice": el código de cada funcionalidad vive junto, en la carpeta del slice; lo compartido vive en
un kernel mínimo; la razón de la elección. La tabla *Modules and boundaries* declara la carpeta de los slices
y la del kernel compartido con sus rutas reales.

### Qué reglas agrega a stack.md, vista 5

- VS-1: un slice no depende de otro slice; solo del kernel compartido.
- VS-2: el kernel compartido no depende de ningún slice.

## Plantilla de diseño por Epic

`gtt-design.sh scaffold` inserta este bloque en la sección 1 del diseño. Se repite una subsección por slice.

```gtt-epic-template
### Slices

The first slice is the thinnest one that crosses the whole stack. A slice depends on no other slice; only on
the shared kernel.

### S-1 — <slice name>

- **Caso de uso:** <who does what, and why> [FUENTE: <ID:§…>]
- **Entrada / salida:** <request or event in; response, view or event out> (#I-n)
- **Lógica:** <what it decides and computes> (#R-n, #F-n)
- **Datos que toca:** <entities and fields it reads and writes>
- **Criterio de aceptación:** <the example that shows it done> (#E-n)
- **Fuera de este slice:** <what a later slice does>
```

## Verificación

### Reglas

Formato neutro: `ID | FROM | MUST NOT DEPEND ON | MAY DEPEND ON | CHECK`. `CHECK` es `dependency` (lo verifica un
adaptador del lenguaje) o `audit` (juicio humano). En stack.md, vista 5, cada regla `dependency` se escribe con
las rutas reales del proyecto y su id en la columna *Rule*.

```gtt-method-rules
VS-1 | slice | another slice | shared kernel | dependency
VS-2 | shared kernel | any slice | - | dependency
VS-3 | slice | - | - | audit: the first slice of each Epic crosses the whole stack and each slice is small
```

### Qué se chequea en el freeze

```gtt-method-checks
epic-forbidden-kind: layer
epic-forbidden-title: modelo de datos, data model, base de datos, database, persistencia, persistence, api, backend, frontend, front-end, back-end, ui, interfaz de usuario, user interface, infraestructura, infrastructure, capa, layer
design-unit: S
design-unit-fields: Caso de uso, Entrada / salida, Lógica, Datos que toca, Criterio de aceptación, Fuera de este slice
```

- Ningún Epic tiene `**Kind:** layer` ni un título que empiece por una capa técnica.
- Cada diseño aprobado tiene al menos un slice (`### S-n`) y cada slice tiene sus seis campos.
- VS-1 y VS-2 están en stack.md, vista 5, con las rutas reales.

### Qué se chequea en gtt check / CI

VS-1 y VS-2, con la herramienta de dependencias del lenguaje del proyecto mediante un adaptador. Sin adaptador
para el lenguaje, el método queda `declared-only` en ese proyecto.

### Qué queda solo para audit

VS-3: que los slices sean de verdad delgados y que el primero atraviese todo el stack; que el kernel compartido
siga siendo mínimo.
