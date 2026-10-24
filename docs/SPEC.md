# Especificación técnica — SaluDuoc

**Versión:** 0.1.0 (Fase 0)
**Estado:** Fase 0 implementada. Las secciones marcadas como planificadas
corresponden a las fases 1–5 y no deben interpretarse como funcionalidad actual.

## 1. Arquitectura

```
Navegador (HTML/CSS/JS vanilla)
        │  fetch + cookie HttpOnly
        ▼
FastAPI  ──►  Servicios (auth implementado; triage, distancia y cola planificados)
   │                 │
   │                 ▼
   └──────────►  PostgreSQL 16
                     ▲
        Scripts de seed (DEIS/MINSAL, rangos, demo)
```

Un solo servicio FastAPI sirve la API y los archivos estáticos/templates. No hay
SPA ni bundler. PostgreSQL es la fuente de verdad.

## 2. Stack

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3.13 (Docker) / ≥3.12 |
| API | FastAPI + Pydantic v2 |
| ORM | SQLAlchemy 2.0 |
| Migraciones | Alembic |
| Base de datos | PostgreSQL 16 |
| Auth | JWT (PyJWT) en cookie HttpOnly, Argon2 (`pwdlib`) |
| Frontend | Jinja2 + HTML + CSS + JS vanilla |
| Tests | pytest + httpx/TestClient + PostgreSQL |
| CI | GitHub Actions |
| Contenedores | Docker + Docker Compose |

## 3. Estructura del proyecto

```
app/
├── main.py                 # FastAPI, rutas de páginas, /healthz y /readyz
├── core/config.py          # Settings (pydantic-settings)
├── core/security.py        # Argon2 + JWT
├── db/base.py              # Base declarativa y naming convention
├── db/session.py           # engine, SessionLocal, get_db
├── models/                 # User, PatientProfile, DoctorProfile,
│                           # Establishment, NormalRange
├── schemas/                # Pydantic de entrada/salida
├── api/deps.py             # get_current_user, require_roles
├── api/v1/auth.py          # register, login, logout, me
├── api/v1/users.py         # perfil y listado admin
├── services/               # rate limit, serialización
├── templates/              # base, index, login, registro
└── static/                 # CSS y JS
alembic/                    # migraciones
data/                       # campuses.json + seed
scripts/                    # fetch_establishments.py, seed.py
tests/                      # pytest
```

## 4. Modelo de datos

### Implementado en Fase 0

**users**
`id UUID PK`, `email unique`, `password_hash`, `role` (`patient|doctor|admin` en
la API; `PATIENT|DOCTOR|ADMIN` en la base con check constraint), `full_name`,
`is_active`, `token_version`, `created_at`, `updated_at`.

**patient_profiles**
`id UUID PK`, `user_id FK unique`, `rut`, `birth_date`, `sexo`, `peso_kg`,
`talla_cm`, `comorbilidades JSON`, `medicamentos JSON`, `es_embarazada`,
`contacto_emergencia`, timestamps.

**doctor_profiles**
`id UUID PK`, `user_id FK unique`, `establecimiento_id FK`, `especialidad`,
timestamps.

**establishments**
`id UUID PK`, `codigo` (código MINSAL, unique), `nombre`, `tipo`, `direccion`,
`comuna`, `region`, `lat`, `lng`, `telefono`, `tiene_urgencia`, `servicios JSON`,
`sede_duoc`, `fuente`, `fecha_snapshot`, `is_active`, timestamps.

**normal_ranges**
`id UUID PK`, `metric`, `label`, `unit`, `normal_min/max`, `mild_low/high`,
`moderate_low/high`, `critical_low/high`, `edad_min/max`, `sexo`,
`is_informational`, `version`, `fuente`, `is_active`, timestamps. Restricción
`unique (metric, version)`.

### Planificado (Fases 1–5)

- `vital_records`: paciente, timestamp, fuente, dispositivo, FC, PAS, PAD, SpO2,
  sueño (score/horas), payload crudo JSON.
- `symptom_reports`: paciente, vital_record, síntomas JSON, dolor 0–10, inicio,
  notas.
- `triage_assessments`: paciente, vital_record, categoría, color, score, reglas
  activadas JSON, explicación, versión del algoritmo, categoría final del médico,
  motivo del cambio.
- `queue_entries`: assessment, establecimiento, paciente, categoría, color,
  estado, timestamps, médico asignado, notas.
- `audit_log`: usuario, acción, entidad, datos, timestamp.

## 5. Autenticación y autorización

1. `POST /api/v1/auth/register` crea el paciente y deja la sesión iniciada
   emitiendo la misma cookie HttpOnly.
2. `POST /api/v1/auth/login` valida Argon2 y firma un JWT HS256 con `sub`,
   `role` y `ver`.
3. El token se envía en la cookie `saluduoc_token` (`HttpOnly`, `SameSite=Lax`,
   `Secure` según configuración, `Max-Age` = TTL). Incluye `ver` (versión de
   sesión).
4. `get_current_user` lee la cookie, valida el JWT, comprueba `ver` contra
   `users.token_version` y carga el usuario activo. El rol efectivo se lee de la
   base de datos, no se confía en el claim del token.
5. `require_roles(*roles)` protege endpoints por rol.
6. Logout incrementa `token_version` (invalida todos los tokens emitidos) y
   elimina la cookie.

Los errores de validación de auth se devuelven en español y sin ecoar la
contraseña. Rate limit de login: 5 fallos por `IP + email` por minuto (en
memoria, un proceso). En producción con varios workers se debe usar Redis. La respuesta
`429` incluye `Retry-After`.

Con `ENV` distinto de `dev`/`test` el arranque falla si `SECRET_KEY` es
débil/menor a 32 caracteres o si `COOKIE_SECURE=false`. Las cuentas demo del
seed solo se crean con `--demo` y `ENV=dev|test`.

## 6. API

### Fase 0 (implementada)

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| GET | `/healthz` | público | Liveness del proceso |
| GET | `/readyz` | público | Readiness (consulta la base de datos) |
| POST | `/api/v1/auth/register` | público | Registro de paciente |
| POST | `/api/v1/auth/login` | público | Login + cookie |
| POST | `/api/v1/auth/logout` | autenticado | Cierra sesión |
| GET | `/api/v1/auth/me` | autenticado | Usuario actual |
| GET | `/api/v1/users/me` | autenticado | Perfil propio |
| PATCH | `/api/v1/users/me` | autenticado | Actualiza perfil |
| GET | `/api/v1/users` | admin | Lista paginada (sin perfiles clínicos) |

### Páginas (Fase 0)

| Ruta | Rol | Descripción |
|------|-----|-------------|
| `/` | público | Landing; si hay sesión muestra acceso al panel |
| `/login` | público | Login; redirige al panel si ya hay sesión |
| `/registro` | público | Registro de paciente con auto-login |
| `/paciente` | patient | Perfil, estado y próximos pasos |
| `/medico` | doctor | Cola placeholder y establecimiento asignado |
| `/admin` | admin | Métricas, establecimientos y usuarios recientes |
| `/dashboard` | autenticado | Redirige al panel según el rol |

Las páginas se protegen en el servidor: sin sesión redirigen a `/login`; con un
rol distinto redirigen al panel correspondiente (HTTP 303).

### Fases 1–2 y cola (implementadas)

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| POST | `/api/v1/vitals` | patient | Formulario manual + triage + cola |
| POST | `/api/v1/vitals/upload` | patient | JSON de wearable + triage |
| GET | `/api/v1/vitals/me` | patient | Historial de vitales |
| GET | `/api/v1/vitals/symptoms` | público | Catálogo de síntomas |
| GET | `/api/v1/triage/me/latest` | patient | Última evaluación |
| GET | `/api/v1/triage/{id}` | dueño/médico/admin | Detalle |
| GET | `/api/v1/establishments` | autenticado | Lista, distancia opcional |
| GET | `/api/v1/queue` | doctor/admin | Cola activa |
| GET | `/api/v1/queue/me` | patient | Entrada activa propia |
| POST | `/api/v1/queue/{id}/status` | doctor/admin | Transición de estado |

### Pendiente (Fase 5)

```
POST      /api/v1/triage/{id}/reclassify
CRUD      /api/v1/admin/establishments|normal-ranges|triage-rules
```

## 7. JSON de wearables (Fase 1)

```json
{
  "device": "SmartWatch Demo",
  "records": [
    {
      "timestamp": "2026-10-24T08:00:00-03:00",
      "heart_rate_bpm": 78,
      "blood_pressure": { "systolic": 118, "diastolic": 76 },
      "oxygen_saturation_pct": 97,
      "sleep_quality": { "score": 82, "hours": 7.5 }
    }
  ]
}
```

Validaciones: rangos plausibles, timestamps no futuros, tamaño máximo, paciente
tomado del token. El payload original se guarda en `vital_records.raw_payload`.

## 8. Motor de triage (implementado)

```
datos validados
   │
   ├─► 1. banderas rojas ──► C1 / C2 (override)
   │      SpO2 <85 (C1), SpO2 85–89 (C2), FC <40 o >150 (C2),
   │      PAS <80 o ≥180 (C2), PAD ≥120 (C2), dolor ≥8 (C2),
   │      síntomas C1/C2 y dolor torácico inestable
   │
   ├─► 2. severidad por banda (normal/leve/moderado/crítico)
   │      + síntomas moderados + dolor + edad + comorbilidades
   │      ──► C3 / C4 / C5
   │
   └─► 3. salvaguardas: datos faltantes ⇒ mínimo C3
```

- Umbrales en `normal_ranges`, versionados y explicables.
- Se devuelve `triggered_rules`, `score` y `rationale`.
- Colores: C1/C2 rojo, C3 amarillo, C4/C5 verde.
- La app nunca da de alta ni diagnostica; el médico confirma.

## 9. Seed de establecimientos

`scripts/fetch_establishments.py`:

1. Descarga el CSV DEIS/MINSAL (snapshot 2026-10-20, CC0). El archivo tiene
   5.782 filas; 5.354 figuran como vigentes y 5.022 quedan como candidatos tras
   excluir cerrados, registros sin coordenadas y pediátricos/maternales/dentales.
2. Lee `data/campuses.json` con las 19 sedes Duoc UC geocodificadas.
3. Descarta pediátricos, maternales y dentales (MVP adulto general).
4. Busca candidatos hasta 25 km y prioriza urgencias (hospital, clínica, SAPU,
   SAR, SUR); garantiza 3 urgencias por sede y completa hasta 4 con CESFAM u
   otros no urgentes.
5. Guarda 4 por sede, deduplicados, con código MINSAL, fuente y snapshot.

Resultado actual: **76 establecimientos** para 19 sedes: **57 con urgencia**
(3 por sede) y 19 CESFAM de complemento. El script falla si una sede no alcanza
el mínimo de 3 urgencias.

`scripts/seed.py` es idempotente: actualiza los establecimientos y rangos
existentes, y desactiva los establecimientos DEIS que ya no pertenecen al
snapshot actual.

## 10. Distancia (Fase 3)

Haversine en el backend:

```
d = 2R · asin(√(sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)))
R = 6371 km
```

`GET /establishments?lat&lng` ordena por distancia ascendente. Las coordenadas
del paciente no se persisten por defecto.

## 11. Cola (implementada)

Máquina de estados:

```
waiting ──► called ──► in_attention ──► attended
   │            │             │
   └────────────┴─────────────┴──► left
```

Orden: prioridad (C1=1 … C5=5) y luego `created_at`. El paciente elige el
establecimiento antes del triage; la entrada se crea automáticamente al calcular
la categoría. El médico ve solo la cola de su establecimiento y puede llamar,
iniciar, finalizar o retirar. Al crear una nueva solicitud, las anteriores
activas del mismo paciente se cierran como `left`.

## 12. Configuración

Variables en `.env`:

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Cadena SQLAlchemy/psycopg (dev: `:5434`; Docker: `db:5432`) |
| `SECRET_KEY` | Firma JWT; ≥32 caracteres y no de ejemplo fuera de `dev`/`test` |
| `ENV` | `dev` / `test` / `prod` (cualquier valor fuera de `dev`/`test` activa las guardas) |
| `COOKIE_NAME` | Nombre de la cookie (por defecto `saluduoc_token`) |
| `COOKIE_SECURE` | `true` obligatorio fuera de `dev`/`test` |
| `TOKEN_TTL_MINUTES` | Vida de la sesión |
| `RATE_LIMIT_LOGIN` | Intentos fallidos permitidos por minuto |
| `TEST_DATABASE_URL` | Base para pytest (servicio `db-test` en `:5433`) |

## 13. Tests

- **29 tests** contra PostgreSQL real (servicio `db-test` en `:5433`):
  - `test_auth.py` (14): registro, login, logout con `token_version`, rate limit,
    cookie HttpOnly, `/healthz`, `/readyz` y errores 422 sin eco de contraseñas.
  - `test_config.py` (4): guardas de producción.
  - `test_rbac.py` (4): acceso por rol.
  - `test_seed_data.py` (2): invariantes del seed (4 por sede, ≥3 urgencias, sin
    pediátricos/dentales).
  - `test_users.py` (5): perfiles y listado admin.
- CI: PostgreSQL 16 como service, `alembic upgrade head`, `alembic check`,
  `pytest` y `ruff`.

## 14. Despliegue

Desarrollo:

- `docker compose up -d db db-test` (Postgres dev en `:5434`, test en `:5433`)
- `alembic upgrade head`
- `python scripts/fetch_establishments.py` (opcional si ya existe el JSON)
- `python scripts/seed.py --demo` (las cuentas demo solo en `dev`/`test`)
- `uvicorn app.main:app --reload`

Docker:

- `docker compose build app`
- `docker compose run --rm app alembic upgrade head`
- `docker compose run --rm app python scripts/seed.py --demo`
- `docker compose up app`

La imagen corre como usuario no root (UID 10001) y define un `HEALTHCHECK`
contra `/healthz`. El compose usa `/readyz` como readiness. El compose de
desarrollo publica la base en `:5434` y la app accede por
`host.docker.internal:5434`; en un despliegue normal usar
`postgresql+psycopg://saluduoc:saluduoc@db:5432/saluduoc`.

En producción: HTTPS, `COOKIE_SECURE=true`, `SECRET_KEY` fuerte, Postgres
gestionado, backups y rate limit distribuido.
