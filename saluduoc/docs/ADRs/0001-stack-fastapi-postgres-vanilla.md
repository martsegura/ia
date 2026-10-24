# ADR 0001 — FastAPI + PostgreSQL + frontend vanilla

## Contexto
Se necesita una app web de salud con backend Python, base relacional y una
interfaz simple para pacientes y médicos.

## Decisión
FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 16. Frontend HTML/CSS/JS vanilla
servido por FastAPI con Jinja2, sin framework ni bundler.

## Consecuencias
- Desarrollo rápido y una sola unidad desplazable.
- Menos dependencias y curva de aprendizaje.
- El frontend requiere más código manual para estado y renderizado.
- Migrar a una SPA es posible manteniendo la API.
