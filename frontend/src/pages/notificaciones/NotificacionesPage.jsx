/**
 * NotificacionesPage.jsx — Dos pestañas: Prescripciones (continuidad) y Traslados.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell, RefreshCw, CheckCircle, AlertTriangle, Clock, Eye,
  ArrowRightLeft, ClipboardList,
} from "lucide-react";
import { toast } from "sonner";

import { listarNotificaciones, listarNotificacionesTraslados, marcarTrasladoLeido } from "../../api/notificaciones";
import { validarContinuidad } from "../../api/registros";
import useAuthStore from "../../store/authStore";

// Badge de urgencia para prescripciones
function getBadgePrescripcion(diasRestantes, esActivo) {
  if (!esActivo) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
        <AlertTriangle size={11} />
        Vencida hace {Math.abs(diasRestantes)} día(s)
      </span>
    );
  }
  if (diasRestantes <= 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
        <AlertTriangle size={11} />
        Vence hoy
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
      <Clock size={11} />
      Vence en {diasRestantes} día(s)
    </span>
  );
}

const ROLES_CON_TRASLADOS = ["SUPER_ADMIN", "RESPONSABLE_UNIDAD"];

export default function NotificacionesPage() {
  const { rolNombre } = useAuthStore();
  const [tab, setTab] = useState("prescripciones");
  const [totalPrescripciones, setTotalPrescripciones] = useState(0);
  const [totalTraslados, setTotalTraslados] = useState(0);

  const tieneTraslados = ROLES_CON_TRASLADOS.includes(rolNombre);

  return (
    <div className="space-y-4">
      {/* Encabezado */}
      <div>
        <h2 className="text-xl font-semibold text-neutral-black">Notificaciones</h2>
        <p className="text-sm text-neutral-gray mt-0.5">
          Alertas y traslados que requieren tu atención
        </p>
      </div>

      {/* Pestañas */}
      <div className="flex gap-1 bg-white border border-neutral-gray/20 rounded-xl p-1 w-fit">
        <TabBtn activo={tab === "prescripciones"} onClick={() => setTab("prescripciones")} icon={ClipboardList} count={totalPrescripciones}>
          Prescripciones
        </TabBtn>
        {tieneTraslados && (
          <TabBtn activo={tab === "traslados"} onClick={() => setTab("traslados")} icon={ArrowRightLeft} count={totalTraslados}>
            Traslados
          </TabBtn>
        )}
      </div>

      {tab === "prescripciones" && (
        <TabPrescripciones onTotal={setTotalPrescripciones} />
      )}
      {tab === "traslados" && tieneTraslados && (
        <TabTraslados onTotal={setTotalTraslados} />
      )}
    </div>
  );
}

// ── Botón de pestaña ──────────────────────────────────────────────────────────
function TabBtn({ activo, onClick, icon: Icon, count, children }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition
        ${activo ? "bg-primary text-white" : "text-neutral-gray hover:text-neutral-black hover:bg-neutral-light"}`}
    >
      <Icon size={15} />
      {children}
      {count > 0 && (
        <span className={`min-w-[18px] h-[18px] px-1 rounded-full text-xs font-bold flex items-center justify-center
          ${activo ? "bg-white text-primary" : "bg-red-500 text-white"}`}>
          {count > 99 ? "99+" : count}
        </span>
      )}
    </button>
  );
}

// ── Pestaña Prescripciones ────────────────────────────────────────────────────
function TabPrescripciones({ onTotal }) {
  const navigate = useNavigate();
  const [notificaciones, setNotificaciones] = useState([]);
  const [loading, setLoading] = useState(true);

  const [modalValidar, setModalValidar] = useState(null);
  const [nuevaFecha, setNuevaFecha] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = async () => {
    setLoading(true);
    try {
      const data = await listarNotificaciones();
      setNotificaciones(data.resultados);
      onTotal(data.total);
    } catch {
      toast.error("Error al cargar las notificaciones.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, []);

  const handleValidar = async () => {
    if (!modalValidar) return;
    const tienePosologia = modalValidar.duracion && modalValidar.unidad_tiempo;
    if (!tienePosologia && !nuevaFecha) return;
    setGuardando(true);
    try {
      await validarContinuidad(modalValidar.id_registro, tienePosologia ? null : nuevaFecha);
      toast.success("Continuidad validada. Prescripción reactivada.");
      setModalValidar(null);
      setNuevaFecha("");
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al validar la continuidad.");
    } finally {
      setGuardando(false);
    }
  };

  // Calcula la nueva fecha fin desde hoy usando la duración guardada
  const calcularNuevaFechaFin = (duracion, unidad_tiempo) => {
    if (!duracion || !unidad_tiempo) return null;
    const factor = { días: 1, semanas: 7, meses: 30 }[unidad_tiempo] ?? 1;
    const fecha = new Date();
    // - 1 porque fecha_fin_tratamiento es exclusiva; mostramos el último día real
    fecha.setDate(fecha.getDate() + duracion * factor - 1);
    return fecha.toLocaleDateString("es-MX", { dateStyle: "long" });
  };

  return (
    <>
      <div className="flex justify-end">
        <button
          onClick={cargar}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-neutral-gray/30
            text-sm text-neutral-gray hover:bg-neutral-light transition"
        >
          <RefreshCw size={14} />
          Actualizar
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-48">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : notificaciones.length === 0 ? (
        <div className="bg-white rounded-xl border border-neutral-gray/20 p-12 flex flex-col items-center gap-3">
          <CheckCircle size={40} className="text-secondary" />
          <p className="text-neutral-black font-medium">Todo al día</p>
          <p className="text-sm text-neutral-gray text-center">
            No hay prescripciones pendientes de validación en los próximos 7 días.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-3 flex items-center gap-3">
            <Bell size={18} className="text-amber-600 flex-shrink-0" />
            <p className="text-sm text-amber-800">
              <span className="font-semibold">{notificaciones.length}</span> prescripción(es) requieren tu atención.
            </p>
          </div>

          <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-neutral-light border-b border-neutral-gray/20">
                    <th className="text-left px-4 py-3 font-semibold text-neutral-black">Paciente</th>
                    <th className="text-left px-4 py-3 font-semibold text-neutral-black">Medicamento</th>
                    <th className="text-left px-4 py-3 font-semibold text-neutral-black">Fin tratamiento</th>
                    <th className="text-left px-4 py-3 font-semibold text-neutral-black">Límite validación</th>
                    <th className="text-left px-4 py-3 font-semibold text-neutral-black">Estado</th>
                    <th className="text-left px-4 py-3 font-semibold text-neutral-black">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {notificaciones.map((n) => (
                    <tr
                      key={n.id_registro}
                      className={`border-b border-neutral-gray/10 hover:bg-neutral-light/60 ${!n.es_activo ? "bg-red-50/30" : ""}`}
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-neutral-black text-sm">{n.nombre_paciente}</p>
                        <p className="text-xs text-neutral-gray">ID #{n.id_paciente}</p>
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-mono text-xs text-neutral-gray">{n.clave_cnis}</p>
                        <p
                          title={n.descripcion_medicamento}
                          className="text-xs text-neutral-black truncate max-w-[200px]"
                        >
                          {n.descripcion_medicamento ?? "—"}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-sm text-neutral-gray">{n.fecha_fin_tratamiento}</td>
                      <td className="px-4 py-3 text-sm font-medium text-neutral-black">{n.fecha_limite}</td>
                      <td className="px-4 py-3">{getBadgePrescripcion(n.dias_restantes, n.es_activo)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => navigate(`/registros/${n.id_registro}`, { state: { from: "notificaciones" } })}
                            className="p-1.5 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
                            title="Ver detalle"
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            onClick={() => { setModalValidar({ id_registro: n.id_registro, nombre: n.nombre_paciente, medicamento: n.descripcion_medicamento ?? n.clave_cnis, duracion: n.duracion ?? null, unidad_tiempo: n.unidad_tiempo ?? null }); setNuevaFecha(""); }}
                            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                              bg-secondary/10 text-secondary hover:bg-secondary/20 transition"
                            title="Validar continuidad"
                          >
                            <RefreshCw size={12} />
                            Validar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Modal de validación rápida */}
      {modalValidar && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 space-y-4">
            <div>
              <h3 className="text-base font-semibold text-neutral-black">Validar continuidad</h3>
              <p className="text-sm font-medium text-neutral-black mt-1">{modalValidar.nombre}</p>
              <p className="text-xs text-neutral-gray">{modalValidar.medicamento}</p>
            </div>

            {modalValidar.duracion && modalValidar.unidad_tiempo ? (
              <div className="bg-secondary/5 border border-secondary/20 rounded-lg px-4 py-3 space-y-1">
                <p className="text-xs text-neutral-gray uppercase tracking-wide font-semibold">
                  Duración del tratamiento
                </p>
                <p className="text-sm font-medium text-neutral-black">
                  {modalValidar.duracion} {modalValidar.unidad_tiempo}
                </p>
                <p className="text-xs text-neutral-gray">
                  Nueva fecha de fin estimada:{" "}
                  <span className="font-semibold text-neutral-black">
                    {calcularNuevaFechaFin(modalValidar.duracion, modalValidar.unidad_tiempo)}
                  </span>
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm text-neutral-gray mb-3">
                  Este registro no tiene posología guardada. Indica manualmente la nueva fecha de fin.
                </p>
                <label className="block text-xs font-medium text-neutral-gray mb-1">
                  Nueva fecha de fin <span className="text-primary">*</span>
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
            )}

            <div className="flex gap-3 pt-1">
              <button
                onClick={() => { setModalValidar(null); setNuevaFecha(""); }}
                className="flex-1 px-4 py-2 rounded-lg border border-neutral-gray/30
                  text-sm text-neutral-gray hover:bg-neutral-light transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleValidar}
                disabled={(!modalValidar.duracion && !nuevaFecha) || guardando}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg
                  bg-secondary hover:bg-secondary-dark text-white text-sm font-medium transition
                  disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {guardando
                  ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <CheckCircle size={14} />}
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ── Pestaña Traslados ─────────────────────────────────────────────────────────
function TabTraslados({ onTotal }) {
  const navigate = useNavigate();
  const [traslados, setTraslados] = useState([]);
  const [loading, setLoading] = useState(true);
  const [aceptando, setAceptando] = useState(null);

  const cargar = async () => {
    setLoading(true);
    try {
      const data = await listarNotificacionesTraslados();
      setTraslados(data.resultados);
      onTotal(data.total);
    } catch {
      // El rol ADMIN_ESTATAL recibe 403 — no mostramos error, solo lista vacía
      setTraslados([]);
      onTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, []);

  const handleEnterado = async (id) => {
    setAceptando(id);
    try {
      await marcarTrasladoLeido(id);
      toast.success("Traslado aceptado. La notificación ha sido retirada.");
      cargar();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al aceptar el traslado.");
    } finally {
      setAceptando(null);
    }
  };

  return (
    <>
      <div className="flex justify-end">
        <button
          onClick={cargar}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-neutral-gray/30
            text-sm text-neutral-gray hover:bg-neutral-light transition"
        >
          <RefreshCw size={14} />
          Actualizar
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-48">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : traslados.length === 0 ? (
        <div className="bg-white rounded-xl border border-neutral-gray/20 p-12 flex flex-col items-center gap-3">
          <CheckCircle size={40} className="text-secondary" />
          <p className="text-neutral-black font-medium">Sin traslados pendientes</p>
          <p className="text-sm text-neutral-gray text-center">
            No hay pacientes transferidos pendientes de aceptar.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-3 flex items-center gap-3">
            <ArrowRightLeft size={18} className="text-blue-600 flex-shrink-0" />
            <p className="text-sm text-blue-800">
              <span className="font-semibold">{traslados.length}</span> paciente(s) transferido(s) a otra unidad. Da clic en "Enterado" para confirmar.
            </p>
          </div>

          <div className="space-y-3">
            {traslados.map((t) => (
              <div
                key={t.id}
                className="bg-white rounded-xl border border-neutral-gray/20 p-5 flex flex-col sm:flex-row sm:items-center gap-4"
              >
                {/* Info del paciente */}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-neutral-black">{t.nombre_paciente}</p>
                    <span className="font-mono text-xs text-neutral-gray">{t.curp_paciente}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-neutral-gray">
                    <span>
                      <span className="text-neutral-black/60">Destino:</span>{" "}
                      <span className="font-medium text-neutral-black">
                        {t.nombre_unidad_destino ?? t.clues_unidad_destino}
                      </span>
                    </span>
                    <span>
                      <span className="text-neutral-black/60">Trasladó:</span>{" "}
                      {t.nombre_usuario_traslado ?? "—"}
                    </span>
                    <span>
                      <span className="text-neutral-black/60">Fecha:</span>{" "}
                      {new Date(t.fecha_traslado).toLocaleString("es-MX", {
                        dateStyle: "medium", timeStyle: "short",
                      })}
                    </span>
                  </div>
                </div>

                {/* Acciones */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => navigate(`/pacientes/${t.curp_paciente}`)}
                    className="p-2 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
                    title="Ver historial del paciente"
                  >
                    <Eye size={15} />
                  </button>
                  <button
                    onClick={() => handleEnterado(t.id)}
                    disabled={aceptando === t.id}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium
                      bg-secondary/10 text-secondary hover:bg-secondary/20 transition
                      disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {aceptando === t.id
                      ? <span className="w-3.5 h-3.5 border-2 border-secondary border-t-transparent rounded-full animate-spin" />
                      : <CheckCircle size={14} />}
                    Enterado
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
