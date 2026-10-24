# Changelog

Todos los cambios notables de SaluDuoc se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
el versionado semántico ([SemVer](https://semver.org/lang/es/)).

## [Unreleased]

Sin cambios posteriores a la Fase 0.

## [0.1.0] - 2026-10-24

Primera entrega: Fase 0 del proyecto. Incluye el scaffold completo, autenticación
y autorización, perfiles, datos base y automatización. **No incluye** carga de
signos vitales, motor de triage, cálculo de distancia ni cola de espera; esas
funcionalidades corresponden a las fases 1–4.

### Added

- Estructura del proyecto con FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2,
  PostgreSQL 16 y frontend HTML/CSS/JavaScript vanilla con Jinja2.
- Configuración central con `pydantic-settings` y archivo `.env.example`
  (`DATABASE_URL`, `SECRET_KEY`, `ENV`, `COOKIE_SECURE`, `TOKEN_TTL_MINUTES`,
  `RATE_LIMIT_LOGIN`, `TEST_DATABASE_URL`).
- Modelos `User`, `PatientProfile`, `DoctorProfile`, `Establishment` y
  `NormalRange`, con UUID, timestamps y convención de nombres para constraints.
- Migraciones Alembic: creación de tablas iniciales y migración de
  `users.token_version`, constraint de rol y unicidad de rangos por métrica/versión.
- Registro de pacientes, login, logout, `GET /api/v1/auth/me`, perfil propio
  (`GET/PATCH /api/v1/users/me`) y listado paginado de usuarios para admin.
- Autenticación con Argon2 y JWT HS256 en cookie HttpOnly, con `SameSite=Lax`,
  `Secure` configurable y claim de versión de sesión (`ver`).
- RBAC con roles `patient`, `doctor` y `admin`; el listado admin no expone
  perfiles clínicos.
- Rate limit de login por `IP + correo` (5 fallos por minuto) con `Retry-After`.
- Endpoints de salud: `/healthz` (liveness) y `/readyz` (readiness con consulta
  a PostgreSQL).
- Seed reproducible de establecimientos desde el snapshot DEIS/MINSAL
  (2026-10-20, CC0): 76 establecimientos alrededor de 19 sedes Duoc UC, con 3
  establecimientos de urgencia por sede.
- Seed de 5 rangos MINSAL versionados (FC, PAS, PAD, SpO2 y calidad de sueño)
  y de 3 cuentas demo (`paciente@demo.cl`, `medico@demo.cl`, `admin@demo.cl`)
  mediante `python scripts/seed.py --demo`.
- 29 tests de backend contra PostgreSQL real, organizados por autenticación,
  configuración, RBAC, seed y perfiles.
- CI con GitHub Actions: PostgreSQL 16 como servicio, `alembic upgrade head`,
  `alembic check`, `pytest` y `ruff check`.
- `Dockerfile` non-root (UID 10001) con `HEALTHCHECK`, y `docker-compose.yml`
  con PostgreSQL de desarrollo en `:5434`, PostgreSQL de test en `:5433`,
  aplicación en `:8000` y healthcheck de readiness.
- Documentación inicial: PRD, SPEC, ADRs 0001–0006, índice de ADRs y este
  CHANGELOG.

### Changed

- Endurecimiento posterior a la revisión de Fase 0: la sesión ahora incluye
  `token_version`, las cuentas demo son opt-in con `--demo`, el seed es
  idempotente y desactiva establecimientos DEIS que ya no están en el snapshot.
- El rate limit distingue por correo, de modo que un login exitoso con otra
  cuenta no limpia el bloqueo de la cuenta atacada.
- El contenedor de la aplicación corre como usuario no root y usa
  `host.docker.internal:5434` en el compose de desarrollo para acceder a la base
  publicada en el host.
- Actualización de PRD, SPEC y ADRs para reflejar `/readyz`, `token_version`,
  las guardas de producción y el estado real del seed.

### Security

- Contraseñas almacenadas con Argon2; los errores de validación no reutilizan
  el valor de la contraseña enviada.
- JWT en cookie `HttpOnly` con `SameSite=Lax`; el token no es accesible desde
  JavaScript.
- Logout revoca todos los tokens del usuario al incrementar `token_version`.
- En entornos distintos de `dev`/`test` el arranque falla con `SECRET_KEY`
  débil o de ejemplo, o con `COOKIE_SECURE=false`.
- Las cuentas demo con contraseña fija solo se permiten en `dev`/`test`.
- Cabeceras de seguridad básicas: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy` y `Permissions-Policy`.
- Documentación deshabilitada en producción (`/docs`, `/redoc` y
  `/openapi.json` no se publican con `ENV=prod`).

### Fixed

- El logout anterior solo borraba la cookie y dejaba válido un token copiado;
  ahora se invalida mediante `token_version`.
- Los errores `422` de validación exponían el valor enviado (incluida la
  contraseña); ahora solo devuelven `loc`, `msg` y `type`.
- El registro maneja la carrera de correos duplicados y responde `409` también
  ante `IntegrityError`.
- El seed de establecimientos evita duplicados, excluye pediátricos, maternales
  y dentales, y falla si una sede no alcanza el mínimo de urgencias.
- Se corrigió la configuración de puertos y red de Docker para desarrollo y
  tests (`5434`/`5433`), y se añadieron healthchecks de liveness y readiness.
