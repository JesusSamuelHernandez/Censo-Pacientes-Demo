/**
 * ProtectedRoute.jsx — Guarda de rutas.
 *
 * Comportamiento:
 *   1. Si no hay token → redirige a /login.
 *   2. Si debe_cambiar_password = true → redirige a /cambiar-password.
 *   3. Si se pasa `rolesPermitidos` y el rol no está en la lista → redirige a /no-autorizado.
 *   4. En cualquier otro caso → renderiza la página hija.
 */
import { Navigate, Outlet } from "react-router-dom";
import useAuthStore from "../../store/authStore";

export default function ProtectedRoute({ rolesPermitidos, ignorarPasswordPendiente = false }) {
  const { token, rolNombre, debeCambiarPassword } = useAuthStore();

  if (!token) return <Navigate to="/login" replace />;

  if (debeCambiarPassword && !ignorarPasswordPendiente)
    return <Navigate to="/cambiar-password" replace />;

  if (rolesPermitidos && !rolesPermitidos.includes(rolNombre)) {
    return <Navigate to="/no-autorizado" replace />;
  }

  return <Outlet />;
}
