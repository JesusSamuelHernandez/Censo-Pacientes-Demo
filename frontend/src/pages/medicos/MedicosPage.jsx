/**
 * MedicosPage.jsx — Lista de médicos con búsqueda y acciones.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserPlus, Search, Eye, Pencil } from "lucide-react";
import { toast } from "sonner";

import { listarMedicos } from "../../api/medicos";
import useAuthStore from "../../store/authStore";

const ROLES_PUEDEN_CREAR = ["SUPER_ADMIN", "RESPONSABLE_UNIDAD"];
const ROLES_PUEDEN_EDITAR = ["SUPER_ADMIN"];

export default function MedicosPage() {
  const navigate = useNavigate();
  const { rolNombre } = useAuthStore();

  const [medicos, setMedicos] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listarMedicos()
      .then(setMedicos)
      .catch(() => toast.error("Error al cargar la lista de médicos."))
      .finally(() => setLoading(false));
  }, []);

  const medicosFiltrados = medicos.filter((m) =>
    busqueda
      ? m.nombre_medico.toLowerCase().includes(busqueda.toLowerCase()) ||
        m.cedula.toLowerCase().includes(busqueda.toLowerCase()) ||
        m.clues_adscripcion.toLowerCase().includes(busqueda.toLowerCase())
      : true
  );

  return (
    <div className="space-y-4">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">Médicos</h2>
          <p className="text-sm text-neutral-gray mt-0.5">{medicos.length} médicos registrados</p>
        </div>
        {ROLES_PUEDEN_CREAR.includes(rolNombre) && (
          <button
            onClick={() => navigate("/medicos/nuevo")}
            className="flex items-center gap-2 bg-primary hover:bg-primary-dark text-white
              text-sm font-medium px-4 py-2 rounded-lg transition"
          >
            <UserPlus size={16} />
            Registrar médico
          </button>
        )}
      </div>

      {/* Búsqueda */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 px-4 py-3">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-gray" />
          <input
            type="text"
            placeholder="Buscar por nombre, cédula o CLUES..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-neutral-gray/30
              bg-neutral-light outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-light border-b border-neutral-gray/20">
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Nombre</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Cédula</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Correo</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Unidad (CLUES)</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="text-center py-12">
                    <div className="flex justify-center">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                  </td>
                </tr>
              ) : medicosFiltrados.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-neutral-gray">
                    No se encontraron médicos.
                  </td>
                </tr>
              ) : (
                medicosFiltrados.map((m) => (
                  <tr key={m.id_medico} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-4 py-3 font-medium text-neutral-black">{m.nombre_medico}</td>
                    <td className="px-4 py-3 font-mono text-xs text-neutral-gray">{m.cedula}</td>
                    <td className="px-4 py-3 text-neutral-gray">{m.email ?? "—"}</td>
                    <td className="px-4 py-3 text-neutral-gray font-mono text-xs">{m.clues_adscripcion}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {ROLES_PUEDEN_EDITAR.includes(rolNombre) && (
                          <button
                            onClick={() => navigate(`/medicos/${m.id_medico}/editar`)}
                            className="p-1.5 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
                            title="Editar"
                          >
                            <Pencil size={15} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
