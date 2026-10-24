# SaluDuoc

Aplicación web de apoyo a la categorización de urgencia (triage C1–C5) y
monitoreo de signos vitales para la comunidad Duoc UC.

> **Aviso:** SaluDuoc es un prototipo de apoyo a la pre-clasificación. No es un
> dispositivo médico y no reemplaza la evaluación de un profesional de la salud.

**Versión:** 0.1.0 · **Estado:** Fase 0 completada · **Tests:** 29 en verde

## Estado del proyecto

| Fase | Alcance | Estado | Documentación |
|------|---------|--------|---------------|
| 0 | Scaffold, Docker, Alembic, auth JWT, RBAC, perfiles, seed base y CI | ✅ Completada (29 tests) | [CHANGELOG](CHANGELOG.md) · [SPEC](docs/SPEC.md) |
| 1 | Perfil completo, carga de signos vitales y JSON de ejemplo | ⏳ Pendiente | [SPEC §7](docs/SPEC.md#7-json-de-wearables-fase-1) |
| 2 | Rangos, reglas y motor de triage C1–C5 | ⏳ Pendiente | [SPEC §8](docs/SPEC.md#8-motor-de-triage-fase-2) · [ADR 0003](docs/ADRs/0003-triage-configurable-minsal.md) |
| 3 | Establecimientos y distancia en la interfaz | ⏳ Pendiente | [SPEC §10](docs/SPEC.md#10-distancia-fase-3) |
| 4 | Cola de espera y vista del médico | ⏳ Pendiente | [SPEC §11](docs/SPEC.md#11-cola-fase-4) · [ADR 0005](docs/ADRs/0005-cola-por-establecimiento.md) |
| 5 | Panel de administración, pulido y despliegue | ⏳ Pendiente | [PRD §10](docs/PRD.md#10-fases) |

**Implementado en la Fase 0:** registro, login y logout; sesión JWT en cookie
HttpOnly con `token_version`; RBAC `patient`/`doctor`/`admin`; perfiles de
paciente y médico; listado de usuarios para admin; seed de 76 establecimientos,
5 rangos MINSAL y 3 cuentas demo; CI y contenedor Docker.

**Aún no implementado:** carga de signos vitales, motor de triage, cálculo de
distancia y cola de espera (fases 1–4). Los ADR 0003 y 0005 documentan
decisiones de diseño para esas fases, no funcionalidad existente.

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2
- **Base de datos:** PostgreSQL 16
- **Frontend:** HTML + CSS + JavaScript vanilla, servido por FastAPI
- **Auth:** JWT en cookie HttpOnly + Argon2, roles `patient`, `doctor`, `admin`
- **Tests:** pytest + httpx contra PostgreSQL
- **CI:** GitHub Actions (ruff, migraciones y tests)

## Arranque local

```bash
cp .env.example .env
docker compose up -d db db-test   # Postgres dev en :5434, test en :5433

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

alembic upgrade head
python scripts/seed.py --demo
uvicorn app.main:app --reload
```

Abre http://localhost:8000

`data/seed/establishments.json` ya está versionado. Para regenerarlo desde el
snapshot DEIS/MINSAL:

```bash
python scripts/fetch_establishments.py
```

> Los puertos publicados son **5434** para desarrollo y **5433** para tests.
> El servicio `app` de Docker usa `host.docker.internal:5434` para llegar a la
> base publicada. Si despliegas en otro entorno, cambia `DATABASE_URL` a
> `postgresql+psycopg://saluduoc:saluduoc@db:5432/saluduoc`.

### Cuentas demo

Se crean solo con `python scripts/seed.py --demo` y `ENV=dev|test`.

| Rol | Correo | Contraseña |
|-----|--------|------------|
| Paciente | `paciente@demo.cl` | `Demo123!` |
| Médico | `medico@demo.cl` | `Demo123!` |
| Admin | `admin@demo.cl` | `Demo123!` |

## Arranque con Docker

```bash
docker compose up -d db
docker compose build app
docker compose run --rm app alembic upgrade head
docker compose run --rm app python scripts/seed.py --demo
docker compose up app
```

La imagen ya incluye el seed de establecimientos. Si necesitas regenerarlo,
ejecuta `python scripts/fetch_establishments.py` en el host **antes** de
construir la imagen; los cambios hechos dentro de un contenedor `--rm` no
persisten.

El contenedor corre como usuario no root (UID 10001). El `Dockerfile` define un
`HEALTHCHECK` de liveness contra `/healthz`; `docker-compose.yml` usa `/readyz`
como readiness, que además consulta la base de datos.

## Tests

```bash
docker compose up -d db-test
TEST_DATABASE_URL=postgresql+psycopg://saluduoc:saluduoc@localhost:5433/saluduoc_test \
  pytest -q
```

Son **29 tests** contra PostgreSQL real:

- `test_auth.py` — registro, login, logout, `token_version`, rate limit y `/readyz`.
- `test_config.py` — guardas de producción.
- `test_rbac.py` — control de acceso por rol.
- `test_seed_data.py` — invariantes del seed (76 establecimientos, 19 sedes).
- `test_users.py` — perfiles y listado admin.

CI ejecuta `ruff check`, `alembic upgrade head`, `alembic check` y `pytest` con
PostgreSQL 16 como servicio.

## Seguridad

- Contraseñas con **Argon2**; nunca se devuelven en las respuestas.
- JWT **HS256** en cookie `saluduoc_token` (`HttpOnly`, `SameSite=Lax`,
  `Secure` configurable). El claim `ver` se compara con `users.token_version`.
- Logout incrementa `token_version`, por lo que invalida todos los tokens
  emitidos para ese usuario.
- RBAC en el backend (`require_roles`), no solo en la interfaz.
- Rate limit de login: 5 fallos por `IP + correo` por minuto, con `Retry-After`.
- Cabeceras de seguridad básicas en todas las respuestas.
- Guardas de producción: con `ENV` distinto de `dev`/`test`, el arranque falla
  si `SECRET_KEY` es débil o si `COOKIE_SECURE=false`.
- Las cuentas demo con contraseña fija solo se crean en `dev`/`test`.

## Estructura

```
app/        API, modelos, schemas, servicios, templates y estáticos
alembic/    migraciones
data/       sedes Duoc UC y seeds (establecimientos, rangos)
scripts/    generación de seed y carga inicial
tests/      pytest contra PostgreSQL
docs/       PRD, SPEC y ADRs
```

## Endpoints de la Fase 0

```
GET    /healthz                  # liveness
GET    /readyz                   # readiness (consulta la base de datos)
GET    /                         # página principal
GET    /login                    # página de login
GET    /registro                 # página de registro
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
GET    /api/v1/users/me
PATCH  /api/v1/users/me
GET    /api/v1/users          # solo admin
```

## Documentación

- [`docs/PRD.md`](docs/PRD.md) — alcance, usuarios, historias y fases.
- [`docs/SPEC.md`](docs/SPEC.md) — arquitectura, modelo de datos, API y despliegue.
- [`docs/ADRs/README.md`](docs/ADRs/README.md) — índice de decisiones de arquitectura.
- [`CHANGELOG.md`](CHANGELOG.md) — cambios notables por versión.

## Fuentes de datos

- Rangos y categorías: protocolo MINSAL de categorización de urgencias.
- Establecimientos: [Establecimientos de Salud – DEIS/MINSAL](https://datos.gob.cl/dataset/establecimientos-de-salud-vigentes)
  (snapshot 2026-10-20, CC0), filtrados alrededor de las sedes Duoc UC.
- Sedes Duoc UC: [duoc.cl](https://www.duoc.cl/nosotros/donde-estamos/sedes).

## Licencia

Distribuido bajo licencia [MIT](LICENSE).
