/**
 * NotificacionesPage.jsx — Registros que requieren validación de continuidad.
 * Muestra prescripciones vencidas o por vencer en los próximos 7 días.
 */
import { useEffect, useState } from "react";
import { Bell, RefreshCw, CheckCircle, AlertTriangle, Clock } from "lucide-react";
import { toast } from "sonner";

import { listarNotificaciones } from "../../api/notificaciones";
import { validarContinuidad } from "../../api/registros";

export default function NotificacionesPage() {
  const [notificaciones, setNotificaciones] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Modal de validación
  const [modalValidar, setModalValidar] = useState(null); // { id_registro, nombre, medicamento }
  const [nuevaFecha, setNuevaFecha] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = async () => {
    setLoading(true);
    try {
      const data = await listarNotificaciones();
      setNotificaciones(data.resultados);
      setTotal(data.total);
    } catch {
      toast.error("Error al cargar las notificaciones.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, []);

  const handleValidar = async () => {
    if (!modalValidar || !nuevaFecha) return;
    setGuardando(true);
    try {
      await validarContinuidad(modalValidar.id_registro, nuevaFecha);
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

  const getBadge = (diasRestantes, esActivo) => {
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
  };

  return (
    <div className="space-y-4">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">Notificaciones</h2>
          <p className="text-sm text-neutral-gray mt-0.5">
            Prescripciones que requieren validación de continuidad
          </p>
        </div>
        <button
          onClick={cargar}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-neutral-gray/30
            text-sm text-neutral-gray hover:bg-neutral-light transition"
        >
          <RefreshCw size={14} />
          Actualizar
        </button>
      </div>

      {/* Contenido */}
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
          {/* Resumen */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-3 flex items-center gap-3">
            <Bell size={18} className="text-amber-600 flex-shrink-0" />
            <p className="text-sm text-amber-800">
              <span className="font-semibold">{total}</span> prescripción(es) requieren tu atención.
              Valida la continuidad para mantenerlas activas.
            </p>
          </div>

          {/* Lista */}
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
                    <th className="text-left px-4 py-3 font-semibold text-neutral-black">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {notificaciones.map((n) => (
                    <tr
                      key={n.id_registro}
                      className={`border-b border-neutral-gray/10 ${
                        !n.es_activo ? "bg-red-50/40" : "hover:bg-neutral-light/60"
                      }`}
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-neutral-black text-sm">{n.nombre_paciente}</p>
                        <p className="text-xs text-neutral-gray">ID #{n.id_paciente}</p>
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-mono text-xs text-neutral-gray">{n.clave_cnis}</p>
                        <p className="text-xs text-neutral-black truncate max-w-[200px]">
                          {n.descripcion_medicamento ?? "—"}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-sm text-neutral-gray">
                        {n.fecha_fin_tratamiento}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-neutral-black">
                        {n.fecha_limite}
                      </td>
                      <td className="px-4 py-3">
                        {getBadge(n.dias_restantes, n.es_activo)}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => {
                            setModalValidar({
                              id_registro: n.id_registro,
                              nombre: n.nombre_paciente,
                              medicamento: n.descripcion_medicamento ?? n.clave_cnis,
                            });
                            setNuevaFecha("");
                          }}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                            bg-secondary/10 text-secondary hover:bg-secondary/20 transition"
                        >
                          <RefreshCw size={12} />
                          Validar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Modal de validación */}
      {modalValidar && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 space-y-4">
            <div>
              <h3 className="text-base font-semibold text-neutral-black">Validar continuidad</h3>
              <p className="text-sm font-medium text-neutral-black mt-1">{modalValidar.nombre}</p>
              <p className="text-xs text-neutral-gray truncate">{modalValidar.medicamento}</p>
            </div>
            <p className="text-sm text-neutral-gray">
              Indica la nueva fecha de fin de tratamiento. El registro se reactivará y el
              contador de 30 días se reiniciará desde esa fecha.
            </p>
            <div>
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
                disabled={!nuevaFecha || guardando}
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
    </div>
  );
}
