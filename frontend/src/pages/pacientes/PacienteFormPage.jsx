/**
 * PacienteFormPage.jsx — Formulario para registrar o editar un paciente.
 * Modo: si la URL tiene /:curp/editar → edición. Si es /nuevo → creación.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Save } from "lucide-react";
import { toast } from "sonner";

import { crearPaciente, actualizarPaciente, obtenerPaciente } from "../../api/pacientes";
import UnidadCombobox from "../../components/shared/UnidadCombobox";

const CURP_REGEX = /^[A-Z]{4}\d{6}[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$/;

const schemaCrear = z.object({
  curp_paciente: z
    .string()
    .length(18, "La CURP debe tener exactamente 18 caracteres.")
    .regex(CURP_REGEX, "Formato de CURP inválido."),
  nombre_completo: z.string().min(2, "El nombre es requerido.").max(255),
  diagnostico_actual: z.string().max(5000).optional().or(z.literal("")),
  clues_unidad_adscripcion: z.string().min(1, "Selecciona una unidad médica."),
});

const schemaEditar = z.object({
  nombre_completo: z.string().min(2, "El nombre es requerido.").max(255).optional(),
  diagnostico_actual: z.string().max(5000).optional().or(z.literal("")),
  clues_unidad_adscripcion: z.string().min(1).optional(),
});

export default function PacienteFormPage() {
  const { curp } = useParams();
  const esEdicion = Boolean(curp);
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

  const cluesSeleccionada = watch("clues_unidad_adscripcion");

  useEffect(() => {
    if (esEdicion) {
      obtenerPaciente(curp)
        .then((p) => reset({
          nombre_completo: p.nombre_completo,
          diagnostico_actual: p.diagnostico_actual ?? "",
          clues_unidad_adscripcion: p.clues_unidad_adscripcion,
        }))
        .catch(() => toast.error("Error al cargar el paciente."));
    }
  }, [curp]);

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      if (esEdicion) {
        // Limpiar campos vacíos
        const payload = Object.fromEntries(
          Object.entries(values).filter(([, v]) => v !== "" && v !== undefined)
        );
        await actualizarPaciente(curp, payload);
        toast.success("Paciente actualizado correctamente.");
      } else {
        const payload = {
          ...values,
          curp_paciente: values.curp_paciente.trim().toUpperCase(),
          diagnostico_actual: values.diagnostico_actual || undefined,
        };
        await crearPaciente(payload);
        toast.success("Paciente registrado correctamente.");
      }
      navigate("/pacientes");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al guardar el paciente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/pacientes")}
          className="p-2 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">
            {esEdicion ? "Editar paciente" : "Registrar paciente"}
          </h2>
          <p className="text-sm text-neutral-gray">
            {esEdicion ? `CURP: ${curp}` : "Completa los datos del nuevo paciente."}
          </p>
        </div>
      </div>

      {/* Formulario */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 p-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

          {/* CURP — solo en creación */}
          {!esEdicion && (
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                CURP <span className="text-primary">*</span>
              </label>
              <input
                type="text"
                placeholder="LOOA890101HDFPRS09"
                maxLength={18}
                className={`w-full px-4 py-2.5 rounded-lg border text-sm font-mono uppercase outline-none transition
                  focus:ring-2 focus:ring-primary/20 focus:border-primary
                  ${errors.curp_paciente ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                {...register("curp_paciente", {
                  setValueAs: (v) => v.trim().toUpperCase(),
                })}
              />
              {errors.curp_paciente && (
                <p className="text-red-500 text-xs mt-1">{errors.curp_paciente.message}</p>
              )}
            </div>
          )}

          {/* Nombre completo */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Nombre completo <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              placeholder="Apellido Paterno Apellido Materno Nombre(s)"
              className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                focus:ring-2 focus:ring-primary/20 focus:border-primary
                ${errors.nombre_completo ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
              {...register("nombre_completo")}
            />
            {errors.nombre_completo && (
              <p className="text-red-500 text-xs mt-1">{errors.nombre_completo.message}</p>
            )}
          </div>

          {/* Diagnóstico */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Diagnóstico actual
              <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
            </label>
            <textarea
              rows={3}
              placeholder="Describe el diagnóstico actual del paciente..."
              className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition resize-none
                focus:ring-2 focus:ring-primary/20 focus:border-primary
                ${errors.diagnostico_actual ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
              {...register("diagnostico_actual")}
            />
            {errors.diagnostico_actual && (
              <p className="text-red-500 text-xs mt-1">{errors.diagnostico_actual.message}</p>
            )}
          </div>

          {/* Unidad médica */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Unidad médica de adscripción <span className="text-primary">*</span>
            </label>
            <UnidadCombobox
              value={cluesSeleccionada}
              onChange={(clues) => setValue("clues_unidad_adscripcion", clues, { shouldValidate: true })}
              error={errors.clues_unidad_adscripcion}
            />
            {errors.clues_unidad_adscripcion && (
              <p className="text-red-500 text-xs mt-1">{errors.clues_unidad_adscripcion.message}</p>
            )}
          </div>

          {/* Botones */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate("/pacientes")}
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
              {loading ? "Guardando..." : esEdicion ? "Guardar cambios" : "Registrar paciente"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
