# GTT Bootstrap — Guía de instalación

> **Canonical reference:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

Este documento contiene los procedimientos detallados para instalar GTT Bootstrap.

El README del repositorio sigue siendo la puerta de entrada canónica. Esta guía amplía la instalación sin sacar el Quick Start del README.

## Modos de instalación

GTT admite dos modos de instalación inicial:

1. **Instalación manual** — una persona integra los archivos de GTT en un proyecto existente.
2. **Instalación asistida por agente** — un ADE/agente de programación con IA lee la documentación de GTT y realiza el bootstrap bajo reglas explícitas.

En ambos casos, el objetivo final es el mismo: establecer el contrato del workspace GTT, poblar el contexto gobernado, obtener confirmación humana y congelar el contexto antes del desarrollo gobernado normal.

---

## Requisitos previos

- Un proyecto/repositorio.
- Git.
- Bash para el CI gate y los scripts.
- Python 3 para el hook de protección.
- Claude Code, Kiro, Codex, GitHub Copilot u otro ADE capaz de seguir el procedimiento de bootstrap.
- Se recomienda un documento de diseño/origen terminado, aunque no es obligatorio.

El documento de diseño puede estar en Markdown, texto, Word, PDF u otro formato habitual.

---

## Instalación manual

### 1. Inspeccionar el proyecto anfitrión

Antes de copiar GTT, inspecciona la raíz del proyecto.

Identifica:

- `AGENTS.md` existente
- `readme-gtt.md` / `readme-gtt.es.md` existente
- `gtt/` existente (el Motor)
- `context/`, `adr/`, `proposals/`, `docs/`, `backlog.md`, `change-request.md`, `session.md`, `.frozen` existentes (Gobernanza del Proyecto y Documentación)
- `.claude/` existente
- `.kiro/` existente
- `.copilot/copilot-instructions.md` existente
- `.gitignore` existente
- documentos de diseño/origen
- archivos o directorios cuyos nombres sean requeridos por GTT

**No sobrescribas archivos existentes silenciosamente.**

Si ya existe un nombre requerido por GTT, detente y resuelve el conflicto explícitamente.

### 2. Instalar el scaffolding de GTT

El workspace final debe contener:

```text
/
├── AGENTS.md                     # contrato portable del agente (archivo de descubrimiento del ADE)
├── readme-gtt.md
├── readme-gtt.es.md
├── SOURCE-BRIEF.*                # si existió documento fuente
│
├── context/                      # GOBERNANZA DEL PROYECTO: contexto gobernado L0
├── adr/                          #   decisiones aceptadas L1
├── proposals/                    #   borradores del agente pendientes de decisión humana
├── backlog.md                    #   línea de desarrollo
├── change-request.md             #   puerta de entrada de los cambios
├── session.md                    #   estado operativo derivado (nunca autoridad)
├── .frozen                       #   marcador de freeze, escrito por gtt-freeze.sh
│
├── docs/                         # DOCUMENTACIÓN DE GTT
│   ├── index.md
│   ├── installation.md
│   ├── installation.es.md
│   ├── usage.md
│   ├── usage.es.md
│   ├── gtt-completion.md
│   ├── evidence.md
│   ├── docs.md
│   └── session-adapter-contract.md
│
├── gtt/                          # MOTOR DE GTT
│   ├── README.md
│   ├── scaffold/manifest.yaml
│   ├── scripts/
│   ├── index/
│   ├── protection/
│   └── session-adapters/
│
└── .claude/ | .kiro/ | .copilot/ # OVERLAY DEL ADE - exactamente uno: el ADE que ejecuta el bootstrap
```

El Motor vive en `gtt/`, la Documentación (incluyendo este archivo) en `docs/` y
la Gobernanza del Proyecto en la raíz del proyecto — ver *Higiene del workspace*
en `readme-gtt.md`. Cada artefacto se genera directamente donde lo ubica el
scaffold (`gtt/scaffold/manifest.yaml`), nunca en otro lugar para moverlo
después. `docs/`, `context/` y `adr/` son nombres comunes: si el proyecto ya
tiene alguno, detente e informa el conflicto en lugar de combinarlos.

Instala únicamente el adaptador correspondiente al ADE que realmente usás — `.claude/` para Claude Code, `.kiro/` para Kiro, o `.copilot/copilot-instructions.md` para GitHub Copilot (Codex no necesita ningún archivo adicional). No copies los demás "por las dudas"; el repositorio fuente distribuye todos los adaptadores como catálogo, no como paquete para instalar completo. Ver la matriz de adaptadores de ADE en el README.

### 3. Preservar el diseño original

Si el proyecto contiene un documento de diseño y se utilizará como fuente del bootstrap, consérvalo como:

```text
SOURCE-BRIEF.*
```

No modifiques silenciosamente el documento original.

### 4. Combinar `.gitignore`

Si el proyecto ya posee `.gitignore`, combina las entradas necesarias de GTT con él.

No reemplaces el `.gitignore` del proyecto.

### 5. Poblar el contexto

Método recomendado:

```text
bootstrap GTT
```

o:

```text
set up GTT
```

No comiences inventando manualmente los seis archivos de contexto si el procedimiento de bootstrap está disponible.

Si decides crearlos manualmente, comienza por:

```text
context/stack.md
```

y marca explícitamente las decisiones desconocidas en lugar de adivinarlas.

### 6. Revisar

El responsable humano debe revisar:

- arquitectura
- stack tecnológico
- requisitos
- restricciones
- principios
- visión de solución
- glosario
- mapa de stack

La generación de archivos no significa que el contexto esté ratificado.

### 7. Freeze

Cuando el contexto esté completo y confirmado:

```bash
./gtt/scripts/gtt-freeze.sh
```

Esto crea:

```text
.frozen
```

y establece el régimen gobernado.

### 8. Verificar el guardrail

Solicita al agente modificar:

```text
context/stack.md
```

El mecanismo de enforcement correspondiente debe bloquear la escritura.

Que el modelo diga “no debería hacerlo” no equivale a enforcement determinista.

### 9. Instalar el CI gate

Conecta:

```text
gtt/scripts/gtt-check-stack.sh
gtt/scripts/gtt-check-backlog.sh
gtt/scripts/gtt-check-protection.sh
```

al CI contra la rama por defecto. Esto asegura que los cambios arquitectónicos gobernados y el mapa permanezcan sincronizados, y que `gtt/protection/registry.yaml` (GTTGuard) siempre coincida con los marcadores `@GTTGuard` realmente presentes en el código.

---

## Instalación asistida por agente

El agente debe tratar este repositorio como un contrato documental ejecutable, no como una colección de archivos que puede copiar sin analizar.

### Procedimiento del agente

1. Leer `readme-gtt.md`.
2. Leer `AGENTS.md`.
3. Detectar qué ADE está ejecutando realmente este bootstrap y resolver exactamente un adaptador para él. Si parece haber más de un ADE posible y no se puede establecer con confianza cuál lo ejecuta, detenerse y preguntar — nunca adivinar, ni instalar más de un adaptador nativo.
4. Inspeccionar el proyecto anfitrión.
5. Identificar el documento de diseño/origen.
6. Si no existe, trabajar mediante conversación.
7. Si existen varios candidatos, preguntar.
8. Nunca adivinar cuál es la fuente autorizada.
9. Nunca sobrescribir silenciosamente un archivo existente con el mismo nombre.
10. Crear el contrato de workspace GTT: el núcleo portable más únicamente el adaptador resuelto, excluyendo explícitamente los demás.
11. Mapear la fuente confirmada al contexto gobernado.
12. Buscar Epics/Stories definidas (documento de requisitos, issue tracker, o conversación previa). Si existen, reconciliarlas en `backlog.md`; si no existe ninguna, decirlo explícitamente en vez de inventarlas.
13. Solicitar confirmación del contexto generado.
14. Preservar la fuente como `SOURCE-BRIEF.*`.
15. Ejecutar freeze solo después de confirmación humana explícita.
16. Verificar la protección.
17. Informar el estado final.

### Informe obligatorio del agente

Debe informar:

- ADE detectado y adaptador resuelto
- adaptadores excluidos explícitamente
- si existe soporte nativo para ese ADE
- archivos creados
- archivos preservados
- conflictos encontrados
- archivos omitidos deliberadamente
- documento fuente utilizado
- si el contexto fue confirmado
- si `backlog.md` está definido y reconciliado con las Epics/Stories conocidas
- si se ejecutó freeze
- si se verificó la protección
- si se conectó el CI gate
- acciones humanas pendientes

---

## Checklist

- [ ] Proyecto anfitrión inspeccionado.
- [ ] ADE ejecutor detectado y exactamente un adaptador resuelto (preguntado, no adivinado, si era ambiguo).
- [ ] Solo se instaló el adaptador resuelto; los demás quedaron explícitamente excluidos.
- [ ] Archivos requeridos identificados.
- [ ] Protegidos los archivos existentes contra sobrescritura silenciosa.
- [ ] Scaffolding GTT creado.
- [ ] `SOURCE-BRIEF.*` preservado cuando corresponde.
- [ ] `.gitignore` combinado.
- [ ] Contexto poblado.
- [ ] `backlog.md` presente; Epics/Stories conocidas reconciliadas o explícitamente ausentes.
- [ ] Revisión humana completada.
- [ ] Contexto confirmado explícitamente.
- [ ] `.frozen` creado.
- [ ] Escritura protegida verificada.
- [ ] CI gate conectado.
- [ ] Instalación informada.

---

## Siguiente paso

Continúa con [usage.es.md](usage.es.md).

### Destino del despliegue: repositorio Bootstrap vs. proyecto anfitrión

`readme-gtt.md`, `readme-gtt.es.md` y `AGENTS.md` permanecen en la **raíz
del proyecto** — los puntos de entrada canónicos, leídos antes que
cualquier otra cosa. Todo lo demás sigue el mismo scaffold en el repositorio Bootstrap y en cualquier
proyecto anfitrión donde se instale: el Motor en `gtt/`, la Gobernanza del
Proyecto en la raíz y la Documentación (incluyendo este archivo) en `docs/`.

Cuando un agente despliega GTT dentro de un proyecto anfitrión, DEBE reorganizar el workspace instalado para que coincida con el scaffold de GTT:

```text
/
├── AGENTS.md                     # contrato portable del agente (archivo de descubrimiento del ADE)
├── readme-gtt.md
├── readme-gtt.es.md
├── SOURCE-BRIEF.*                # si existió documento fuente
│
├── context/                      # GOBERNANZA DEL PROYECTO: contexto gobernado L0
├── adr/                          #   decisiones aceptadas L1
├── proposals/                    #   borradores del agente pendientes de decisión humana
├── backlog.md                    #   línea de desarrollo
├── change-request.md             #   puerta de entrada de los cambios
├── session.md                    #   estado operativo derivado (nunca autoridad)
├── .frozen                       #   marcador de freeze, escrito por gtt-freeze.sh
│
├── docs/                         # DOCUMENTACIÓN DE GTT
│   ├── index.md
│   ├── installation.md
│   ├── installation.es.md
│   ├── usage.md
│   ├── usage.es.md
│   ├── gtt-completion.md
│   ├── evidence.md
│   ├── docs.md
│   └── session-adapter-contract.md
│
├── gtt/                          # MOTOR DE GTT
│   ├── README.md
│   ├── scaffold/manifest.yaml
│   ├── scripts/
│   ├── index/
│   ├── protection/
│   └── session-adapters/
│
└── .claude/ | .kiro/ | .copilot/ # OVERLAY DEL ADE - exactamente uno: el ADE que ejecuta el bootstrap
```

El único adaptador resuelto — `.claude/` (Claude Code), `.kiro/` (Kiro), o `.copilot/copilot-instructions.md` (GitHub Copilot) — permanece en la raíz del proyecto anfitrión. Solo ese se instala, nunca más de uno.

El agente debe preservar los archivos existentes del proyecto, no sobrescribir conflictos silenciosamente y no ejecutar automáticamente el freeze. La revisión y confirmación humana deben ocurrir antes del freeze.
