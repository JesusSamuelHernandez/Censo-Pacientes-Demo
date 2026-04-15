/**
 * App.jsx — Definición de rutas de la aplicación.
 *
 * Estructura de rutas:
 *   /login                   → Pública
 *   /cambiar-password        → Protegida (requiere token)
 *   /no-autorizado           → Pública
 *   /*                       → Protegidas dentro de AppLayout (Sidebar + Topbar)
 */
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";

import ProtectedRoute from "./components/layout/ProtectedRoute";
import AppLayout from "./components/layout/AppLayout";

import LoginPage from "./pages/auth/LoginPage";
import CambiarPasswordPage from "./pages/auth/CambiarPasswordPage";
import PacientesPage from "./pages/pacientes/PacientesPage";
import PacienteFormPage from "./pages/pacientes/PacienteFormPage";
import PacienteDetallePage from "./pages/pacientes/PacienteDetallePage";
import MedicosPage from "./pages/medicos/MedicosPage";
import MedicoFormPage from "./pages/medicos/MedicoFormPage";
import RecetasPage from "./pages/recetas/RecetasPage";
import RecetaFormPage from "./pages/recetas/RecetaFormPage";
import ReportesPage from "./pages/reportes/ReportesPage";
import MedicamentosPage from "./pages/catalogos/MedicamentosPage";
import UnidadesPage from "./pages/catalogos/UnidadesPage";
import UsuariosPage from "./pages/usuarios/UsuariosPage";

const ROLES = {
  TODOS: ["SUPER_ADMIN", "ADMIN_ESTATAL", "RESPONSABLE_UNIDAD"],
  ADMIN_SUPERIOR: ["SUPER_ADMIN", "ADMIN_ESTATAL"],
  SOLO_SUPER: ["SUPER_ADMIN"],
};

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" richColors closeButton />
      <Routes>
        {/* ── Rutas públicas ──────────────────────────────────── */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/no-autorizado" element={
          <div className="min-h-screen flex items-center justify-center bg-neutral-light">
            <div className="text-center">
              <p className="text-6xl font-bold text-primary">403</p>
              <p className="text-neutral-gray mt-2">No tienes permiso para acceder a esta página.</p>
            </div>
          </div>
        } />

        {/* ── Cambiar contraseña (requiere token pero no layout) ── */}
        <Route element={<ProtectedRoute ignorarPasswordPendiente />}>
          <Route path="/cambiar-password" element={<CambiarPasswordPage />} />
        </Route>

        {/* ── Rutas protegidas con layout ─────────────────────── */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            {/* Todos los roles */}
            <Route element={<ProtectedRoute rolesPermitidos={ROLES.TODOS} />}>
              <Route path="/pacientes" element={<PacientesPage />} />
              <Route path="/pacientes/nuevo" element={<PacienteFormPage />} />
              <Route path="/pacientes/:curp" element={<PacienteDetallePage />} />
              <Route path="/pacientes/:curp/editar" element={<PacienteFormPage />} />
              <Route path="/medicos" element={<MedicosPage />} />
              <Route path="/medicos/nuevo" element={<MedicoFormPage />} />
              <Route path="/medicos/:id/editar" element={<MedicoFormPage />} />
              <Route path="/recetas" element={<RecetasPage />} />
              <Route path="/recetas/nueva" element={<RecetaFormPage />} />
              <Route path="/recetas/:id/editar" element={<RecetaFormPage />} />
              <Route path="/reportes" element={<ReportesPage />} />
            </Route>

            {/* Solo SUPER_ADMIN */}
            <Route element={<ProtectedRoute rolesPermitidos={ROLES.SOLO_SUPER} />}>
              <Route path="/catalogos/medicamentos" element={<MedicamentosPage />} />
              <Route path="/catalogos/unidades" element={<UnidadesPage />} />
              <Route path="/usuarios" element={<UsuariosPage />} />
            </Route>
          </Route>
        </Route>

        {/* Raíz → redirige a pacientes */}
        <Route path="/" element={<Navigate to="/pacientes" replace />} />
        <Route path="*" element={<Navigate to="/pacientes" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
