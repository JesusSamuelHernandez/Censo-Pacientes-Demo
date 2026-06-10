# Arquitectura del Frontend — App "Medicamentos de Alto Costo"

> Última actualización: 2026-06-09

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
│   │       ├── LoadingSpinner.jsx
│   │       ├── UnidadCombobox.jsx     # Combobox de búsqueda de unidades; onChange(clues, nombre)
│   │       ├── RegistrarMedicoModal.jsx # Modal para registrar médico sin salir del form de prescripción
│   │       └── BanderinEstado.jsx     # Banderín de color (estatus_evolucion) en Pacientes Activos
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
  token: null,                  // JWT string
  rolNombre: null,              // "SUPER_ADMIN" | "ADMIN_ESTATAL" | "RESPONSABLE_UNIDAD"
  idUsuario: null,              // integer
  debeCambiarPassword: false,
  email: null,                  // email del usuario autenticado
  nombreUsuario: null,          // nombre completo del usuario
  cluesUnidadAsignada: null,    // solo RESPONSABLE_UNIDAD
  nombreUnidad: null,           // nombre de la unidad (solo RESPONSABLE_UNIDAD)
  idEntidad: null,              // clave de estado (solo ADMIN_ESTATAL)
  login: (data) => ...,         // guarda todos los campos al iniciar sesión
  logout: () => ...
}
```

Todos los campos se persisten en `localStorage` (excepto los que se excluyen con `partialize`). El Sidebar usa `email`, `nombreUnidad`, `cluesUnidadAsignada` e `idEntidad` para mostrar información contextual según el rol.

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
- `crearPaciente(data)` → `POST /pacientes`
- `actualizarPaciente(curp, data)` → `PATCH /pacientes/{curp}` (también usado por `BanderinEstado` para actualizar `estatus_evolucion`)
- `darBajaPaciente(curp)` → `DELETE /pacientes/{curp}`
- `buscarPacientePorCurp(curp)` → `GET /pacientes/buscar?curp=`
- `listarRegistrosDePaciente(curp, soloActivos)` → `GET /pacientes/{curp}/registros`
- `listarExpedientesPaciente(curp)` → `GET /pacientes/{curp}/expedientes`
- `guardarExpediente(curp, clues, numeroExpediente)` → `POST /pacientes/{curp}/expedientes` (upsert)

### 4.3 `medicos.js`
- `listarMedicos()` → `GET /medicos` (filtrado por RBAC en backend)
- `obtenerMedico(id)` → `GET /medicos/{id}`
- `crearMedico(data)` → `POST /medicos`
- `actualizarMedico(id, data)` → `PATCH /medicos/{id}`
- `darBajaMedico(id)` → `PATCH /medicos/{id}` con `{ es_activo: false }` (Soft Delete)
- `eliminarMedico(id)` → `DELETE /medicos/{id}` (eliminación física, solo SUPER_ADMIN)

### 4.4 `registros.js`
- `listarRegistros(params)` → `GET /registros`
- `obtenerRegistro(id)` → `GET /registros/{id}`
- `crearRegistro(data)` → `POST /registros`
- `crearRegistroCompleto(data)` → `POST /registros/completo`
- `actualizarRegistro(id, data)` → `PATCH /registros/{id}`
- `anularRegistro(id)` → `DELETE /registros/{id}`
- `validarContinuidad(id, nuevaFechaFin)` → `PATCH /registros/{id}/validar-continuidad`
- `reemplazarRegistro(id, data)` → `POST /registros/{id}/reemplazar`
- `listarOrdenesSuministro(id)` / `crearOrdenSuministro(id, data)` / `eliminarOrdenSuministro(id, idOrden)` → `/registros/{id}/ordenes-suministro[...]`
- `listarOrdenesRemision(id)` / `crearOrdenRemision(id, data)` / `eliminarOrdenRemision(id, idOrden)` → `/registros/{id}/ordenes-remision[...]`

### 4.5 `catalogos.js`
- `listarDiagnosticos(soloActivos)` → `GET /catalogos/diagnosticos`
- `listarMedicamentos(clues = null, soloActivos = true)` → `GET /catalogos/medicamentos[?clues=]` — si `clues` está presente, filtra solo los medicamentos asignados a esa unidad (vía `unidad_medicamentos`)
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
| Detalle | `/pacientes/:curp` | `GET /pacientes/{curp}` + `GET /pacientes/{curp}/registros` + `GET /pacientes/{curp}/expedientes` | Todos |
| Registrar | `/pacientes/nuevo` | `POST /pacientes` | RESPONSABLE_UNIDAD, SUPER_ADMIN |
| Editar | `/pacientes/:curp/editar` | `PATCH /pacientes/{curp}` | RESPONSABLE_UNIDAD, SUPER_ADMIN |

**Banderín de estatus de evolución (`BanderinEstado.jsx`):** En `PacientesPage.jsx`, cuando `soloActivos = true`, cada fila muestra un banderín de color con forma de listón (clip-path) a la izquierda del nombre, posicionado `absolute` dentro de un contenedor `relative` con `-top-1.5 -bottom-1.5` para sobresalir visualmente sin ser recortado por el `overflow-hidden` de la tabla. El color depende de `paciente.estatus_evolucion`:

| Estatus | Color |
|---|---|
| Inicia tx | Verde (`#22c55e`) — valor por defecto |
| Tx fase intermedia | Ámbar (`#f59e0b`) |
| Recaída | Rojo (`#ef4444`) |
| Curación | Azul (`#3b82f6`) |

Al hacer clic se abre un modal con la leyenda de colores y un selector; al elegir un valor distinto llama `actualizarPaciente(curp, { estatus_evolucion })` (`PATCH /pacientes/{curp}`) y actualiza el estado local vía el callback `onChange`.

---

### 5.3 Médicos

| Página | Ruta | Endpoints consumidos | Roles con acceso |
|---|---|---|---|
| Lista | `/medicos` | `GET /medicos` | Todos (RBAC geográfico en backend) |
| Registrar | `/medicos/nuevo` | `POST /medicos` | Todos (RBAC geográfico en backend) |
| Editar | `/medicos/:id/editar` | `PATCH /medicos/:id` | Todos (RBAC geográfico en backend) |

**Dar de baja:** botón disponible en la tabla de lista para todos los roles. Llama a `darBajaMedico()` con confirmación. El médico desaparece del listado y del dropdown de prescripciones (`GET /medicos` filtra `es_activo=True`).

---

### 5.4 Registros (Prescripciones)

| Página | Ruta | Endpoints consumidos | Roles con acceso |
|---|---|---|---|
| Lista | `/registros` | `GET /registros` | Todos |
| Registrar | `/registros/nuevo` | `POST /registros/completo` | RESPONSABLE_UNIDAD, SUPER_ADMIN |
| Editar | `/registros/:id/editar` | `PATCH /registros/:id` | RESPONSABLE_UNIDAD, SUPER_ADMIN |

**Formulario combinado (`RegistroFormPage`):** Busca primero el paciente por CURP (`GET /pacientes/buscar`). Si existe, usa sus datos. Si no existe, muestra campos para capturarlo.

Comportamiento por rol:
- **RESPONSABLE_UNIDAD:** La unidad de la prescripción (`clues`) se bloquea y pre-llena automáticamente con su unidad asignada. El dropdown de medicamentos carga solo los asignados a esa unidad (vía `?clues=`).
- **SUPER_ADMIN:** Puede seleccionar cualquier unidad con `UnidadCombobox`; al cambiar de unidad se recargan los medicamentos disponibles y se limpia `clave_cnis`.
- **ADMIN_ESTATAL:** Sin acceso a registrar (403 en backend).

**Médico inline:** Si el médico buscado no existe, el botón "+ Registrar médico" abre `RegistrarMedicoModal`. Al crearlo, se auto-selecciona en el formulario sin perder el estado del form.

**Descripción completa del medicamento:** Al seleccionar un medicamento del dropdown, se muestra su descripción completa en un cuadro de texto de solo lectura debajo del select.

**Todos los campos son requeridos**, incluida la posología completa (dosis, cantidad, frecuencia, unidad de tiempo, duración, peso, talla, etc.). El campo `estatus_diagnostico` siempre se envía como `"confirmado"` — no aparece en la UI.

**Fecha de nacimiento del paciente:** Si la búsqueda por CURP no encuentra al paciente, se muestra el campo **Fecha de nacimiento** (opcional) para capturarlo junto con el resto de datos del paciente nuevo (`fecha_nacimiento` en el payload de `POST /registros/completo`). Si el paciente ya existe y tiene `fecha_nacimiento`, se muestra como dato de solo lectura en el resumen de búsqueda.

**Confirmado por (campo fijo):** El select `confirmado_por` aparece deshabilitado y fijo en `"Médico tratante"` (`CONFIRMADO_POR_FIJO` en `RegistroFormPage.jsx`). En modo creación, `defaultValues` lo precarga con ese valor; en modo edición se muestra el valor históricamente guardado. Las demás opciones (`CONFIRMADO_POR_OPTIONS`: "Consulta Externa", "Farmacia Hospitalaria", "Comité de Medicamentos", "Dirección Médica", "Trabajo Social") se conservan en el array por si se reactivan más adelante.

**Fuente de financiamiento y número de expediente:** Campo de texto opcional `fuente_financiamiento` (ej. "Federal", "Estatal", "IMSS Bienestar"). El campo **Número de expediente** solo aparece al crear (no en edición); si se captura, se envía como `numero_expediente` en `POST /registros/completo`, que el backend usa para hacer upsert del expediente del paciente en la unidad de la prescripción (`POST /pacientes/{curp}/expedientes`).

**Órdenes de suministro y de remisión:** Dos secciones independientes (listas dinámicas) donde el usuario puede agregar/quitar entradas con `numero_orden` y `fecha` opcional, antes de guardar. Se envían como `ordenes_suministro` / `ordenes_remision` (arrays) dentro del payload de `POST /registros/completo`, que las crea junto con el registro.

**Flujo Vista previa:** El botón "Vista previa" (ojo) valida todos los campos antes de mostrar un resumen de la prescripción (Paciente, Prescripción, Posología, fuente de financiamiento, número de expediente). El usuario confirma o regresa a editar. El form permanece montado pero oculto con CSS (`hidden`) para preservar el estado de `react-hook-form`. Solo en modo edición se muestra directamente "Guardar cambios". Envía a `POST /registros/completo`.

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
