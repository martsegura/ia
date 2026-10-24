# ia

Repositorio contenedor de proyectos y prototipos de Martín Segura.

## Proyectos

### SaluDuoc

Prototipo de apoyo a la categorización de urgencia (C1–C5) y monitoreo de
signos vitales, construido con FastAPI y PostgreSQL. Vive en la subcarpeta
[`saluduoc/`](saluduoc/).

- Código y guía de uso: [`saluduoc/README.md`](saluduoc/README.md)
- Alcance y requisitos: [`saluduoc/docs/PRD.md`](saluduoc/docs/PRD.md)
- Historial de cambios: [`saluduoc/CHANGELOG.md`](saluduoc/CHANGELOG.md)

## Integración continua

El monorepo usa un único workflow en
[`.github/workflows/ci.yml`](.github/workflows/ci.yml), que se ejecuta con
`working-directory: saluduoc`. GitHub Actions solo lee los workflows ubicados en
`.github/workflows/` de la raíz del repositorio, por lo que la CI de cada
proyecto se define ahí.

## Licencia

Distribuido bajo licencia [MIT](LICENSE).
