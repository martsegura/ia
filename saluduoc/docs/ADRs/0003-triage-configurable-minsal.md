# ADR 0003 — Triage configurable basado en MINSAL

## Contexto
El triage C1–C5 combina signos vitales, síntomas y criterios clínicos. Los
tiempos y umbrales varían entre establecimientos y protocolos locales.

## Decisión
Motor en dos capas: banderas rojas con override (C1/C2) y score ponderado
(C3–C5). Rangos y reglas se guardan versionados en la base de datos con fuente
MINSAL. Toda clasificación es explicable y el médico puede reclasificar con
motivo.

## Consecuencias
- El admin puede actualizar umbrales sin desplegar código.
- Se necesita validación clínica periódica.
- El sistema es una ayuda, no un dispositivo médico.
