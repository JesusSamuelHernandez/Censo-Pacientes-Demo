# Arquitectura del Frontend — App "Medicamentos de Alto Costo"

## 1. Stack Tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Framework UI | **React 18** | Componentes reutilizables, ecosistema amplio, compatible con Vite |
| Build tool | **Vite** | Arranque instantáneo, HMR, reemplaza Create React App |
| Estilos | **Tailwind CSS** | Utility-first, no requiere archivos CSS separados, muy rápido para prototipos |
| Componentes UI | **shadcn/ui** | Componentes accesibles sobre Tailwind, sin dependencia de librería externa |
| Routing | **React Router v6** | Estándar de facto para SPA en React |
| Estado global | **Zustand** | Ligero, sin boilerplate, ideal para estado de sesión/auth |
| Peticiones HTTP | **Axios** | Interceptores para adjuntar JWT automáticamente en cada request |
| Tablas | **TanStack Table v8** | Paginación, ordenamiento y filtros del lado cliente |
| Formularios | **React Hook Form + Zod** | Validación tipada, sincronizada con los esquemas del backend |
| Notificaciones | **Sonner** | Toasts minimalistas para feedback de operaciones |

---

## 2. Estructura de Carpetas

```
frontend/
├── public/
├── src/
│   ├── api/                  # Funciones de llamada a cada endpoint
│   │   ├── auth.js
│   │   ├── pacientes.js
│   │   ├── medicos.js
│   │   ├── recetas.js
│   │   ├── catalogos.js
│   │   ├── usuarios.js
│   │   └── reportes.js
│   ├── components/           # Componentes reutilizables
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Topbar.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── ui/               # Componentes base (shadcn/ui)
│   │   └── shared/
│   │       ├── DataTable.jsx
│   │       ├── ConfirmDialog.jsx
│   │       └── LoadingSpinner.jsx
│   ├── pages/                # Una carpeta por módulo
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
│   │   ├── recetas/
│   │   │   ├── RecetasPage.jsx
│   │   │   └── RecetaFormPage.jsx
│   │   ├── reportes/
│   │   │   ├── ReporteDetalladoPage.jsx
│   │   │   └── ReporteEstatalPage.jsx
│   │   ├── catalogos/
│   │   │   ├── MedicamentosPage.jsx
│   │   │   └── UnidadesPage.jsx
│   │   └── usuarios/
│   │       ├── UsuariosPage.jsx
│   │       └── UsuarioFormPage.jsx
│   ├── store/
│   │   └── authStore.js      # Estado global: token, rol, id_usuario
│   ├── hooks/
│   │   └── useAuth.js        # Hook de acceso al store de auth
│   ├── lib/
│   │   └── axiosClient.js    # Instancia Axios con interceptor JWT
│   ├── App.jsx               # Definición de rutas
│   └── main.jsx
├── .env
├── index.html
└── package.json
```

---

## 3. Páginas y su Relación con los Endpoints

### 3.1 Autenticación

| Página | Ruta | Endpoints consumidos |
|---|---|---|
| Login | `/login` | `POST /auth/login` |
| Cambiar contraseña | `/cambiar-password` | `POST /usuarios/me/cambiar-password` |

**Flujo:** Al hacer login, el backend devuelve `{ access_token, rol_nombre, debe_cambiar_password }`. Si `debe_cambiar_password = true`, la app redirige automáticamente a `/cambiar-password` y bloquea el resto de rutas hasta completarlo.

---

### 3.2 Pacientes

| Página | Ruta | Endpoints consumidos | Roles con acceso |
|---|---|---|---|
| Lista de pacientes | `/pacientes` | `GET /pacientes` | Todos |
| Detalle de paciente | `/pacientes/:id` | `GET /pacientes/:curp` + `GET /recetas` | Todos |
| Registrar paciente | `/pacientes/nuevo` | `POST /pacientes` | RESPONSABLE_UNIDAD, SUPER_ADMIN |
| Editar paciente | `/pacientes/:id/editar` | `PATCH /pacientes/:curp` | RESPONSABLE_UNIDAD, SUPER_ADMIN |

**Nota RBAC:** `GET /pacientes` ya aplica el filtro en el backend. El frontend no necesita filtrar — solo mostrar lo que devuelve la API.

---

### 3.3 Médicos

| Página | Ruta | Endpoints consumidos | Roles con acceso |
|---|---|---|---|
| Lista de médicos | `/medicos` | `GET /medicos` | Todos |
| Registrar médico | `/medicos/nuevo` | `POST /medicos` | RESPONSABLE_UNIDAD, SUPER_ADMIN |
| Editar médico | `/medicos/:id/editar` | `PATCH /medicos/:id` | Solo SUPER_ADMIN |

---

### 3.4 Recetas

| Página | Ruta | Endpoints consumidos | Roles con acceso |
|---|---|---|---|
| Lista de recetas | `/recetas` | `GET /recetas` | Todos |
| Registrar receta | `/recetas/nueva` | `POST /recetas` | RESPONSABLE_UNIDAD, SUPER_ADMIN |
| Editar receta | `/recetas/:id/editar` | `PATCH /recetas/:id` | RESPONSABLE_UNIDAD, SUPER_ADMIN |

**Formulario de receta requiere:** seleccionar paciente (`GET /pacientes`), médico (`GET /medicos`) y medicamento (`GET /catalogos/medicamentos`).

---

### 3.5 Reportes

| Página | Ruta | Endpoints consumidos | Roles con acceso |
|---|---|---|---|
| Reporte detallado | `/reportes/detallado` | `GET /reportes/resumen-detallado` | Todos |
| Reporte estatal | `/reportes/estatal` | `GET /reportes/estatal` | ADMIN_ESTATAL, SUPER_ADMIN |

**Funcionalidad clave:** botón "Exportar a Excel" usando la librería `xlsx` del lado cliente — el frontend convierte el JSON de la API en un archivo `.xlsx` descargable sin necesidad de un endpoint adicional.

---

### 3.6 Catálogos *(Solo SUPER_ADMIN)*

| Página | Ruta | Endpoints consumidos |
|---|---|---|
| Catálogo de medicamentos | `/catalogos/medicamentos` | `GET/POST/PATCH /catalogos/medicamentos` |
| Unidades médicas | `/catalogos/unidades` | `GET/POST/PATCH /catalogos/unidades` |

---

### 3.7 Usuarios *(Solo SUPER_ADMIN)*

| Página | Ruta | Endpoints consumidos |
|---|---|---|
| Lista de usuarios | `/usuarios` | `GET /usuarios` |
| Crear usuario | `/usuarios/nuevo` | `POST /usuarios` |
| Editar usuario | `/usuarios/:id/editar` | `PATCH /usuarios/:id` |

**Flujo de creación:** al crear un usuario, el backend devuelve `password_temporal`. El frontend debe mostrarla en un modal con advertencia de "copia esta contraseña, no se volverá a mostrar".

---

## 4. Navegación por Rol

El Sidebar se renderiza dinámicamente según el rol almacenado en Zustand:

```
SUPER_ADMIN        → Pacientes | Médicos | Recetas | Reportes | Catálogos | Usuarios
ADMIN_ESTATAL      → Pacientes | Médicos | Recetas | Reportes (ambos)
RESPONSABLE_UNIDAD → Pacientes | Médicos | Recetas | Reportes (solo detallado)
```

Las rutas restringidas usan un componente `ProtectedRoute` que verifica el rol antes de renderizar la página. Si el rol no tiene acceso, redirige a `/no-autorizado`.

---

## 5. Manejo del JWT

El archivo `src/lib/axiosClient.js` configura un interceptor que:
1. Lee el token de Zustand (o `localStorage` como fallback).
2. Lo adjunta automáticamente como `Authorization: Bearer <token>` en cada request.
3. Si recibe un `401`, limpia el store y redirige a `/login`.

Esto significa que ninguna página necesita manejar el token manualmente.

---

## 6. Plan de Implementación por Fases

### Fase 1 — Base del proyecto
- [ ] Crear proyecto con `npm create vite@latest frontend -- --template react`
- [ ] Instalar dependencias (Tailwind, shadcn/ui, React Router, Zustand, Axios)
- [ ] Configurar `axiosClient.js` con interceptor JWT
- [ ] Implementar `LoginPage` y flujo de autenticación
- [ ] Implementar `CambiarPasswordPage` con redirección automática
- [ ] Crear layout base: `Sidebar` + `Topbar` + `ProtectedRoute`

### Fase 2 — Módulos principales
- [ ] Módulo Pacientes (lista + detalle + formulario)
- [ ] Módulo Médicos (lista + formulario)
- [ ] Módulo Recetas (lista + formulario con selects encadenados)

### Fase 3 — Reportes
- [ ] Reporte detallado con tabla paginada
- [ ] Reporte estatal con agrupación por unidad
- [ ] Botón de exportación a Excel (librería `xlsx`)

### Fase 4 — Administración *(Solo SUPER_ADMIN)*
- [ ] Catálogo de medicamentos
- [ ] Catálogo de unidades médicas
- [ ] Gestión de usuarios con modal de contraseña temporal

---

## 7. Variables de Entorno del Frontend

```env
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```

En producción se cambia a la URL del servidor donde esté corriendo uvicorn.

---

## 8. Decisiones de Diseño

| Decisión | Alternativas consideradas | Razón de la elección |
|---|---|---|
| **Vite** sobre CRA | Create React App, Next.js | CRA está deprecado; Next.js agrega complejidad SSR innecesaria para una SPA con auth |
| **Zustand** sobre Redux | Redux Toolkit, Context API | Redux es excesivo para el estado simple de esta app; Context causa re-renders excesivos |
| **Axios** sobre fetch | fetch nativo | Los interceptores de Axios simplifican el manejo global del JWT y errores 401 |
| **TanStack Table** sobre AG Grid | AG Grid, React Table v7 | AG Grid es de pago para features avanzados; TanStack Table v8 es gratuito y moderno |
| **shadcn/ui** sobre Material UI | MUI, Ant Design, Chakra UI | shadcn/ui copia los componentes al proyecto (no es dependencia), total control del código |
| **Exportar Excel en cliente** sobre endpoint | Endpoint `/reportes/export` | Evita agregar openpyxl al backend; el frontend ya tiene el JSON, solo lo transforma |
