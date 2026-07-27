/**
 * BanderinEstado.jsx — Banderín de color que indica el estatus de evolución del paciente.
 * Al hacer clic se abre una ventana con la leyenda de colores y el selector de estatus.
 */
import { useState } from "react";
import { X } from "lucide-react";
import { toast } from "sonner";

import { actualizarPaciente } from "../../api/pacientes";

const ESTATUS_EVOLUCION_OPTIONS = [
  { valor: "Inicia tx", color: "#22c55e", descripcion: "El paciente está iniciando tratamiento." },
  { valor: "Tx fase intermedia", color: "#f59e0b", descripcion: "El paciente se encuentra en fase intermedia del tratamiento." },
  { valor: "Recaída", color: "#ef4444", descripcion: "El paciente presentó una recaída." },
  { valor: "Curación", color: "#3b82f6", descripcion: "El paciente fue dado de alta por curación." },
];

const colorDe = (estatus) =>
  ESTATUS_EVOLUCION_OPTIONS.find((o) => o.valor === estatus)?.color ?? "#9ca3af";

export default function BanderinEstado({ identificador, estatus, onChange }) {
  const [abierto, setAbierto] = useState(false);
  const [guardando, setGuardando] = useState(false);

  const seleccionar = async (valor) => {
    if (valor === estatus) {
      setAbierto(false);
      return;
    }
    setGuardando(true);
    try {
      await actualizarPaciente(identificador, { estatus_evolucion: valor });
      onChange?.(valor);
      toast.success("Estatus de evolución actualizado.");
      setAbierto(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al actualizar el estatus.");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setAbierto(true)}
        title="Estatus de evolución (clic para cambiar)"
        className="absolute left-0 -top-1.5 -bottom-1.5 w-3.5 rounded-b-sm hover:opacity-80 transition"
        style={{
          backgroundColor: colorDe(estatus),
          clipPath: "polygon(0 0, 100% 0, 100% 100%, 50% 78%, 0 100%)",
        }}
      />

      {abierto && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
          onMouseDown={(e) => { if (e.target === e.currentTarget) setAbierto(false); }}
        >
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm">
            <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-gray/10">
              <h3 className="text-sm font-semibold text-neutral-black">Estatus de evolución</h3>
              <button
                type="button"
                onClick={() => setAbierto(false)}
                className="p-1 rounded-lg text-neutral-gray hover:text-neutral-black hover:bg-neutral-light transition"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-5 space-y-2">
              {ESTATUS_EVOLUCION_OPTIONS.map((op) => (
                <button
                  key={op.valor}
                  type="button"
                  disabled={guardando}
                  onClick={() => seleccionar(op.valor)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition
                    disabled:opacity-60 disabled:cursor-not-allowed
                    ${op.valor === estatus ? "border-primary bg-primary/5" : "border-neutral-gray/20 hover:bg-neutral-light"}`}
                >
                  <span className="w-3.5 h-3.5 rounded-sm shrink-0" style={{ backgroundColor: op.color }} />
                  <span className="flex-1">
                    <span className="block text-sm font-medium text-neutral-black">{op.valor}</span>
                    <span className="block text-xs text-neutral-gray">{op.descripcion}</span>
                  </span>
                  {op.valor === estatus && (
                    <span className="text-xs font-medium text-primary shrink-0">Actual</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
