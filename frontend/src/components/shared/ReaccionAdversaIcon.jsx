/**
 * ReaccionAdversaIcon.jsx — Icono de advertencia para pacientes con reacción adversa registrada.
 * Al hacer clic carga y muestra la lista de reacciones (lazy).
 * Prop modoDetalle: muestra el icono + etiqueta "Reacción adversa" como badge clickeable.
 */
import { useState } from "react";
import { TriangleAlert, X } from "lucide-react";
import { obtenerReaccionesAdversas } from "../../api/pacientes";

const formatFecha = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "2-digit", year: "numeric" });
};

export default function ReaccionAdversaIcon({ identificador, modoDetalle = false }) {
  const [abierto, setAbierto] = useState(false);
  const [reacciones, setReacciones] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(false);

  const abrir = async () => {
    setAbierto(true);
    if (reacciones !== null) return;
    setCargando(true);
    setError(false);
    try {
      const data = await obtenerReaccionesAdversas(identificador);
      setReacciones(data);
    } catch {
      setError(true);
    } finally {
      setCargando(false);
    }
  };

  return (
    <>
      {modoDetalle ? (
        <button
          type="button"
          onClick={abrir}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
            bg-yellow-50 text-yellow-700 border border-yellow-200 hover:bg-yellow-100 transition"
          title="Ver reacciones adversas"
        >
          <TriangleAlert size={13} />
          Reacción adversa
        </button>
      ) : (
        <button
          type="button"
          onClick={abrir}
          className="shrink-0 hover:opacity-70 transition"
          title="Ver reacciones adversas (clic para ver)"
        >
          <TriangleAlert size={14} className="text-yellow-500" />
        </button>
      )}

      {abierto && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
          onMouseDown={(e) => { if (e.target === e.currentTarget) setAbierto(false); }}
        >
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-gray/10">
              <div className="flex items-center gap-2">
                <TriangleAlert size={16} className="text-yellow-500" />
                <h3 className="text-sm font-semibold text-neutral-black">Reacciones adversas a medicamentos</h3>
              </div>
              <button
                type="button"
                onClick={() => setAbierto(false)}
                className="p-1 rounded-lg text-neutral-gray hover:text-neutral-black hover:bg-neutral-light transition"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-5">
              {cargando && (
                <p className="text-sm text-neutral-gray text-center py-4">Cargando...</p>
              )}
              {error && (
                <p className="text-sm text-red-600 text-center py-4">Error al cargar las reacciones.</p>
              )}
              {reacciones && reacciones.length === 0 && (
                <p className="text-sm text-neutral-gray text-center py-4">No hay reacciones registradas.</p>
              )}
              {reacciones && reacciones.length > 0 && (
                <div className="space-y-3">
                  {reacciones.map((r) => (
                    <div
                      key={r.id_reaccion}
                      className="rounded-xl border border-yellow-200 bg-yellow-50 p-4 space-y-1.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-sm font-medium text-neutral-black">{r.nombre_medicamento}</span>
                        <span className="text-xs text-neutral-gray shrink-0">{formatFecha(r.fecha_registro)}</span>
                      </div>
                      <p className="text-sm text-neutral-black leading-relaxed">{r.comentario}</p>
                      {(r.nombre_usuario_registro || r.email_usuario_registro) && (
                        <p className="text-xs text-neutral-gray">
                          Registrado por:{" "}
                          {r.nombre_usuario_registro
                            ? `${r.nombre_usuario_registro} (${r.email_usuario_registro})`
                            : r.email_usuario_registro}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
