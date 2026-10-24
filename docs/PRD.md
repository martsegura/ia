# PRD — SaluDuoc

**Versión:** 0.1.0 (Fase 0)
**Fecha:** 2026-10-24
**Estado:** Aprobado para implementación por fases

> **Alcance de la Fase 0:** están implementados el registro/login (4.1), el
> perfil del paciente (4.2), la actualización de especialidad del médico y el
> listado de usuarios para admin (gestión de usuarios). La carga de signos
> vitales (4.3), el triage (4.4), la distancia en la interfaz (4.5), la cola
> (4.6) y el CRUD de administración (4.7) corresponden a las fases 1–5 y aún no
> están implementados.

## 1. Problema y oportunidad

La comunidad Duoc UC no cuenta con una herramienta simple para interpretar los
datos que entregan los relojes inteligentes (presión arterial, saturación de
oxígeno, frecuencia cardíaca y calidad de sueño) ni para saber qué tan urgente
puede ser una consulta y dónde atenderse.

SaluDuoc propone un flujo único: registrar los datos, compararlos con rangos de
normalidad, obtener una **pre-categorización de urgencia C1–C5** y ver los
establecimientos de salud cercanos a cada sede, con una cola de espera visible
para el médico.

> SaluDuoc es un prototipo de apoyo. **No es un dispositivo médico, no emite
> diagnósticos y no reemplaza la evaluación de un profesional.**

## 2. Objetivos

- Centralizar los datos de wearables y del formulario clínico del paciente.
- Traducir esos datos a una categoría de urgencia explicable (C1–C5).
- Ordenar establecimientos de salud por distancia a la sede Duoc UC.
- Entregar al médico una cola priorizada por color y gravedad.
- Mantener trazabilidad y auditoría de cada clasificación y cambio.

### No objetivos (MVP)

- Diagnóstico automático o prescripción.
- Integración real con fabricantes de wearables.
- Mapas interactivos, notificaciones push/SMS, telemedicina.
- Historia clínica completa, recetas, facturación.
- Población pediátrica (el MVP es para adultos de 18 años o más).

## 3. Usuarios y roles

| Rol | Necesidades |
|-----|-------------|
| **Paciente** | Registrarse, completar su perfil, subir datos del reloj, responder el formulario, ver su categoría, elegir establecimiento y seguir su posición en la cola. |
| **Médico** | Ver la cola de su establecimiento ordenada por gravedad, revisar la ficha y los signos vitales, llamar al paciente, atenderlo, finalizar y reclasificar con motivo. |
| **Admin** | Gestionar establecimientos, rangos de normalidad y reglas de triage; administrar usuarios. |

## 4. Historias de usuario y criterios de aceptación

### 4.1 Registro e inicio de sesión

**Como** paciente **quiero** crear una cuenta e iniciar sesión **para** acceder a
mis datos de salud.

- Registro con nombre, correo y contraseña (mínimo 8 caracteres y un número).
- El correo es único; un duplicado responde `409`.
- Login correcto deja una cookie HttpOnly `saluduoc_token` y responde `200`.
- Credenciales inválidas responden `401`; 5 fallos por minuto por IP+correo
  bloquean con `429` (un login exitoso de otra cuenta no limpia el bloqueo).
- Logout invalida los tokens emitidos y `/api/v1/auth/me` vuelve a responder `401`.
- Los errores de validación no reflejan la contraseña enviada.
- En producción no se permite un `SECRET_KEY` débil ni cookies sin `Secure`.

### 4.2 Perfil del paciente

**Como** paciente **quiero** registrar edad, sexo, peso, talla, comorbilidades,
medicamentos y contacto de emergencia **para** que el triage sea más preciso.

- `GET/PATCH /api/v1/users/me` devuelve y actualiza el perfil.
- El listado admin muestra datos de cuenta, no el perfil clínico completo.
- Los campos son opcionales, pero si faltan datos críticos el triage aplica un
  mínimo conservador de C3.
- Un paciente no puede ver datos de otro paciente.

### 4.3 Carga de signos vitales

**Como** paciente **quiero** subir el JSON de mi reloj o ingresar los valores
manualmente **para** mantener mi historial.

- JSON aceptado con: timestamp, FC, presión sistólica/diastólica, SpO2,
  calidad y horas de sueño.
- El backend valida rangos plausibles y rechaza valores imposibles.
- El paciente se obtiene del token, nunca del archivo.
- Se conserva el payload original para auditoría.

### 4.4 Triage C1–C5

**Como** paciente **quiero** saber mi categoría de urgencia **para** decidir cómo
actuar.

- El motor evalúa primero banderas rojas (C1/C2) y luego un score ponderado
  (C3–C5), usando rangos MINSAL versionados.
- Devuelve categoría, color, reglas activadas y explicación.
- C1/C2 muestran una instrucción de acudir a urgencias o llamar al 131.
- Si faltan datos o hay ambigüedad, la categoría mínima es C3.
- El médico puede reclasificar dejando motivo; se audita.
- La calidad de sueño es informativa y no sube la categoría por sí sola.

### 4.5 Establecimientos y distancia

**Como** paciente **quiero** ver los establecimientos ordenados por distancia
**para** elegir dónde atenderme.

- La lista se calcula con Haversine desde la ubicación del navegador o desde la
  sede Duoc UC seleccionada.
- Se puede filtrar por urgencias.
- Los datos provienen del dataset DEIS/MINSAL (snapshot 2026-10-20), filtrado
  alrededor de las sedes Duoc UC.
- Si el paciente niega la geolocalización, puede elegir una sede manualmente.

### 4.6 Cola de espera

**Como** paciente **quiero** elegir un establecimiento antes del triage y entrar
automáticamente a su cola **para** saber cuándo me atenderán.

**Como** médico **quiero** ver la cola de mi establecimiento **para** atender
primero a los casos más graves.

- La entrada se crea automáticamente al calcular el triage en el establecimiento
  elegido.
- Orden: categoría (C1 primero) y luego hora de llegada.
- Estados: `waiting → called → in_attention → attended`; también `left` y
  `reclassified`.
- La vista del médico muestra color, tiempo de espera, signos alterados y
  síntomas.
- El paciente ve su posición y estado (polling cada 10 s en el MVP).

### 4.7 Pantallas por rol

**Como** usuario **quiero** entrar a mi panel según mi rol **para** ver la
información y acciones que me corresponden.

- Después del login, el paciente va a `/paciente`, el médico a `/medico` y el
  admin a `/admin`.
- Sin sesión, los paneles redirigen a `/login`.
- Un rol no puede abrir el panel de otro rol; se redirige al suyo.
- El paciente ve su perfil; el médico ve su establecimiento y la cola (vacía en
  Fase 0); el admin ve métricas, establecimientos y usuarios recientes.

### 4.8 Administración

**Como** admin **quiero** gestionar establecimientos, rangos y reglas **para**
mantener el sistema actualizado.

- CRUD de establecimientos, rangos de normalidad y reglas de triage.
- Los rangos y reglas tienen versión, fuente y vigencia.
- Solo el rol admin accede a estos endpoints.

## 5. Reglas de triage (referencia)

| Categoría | Color | Tiempo objetivo inicial |
|-----------|-------|--------------------------|
| C1 — riesgo vital inminente | Rojo | Inmediato |
| C2 — emergencia evidente | Rojo | ≤ 30 min |
| C3 — urgencia con potencial riesgo | Amarillo | ≤ 60 min |
| C4 — urgencia mediata | Verde | ≤ 120 min |
| C5 — consulta general | Verde | ≤ 180 min |

Los tiempos son configurables porque los protocolos locales varían.

Rangos iniciales (adulto, MINSAL, a validar por un profesional):

| Métrica | Normal | Leve | Moderado | Crítico |
|---------|--------|------|----------|---------|
| FC (lpm) | 60–100 | 50–59 / 101–120 | 40–49 / 121–150 | <40 / >150 |
| PAS (mmHg) | 90–119 | — / 120–139 | 80–89 / 140–179 | <80 / ≥180 |
| PAD (mmHg) | 60–79 | — / 80–89 | 50–59 / 90–119 | <50 / ≥120 |
| SpO2 (%) | ≥95 | 92–94 | 90–91 | <90 (C2), <85 (C1) |
| Sueño (0–100) | ≥70 | 50–69 | <50 | — (informativo) |

## 6. Requisitos no funcionales

- **Seguridad:** Argon2, JWT HttpOnly, HTTPS en producción, rate limit, RBAC,
  auditoría de accesos y cambios, validación estricta de archivos.
- **Privacidad:** datos de salud sensibles; consentimiento, minimización,
  retención definida y derecho de eliminación.
- **Rendimiento:** respuesta de triage < 300 ms para un registro; lista de
  establecimientos < 500 ms con el seed actual.
- **Usabilidad:** interfaz en español, responsive, colores accesibles y claros.
- **Disponibilidad:** despliegue contenedorizado, liveness `/healthz` y
  readiness `/readyz` (este último comprueba la base de datos).
- **Mantenibilidad:** tests automatizados, migraciones Alembic, documentación.

## 7. Marco legal y ético

- Ley 19.628 sobre protección de la vida privada.
- Ley 21.719 sobre protección de datos personales (nueva normativa).
- Ley 20.584 sobre derechos y deberes de los pacientes.
- Los datos de salud son sensibles: se requiere consentimiento informado y
  medidas de seguridad reforzadas.
- Descargo visible en la interfaz y en cada resultado de triage.

## 8. Métricas de éxito

- Tiempo desde el registro hasta la primera categorización < 3 minutos.
- 100% de las categorizaciones con explicación y reglas activadas.
- 0 accesos de pacientes a datos de otros pacientes.
- Cobertura de tests del backend ≥ 80% en las fases 1–4.
- 3 establecimientos con urgencia por cada una de las 19 sedes en el seed.
- 29 tests de backend en verde en la Fase 0.

## 9. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Falsa sensación de seguridad por el triage automático | Descargo, mínimos conservadores, validación médica obligatoria |
| Rangos MINSAL desactualizados o mal interpretados | Versionado, fuente explícita, revisión por profesional |
| Datos de wearable imprecisos | Validación de rangos plausibles y advertencia al usuario |
| Filtración de datos de salud | Cookie HttpOnly, RBAC, auditoría, cifrado en tránsito |
| Dependencia de un dataset externo | Snapshot local y script reproducible con fuente |

## 10. Fases

| Fase | Alcance | Estado |
|------|---------|--------|
| 0 | Scaffold, Docker, Alembic, auth, RBAC, seed base, CI | Completada |
| 1 | Perfil, carga manual y JSON de wearables | Completada |
| 2 | Rangos MINSAL y motor de triage C1–C5 | Completada |
| 3 | Establecimientos y distancia en la UI | Parcial (API y selector; falta orden por geolocalización) |
| 4 | Cola por establecimiento y vista del médico | Completada |
| 5 | Gestión admin completa, pulido y despliegue | Pendiente |
