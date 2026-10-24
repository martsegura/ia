# ADR 0002 — JWT en cookie HttpOnly

## Contexto
La app maneja datos de salud sensibles y debe evitar el robo de tokens por XSS.

## Decisión
JWT HS256 firmado en el servidor, enviado en cookie `HttpOnly`, `SameSite=Lax`,
`Secure` en producción. Roles en el claim `role` y validación adicional contra
la base de datos.

## Alternativas
- JWT en `localStorage` + `Authorization: Bearer`.
- Sesiones server-side con almacén externo.

## Consecuencias
- El JavaScript no puede leer el token.
- Se requiere protección CSRF si se agregan formularios cross-site.
- En varios dominios haría falta configurar CORS y cookies de terceros.
