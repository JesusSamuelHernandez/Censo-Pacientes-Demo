import { useEffect, useState } from "react";
import { X, UserPlus, Save } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { crearMedico } from "../../api/medicos";
import UnidadCombobox from "./UnidadCombobox";
import useAuthStore from "../../store/authStore";

const schema = z.object({
  nombre_medico: z.string().min(3, "Mínimo 3 caracteres."),
  cedula: z.string().min(3, "Ingresa la cédula profesional."),
  email: z.string().email("Correo inválido.").optional().or(z.literal("")),
  clues_adscripcion: z.string().min(1, "Selecciona la unidad de adscripción."),
});

const ROLES = { RESPONSABLE_UNIDAD: "RESPONSABLE_UNIDAD", ADMIN_ESTATAL: "ADMIN_ESTATAL" };

export default function RegistrarMedicoModal({ onClose, onMedicoCreado }) {
  const [loading, setLoading] = useState(false);
  const { rolNombre, cluesUnidadAsignada, nombreUnidad, idEntidad } = useAuthStore();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) });

  const cluesSeleccionada = watch("clues_adscripcion");

  useEffect(() => {
    if (rolNombre === ROLES.RESPONSABLE_UNIDAD && cluesUnidadAsignada) {
      setValue("clues_adscripcion", cluesUnidadAsignada, { shouldValidate: false });
    }
  }, []);

  // Cerrar con Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(values).filter(([, v]) => v !== "" && v !== undefined)
      );
      const nuevo = await crearMedico(payload);
      toast.success("Médico registrado. Ahora aparece seleccionado en el formulario.");
      onMedicoCreado(nuevo);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al registrar el médico.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        {/* Encabezado */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-gray/10">
          <div className="flex items-center gap-2">
            <UserPlus size={18} className="text-primary" />
            <h3 className="text-base font-semibold text-neutral-black">Registrar nuevo médico</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-neutral-gray hover:text-neutral-black hover:bg-neutral-light transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">

          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Nombre completo <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              placeholder="Dr. Nombre Apellido Apellido"
              className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                focus:ring-2 focus:ring-primary/20 focus:border-primary
                ${errors.nombre_medico ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
              {...register("nombre_medico")}
            />
            {errors.nombre_medico && (
              <p className="text-red-500 text-xs mt-1">{errors.nombre_medico.message}</p>
            )}
          </div>

          {/* Cédula */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Cédula profesional <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              placeholder="ej. 4521876"
              className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                focus:ring-2 focus:ring-primary/20 focus:border-primary
                ${errors.cedula ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
              {...register("cedula")}
            />
            {errors.cedula && (
              <p className="text-red-500 text-xs mt-1">{errors.cedula.message}</p>
            )}
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Correo electrónico
              <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
            </label>
            <input
              type="email"
              placeholder="medico@imssbienestar.gob.mx"
              className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                focus:ring-2 focus:ring-primary/20 focus:border-primary
                ${errors.email ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
              {...register("email")}
            />
            {errors.email && (
              <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>
            )}
          </div>

          {/* Unidad de adscripción */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Unidad de adscripción <span className="text-primary">*</span>
            </label>
            {rolNombre === ROLES.RESPONSABLE_UNIDAD ? (
              <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-neutral-gray/20
                bg-neutral-gray/10 text-sm text-neutral-black cursor-not-allowed">
                <span className="font-mono text-xs text-neutral-gray">{cluesUnidadAsignada}</span>
                <span>{nombreUnidad ?? "—"}</span>
              </div>
            ) : (
              <UnidadCombobox
                value={cluesSeleccionada}
                onChange={(clues) => setValue("clues_adscripcion", clues, { shouldValidate: true })}
                error={errors.clues_adscripcion}
                idEntidad={rolNombre === ROLES.ADMIN_ESTATAL ? idEntidad : null}
              />
            )}
            {errors.clues_adscripcion && (
              <p className="text-red-500 text-xs mt-1">{errors.clues_adscripcion.message}</p>
            )}
          </div>

          {/* Botones */}
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
              {loading ? "Registrando..." : "Registrar médico"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
