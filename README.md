# SaluDuoc

Aplicación web de apoyo a la categorización de urgencia (triage C1–C5) y
monitoreo de signos vitales para la comunidad Duoc UC.

> **Aviso:** SaluDuoc es un prototipo de apoyo a la pre-clasificación. No es un
> dispositivo médico y no reemplaza la evaluación de un profesional de la salud.

**Estado:** Fase 0 completada (scaffold, base de datos, auth, RBAC, seed base y CI).

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2
- **Base de datos:** PostgreSQL 16
- **Frontend:** HTML + CSS + JavaScript vanilla, servido por FastAPI
- **Auth:** JWT en cookie HttpOnly + Argon2, roles `patient`, `doctor`, `admin`
- **Tests:** pytest + httpx contra PostgreSQL

## Arranque local

```bash
cp .env.example .env
docker compose up -d db db-test   # Postgres dev en :5434, test en :5433

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

alembic upgrade head
python scripts/fetch_establishments.py   # genera data/seed/establishments.json
python scripts/seed.py

uvicorn app.main:app --reload
```

Abre http://localhost:8000

> El servicio `app` de Docker usa `host.docker.internal:5434` para llegar a la
> base publicada. Si despliegas en otro entorno, cambia `DATABASE_URL` a
> `postgresql+psycopg://saluduoc:saluduoc@db:5432/saluduoc`.

### Cuentas demo

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
docker compose run --rm app python scripts/fetch_establishments.py
docker compose run --rm app python scripts/seed.py
docker compose up app
```

## Tests

```bash
docker compose up -d db-test
TEST_DATABASE_URL=postgresql+psycopg://saluduoc:saluduoc@localhost:5433/saluduoc_test pytest -q
```

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
GET    /healthz
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
GET    /api/v1/users/me
PATCH  /api/v1/users/me
GET    /api/v1/users          # solo admin
```

## Documentación

- `docs/PRD.md` — alcance, usuarios e historias
- `docs/SPEC.md` — arquitectura, modelo de datos y API
- `docs/ADRs/` — decisiones de arquitectura

## Fuentes de datos

- Rangos y categorías: protocolo MINSAL de categorización de urgencias.
- Establecimientos: [Establecimientos de Salud – DEIS/MINSAL](https://datos.gob.cl/dataset/establecimientos-de-salud-vigentes)
  (snapshot 2026-10-20, CC0), filtrados alrededor de las sedes Duoc UC.
- Sedes Duoc UC: [duoc.cl](https://www.duoc.cl/nosotros/donde-estamos/sedes).
