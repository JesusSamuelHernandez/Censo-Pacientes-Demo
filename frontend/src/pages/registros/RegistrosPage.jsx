/**
 * RegistrosPage.jsx — Lista paginada de prescripciones (registros) con filtros y acciones.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FilePlus, Search, ChevronLeft, ChevronRight, Eye, Pencil, Trash2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { listarRegistros, anularRegistro, validarContinuidad } from "../../api/registros";
import useAuthStore from "../../store/authStore";

const ROLES_PUEDEN_CREAR = ["SUPER_ADMIN", "RESPONSABLE_UNIDAD"];

/**
 * Determina el estado visual de un registro.
 * - "activa"  : es_activo = true
 * - "vencida" : es_activo = false, fecha_fin_tratamiento + 30 días <= hoy (expiró por tiempo)
 * - "anulada" : es_activo = false, fue cancelada manualmente o no tiene fecha_fin
 */
function getEstadoRegistro(r) {
  if (r.es_activo) return { label: "Activa", classes: "bg-secondary/10 text-secondary" };
  if (r.fecha_fin_tratamiento) {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const limite = new Date(r.fecha_fin_tratamiento);
    limite.setDate(limite.getDate() + 30);
    limite.setHours(0, 0, 0, 0);
    if (limite <= hoy) return { label: "Vencida", classes: "bg-red-100 text-red-700" };
  }
  return { label: "Anulada", classes: "bg-neutral-gray/10 text-neutral-gray" };
}

export default function RegistrosPage() {
  const navigate = useNavigate();
  const { rolNombre } = useAuthStore();

  const [registros, setRegistros] = useState([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [busqueda, setBusqueda] = useState("");
  const [soloActivos, setSoloActivos] = useState(true);
  const [loading, setLoading] = useState(true);
  const [confirmAnular, setConfirmAnular] = useState(null);

  // Modal de validación de continuidad
  const [modalValidar, setModalValidar] = useState(null); // { id_registro, medicamento }
  const [nuevaFecha, setNuevaFecha] = useState("");

  const porPagina = 20;
  const totalPaginas = Math.ceil(total / porPagina);

  const cargar = async () => {
    setLoading(true);
    try {
      const data = await listarRegistros({ pagina, porPagina, soloActivos });
      setRegistros(data.resultados);
      setTotal(data.total);
    } catch {
      toast.error("Error al cargar las prescripciones.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
  }, [pagina, soloActivos]);

  const registrosFiltrados = registros.filter((r) =>
    busqueda
      ? String(r.id_registro).includes(busqueda) ||
        r.medico?.nombre_medico?.toLowerCase().includes(busqueda.toLowerCase()) ||
        r.clave_cnis.toLowerCase().includes(busqueda.toLowerCase())
      : true
  );

  const handleAnular = async () => {
    if (!confirmAnular) return;
    try {
      await anularRegistro(confirmAnular);
      toast.success("Prescripción anulada correctamente.");
      setConfirmAnular(null);
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al anular la prescripción.");
      setConfirmAnular(null);
    }
  };

  const handleValidarContinuidad = async () => {
    if (!modalValidar || !nuevaFecha) return;
    try {
      await validarContinuidad(modalValidar.id_registro, nuevaFecha);
      toast.success("Continuidad validada. Prescripción reactivada.");
      setModalValidar(null);
      setNuevaFecha("");
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al validar la continuidad.");
    }
  };

  return (
    <div className="space-y-4">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">Registrar Paciente</h2>
          <p className="text-sm text-neutral-gray mt-0.5">{total} prescripciones registradas</p>
        </div>
        {ROLES_PUEDEN_CREAR.includes(rolNombre) && (
          <button
            onClick={() => navigate("/registros/nuevo")}
            className="flex items-center gap-2 bg-primary hover:bg-primary-dark text-white
              text-sm font-medium px-4 py-2 rounded-lg transition"
          >
            <FilePlus size={16} />
            Registrar Paciente
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-3 bg-white rounded-xl border border-neutral-gray/20 px-4 py-3">
        <div className="flex-1 relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-gray" />
          <input
            type="text"
            placeholder="Buscar por ID, médico o clave CNIS..."
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
          Solo activas
        </label>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-light border-b border-neutral-gray/20">
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">ID</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Medicamento</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Médico</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Paciente</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Unidad</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Inicio</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Estado</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-12">
                    <div className="flex justify-center">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                  </td>
                </tr>
              ) : registrosFiltrados.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-neutral-gray">
                    No se encontraron prescripciones.
                  </td>
                </tr>
              ) : (
                registrosFiltrados.map((r) => (
                  <tr key={r.id_registro} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-4 py-3 font-mono text-xs text-neutral-gray">#{r.id_registro}</td>
                    <td className="px-4 py-3">
                      <p className="font-mono text-xs text-neutral-gray">{r.clave_cnis}</p>
                      <p className="text-xs text-neutral-black truncate max-w-[200px]">
                        {r.medicamento?.descripcion ?? "—"}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-neutral-black text-xs">
                      {r.medico?.nombre_medico ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      {r.nombre_paciente ? (
                        <button
                          onClick={() => navigate(`/pacientes/${r.curp_paciente}`, {
                            state: { from: "registros-list" }
                          })}
                          className="text-left hover:text-primary transition"
                        >
                          <p className="text-xs font-medium text-neutral-black">{r.nombre_paciente}</p>
                          <p className="text-xs font-mono text-neutral-gray">{r.curp_paciente}</p>
                        </button>
                      ) : (
                        <span className="text-xs text-neutral-gray">#{r.id_paciente}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-neutral-gray">{r.clues}</td>
                    <td className="px-4 py-3 text-neutral-gray text-xs">
                      {r.fecha_inicio_tratamiento ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      {(() => { const e = getEstadoRegistro(r); return (
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${e.classes}`}>
                          {e.label}
                        </span>
                      ); })()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {/* Ver detalle */}
                        <button
                          onClick={() => navigate(`/registros/${r.id_registro}`)}
                          className="p-1.5 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
                          title="Ver detalle"
                        >
                          <Eye size={15} />
                        </button>
                        {ROLES_PUEDEN_CREAR.includes(rolNombre) && r.es_activo && (
                          <>
                            <button
                              onClick={() => navigate(`/registros/${r.id_registro}/editar`)}
                              className="p-1.5 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
                              title="Editar"
                            >
                              <Pencil size={15} />
                            </button>
                            <button
                              onClick={() => setConfirmAnular(r.id_registro)}
                              className="p-1.5 rounded-lg text-neutral-gray hover:text-red-600 hover:bg-red-50 transition"
                              title="Anular prescripción"
                            >
                              <Trash2 size={15} />
                            </button>
                          </>
                        )}
                        {ROLES_PUEDEN_CREAR.includes(rolNombre) && getEstadoRegistro(r).label === "Vencida" && (
                          <button
                            onClick={() => {
                              setModalValidar({ id_registro: r.id_registro, medicamento: r.medicamento?.descripcion ?? r.clave_cnis });
                              setNuevaFecha("");
                            }}
                            className="flex items-center gap-1 p-1.5 rounded-lg text-neutral-gray hover:text-secondary hover:bg-secondary/10 transition text-xs"
                            title="Validar continuidad"
                          >
                            <RefreshCw size={14} />
                            Validar
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

      {/* Modal de validación de continuidad */}
      {modalValidar && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 space-y-4">
            <div>
              <h3 className="text-base font-semibold text-neutral-black">Validar continuidad</h3>
              <p className="text-sm text-neutral-gray mt-1 truncate">
                {modalValidar.medicamento}
              </p>
            </div>
            <p className="text-sm text-neutral-gray">
              Indica la nueva fecha de fin de tratamiento. El registro se reactivará y el
              contador de 30 días se reiniciará desde esa fecha.
            </p>
            <div>
              <label className="block text-xs font-medium text-neutral-gray mb-1">
                Nueva fecha de fin de tratamiento <span className="text-primary">*</span>
              </label>
              <input
                type="date"
                value={nuevaFecha}
                onChange={(e) => setNuevaFecha(e.target.value)}
                min={new Date().toISOString().slice(0, 10)}
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
            </div>
            <div className="flex gap-3 pt-1">
              <button
                onClick={() => { setModalValidar(null); setNuevaFecha(""); }}
                className="flex-1 px-4 py-2 rounded-lg border border-neutral-gray/30
                  text-sm text-neutral-gray hover:bg-neutral-light transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleValidarContinuidad}
                disabled={!nuevaFecha}
                className="flex-1 px-4 py-2 rounded-lg bg-secondary hover:bg-secondary-dark
                  text-white text-sm font-medium transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal confirmación de anulación */}
      {confirmAnular && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="text-base font-semibold text-neutral-black mb-2">¿Anular esta prescripción?</h3>
            <p className="text-sm text-neutral-gray mb-1">ID: <span className="font-mono">#{confirmAnular}</span></p>
            <p className="text-sm text-neutral-gray mb-6">
              La prescripción quedará marcada como anulada. Esta acción es por error de captura.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmAnular(null)}
                className="flex-1 px-4 py-2 rounded-lg border border-neutral-gray/30
                  text-sm text-neutral-gray hover:bg-neutral-light transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleAnular}
                className="flex-1 px-4 py-2 rounded-lg bg-primary-dark hover:bg-primary
                  text-white text-sm font-medium transition"
              >
                Confirmar anulación
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
