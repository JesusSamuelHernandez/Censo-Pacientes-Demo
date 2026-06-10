/**
 * PacientesPage.jsx — Lista paginada de pacientes con búsqueda, filtro por medicamento y acciones.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ChevronLeft, ChevronRight, Eye, UserX } from "lucide-react";
import { toast } from "sonner";

import { listarPacientes, darBajaPaciente } from "../../api/pacientes";
import { listarMedicamentos } from "../../api/catalogos";
import useAuthStore from "../../store/authStore";
import BanderinEstado from "../../components/shared/BanderinEstado";

const ROLES_PUEDEN_CREAR = ["SUPER_ADMIN", "RESPONSABLE_UNIDAD"];

export default function PacientesPage() {
  const navigate = useNavigate();
  const { rolNombre } = useAuthStore();

  const [pacientes, setPacientes] = useState([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [busqueda, setBusqueda] = useState("");
  const [soloActivos, setSoloActivos] = useState(true);
  const [filtroClaveCnis, setFiltroClaveCnis] = useState("");
  const [medicamentos, setMedicamentos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [confirmBaja, setConfirmBaja] = useState(null);

  const porPagina = 20;
  const totalPaginas = Math.ceil(total / porPagina);

  // Carga el catálogo de medicamentos para el filtro (solo una vez)
  useEffect(() => {
    listarMedicamentos()
      .then(setMedicamentos)
      .catch(() => {});
  }, []);

  const cargar = async () => {
    setLoading(true);
    try {
      const data = await listarPacientes({
        pagina,
        porPagina,
        soloActivos,
        claveCnis: filtroClaveCnis || null,
      });
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
  }, [pagina, soloActivos, filtroClaveCnis]);

  const pacientesFiltrados = pacientes.filter((p) =>
    busqueda
      ? p.nombre_completo.toLowerCase().includes(busqueda.toLowerCase()) ||
        p.curp_paciente.toLowerCase().includes(busqueda.toLowerCase())
      : true
  );

  const handleEstatusEvolucionCambiado = (curp, nuevoEstatus) => {
    setPacientes((prev) =>
      prev.map((p) => (p.curp_paciente === curp ? { ...p, estatus_evolucion: nuevoEstatus } : p))
    );
  };

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
          <h2 className="text-xl font-semibold text-neutral-black">
            {soloActivos ? "Pacientes Activos" : "Padrón de Pacientes"}
          </h2>
          <p className="text-sm text-neutral-gray mt-0.5">
            {total} {soloActivos ? "paciente(s) con prescripción activa" : "paciente(s) registrado(s)"}
          </p>
        </div>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-3 bg-white rounded-xl border border-neutral-gray/20 px-4 py-3">
        {/* Búsqueda por nombre/CURP */}
        <div className="flex-1 min-w-[200px] relative">
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

        {/* Filtro por medicamento */}
        <select
          value={filtroClaveCnis}
          onChange={(e) => { setFiltroClaveCnis(e.target.value); setPagina(1); }}
          className="px-3 py-2 text-sm rounded-lg border border-neutral-gray/30 bg-neutral-light
            outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary min-w-[200px]"
        >
          <option value="">— Todos los medicamentos —</option>
          {medicamentos.map((m) => (
            <option key={m.clave_cnis} value={m.clave_cnis}>
              {m.clave_cnis} — {m.descripcion.slice(0, 50)}
            </option>
          ))}
        </select>

        {/* Solo activos */}
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
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Medicamentos activos</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Adherencia</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Estado</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12">
                    <div className="flex justify-center">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                  </td>
                </tr>
              ) : pacientesFiltrados.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-neutral-gray">
                    No se encontraron pacientes.
                  </td>
                </tr>
              ) : (
                pacientesFiltrados.map((p) => (
                  <tr key={p.curp_paciente} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-4 py-3 font-medium text-neutral-black">
                      <div className={`relative ${soloActivos ? "pl-5" : ""}`}>
                        {soloActivos && (
                          <BanderinEstado
                            curp={p.curp_paciente}
                            estatus={p.estatus_evolucion}
                            onChange={(nuevo) => handleEstatusEvolucionCambiado(p.curp_paciente, nuevo)}
                          />
                        )}
                        <span title={p.nombre_completo}>{p.nombre_completo}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-neutral-gray font-mono text-xs">{p.curp_paciente}</td>
                    <td className="px-4 py-3 text-neutral-gray text-xs">{p.clues_unidad_adscripcion}</td>

                    {/* Columna de medicamentos activos */}
                    <td className="px-4 py-3">
                      {p.medicamentos_activos && p.medicamentos_activos.length > 0 ? (
                        <div className="flex flex-col gap-1">
                          {p.medicamentos_activos.slice(0, 2).map((med, i) => (
                            <span
                              key={i}
                              title={med}
                              className="inline-flex items-center px-2 py-0.5 rounded-md text-xs
                                bg-primary/10 text-primary font-medium max-w-[180px] truncate"
                            >
                              {med}
                            </span>
                          ))}
                          {p.medicamentos_activos.length > 2 && (
                            <span
                              title={p.medicamentos_activos.slice(2).join("\n")}
                              className="text-xs text-neutral-gray cursor-default"
                            >
                              +{p.medicamentos_activos.length - 2} más
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-neutral-gray">—</span>
                      )}
                    </td>

                    <td className="px-4 py-3">
                      {p.dias_adherencia != null ? (
                        <span className="text-secondary font-medium">{p.dias_adherencia} días</span>
                      ) : (
                        <span className="text-neutral-gray">—</span>
                      )}
                    </td>

                    <td className="px-4 py-3">
                      {!p.es_activo ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-gray/10 text-neutral-gray">
                          Baja
                        </span>
                      ) : p.tiene_prescripcion_activa ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary/10 text-secondary">
                          Activo
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                          Sin prescripción activa
                        </span>
                      )}
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
