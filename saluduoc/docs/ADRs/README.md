# Architecture Decision Records (ADRs)

Registro de las decisiones de arquitectura de SaluDuoc. Cada ADR describe el
contexto, la decisión y sus consecuencias; las decisiones se mantienen aunque
cambie la implementación.

| ADR | Título | Estado | Fase |
|-----|--------|--------|------|
| [0001](0001-stack-fastapi-postgres-vanilla.md) | FastAPI + PostgreSQL + frontend vanilla | Aceptada | 0 |
| [0002](0002-jwt-cookie-httponly.md) | JWT en cookie HttpOnly | Aceptada | 0 |
| [0003](0003-triage-configurable-minsal.md) | Triage configurable basado en MINSAL | Implementada | 2 |
| [0004](0004-seed-deis-duoc.md) | Seed de establecimientos desde DEIS alrededor de sedes Duoc | Aceptada | 0 |
| [0005](0005-cola-por-establecimiento.md) | Cola por establecimiento y creación desde el triage | Implementada | 4 |
| [0006](0006-guardas-produccion-y-sesion.md) | Guardas de producción y versión de sesión | Aceptada | 0 |
| [0007](0007-publicacion-repo-publico.md) | Publicación en repositorio público como subcarpeta | Aceptada | — |

## Alcance

- **Implementadas en la Fase 0:** 0001 (stack), 0002 (sesión JWT), 0004 (seed
  DEIS) y 0006 (guardas de producción y `token_version`).
- **Implementadas en fases posteriores:** 0003 (motor de triage, Fase 2) y
  0005 (cola de espera, Fase 4).
- **Decisión transversal:** 0007 (publicación del proyecto en `martsegura/ia`
  bajo `saluduoc/`), no asociada a una fase.

## Convenciones

- Numeración secuencial de cuatro dígitos: `NNNN-titulo-corto.md`.
- Un ADR por decisión; no se reescribe uno aceptado, salvo correcciones
  editoriales. Si una decisión cambia, se crea un ADR nuevo que reemplaza al
  anterior.
- Estructura mínima: **Contexto**, **Decisión**, **Alternativas** (cuando
  aplique) y **Consecuencias**.
- Los ADRs se versionan junto al código y se revisan en el mismo cambio que la
  decisión.
