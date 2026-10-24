# ADR 0006 — Guardas de producción y versión de sesión

## Contexto
La revisión de Fase 0 detectó que un `SECRET_KEY` de ejemplo, `COOKIE_SECURE`
desactivado o las cuentas demo podían llegar a producción. Además, el logout
solo borraba la cookie y el token copiado seguía vigente.

## Decisión
- El arranque en `ENV=prod` falla con `SECRET_KEY` débil (<32 caracteres o valor
  de ejemplo) o con `COOKIE_SECURE=false`.
- Las cuentas demo requieren `python scripts/seed.py --demo` y solo se permiten
  en `dev|test`.
- `users.token_version` se incluye en el JWT (`ver`); el logout lo incrementa.
- Rate limit de login por `IP + email` con `Retry-After`.
- Cabeceras de seguridad básicas y `/readyz` para comprobar la base de datos.

## Consecuencias
- Un despliegue mal configurado falla al arrancar en lugar de quedar expuesto.
- El logout invalida todas las sesiones del usuario (aceptable en el MVP).
- Para sesiones por dispositivo se necesitará `jti` y una denylist.
