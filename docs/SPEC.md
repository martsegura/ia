# Especificación técnica — SaluDuoc

**Versión:** 0.1 (Fase 0)

## 1. Arquitectura

```
Navegador (HTML/CSS/JS vanilla)
        │  fetch + cookie HttpOnly
        ▼
FastAPI  ──►  Servicios (auth, triage, distancia, cola)
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
├── main.py                 # FastAPI, rutas de páginas, /healthz
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
`id UUID PK`, `email unique`, `password_hash`, `role` (`patient|doctor|admin`),
`full_name`, `is_active`, `created_at`, `updated_at`.

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
`is_informational`, `version`, `fuente`, `is_active`, timestamps.

### Planificado (Fases 1–4)

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

1. `POST /auth/login` valida Argon2 y firma un JWT HS256 con `sub` y `role`.
2. El token se envía en la cookie `saluduoc_token` (`HttpOnly`, `SameSite=Lax`,
   `Secure` según configuración, `Max-Age` = TTL).
3. `get_current_user` lee la cookie, valida el JWT y carga el usuario activo.
4. `require_roles(*roles)` protege endpoints por rol.
5. Logout elimina la cookie.

Rate limit de login: 5 fallos por IP por minuto (en memoria, un proceso). En
producción con varios workers se debe usar Redis.

## 6. API

### Fase 0 (implementada)

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| GET | `/healthz` | público | Estado del servicio |
| POST | `/api/v1/auth/register` | público | Registro de paciente |
| POST | `/api/v1/auth/login` | público | Login + cookie |
| POST | `/api/v1/auth/logout` | autenticado | Cierra sesión |
| GET | `/api/v1/auth/me` | autenticado | Usuario actual |
| GET | `/api/v1/users/me` | autenticado | Perfil propio |
| PATCH | `/api/v1/users/me` | autenticado | Actualiza perfil |
| GET | `/api/v1/users` | admin | Lista paginada |

### Planificado

```
GET/POST  /api/v1/patients/me/vitals
POST      /api/v1/patients/me/vitals/upload
POST      /api/v1/triage/assess
GET       /api/v1/triage/me/latest
GET       /api/v1/triage/{id}
POST      /api/v1/triage/{id}/reclassify
GET       /api/v1/establishments?lat&lng&emergency
GET       /api/v1/queue
GET       /api/v1/queue/me
POST      /api/v1/queue/{id}/call|start|attend|leave
POST      /api/v1/queue/{id}/reclassify
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

## 8. Motor de triage (Fase 2)

```
datos validados
   │
   ├─► 1. banderas rojas ──► C1 / C2 (override)
   │
   ├─► 2. score ponderado por desviación de rangos
   │        + edad + síntomas + comorbilidades
   │        ──► C3 / C4 / C5
   │
   └─► 3. salvaguardas: datos faltantes ⇒ mínimo C3
```

- Reglas y umbrales en base de datos, versionados y explicables.
- Se devuelve `triggered_rules`, `score` y `rationale`.
- El médico puede reclasificar con motivo obligatorio; se guarda
  `final_category` y `override_reason`.
- La app nunca da de alta ni diagnostica.

## 9. Seed de establecimientos

`scripts/fetch_establishments.py`:

1. Descarga el CSV DEIS/MINSAL (5.181 establecimientos vigentes, CC0).
2. Lee `data/campuses.json` con las sedes Duoc UC geocodificadas.
3. Filtra establecimientos a ≤3 km (amplía a 6/12/25 km si faltan).
4. Prioriza urgencias (hospital, clínica, SAPU, SAR, SUR), luego CESFAM.
5. Guarda 4 por sede, deduplicados, con código MINSAL, fuente y snapshot.

Resultado actual: **76 establecimientos** para 19 sedes.

## 10. Distancia (Fase 3)

Haversine en el backend:

```
d = 2R · asin(√(sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)))
R = 6371 km
```

`GET /establishments?lat&lng` ordena por distancia ascendente. Las coordenadas
del paciente no se persisten por defecto.

## 11. Cola (Fase 4)

Máquina de estados:

```
waiting ──► called ──► in_attention ──► attended
   │            │
   └────────────┴──► left
```

Orden: categoría (C1→C5) y luego `created_at`. El paciente elige el
establecimiento antes del triage; la entrada se crea automáticamente al calcular
la categoría.

## 12. Configuración

Variables en `.env`:

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Cadena SQLAlchemy/psycopg |
| `SECRET_KEY` | Firma JWT (≥32 caracteres) |
| `ENV` | `dev` / `prod` |
| `COOKIE_SECURE` | `true` en HTTPS |
| `TOKEN_TTL_MINUTES` | Vida de la sesión |
| `RATE_LIMIT_LOGIN` | Intentos por minuto |
| `TEST_DATABASE_URL` | Base para pytest |

## 13. Tests

- Unitarios: seguridad, rate limit, serialización.
- Integración: registro, login, logout, `/me`, RBAC, perfil.
- Base de datos PostgreSQL real (servicio `db-test` en 5433).
- CI: PostgreSQL 16 como service, `alembic upgrade head`, `pytest`, `ruff`.

## 14. Despliegue

- `docker compose up -d db db-test`
- `alembic upgrade head`
- `python scripts/fetch_establishments.py`
- `python scripts/seed.py`
- `uvicorn app.main:app`

En producción: HTTPS, `COOKIE_SECURE=true`, `SECRET_KEY` fuerte, Postgres
gestionado, backups y rate limit distribuido.
