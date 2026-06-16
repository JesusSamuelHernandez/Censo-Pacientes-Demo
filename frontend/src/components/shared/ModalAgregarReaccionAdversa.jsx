/**
 * ModalAgregarReaccionAdversa.jsx — Formulario modal para registrar una reacción adversa a medicamento.
 */
import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { toast } from "sonner";

import { listarMedicamentos } from "../../api/catalogos";
import { agregarReaccionAdversa } from "../../api/pacientes";

export default function ModalAgregarReaccionAdversa({ identificador, isOpen, onClose, onGuardado }) {
  const [medicamentos, setMedicamentos] = useState([]);
  const [claveCnis, setClaveCnis] = useState("");
  const [comentario, setComentario] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setClaveCnis("");
    setComentario("");
    listarMedicamentos(null, true)
      .then((data) => setMedicamentos(data))
      .catch(() => setMedicamentos([]));
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!claveCnis) {
      toast.error("Selecciona un medicamento.");
      return;
    }
    if (!comentario.trim()) {
      toast.error("Escribe un comentario sobre la reacción.");
      return;
    }
    setGuardando(true);
    try {
      await agregarReaccionAdversa(identificador, {
        clave_cnis: claveCnis,
        comentario: comentario.trim(),
      });
      toast.success("Reacción adversa registrada.");
      onGuardado();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al registrar la reacción adversa.");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-gray/10">
          <h3 className="text-sm font-semibold text-neutral-black">Registrar reacción adversa</h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-neutral-gray hover:text-neutral-black hover:bg-neutral-light transition"
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-neutral-gray">
              Medicamento <span className="text-red-500">*</span>
            </label>
            <select
              value={claveCnis}
              onChange={(e) => setClaveCnis(e.target.value)}
              className="w-full rounded-xl border border-neutral-gray/30 px-3 py-2 text-sm
                focus:outline-none focus:ring-2 focus:ring-primary/40 bg-white"
            >
              <option value="">— Selecciona un medicamento —</option>
              {medicamentos.map((m) => (
                <option key={m.clave_cnis} value={m.clave_cnis}>
                  {m.descripcion}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-neutral-gray">
              Comentario sobre la reacción <span className="text-red-500">*</span>
            </label>
            <textarea
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
              maxLength={2000}
              rows={4}
              placeholder="Describe la reacción adversa observada..."
              className="w-full rounded-xl border border-neutral-gray/30 px-3 py-2 text-sm resize-none
                focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <p className="text-xs text-neutral-gray text-right">{comentario.length}/2000</p>
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={guardando}
              className="px-4 py-2 rounded-xl text-sm border border-neutral-gray/30 text-neutral-gray
                hover:bg-neutral-light transition disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={guardando}
              className="px-4 py-2 rounded-xl text-sm bg-yellow-500 text-white font-medium
                hover:bg-yellow-600 transition disabled:opacity-50"
            >
              {guardando ? "Guardando..." : "Guardar reacción"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
