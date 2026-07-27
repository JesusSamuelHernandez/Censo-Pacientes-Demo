# Seguimiento reporte SAST/SCA — 2026-07-27

Comparación entre los hallazgos del reporte **"Reevaluacion SAST/SCA: Censo de Pacientes"** (corte 2026-07-22) y el estado real del código en `main` al 2026-07-27, incluyendo revisión de los stashes pendientes en la rama `carolinacc`.

## Nota sobre PRs recientes

Varios PRs de "fix" de seguridad mergeados a `main` en los días previos a este corte fueron **merges vacíos** (sin ningún cambio de archivo, solo el mensaje "Initial plan"): `#40`, `#41` (react-router-csrf), `#42`, `#47`, `#48` (sheetjs-redos), `#49` (sheetjs-prototype-pollution). Vale la pena investigar por qué el agente automatizado los mergeó sin contenido.

## Hallazgos SAST

| # | Hallazgo | Severidad | Estado | Evidencia |
|---|---|---|---|---|
| SAST-01 | BOLA en lecturas de PHI/PII (pacientes, médicos) | High | ✅ Corregido | commit `568fc40`: `_verificar_acceso_paciente` aplicado en `obtener_paciente`, `listar_expedientes_paciente`, `listar_reacciones_adversas`, `listar_registros_de_paciente`; helper nuevo `_verificar_acceso_medico`/`_obtener_medico_o_404` en `app/services/medicos.py` aplicado en `obtener_medico`/`actualizar_medico`/`eliminar_medico`. Requirió además el commit `0ccd62f` (migración de columnas faltantes en BD, descubierto al probar este fix) |
| SAST-02 | Escrituras fuera del límite geográfico | High | ✅ Corregido | commit `59fedba`: nuevo helper único `_verificar_clues_en_ambito` en `app/auth.py`, aplicado en `actualizar_medico`, `crear_medico`, `crear_paciente`, `actualizar_paciente` (rama ADMIN_ESTATAL), `upsert_expediente_paciente`; `validar_continuidad` en `registros.py` ahora reutiliza `_verificar_acceso_registro` (unidad actual del paciente) en vez de `registro.clues` histórico |
| SAST-03 | Enumeración de cuentas (bcrypt >72 bytes) | Medium | ✅ Corregido | commit `3a836cf`: `verify_password` devuelve `False` para >72 bytes en vez de propagar `ValueError`; `autenticar_usuario` siempre ejecuta `verify_password` (hash real o señuelo `_DUMMY_BCRYPT_HASH`) exista o no la cuenta, para no filtrar por status ni por tiempo |
| SAST-04 | Sin throttling de autenticación | Medium | ✅ Corregido | commit `19436c1`: `slowapi` con `Limiter` compartido en `app/rate_limit.py` — 5/minute en `/auth/login`, 3/hour en `/auth/solicitar-acceso`; se agrega `usuarios.fecha_ultima_solicitud_acceso` (ventana de 5 min) para no rotar la contraseña temporal de una cuenta pendiente en cada llamada, y se reordena el envío de correo ANTES del commit. Nota: storage en memoria de slowapi — con gunicorn multi-worker el límite efectivo se multiplica por worker; para límite estricto compartido se necesitaría Redis |
| SAST-05 | JWT en `localStorage`, no revocable | Medium | ⚠️ Mitigado (parcial, decisión del usuario) | commit `6eeee0a`: se optó por mitigación contenida en vez de migrar a cookies httpOnly + refresh tokens (evita reescribir el flujo de auth y agregar CSRF). Nuevo `usuarios.token_version` verificado en `get_current_user`; `POST /auth/logout` lo incrementa (revocación real, no solo borrar localStorage); cambiar contraseña propia/por SUPER_ADMIN y rotar password temporal también lo incrementan. `cambiar-password` devuelve un `access_token` nuevo para no cortar la sesión propia. Verificado en vivo (login→logout→mismo token da 401; token viejo sin claim también queda invalidado). **No cierra CWE-922**: el token sigue siendo bearer en `localStorage`, expuesto a robo vía XSS mientras es válido |
| SAST-06 | Password mínimo 8 (NIST pide 15) | Medium | ❌ Pendiente | `app/schemas/auth.py:39` y `app/schemas/usuarios.py:54` siguen en `min_length=8` |
| SAST-07 | Contraseña SUPER_ADMIN impresa en stdout | Medium | ✅ Corregido | commit `994ac2c`: `print("Contraseña: [OCULTA]...")` en `create_admin.py` |
| SAST-08 | STARTTLS sin verificar certificado | Medium | ❌ Pendiente | `app/email_service.py:56` sigue con `server.starttls()` sin `context` |
| SAST-09 | PostgreSQL permite downgrade de TLS (`prefer`) | Medium | ❌ Pendiente | `.env.example` sigue en `DATABASE_SSL_MODE=prefer` |
| SAST-10 | Índices CURP/cédula con SHA-256 sin clave | Medium | ❌ Pendiente | sin cambios en `crypto.py` |
| SAST-11 | Cobertura incompleta de cifrado PHI | Medium | ❌ Pendiente | sin cambios |
| SAST-12 | Credenciales dev fijas / puerto DB publicado | Medium | ❌ Pendiente | sin cambios en `docker-compose.yml` |
| SAST-13 | Sin audit trail de seguridad | Medium | ❌ Pendiente | sin cambios |
| SAST-14 | Password temporal por correo sin TTL | Low | ❌ Pendiente | sin cambios |
| SAST-15 | Respuestas sin headers de seguridad (cache/CSP/HSTS) | Low | ❌ Pendiente | `frontend/nginx.conf` no tiene ningún `add_header` |
| SAST-16 | Build/contenedores con privilegios innecesarios | Low | ❌ Pendiente | `frontend/Dockerfile*` siguen con `npm install` (no `npm ci`) y sin `USER` no-root |

## Hallazgos SCA

| # | Hallazgo | Severidad | Estado | Evidencia |
|---|---|---|---|---|
| SCA-01 | `xlsx@0.18.5` ReDoS (CVE-2024-22363) | High | ❌ Pendiente | `package-lock.json` sigue resolviendo `xlsx` en `0.18.5` — los 3 PRs "sheetjs-redos" fueron vacíos |
| SCA-02 | `xlsx@0.18.5` Prototype Pollution (CVE-2023-30533) | High | ❌ Pendiente | mismo, el PR "another-one" fue vacío |
| SCA-03 | `python-jose==3.3.0` algorithm confusion | Medium | ⚠️ Parcial | `requirements.txt` ya tiene `python-jose[cryptography]==3.4.0` (cumple el fix mínimo del CVE), pero el reporte recomienda `3.5.0` |
| SCA-04 | `python-jose==3.3.0` JWE JWT bomb | Medium | ⚠️ Parcial | mismo — 3.4.0 instalado, reporte pide 3.5.0 |

## Correcciones reales fuera de los 20 hallazgos numerados

| Cambio | Commit | Nota |
|---|---|---|
| `react-router-dom` → `react-router@8.3.0` (GHSA-qwww-vcr4-c8h2) | `e193b23` | Diff real en 18 archivos + lockfile |
| `js-yaml` fijado a `4.3.0` vía `overrides` (CVE-2026-59869) | `c74e2a4` / `168cadf` | Diff real en lockfile |
| `@babel/core` pineado a versión parchada | `d227fef` | Diff real |
| CURP fuera de query/path params (`POST /pacientes/buscar`, rutas por `id_paciente`) | `8ee857b` | No es uno de los 20 hallazgos; toca las mismas rutas de SAST-01 pero **no agrega** la verificación de acceso por objeto que ese hallazgo requiere |
| Migración: columnas `medicos.curp/curp_hash/id_puesto`, `pacientes.motivo_baja`, `registros.confirmado_mediante/tratamiento_amparo/queja_derechos_humanos` nunca migradas a BD | `0ccd62f` | Bloqueaba `GET /pacientes` y `GET /medicos` con 500 para cualquier usuario; se descubrió al verificar el fix de SAST-01 |
| Migración: `usuarios.fecha_ultima_solicitud_acceso` | incluida en `19436c1` | Soporte de datos para el fix de SAST-04 |

## Resumen del plan priorizado del reporte (16 puntos)

- **Inmediato: bloquear liberación (6):** 5/6 resueltos — (1) autorización por objeto, (2) propiedades destino/continuidad, (3) enumeración bcrypt, (4) throttling/idempotencia, (6) contraseña en stdout. Pendiente: (5) actualizar `python-jose` a 3.5.0 y `xlsx` a 0.20.3 o reemplazarlo.
- **Siguiente sprint (6):** punto 7 parcialmente resuelto (revocación de sesión sí, vía `token_version`; migración fuera de `localStorage` no — decisión explícita del usuario para acotar el alcance). Puntos 8-12 (password mínimo 15, TLS verificado SMTP/PostgreSQL, HMAC en índices, audit trail, contraseña temporal de un solo uso) pendientes.
- **Hardening (4):** 0/4 resueltos (headers de seguridad, contenedores no-root, SBOM/lock Python, tests de autorización negativos).

**Total: 5 de 20 hallazgos formales corregidos (SAST-01, SAST-02, SAST-03, SAST-04, SAST-07), 1 mitigado parcialmente por decisión de alcance (SAST-05), 2 parcialmente mitigados por versión de dependencia (SCA-03/04).** El riesgo dominante que el reporte marcaba como bloqueante —BOLA en lecturas y escrituras de pacientes/médicos (SAST-01/SAST-02)— ya está remediado. Cada hallazgo corregido se verificó con pruebas aisladas de la lógica RBAC contra la base de datos real (sin efectos persistentes) y, cuando aplicó, con llamadas HTTP en vivo.

## Revisión de los stashes en `carolinacc`

| Stash | Contenido | Relación con el reporte |
|---|---|---|
| `stash@{0}` — "modularización y cifrado de datos en base" | Agrega el campo `insumo` al catálogo de medicamentos (modelo, schema, endpoints, frontend) y limpia `scripts/cargar_medicamentos.py`. Corresponde a la migración sin trackear `alembic/versions/20260708_0002_add_insumo_to_cat_medicamentos.py`. | Sin relación — es una mejora funcional del catálogo, no de seguridad. |
| `stash@{1}` | Introduce `EncryptedString` (TypeDecorator de SQLAlchemy que cifra/descifra Fernet automáticamente) aplicado a `curp_paciente`, `nombre_completo`, `diagnostico_actual`. | **Ya integrado en `main`** — `app/crypto.py` y `app/models/pacientes.py:16-18` ya tienen exactamente esta implementación, y no quedan llamadas manuales a `cifrar()`/`descifrar()` en el código. El stash quedó obsoleto/duplicado. Coincide con lo que el propio reporte señala: el `EncryptedString` automático ya existe pero no cierra ningún hallazgo de seguridad (SAST-01, SAST-02 y SAST-11 siguen abiertos). |

**Conclusión:** ninguno de los dos stashes corrige un hallazgo del reporte. `stash@{0}` puede aplicarse por su valor funcional (catálogo de medicamentos) sin impacto en seguridad; `stash@{1}` puede descartarse porque su contenido ya está en `main`.
