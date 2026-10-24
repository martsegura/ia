# ADR 0004 — Seed de establecimientos desde DEIS alrededor de sedes Duoc

## Contexto
Se necesitan establecimientos reales con coordenadas para calcular distancias.

## Decisión
Usar el dataset abierto DEIS/MINSAL (snapshot 2026-10-20, CC0) y filtrar los más
cercanos a cada sede Duoc UC, priorizando urgencias. El script es reproducible y
guarda código MINSAL, fuente y fecha.

## Consecuencias
- Datos verificables y actualizables.
- El snapshot puede quedar desactualizado; se debe reejecutar el script.
- La asignación por cercanía a la sede es una aproximación, no una derivación
  clínica.
