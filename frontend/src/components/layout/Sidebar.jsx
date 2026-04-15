/**
 * Sidebar.jsx — Navegación lateral.
 * Las opciones visibles dependen del rol almacenado en Zustand.
 */
import { NavLink, useNavigate } from "react-router-dom";
import {
  Users,
  Stethoscope,
  ClipboardList,
  BarChart2,
  BookOpen,
  Building2,
  UserCog,
  LogOut,
} from "lucide-react";
import { toast } from "sonner";
import useAuthStore from "../../store/authStore";

const ROLES = {
  SUPER_ADMIN: "SUPER_ADMIN",
  ADMIN_ESTATAL: "ADMIN_ESTATAL",
  RESPONSABLE_UNIDAD: "RESPONSABLE_UNIDAD",
};

const navItems = [
  {
    label: "Pacientes",
    to: "/pacientes",
    icon: Users,
    roles: [ROLES.SUPER_ADMIN, ROLES.ADMIN_ESTATAL, ROLES.RESPONSABLE_UNIDAD],
  },
  {
    label: "Médicos",
    to: "/medicos",
    icon: Stethoscope,
    roles: [ROLES.SUPER_ADMIN, ROLES.ADMIN_ESTATAL, ROLES.RESPONSABLE_UNIDAD],
  },
  {
    label: "Recetas",
    to: "/recetas",
    icon: ClipboardList,
    roles: [ROLES.SUPER_ADMIN, ROLES.ADMIN_ESTATAL, ROLES.RESPONSABLE_UNIDAD],
  },
  {
    label: "Reportes",
    to: "/reportes",
    icon: BarChart2,
    roles: [ROLES.SUPER_ADMIN, ROLES.ADMIN_ESTATAL, ROLES.RESPONSABLE_UNIDAD],
  },
  {
    label: "Medicamentos",
    to: "/catalogos/medicamentos",
    icon: BookOpen,
    roles: [ROLES.SUPER_ADMIN],
  },
  {
    label: "Unidades",
    to: "/catalogos/unidades",
    icon: Building2,
    roles: [ROLES.SUPER_ADMIN],
  },
  {
    label: "Usuarios",
    to: "/usuarios",
    icon: UserCog,
    roles: [ROLES.SUPER_ADMIN],
  },
];

const rolLabel = {
  SUPER_ADMIN: "Super Administrador",
  ADMIN_ESTATAL: "Administrador Estatal",
  RESPONSABLE_UNIDAD: "Responsable de Unidad",
};

export default function Sidebar() {
  const { rolNombre, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    toast.success("Sesión cerrada.");
    navigate("/login", { replace: true });
  };

  const itemsVisibles = navItems.filter((item) => item.roles.includes(rolNombre));

  return (
    <aside className="w-52 min-h-screen bg-secondary-dark flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/10">
        <img
          src="/shared/logos/logohorizontal2.png"
          alt="IMSS Bienestar"
          className="w-full object-contain max-h-12"
        />
        <p className="text-white/70 text-xs mt-2 text-center tracking-wide">
          Medicamentos Huérfanos
        </p>
      </div>

      {/* Rol del usuario */}
      <div className="px-6 py-4 border-b border-white/10">
        <p className="text-white/40 text-xs uppercase tracking-widest mb-1">Rol</p>
        <p className="text-white/80 text-xs font-medium">{rolLabel[rolNombre] || rolNombre}</p>
      </div>

      {/* Navegación */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {itemsVisibles.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary text-white"
                  : "text-white/60 hover:bg-white/10 hover:text-white"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="px-3 py-4 border-t border-white/10">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
            text-white/60 hover:bg-white/10 hover:text-white transition-colors"
        >
          <LogOut size={18} />
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
