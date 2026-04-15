/**
 * PacientesPage.jsx — Lista paginada de pacientes con búsqueda y acciones.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserPlus, Search, ChevronLeft, ChevronRight, Eye, UserX } from "lucide-react";
import { toast } from "sonner";

import { listarPacientes, darBajaPaciente } from "../../api/pacientes";
import useAuthStore from "../../store/authStore";

const ROLES_PUEDEN_CREAR = ["SUPER_ADMIN", "RESPONSABLE_UNIDAD"];

export default function PacientesPage() {
  const navigate = useNavigate();
  const { rolNombre } = useAuthStore();

  const [pacientes, setPacientes] = useState([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [busqueda, setBusqueda] = useState("");
  const [soloActivos, setSoloActivos] = useState(true);
  const [loading, setLoading] = useState(true);
  const [confirmBaja, setConfirmBaja] = useState(null); // curp del paciente a dar de baja

  const porPagina = 20;
  const totalPaginas = Math.ceil(total / porPagina);

  const cargar = async () => {
    setLoading(true);
    try {
      const data = await listarPacientes({ pagina, porPagina, soloActivos });
      setPacientes(data.resultados);
      setTotal(data.total);
    } catch {
      toast.error("Error al cargar la lista de pacientes.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
  }, [pagina, soloActivos]);

  const pacientesFiltrados = pacientes.filter((p) =>
    busqueda
      ? p.nombre_completo.toLowerCase().includes(busqueda.toLowerCase()) ||
        p.curp_paciente.toLowerCase().includes(busqueda.toLowerCase())
      : true
  );

  const handleBaja = async () => {
    if (!confirmBaja) return;
    try {
      await darBajaPaciente(confirmBaja);
      toast.success("Paciente dado de baja correctamente.");
      setConfirmBaja(null);
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al dar de baja al paciente.");
      setConfirmBaja(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">Padrón de Pacientes</h2>
          <p className="text-sm text-neutral-gray mt-0.5">{total} pacientes registrados</p>
        </div>
        {ROLES_PUEDEN_CREAR.includes(rolNombre) && (
          <button
            onClick={() => navigate("/pacientes/nuevo")}
            className="flex items-center gap-2 bg-primary hover:bg-primary-dark text-white
              text-sm font-medium px-4 py-2 rounded-lg transition"
          >
            <UserPlus size={16} />
            Registrar paciente
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-3 bg-white rounded-xl border border-neutral-gray/20 px-4 py-3">
        <div className="flex-1 relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-gray" />
          <input
            type="text"
            placeholder="Buscar por nombre o CURP..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-neutral-gray/30
              bg-neutral-light outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-neutral-gray cursor-pointer select-none">
          <input
            type="checkbox"
            checked={soloActivos}
            onChange={(e) => { setSoloActivos(e.target.checked); setPagina(1); }}
            className="accent-primary w-4 h-4"
          />
          Solo activos
        </label>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-light border-b border-neutral-gray/20">
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Nombre</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">CURP</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Unidad</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Adherencia</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Estado</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-neutral-gray">
                    <div className="flex justify-center">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                  </td>
                </tr>
              ) : pacientesFiltrados.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-neutral-gray">
                    No se encontraron pacientes.
                  </td>
                </tr>
              ) : (
                pacientesFiltrados.map((p) => (
                  <tr key={p.curp_paciente} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-4 py-3 font-medium text-neutral-black">{p.nombre_completo}</td>
                    <td className="px-4 py-3 text-neutral-gray font-mono text-xs">{p.curp_paciente}</td>
                    <td className="px-4 py-3 text-neutral-gray">{p.clues_unidad_adscripcion}</td>
                    <td className="px-4 py-3">
                      {p.dias_adherencia != null ? (
                        <span className="text-secondary font-medium">{p.dias_adherencia} días</span>
                      ) : (
                        <span className="text-neutral-gray">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${p.es_activo
                          ? "bg-secondary/10 text-secondary"
                          : "bg-neutral-gray/10 text-neutral-gray"}`}>
                        {p.es_activo ? "Activo" : "Baja"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => navigate(`/pacientes/${p.curp_paciente}`)}
                          className="p-1.5 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
                          title="Ver detalle"
                        >
                          <Eye size={15} />
                        </button>
                        {ROLES_PUEDEN_CREAR.includes(rolNombre) && p.es_activo && (
                          <button
                            onClick={() => setConfirmBaja(p.curp_paciente)}
                            className="p-1.5 rounded-lg text-neutral-gray hover:text-red-600 hover:bg-red-50 transition"
                            title="Dar de baja"
                          >
                            <UserX size={15} />
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

        {/* Paginación */}
        {totalPaginas > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-neutral-gray/10">
            <p className="text-xs text-neutral-gray">
              Página {pagina} de {totalPaginas}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPagina((p) => Math.max(1, p - 1))}
                disabled={pagina === 1}
                className="p-1.5 rounded-lg border border-neutral-gray/30 text-neutral-gray
                  hover:border-primary hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                <ChevronLeft size={15} />
              </button>
              <button
                onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
                disabled={pagina === totalPaginas}
                className="p-1.5 rounded-lg border border-neutral-gray/30 text-neutral-gray
                  hover:border-primary hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                <ChevronRight size={15} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal de confirmación de baja */}
      {confirmBaja && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="text-base font-semibold text-neutral-black mb-2">¿Dar de baja al paciente?</h3>
            <p className="text-sm text-neutral-gray mb-6">
              Esta acción marcará al paciente como inactivo. No se eliminará de la base de datos.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmBaja(null)}
                className="flex-1 px-4 py-2 rounded-lg border border-neutral-gray/30
                  text-sm text-neutral-gray hover:bg-neutral-light transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleBaja}
                className="flex-1 px-4 py-2 rounded-lg bg-primary-dark hover:bg-primary
                  text-white text-sm font-medium transition"
              >
                Confirmar baja
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
