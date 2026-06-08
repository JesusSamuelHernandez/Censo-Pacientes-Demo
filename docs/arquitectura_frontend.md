# Arquitectura del Frontend — App "Medicamentos de Alto Costo"

> Última actualización: 2026-06-07

## 1. Stack Tecnológico

| Capa | Tecnología | Notas |
|---|---|---|
| Framework UI | **React 18** | Componentes reutilizables, Strict Mode activo en dev |
| Build tool | **Vite** | HMR instantáneo, `preview` para prod local |
| Estilos | **Tailwind CSS** | Utility-first, sin archivos CSS separados |
| Componentes UI | **shadcn/ui** | Copia componentes al proyecto (no dependencia externa) |
| Routing | **React Router v6** | SPA con `<BrowserRouter>` |
| Estado global | **Zustand** | 2 stores: `authStore` (auth) + `rtmStore` (RTM) |
| Peticiones HTTP | **Axios** | Interceptor adjunta JWT en cada request |
| Tablas | **TanStack Table v8** | Paginación, ordenamiento y filtros del lado cliente |
| Formularios | **React Hook Form + Zod** | Validación sincronizada con esquemas del backend |
| Notificaciones | **Sonner** | Toasts para feedback de operaciones |
| Excel | **xlsx (SheetJS)** | Exportación a `.xlsx` en el cliente sin endpoint adicional |

---

## 2. Estructura de Carpetas

```
frontend/
├── public/
├── src/
│   ├── api/                       # Funciones de llamada a cada endpoint
│   │   ├── auth.js
│   │   ├── pacientes.js
│   │   ├── medicos.js
│   │   ├── registros.js           # Prescripciones (antes recetas.js)
│   │   ├── catalogos.js
│   │   ├── usuarios.js
│   │   └── reportes.js            # resumen-detallado, estatal y RTM
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx        # Menú dinámico según rol
│   │   │   ├── Topbar.jsx
│   │   │   └── ProtectedRoute.jsx # Verifica rol antes de renderizar
│   │   ├── ui/                    # Componentes base (shadcn/ui)
│   │   └── shared/
│   │       ├── DataTable.jsx
│   │       ├── ConfirmDialog.jsx
│   │       └── LoadingSpinner.jsx
│   ├── pages/
│   │   ├── auth/
│   │   │   ├── LoginPage.jsx
│   │   │   └── CambiarPasswordPage.jsx
│   │   ├── pacientes/
│   │   │   ├── PacientesPage.jsx
│   │   │   ├── PacienteDetallePage.jsx
│   │   │   └── PacienteFormPage.jsx
│   │   ├── medicos/
│   │   │   ├── MedicosPage.jsx
│   │   │   └── MedicoFormPage.jsx
│   │   ├── registros/             # Antes "recetas/"
│   │   │   ├── RegistrosPage.jsx
│   │   │   └── RegistroFormPage.jsx  # Formulario combinado (paciente + prescripción)
│   │   ├── reportes/
│   │   │   └── ReportesPage.jsx   # Contiene subcomponentes: RTM, Detallado, Estatal
│   │   ├── catalogos/
│   │   │   ├── MedicamentosPage.jsx
│   │   │   └── UnidadesPage.jsx
│   │   └── usuarios/
│   │       ├── UsuariosPage.jsx
│   │       └── UsuarioFormPage.jsx
│   ├── store/
│   │   ├── authStore.js           # Token, rol, id_usuario, debe_cambiar_password
│   │   └── rtmStore.js            # Selección de entidad/unidad para RTM (session-only)
│   ├── lib/
│   │   └── axiosClient.js         # Instancia Axios con interceptor JWT + manejo 401
│   ├── App.jsx                    # Definición de rutas
│   └── main.jsx
├── .env                           # VITE_API_BASE_URL=http://localhost:8000
├── .env.production                # VITE_API_BASE_URL=https://censo-backend-production-06f3.up.railway.app
├── Dockerfile.prod                # Build multi-stage para producción (Railway)
├── nginx.conf                     # Sirve la SPA y hace proxy inverso a la API
├── index.html
└── package.json
```

---

## 3. Stores de Zustand

### 3.1 authStore — `src/store/authStore.js`

Estado de autenticación global. Persiste en `localStorage` (o memoria, según configuración).

```js
{
  token: null,              // JWT string
  rol: null,                // "SUPER_ADMIN" | "ADMIN_ESTATAL" | "RESPONSABLE_UNIDAD"
  idUsuario: null,          // integer
  debecambiarPassword: false,
  setAuth: (token, rol, idUsuario, debeCambiar) => ...,
  clearAuth: () => ...
}
```

---

### 3.2 rtmStore — `src/store/rtmStore.js`

Estado de la selección activa en el módulo RTM. **Session-only** (sin `persist` middleware) — se limpia al cerrar el navegador.

```js
import { create } from "zustand";

const useRtmStore = create((set) => ({
  entidad: "",
  unidadSeleccionada: null,
  setEntidad: (entidad) => set({ entidad }),
  setUnidadSeleccionada: (unidad) => set({ unidadSeleccionada: unidad }),
  limpiarUnidad: () => set({ unidadSeleccionada: null }),
}));

export default useRtmStore;
```

**Propósito:** Al navegar fuera del módulo RTM y regresar, la selección de estado (entidad) y unidad (CLUES) se mantiene y los datos se vuelven a cargar automáticamente. La unidad se limpia **solo** en los event handlers (cambio de entidad, botón "Cambiar unidad") — nunca dentro de un `useEffect`, para evitar problemas con React Strict Mode.

---

## 4. Módulos API

Cada archivo en `src/api/` encapsula las llamadas a los endpoints del backend usando `axiosClient`.

### 4.1 `auth.js`
- `login(email, password)` → `POST /auth/login`
- `cambiarPassword(passwordActual, passwordNueva)` → `POST /usuarios/me/cambiar-password`

### 4.2 `pacientes.js`
- `listarPacientes(params)` → `GET /pacientes`
- `obtenerPaciente(curp)` → `GET /pacientes/{curp}`
- `buscarPorCurp(curp)` → `GET /pacientes/buscar?curp=`
- `crearPaciente(data)` → `POST /pacientes`
- `actualizarPaciente(curp, data)` → `PATCH /pacientes/{curp}`
- `desactivarPaciente(curp)` → `DELETE /pacientes/{curp}`
- `obtenerRegistrosDePaciente(curp, params)` → `GET /pacientes/{curp}/registros`

### 4.3 `medicos.js`
- `listarMedicos(params)` → `GET /medicos`
- `obtenerMedico(id)` → `GET /medicos/{id}`
- `crearMedico(data)` → `POST /medicos`
- `actualizarMedico(id, data)` → `PATCH /medicos/{id}`
- `eliminarMedico(id)` → `DELETE /medicos/{id}`

### 4.4 `registros.js`
- `listarRegistros(params)` → `GET /registros`
- `obtenerRegistro(id)` → `GET /registros/{id}`
- `crearRegistro(data)` → `POST /registros`
- `crearRegistroCompleto(data)` → `POST /registros/completo`
- `actualizarRegistro(id, data)` → `PATCH /registros/{id}`
- `desactivarRegistro(id)` → `DELETE /registros/{id}`
- `validarContinuidad(id, data)` → `PATCH /registros/{id}/validar-continuidad`
- `reemplazarRegistro(id, data)` → `POST /registros/{id}/reemplazar`

### 4.5 `catalogos.js`
- `listarMedicamentos(params)` → `GET /catalogos/medicamentos`
- `crearMedicamento(data)` → `POST /catalogos/medicamentos`
- `actualizarMedicamento(clave, data)` → `PATCH /catalogos/medicamentos/{clave}`
- `listarUnidades(idEntidad)` → `GET /catalogos/unidades?id_entidad=`
- `crearUnidad(data)` → `POST /catalogos/unidades`
- `actualizarUnidad(clues, data)` → `PATCH /catalogos/unidades/{clues}`

### 4.6 `reportes.js`
- `obtenerResumenDetallado(params)` → `GET /reportes/resumen-detallado`
- `obtenerReporteEstatal(params)` → `GET /reportes/estatal`
- `obtenerRtm(clues, meses)` → `GET /reportes/rtm?clues=&meses=`
- `listarNotificaciones(params)` → `GET /notificaciones`
- `listarTransferencias()` → `GET /notificaciones/transferencias`
- `marcarTransferenciaLeida(id)` → `PATCH /notificaciones/transferencias/{id}/leer`
- `listarEntidades()` → `GET /catalogos/unidades` (extrae entidades únicas del catálogo)

### 4.7 `usuarios.js`
- `listarUsuarios()` → `GET /usuarios`
- `crearUsuario(data)` → `POST /usuarios`
- `actualizarUsuario(id, data)` → `PATCH /usuarios/{id}`
- `eliminarUsuario(id)` → `DELETE /usuarios/{id}`

---

## 5. Páginas y su Relación con los Endpoints

### 5.1 Autenticación

| Página | Ruta | Endpoints consumidos |
|---|---|---|
| Login | `/login` | `POST /auth/login` |
| Cambiar contraseña | `/cambiar-password` | `POST /usuarios/me/cambiar-password` |

**Flujo:** Al hacer login, si `debe_cambiar_password = true`, la app redirige automáticamente a `/cambiar-password` y bloquea el resto de rutas hasta completarlo.

---

### 5.2 Pacientes

| Página | Ruta | Endpoints consumidos | Roles con acceso |
|---|---|---|---|
| Lista | `/pacientes` | `GET /pacientes` | Todos |
| Detalle | `/pacientes/:curp` | `GET /pacientes/{curp}` + `GET /pacientes/{curp}/registros` | Todos |
| Registrar | `/pacientes/nuevo` | `POST /pacientes` | RESPONSABLE_UNIDAD, SUPER_ADMIN |
| Editar | `/pacientes/:curp/editar` | `PATCH /pacientes/{curp}` | RESPONSABLE_UNIDAD, SUPER_ADMIN |

---

### 5.3 Médicos

| Página | Ruta | Endpoints consumidos | Roles con acceso |
|---|---|---|---|
| Lista | `/medicos` | `GET /medicos` | Todos |
| Registrar | `/medicos/nuevo` | `POST /medicos` | RESPONSABLE_UNIDAD, SUPER_ADMIN |
| Editar | `/medicos/:id/editar` | `PATCH /medicos/:id` | Solo SUPER_ADMIN |

---

### 5.4 Registros (Prescripciones)

| Página | Ruta | Endpoints consumidos | Roles con acceso |
|---|---|---|---|
| Lista | `/registros` | `GET /registros` | Todos |
| Registrar | `/registros/nuevo` | `POST /registros/completo` | RESPONSABLE_UNIDAD, SUPER_ADMIN |
| Editar | `/registros/:id/editar` | `PATCH /registros/:id` | RESPONSABLE_UNIDAD, SUPER_ADMIN |

**Formulario combinado (`RegistroFormPage`):** Busca primero el paciente por CURP (`GET /pacientes/buscar`). Si existe, usa sus datos. Si no existe, muestra campos para capturarlo. En ambos casos, los campos de posología están disponibles en el mismo formulario. Envía a `POST /registros/completo`.

---

### 5.5 Reportes

`ReportesPage.jsx` contiene tres subcomponentes seleccionables mediante pestañas:

| Subcomponente | Endpoints consumidos | Roles con acceso |
|---|---|---|
| Reporte Detallado | `GET /reportes/resumen-detallado` | Todos |
| Reporte Estatal | `GET /reportes/estatal` | ADMIN_ESTATAL, SUPER_ADMIN |
| RTM (Requerimiento Teórico Mensual) | `GET /reportes/rtm` | Solo SUPER_ADMIN |

**Funcionalidad RTM:**
- Selección de entidad → carga unidades → selección de unidad (CLUES).
- La selección persiste en `rtmStore` durante la sesión.
- Al regresar al módulo, se auto-recupera la selección y se vuelve a cargar el RTM.
- Muestra tabla de medicamentos × meses con cantidades calculadas.

**Exportar a Excel:** Botón disponible en Reporte Detallado. Usa SheetJS en el cliente para convertir el JSON de la API a `.xlsx` descargable.

---

### 5.6 Catálogos *(Solo SUPER_ADMIN)*

| Página | Ruta | Endpoints consumidos |
|---|---|---|
| Catálogo de medicamentos | `/catalogos/medicamentos` | `GET/POST/PATCH /catalogos/medicamentos` |
| Unidades médicas | `/catalogos/unidades` | `GET/POST/PATCH /catalogos/unidades` |

---

### 5.7 Usuarios *(Solo SUPER_ADMIN)*

| Página | Ruta | Endpoints consumidos |
|---|---|---|
| Lista | `/usuarios` | `GET /usuarios` |
| Crear | `/usuarios/nuevo` | `POST /usuarios` |
| Editar | `/usuarios/:id/editar` | `PATCH /usuarios/:id` |

**Flujo de creación:** El backend devuelve `password_temporal`. El frontend la muestra en un modal con advertencia "copia esta contraseña, no se volverá a mostrar".

---

## 6. Navegación por Rol

El Sidebar se renderiza dinámicamente según el rol en `authStore`:

```
SUPER_ADMIN        → Pacientes | Médicos | Registros | Reportes (todos) | Catálogos | Usuarios
ADMIN_ESTATAL      → Pacientes | Médicos | Registros | Reportes (Detallado + Estatal)
RESPONSABLE_UNIDAD → Pacientes | Médicos | Registros | Reportes (solo Detallado)
```

`ProtectedRoute` verifica el rol antes de renderizar. Si el rol no tiene acceso, redirige a `/no-autorizado`.

---

## 7. Manejo del JWT

`src/lib/axiosClient.js` configura un interceptor que:
1. Lee el token desde `authStore`.
2. Lo adjunta como `Authorization: Bearer <token>` en cada request.
3. Si recibe un `401`, ejecuta `clearAuth()` y redirige a `/login`.

Ninguna página necesita manejar el token manualmente.

---

## 8. Variables de Entorno

```env
# frontend/.env (desarrollo local)
VITE_API_BASE_URL=http://localhost:8000

# frontend/.env.production (Railway)
VITE_API_BASE_URL=https://censo-backend-production-06f3.up.railway.app
```

**Importante:** Las variables `VITE_*` se inyectan en el bundle durante el build (`npm run build`). NO están disponibles en runtime. Por eso la URL del backend debe estar en `.env.production` (archivo commitado), no en Railway Service Variables.

---

## 9. Despliegue en Railway

El frontend usa `frontend/Dockerfile.prod`:
- **Stage 1:** Node — `npm install` + `npm run build` → genera `dist/`.
- **Stage 2:** Nginx — copia `dist/` y sirve con `nginx.conf`.
- `nginx.conf` sirve `index.html` para todas las rutas (SPA fallback) y hace proxy inverso de `/api/` al backend si es necesario.

Configuración Railway:
- **Root Directory:** `/frontend` (cambia el contexto de build a la carpeta frontend).
- **Dockerfile Path:** `/Dockerfile.prod` (relativo al Root Directory).
- **Service Variables:** No son necesarias para el frontend (la URL del backend va en `.env.production`).

---

## 10. Convenciones Importantes

| Convención | Descripción |
|---|---|
| **Stores session-only** | `rtmStore` no usa `persist` — la selección se pierde al cerrar el navegador, lo que es correcto (datos sensibles no deben quedar en localStorage). |
| **Strict Mode** | React Strict Mode ejecuta efectos dos veces en desarrollo. Evitar lógica de "primera vez" en `useEffect` — moverla a event handlers. |
| **Módulo "registros"** | El módulo se llama `registros` (no `recetas`) desde Blueprint v6. Los archivos y rutas usan este nombre. |
| **fecha_fin exclusiva** | Al mostrar "último día de tratamiento" al usuario, restar 1 día al valor que devuelve la API (que es exclusivo). |
| **Exportación Excel** | Se hace en el cliente con SheetJS. No hay endpoint de exportación en el backend. |
