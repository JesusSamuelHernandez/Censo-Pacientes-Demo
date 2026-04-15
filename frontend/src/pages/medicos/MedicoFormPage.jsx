/**
 * MedicoFormPage.jsx — Formulario para registrar o editar un médico.
 * Modo: si la URL tiene /:id/editar → edición. Si es /nuevo → creación.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Save } from "lucide-react";
import { toast } from "sonner";

import { crearMedico, actualizarMedico, obtenerMedico } from "../../api/medicos";
import UnidadCombobox from "../../components/shared/UnidadCombobox";

const schemaCrear = z.object({
  nombre_medico: z.string().min(2, "El nombre es requerido.").max(255),
  cedula: z.string().min(1, "La cédula es requerida.").max(30),
  email: z.string().email("Correo inválido.").optional().or(z.literal("")),
  clues_adscripcion: z.string().min(1, "Selecciona una unidad médica."),
});

const schemaEditar = z.object({
  nombre_medico: z.string().min(2).max(255).optional(),
  cedula: z.string().min(1).max(30).optional(),
  email: z.string().email("Correo inválido.").optional().or(z.literal("")),
  clues_adscripcion: z.string().min(1).optional(),
});

export default function MedicoFormPage() {
  const { id } = useParams();
  const esEdicion = Boolean(id);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esEdicion ? schemaEditar : schemaCrear),
  });

  const cluesSeleccionada = watch("clues_adscripcion");

  useEffect(() => {
    if (esEdicion) {
      obtenerMedico(id)
        .then((m) => reset({
          nombre_medico: m.nombre_medico,
          cedula: m.cedula,
          email: m.email ?? "",
          clues_adscripcion: m.clues_adscripcion,
        }))
        .catch(() => toast.error("Error al cargar el médico."));
    }
  }, [id]);

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(values).filter(([, v]) => v !== "" && v !== undefined)
      );
      if (esEdicion) {
        await actualizarMedico(id, payload);
        toast.success("Médico actualizado correctamente.");
      } else {
        await crearMedico(payload);
        toast.success("Médico registrado correctamente.");
      }
      navigate("/medicos");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al guardar el médico.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/medicos")}
          className="p-2 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">
            {esEdicion ? "Editar médico" : "Registrar médico"}
          </h2>
          <p className="text-sm text-neutral-gray">
            {esEdicion ? `ID: ${id}` : "Completa los datos del nuevo médico."}
          </p>
        </div>
      </div>

      {/* Formulario */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 p-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

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

          {/* Unidad */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Unidad de adscripción <span className="text-primary">*</span>
            </label>
            <UnidadCombobox
              value={cluesSeleccionada}
              onChange={(clues) => setValue("clues_adscripcion", clues, { shouldValidate: true })}
              error={errors.clues_adscripcion}
            />
            {errors.clues_adscripcion && (
              <p className="text-red-500 text-xs mt-1">{errors.clues_adscripcion.message}</p>
            )}
          </div>

          {/* Botones */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate("/medicos")}
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
              {loading ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Save size={15} />
              )}
              {loading ? "Guardando..." : esEdicion ? "Guardar cambios" : "Registrar médico"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
