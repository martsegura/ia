# ADR 0007 — Publicación de SaluDuoc en un repositorio público

**Estado:** Aceptada · **Fecha:** 2026-10-24

## Contexto
SaluDuoc se desarrolló en un repositorio local y se quiso publicar en un
repositorio nuevo, `martsegura/saluduoc`, para que el proyecto quedara visible
de forma independiente. El token de GitHub disponible en el entorno (la App de
GitHub de Codespaces) no tiene el permiso `Administration: write`: la creación
del repositorio falla con `Resource not accessible by integration`. El mismo
token sí puede hacer push sobre repositorios existentes del usuario.

## Decisión
Publicar SaluDuoc como subcarpeta `saluduoc/` del repositorio público existente
`martsegura/ia` (antes `martsegura/lemoria`), conservando su historial completo.
La importación se hizo con un merge de historiales no relacionados:

```bash
git merge -s ours --allow-unrelated-histories <rama-saluduoc>
git read-tree --prefix=saluduoc/ -u <rama-saluduoc>
```

Es el equivalente a `git subtree`, que no está instalado en el entorno. SaluDuoc
se distribuye con licencia MIT, igual que el repositorio contenedor. La
integración continua queda en un workflow único en la raíz
(`.github/workflows/ci.yml`) con `working-directory: saluduoc`, porque GitHub
solo ejecuta los workflows ubicados en `.github/workflows/` de la raíz del
repositorio.

## Alternativas descartadas
- **Crear un repositorio nuevo `martsegura/saluduoc`:** bloqueado por permisos
  del token (`Administration: write` ausente).
- **Force push reemplazando `main` del repositorio contenedor:** destructivo
  para el historial y el contenido existente del repositorio.
- **Publicar en una rama separada:** no cumple el objetivo de tener el proyecto
  visible en `main` de un repositorio público.

## Consecuencias
- El repositorio anidado `saluduoc/.git` se mantiene solo en local; el
  historial que importa el repositorio contenedor es el que se publica.
- `saluduoc/.github/workflows/ci.yml` queda como referencia inerte: GitHub no lo
  ejecuta dentro de un repositorio anidado. La CI real es la del monorepo.
- El `README.md` de SaluDuoc sigue describiendo solo la Fase 0, aunque el código
  ya incluye fases posteriores. Es una deuda documental asumida por decisión
  del usuario.
- Cualquier cambio futuro en SaluDuoc se hace dentro de `saluduoc/` del
  monorepo; el repositorio anidado local no es la fuente de publicación.
