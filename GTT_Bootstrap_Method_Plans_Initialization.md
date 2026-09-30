# GTT Bootstrap — Method Plans and Project Initialization

> **GTT Canonical Governance:** https://github.com/GTT-Community/gtt-method/blob/main/GTT-CANONICAL-v2.1.md

## 1. Propósito

Definir cómo **GTT Bootstrap** crea un proyecto según el plan metodológico seleccionado.

Bootstrap no ejecuta toda la metodología.

Su responsabilidad es:

```text
PLAN
 ↓
PROJECT STRUCTURE
 ↓
DEFAULT POLICY
 ↓
CLI CONFIGURATION
```

El CLI será responsable de ejecutar las operaciones posteriores.

---

# 2. Planes disponibles

GTT Bootstrap debe ofrecer cuatro planes:

```text
Light Method
Medium Method
Hard Method
Team Method
```

No deben presentarse como niveles de calidad.

Son perfiles de operación y colaboración.

---

# 3. Light Method

### Perfil

Para:

- desarrollador individual;
- prototipo gobernado;
- proyecto personal;
- proyecto donde se busca mínima carga operativa.

### Principio

> **Light Method reduce decisiones operativas e intervención humana, pero conserva el gobierno del proyecto.**

Bootstrap debe crear la configuración para que el CLI pueda:

- detectar automáticamente inconsistencias;
- resolver IDs disponibles;
- actualizar referencias;
- reconstruir índices;
- validar;
- sincronizar contexto de ADE/agentes;
- evitar tareas manuales repetitivas.

Ejemplo:

```bash
gtt bootstrap --method light
```

Debe producir:

```text
.gtt/
├── config.yaml
├── index/
├── scripts/
└── ...
```

con:

```yaml
method:
  plan: light
```

---

# 4. Medium Method

Perfil para proyectos individuales o pequeños equipos que quieren automatización pero prefieren confirmar cambios relevantes.

```yaml
method:
  plan: medium
```

Bootstrap configura:

- automatización determinista;
- confirmación de cambios relevantes;
- validación;
- trazabilidad.

---

# 5. Hard Method

Perfil para proyectos donde los cambios gobernados deben tener autorización explícita.

```yaml
method:
  plan: hard
```

Bootstrap configura:

- validación estricta;
- confirmaciones;
- protección reforzada de L0;
- operaciones destructivas siempre explícitas;
- controles adicionales para promoción.

Hard no significa trabajo manual.

Significa **control explícito sobre operaciones gobernadas**.

---

# 6. Team Method

Perfil para equipos y proyectos colaborativos.

```yaml
method:
  plan: team
```

Bootstrap prepara:

- políticas compartidas;
- CI/CD;
- trazabilidad de actores;
- coordinación;
- validación de cambios;
- detección de modificaciones concurrentes;
- integración con revisiones.

---

# 7. Matriz Bootstrap

| Capacidad | Light | Medium | Hard | Team |
|---|---|---|---|---|
| Estructura GTT | sí | sí | sí | sí |
| Gobierno | completo | completo | completo | completo |
| Automatización | alta | media/alta | controlada | alta |
| Confirmación | mínima | relevante | explícita | política |
| CI | opcional | recomendado | recomendado | requerido |
| Multiusuario | opcional | opcional | posible | central |
| ADE sync | automática segura | confirmada | controlada | política |
| Resolución de IDs | automática | automática | propuesta/confirmación | política |
| Trazabilidad | sí | sí | sí | reforzada |

---

# 8. Bootstrap no debe decidir por el usuario

Bootstrap debe preguntar:

```text
Select GTT Method Plan

[1] Light Method
    Maximum automation, individual project

[2] Medium Method
    Automation with confirmation

[3] Hard Method
    Strict human authorization

[4] Team Method
    Collaborative governance
```

El usuario selecciona el plan.

A partir de ese momento, Bootstrap materializa la configuración.

---

# 9. Defaults

Si el usuario no selecciona un plan explícitamente, Bootstrap debe:

```text
ask
```

No debe inferir silenciosamente:

```text
Light
```

salvo que exista una política explícita del entorno que lo determine.

---

# 10. Configuración generada

Bootstrap debe generar una configuración central.

Ejemplo:

```yaml
method:
  plan: light
  version: 1

automation:
  identity_resolution: automatic
  reference_updates: automatic
  validation: automatic
  agent_context_sync: automatic_safe

human:
  confirmation:
    destructive: required
    governed_decision: plan_defined
```

El CLI consume esta configuración.

---

# 11. Bootstrap no duplica lógica

No debe existir:

```text
Bootstrap implementation
+
CLI implementation
```

de las mismas reglas.

Bootstrap solamente genera configuración.

El CLI interpreta esa configuración.

Arquitectura:

```text
                 Method Plan
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
      Bootstrap                CLI
          │                     │
   creates config         executes policy
          │                     │
          └──────────┬──────────┘
                     ▼
              GTT Project
```

---

# 12. Migración

Un proyecto existente debe poder seleccionar un plan posteriormente.

Ejemplo:

```bash
gtt method set light
```

Bootstrap no debe obligar a recrear el proyecto.

La migración debe preservar:

- ADRs;
- contexto;
- índice;
- proposals;
- constraints;
- architecture;
- stack;
- historial.

---

# 13. Compatibilidad con ADE/agentes

Bootstrap debe preparar el proyecto para que el CLI pueda descubrir ADE/agentes posteriormente.

No debe asumir:

```text
Claude only
```

ni:

```text
Copilot only
```

Debe permitir:

```text
Claude Code
GitHub Copilot
Codex
Kiro
future agents
```

mediante el mecanismo de registro/adapters del CLI.

---

# 14. Agent registry

Cuando corresponda, Bootstrap puede inicializar:

```text
.gtt/agents/registry.yaml
```

Ejemplo:

```yaml
version: 1

agents: []
```

El registro puede crecer posteriormente.

Bootstrap no debe agregar automáticamente agentes solamente porque estén instalados en la máquina.

---

# 15. Primera ejecución

Después del bootstrap:

```text
GTT initialized.

Method:
  Light Method

Governance:
  enabled

Automation:
  high

Agent discovery:
  enabled

Run:
  gtt status
```

En Light, la experiencia inicial debe ser deliberadamente sencilla.

---

# 16. Regla de UX

El usuario debe elegir **intención metodológica**, no detalles técnicos.

Mala experiencia:

```text
Choose:
ADR policy
Index policy
Identity policy
Validation policy
Agent policy
Proposal policy
...
```

Buena experiencia:

```text
Choose Method:

Light
Medium
Hard
Team
```

GTT deriva las políticas técnicas desde el plan.

---

# 17. Escalamiento posterior

Un proyecto puede pasar:

```text
Light
  ↓
Medium
  ↓
Hard
  ↓
Team
```

sin perder sus artefactos.

El cambio debe modificar la política de operación, no rehacer el proyecto.

---

# 18. Regla de conservación del gobierno

Cambiar a Light no significa:

```text
disable governance
```

Significa:

```text
delegate deterministic operations to GTT
```

Por lo tanto:

```text
Light Method
    ↓
Same governed context
    ↓
Same integrity
    ↓
Same traceability
    ↓
Less manual operation
```

---

# 19. Criterio de éxito

Un proyecto inicializado con Light Method debe permitir que un usuario con poca carga operativa pueda hacer:

```bash
gtt status
gtt promote
gtt validate
gtt sync
```

sin tener que conocer:

- estructura interna del índice;
- IDs históricos;
- referencias cruzadas;
- detalles de sincronización de ADE;
- scripts internos;
- mecanismos de validación.

Eso no elimina la posibilidad de inspección.

Simplemente evita que el conocimiento interno del mecanismo sea requisito para operar GTT.

---

# 20. Regla final de Bootstrap

> **Bootstrap debe preguntar al usuario cuánto gobierno operativo desea delegar a GTT; no debe preguntarle cómo funciona internamente GTT.**

La selección:

```text
Light Method
Medium Method
Hard Method
Team Method
```

es una decisión de experiencia y operación.

Las reglas técnicas derivadas de ella pertenecen al CLI y al plano de control de GTT.
