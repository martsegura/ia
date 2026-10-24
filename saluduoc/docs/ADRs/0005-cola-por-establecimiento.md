# ADR 0005 — Cola por establecimiento y creación desde el triage

## Contexto
Varios establecimientos atienden simultáneamente y cada médico debe ver solo su
cola.

## Decisión
La cola pertenece a un establecimiento. El paciente elige el establecimiento
antes de calcular el triage y la entrada se crea automáticamente con la
categoría y el color resultantes. Orden por categoría y hora de llegada.

## Consecuencias
- Aislamiento natural por establecimiento y RBAC.
- El paciente debe elegir sede/establecimiento antes de clasificarse.
- Se necesita definir derivaciones entre establecimientos en una fase futura.
