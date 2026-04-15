/**
 * MedicamentosPage.jsx — Catálogo de medicamentos CNIS (Solo SUPER_ADMIN).
 * Permite listar, crear y editar claves CNIS.
 */
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Pencil, X, Save, Pill } from "lucide-react";
import { toast } from "sonner";

import {
  listarMedicamentos,
  crearMedicamento,
  actualizarMedicamento,
} from "../../api/catalogos";

const schemaCrear = z.object({
  clave_cnis: z
    .string()
    .min(1, "La clave CNIS es requerida.")
    .max(20)
    .regex(/^[A-Z0-9\-]+$/i, "Solo letras, números y guiones."),
  descripcion: z.string().min(1, "La descripción es requerida.").max(2000),
  grupo: z.string().max(150).optional().or(z.literal("")),
  tipo_clave: z.string().max(100).optional().or(z.literal("")),
});

const schemaEditar = z.object({
  descripcion: z.string().min(1, "La descripción es requerida.").max(2000),
  grupo: z.string().max(150).optional().or(z.literal("")),
  tipo_clave: z.string().max(100).optional().or(z.literal("")),
  es_activo: z.boolean(),
});

// ── Modal ─────────────────────────────────────────────────────────────────────
function Modal({ item, onClose, onGuardado }) {
  const esEdicion = Boolean(item);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esEdicion ? schemaEditar : schemaCrear),
    defaultValues: esEdicion
      ? {
          descripcion: item.descripcion,
          grupo: item.grupo ?? "",
          tipo_clave: item.tipo_clave ?? "",
          es_activo: item.es_activo,
        }
      : { clave_cnis: "", descripcion: "", grupo: "", tipo_clave: "" },
  });

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      if (esEdicion) {
        const payload = {
          descripcion: values.descripcion,
          grupo: values.grupo || undefined,
          tipo_clave: values.tipo_clave || undefined,
          es_activo: values.es_activo,
        };
        await actualizarMedicamento(item.clave_cnis, payload);
        toast.success("Medicamento actualizado.");
      } else {
        const payload = {
          clave_cnis: values.clave_cnis.toUpperCase(),
          descripcion: values.descripcion,
          grupo: values.grupo || undefined,
          tipo_clave: values.tipo_clave || undefined,
        };
        await crearMedicamento(payload);
        toast.success("Medicamento registrado.");
      }
      onGuardado();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al guardar.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-gray/20">
          <h3 className="font-semibold text-neutral-black">
            {esEdicion
              ? `Editar — ${item.clave_cnis}`
              : "Nueva clave CNIS"}
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-neutral-gray hover:text-neutral-black hover:bg-neutral-light transition"
          >
            <X size={16} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
          {!esEdicion && (
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Clave CNIS <span className="text-primary">*</span>
              </label>
              <input
                type="text"
                placeholder="ej. 010.000.5765.00"
                className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                  focus:ring-2 focus:ring-primary/20 focus:border-primary uppercase
                  ${errors.clave_cnis ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                {...register("clave_cnis")}
              />
              {errors.clave_cnis && (
                <p className="text-red-500 text-xs mt-1">{errors.clave_cnis.message}</p>
              )}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Descripción <span className="text-primary">*</span>
            </label>
            <textarea
              rows={3}
              placeholder="Nombre completo del medicamento..."
              className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition resize-none
                focus:ring-2 focus:ring-primary/20 focus:border-primary
                ${errors.descripcion ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
              {...register("descripcion")}
            />
            {errors.descripcion && (
              <p className="text-red-500 text-xs mt-1">{errors.descripcion.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Grupo <span className="text-neutral-gray font-normal">(opcional)</span>
              </label>
              <input
                type="text"
                placeholder="ej. Biológicos"
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                {...register("grupo")}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Tipo de clave <span className="text-neutral-gray font-normal">(opcional)</span>
              </label>
              <input
                type="text"
                placeholder="ej. Cuadro básico"
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                {...register("tipo_clave")}
              />
            </div>
          </div>

          {esEdicion && (
            <label className="flex items-center gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                className="accent-primary w-4 h-4"
                {...register("es_activo")}
              />
              <span className="text-sm text-neutral-black">Medicamento activo</span>
            </label>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-lg border border-neutral-gray/30
                text-sm text-neutral-gray hover:bg-neutral-light transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark
                text-white text-sm font-medium py-2.5 rounded-lg transition
                disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading
                ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                : <Save size={15} />}
              {loading ? "Guardando..." : esEdicion ? "Guardar cambios" : "Registrar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────────────────
export default function MedicamentosPage() {
  const [medicamentos, setMedicamentos] = useState([]);
  const [soloActivos, setSoloActivos] = useState(true);
  const [busqueda, setBusqueda] = useState("");
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState({ open: false, item: null });

  const cargar = async () => {
    setLoading(true);
    try {
      const data = await listarMedicamentos(soloActivos);
      setMedicamentos(data);
    } catch {
      toast.error("Error al cargar medicamentos.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, [soloActivos]);

  const filtrados = busqueda.length < 2
    ? medicamentos
    : medicamentos.filter(
        (m) =>
          m.clave_cnis.toLowerCase().includes(busqueda.toLowerCase()) ||
          m.descripcion.toLowerCase().includes(busqueda.toLowerCase()) ||
          (m.grupo ?? "").toLowerCase().includes(busqueda.toLowerCase())
      );

  const cerrarModal = () => setModal({ open: false, item: null });
  const onGuardado = () => { cerrarModal(); cargar(); };

  return (
    <div className="space-y-4">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">
            Catálogo de Medicamentos
          </h2>
          <p className="text-sm text-neutral-gray mt-0.5">
            Claves CNIS del cuadro básico de medicamentos de alto costo.
          </p>
        </div>
        <button
          onClick={() => setModal({ open: true, item: null })}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary hover:bg-primary-dark
            text-white text-sm font-medium transition"
        >
          <Plus size={16} />
          Nueva clave CNIS
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 px-4 py-3 flex flex-wrap items-center gap-4">
        <input
          type="text"
          placeholder="Buscar por clave, descripción o grupo..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="flex-1 min-w-[220px] px-4 py-2 rounded-lg border border-neutral-gray/30 bg-neutral-light
            text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
        />
        <label className="flex items-center gap-2 text-sm text-neutral-gray cursor-pointer">
          <input
            type="checkbox"
            checked={soloActivos}
            onChange={(e) => setSoloActivos(e.target.checked)}
            className="accent-primary w-4 h-4"
          />
          Solo activos
        </label>
        <span className="text-xs text-neutral-gray ml-auto">
          {filtrados.length} registro(s)
        </span>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-light border-b border-neutral-gray/20">
                <th className="text-left px-4 py-3 font-semibold text-neutral-black whitespace-nowrap">Clave CNIS</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Descripción</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black whitespace-nowrap">Grupo</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black whitespace-nowrap">Tipo Clave</th>
                <th className="text-center px-4 py-3 font-semibold text-neutral-black">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12">
                    <div className="flex justify-center">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                  </td>
                </tr>
              ) : filtrados.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12">
                    <Pill size={32} className="mx-auto text-neutral-gray/40 mb-2" />
                    <p className="text-neutral-gray text-sm">Sin registros.</p>
                  </td>
                </tr>
              ) : (
                filtrados.map((m) => (
                  <tr key={m.clave_cnis} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-neutral-black whitespace-nowrap">
                      {m.clave_cnis}
                    </td>
                    <td className="px-4 py-3 text-neutral-gray max-w-xs">
                      <span className="line-clamp-2">{m.descripcion}</span>
                    </td>
                    <td className="px-4 py-3 text-neutral-gray whitespace-nowrap">
                      {m.grupo ?? <span className="text-neutral-gray/40">—</span>}
                    </td>
                    <td className="px-4 py-3 text-neutral-gray whitespace-nowrap">
                      {m.tipo_clave ?? <span className="text-neutral-gray/40">—</span>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${m.es_activo
                          ? "bg-secondary/10 text-secondary"
                          : "bg-neutral-gray/10 text-neutral-gray"}`}>
                        {m.es_activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setModal({ open: true, item: m })}
                        className="p-1.5 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
                        title="Editar"
                      >
                        <Pencil size={15} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {modal.open && (
        <Modal item={modal.item} onClose={cerrarModal} onGuardado={onGuardado} />
      )}
    </div>
  );
}
