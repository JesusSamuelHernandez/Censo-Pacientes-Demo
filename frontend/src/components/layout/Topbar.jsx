/**
 * Topbar.jsx — Barra superior con título de página y datos del usuario.
 */
import { useLocation } from "react-router-dom";
import { User } from "lucide-react";
import useAuthStore from "../../store/authStore";

const titulos = {
  "/pacientes": "Pacientes",
  "/medicos": "Médicos",
  "/recetas": "Recetas",
  "/reportes": "Reportes",
  "/catalogos/medicamentos": "Catálogo de Medicamentos",
  "/catalogos/unidades": "Unidades Médicas",
  "/usuarios": "Usuarios",
};

export default function Topbar() {
  const { pathname } = useLocation();
  const { rolNombre } = useAuthStore();

  const titulo = Object.entries(titulos).find(([ruta]) =>
    pathname.startsWith(ruta)
  )?.[1] ?? "Inicio";

  return (
    <header className="h-14 bg-white border-b border-neutral-gray/20 flex items-center justify-between px-6">
      <h1 className="text-neutral-black font-semibold text-base">{titulo}</h1>
      <div className="flex items-center gap-2 text-sm text-neutral-gray">
        <User size={16} />
        <span>{rolNombre}</span>
      </div>
    </header>
  );
}
