/**
 * RecetaFormPage.jsx — Formulario para registrar o editar una receta.
 * Los selects de paciente y médico usan búsqueda por texto para evitar listas largas.
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Save, Search, X } from "lucide-react";
import { toast } from "sonner";

import { crearReceta, actualizarReceta, obtenerReceta } from "../../api/recetas";
import { listarPacientes } from "../../api/pacientes";
import { listarMedicos } from "../../api/medicos";
import { listarMedicamentos } from "../../api/catalogos";
import UnidadCombobox from "../../components/shared/UnidadCombobox";

const schemaCrear = z.object({
  id_receta: z.string().min(1, "El folio es requerido.").max(50),
  id_medico: z.number({ invalid_type_error: "Selecciona un médico." }).int().positive(),
  id_paciente: z.number({ invalid_type_error: "Selecciona un paciente." }).int().positive(),
  clave_cnis: z.string().min(1, "Selecciona un medicamento."),
  clues: z.string().min(1, "Selecciona una unidad."),
  fecha_inicio_tratamiento: z.string().optional().or(z.literal("")),
  fecha_primera_admin: z.string().optional().or(z.literal("")),
  dosis_administrada: z.string().max(100).optional().or(z.literal("")),
});

const schemaEditar = z.object({
  fecha_inicio_tratamiento: z.string().optional().or(z.literal("")),
  fecha_primera_admin: z.string().optional().or(z.literal("")),
  dosis_administrada: z.string().max(100).optional().or(z.literal("")),
});

// Componente de búsqueda genérico para médicos y pacientes
function BuscadorItem({ placeholder, items, displayFn, itemKey, onSelect, error }) {
  const [query, setQuery] = useState("");
  const [abierto, setAbierto] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setAbierto(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtrados = query.length < 2
    ? []
    : items.filter((i) => displayFn(i).toLowerCase().includes(query.toLowerCase())).slice(0, 10);

  return (
    <div ref={ref} className="relative">
      <div className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm transition
        focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary
        ${error ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}>
        <Search size={14} className="text-neutral-gray flex-shrink-0" />
        <input
          type="text"
          placeholder={placeholder}
          value={query}
          onChange={(e) => { setQuery(e.target.value); setAbierto(true); if (!e.target.value) onSelect(null); }}
          onFocus={() => { if (query.length >= 2) setAbierto(true); }}
          className="flex-1 bg-transparent outline-none text-neutral-black placeholder:text-neutral-gray"
        />
        {query && (
          <button type="button" onClick={() => { setQuery(""); onSelect(null); }}
            className="text-neutral-gray hover:text-neutral-black">
            <X size={14} />
          </button>
        )}
      </div>
      {abierto && filtrados.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-neutral-gray/20 rounded-lg
          shadow-lg max-h-48 overflow-y-auto">
          {filtrados.map((item) => (
            <li key={itemKey(item)}
              onMouseDown={() => { onSelect(item); setQuery(displayFn(item)); setAbierto(false); }}
              className="px-4 py-2.5 cursor-pointer hover:bg-primary/5 text-sm text-neutral-black">
              {displayFn(item)}
            </li>
          ))}
        </ul>
      )}
      {abierto && query.length >= 2 && filtrados.length === 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-gray/20 rounded-lg
          shadow-lg px-4 py-3 text-sm text-neutral-gray">
          No se encontraron resultados.
        </div>
      )}
    </div>
  );
}

export default function RecetaFormPage() {
  const { id } = useParams();
  const esEdicion = Boolean(id);
  const navigate = useNavigate();

  const [medicos, setMedicos] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm({ resolver: zodResolver(esEdicion ? schemaEditar : schemaCrear) });

  const cluesSeleccionada = watch("clues");

  useEffect(() => {
    Promise.all([
      listarMedicos(),
      listarPacientes({ soloActivos: true, porPagina: 500 }),
      listarMedicamentos(),
    ]).then(([m, p, med]) => {
      setMedicos(m);
      setPacientes(p.resultados);
      setMedicamentos(med);
    }).catch(() => toast.error("Error al cargar datos del formulario."));

    if (esEdicion) {
      obtenerReceta(id).then((r) => {
        reset({
          fecha_inicio_tratamiento: r.fecha_inicio_tratamiento ?? "",
          fecha_primera_admin: r.fecha_primera_admin ?? "",
          dosis_administrada: r.dosis_administrada ?? "",
        });
      }).catch(() => toast.error("Error al cargar la receta."));
    }
  }, [id]);

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      if (esEdicion) {
        const payload = Object.fromEntries(
          Object.entries(values).filter(([, v]) => v !== "" && v !== undefined)
        );
        await actualizarReceta(id, payload);
        toast.success("Receta actualizada correctamente.");
      } else {
        const payload = {
          ...values,
          fecha_inicio_tratamiento: values.fecha_inicio_tratamiento || undefined,
          fecha_primera_admin: values.fecha_primera_admin || undefined,
          dosis_administrada: values.dosis_administrada || undefined,
        };
        await crearReceta(payload);
        toast.success("Receta registrada correctamente.");
      }
      navigate("/recetas");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al guardar la receta.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate("/recetas")}
          className="p-2 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">
            {esEdicion ? `Editar receta: ${id}` : "Registrar receta"}
          </h2>
          <p className="text-sm text-neutral-gray">
            {esEdicion ? "Solo puedes modificar fechas y dosis." : "Completa los datos de la nueva receta."}
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-neutral-gray/20 p-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

          {!esEdicion && (
            <>
              {/* Folio */}
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Folio de receta <span className="text-primary">*</span>
                </label>
                <input type="text" placeholder="ej. RX-ZS-2026-0020"
                  className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                    focus:ring-2 focus:ring-primary/20 focus:border-primary
                    ${errors.id_receta ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                  {...register("id_receta")} />
                {errors.id_receta && <p className="text-red-500 text-xs mt-1">{errors.id_receta.message}</p>}
              </div>

              {/* Paciente */}
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Paciente <span className="text-primary">*</span>
                </label>
                <BuscadorItem
                  placeholder="Escribe nombre o CURP (mín. 2 caracteres)..."
                  items={pacientes}
                  displayFn={(p) => `${p.nombre_completo} (${p.curp_paciente})`}
                  itemKey={(p) => p.id_paciente}
                  onSelect={(p) => setValue("id_paciente", p?.id_paciente ?? null, { shouldValidate: true })}
                  error={errors.id_paciente}
                />
                {errors.id_paciente && <p className="text-red-500 text-xs mt-1">{errors.id_paciente.message}</p>}
              </div>

              {/* Médico */}
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Médico <span className="text-primary">*</span>
                </label>
                <BuscadorItem
                  placeholder="Escribe nombre o cédula (mín. 2 caracteres)..."
                  items={medicos}
                  displayFn={(m) => `${m.nombre_medico} — Céd. ${m.cedula}`}
                  itemKey={(m) => m.id_medico}
                  onSelect={(m) => setValue("id_medico", m?.id_medico ?? null, { shouldValidate: true })}
                  error={errors.id_medico}
                />
                {errors.id_medico && <p className="text-red-500 text-xs mt-1">{errors.id_medico.message}</p>}
              </div>

              {/* Medicamento — select dropdown (solo 24 opciones) */}
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Medicamento (clave CNIS) <span className="text-primary">*</span>
                </label>
                <select
                  className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                    focus:ring-2 focus:ring-primary/20 focus:border-primary
                    ${errors.clave_cnis ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                  {...register("clave_cnis")}
                >
                  <option value="">— Selecciona un medicamento —</option>
                  {medicamentos.map((m) => (
                    <option key={m.clave_cnis} value={m.clave_cnis}>
                      {m.clave_cnis} — {m.descripcion.slice(0, 70)}
                    </option>
                  ))}
                </select>
                {errors.clave_cnis && <p className="text-red-500 text-xs mt-1">{errors.clave_cnis.message}</p>}
              </div>

              {/* Unidad */}
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Unidad donde se genera la receta <span className="text-primary">*</span>
                </label>
                <UnidadCombobox
                  value={cluesSeleccionada}
                  onChange={(clues) => setValue("clues", clues, { shouldValidate: true })}
                  error={errors.clues}
                />
                {errors.clues && <p className="text-red-500 text-xs mt-1">{errors.clues.message}</p>}
              </div>
            </>
          )}

          {/* Fecha inicio tratamiento */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Fecha inicio de tratamiento
              <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
            </label>
            <input type="date"
              className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
              {...register("fecha_inicio_tratamiento")} />
          </div>

          {/* Fecha primera administración */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Fecha de primera administración
              <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
            </label>
            <input type="date"
              className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
              {...register("fecha_primera_admin")} />
          </div>

          {/* Dosis */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Dosis administrada
              <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
            </label>
            <input type="text" placeholder="ej. 500 mg IV, 40 mg SC"
              className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
              {...register("dosis_administrada")} />
          </div>

          {/* Botones */}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => navigate("/recetas")}
              className="flex-1 px-4 py-2.5 rounded-lg border border-neutral-gray/30
                text-sm text-neutral-gray hover:bg-neutral-light transition">
              Cancelar
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark
                text-white text-sm font-medium py-2.5 rounded-lg transition
                disabled:opacity-60 disabled:cursor-not-allowed">
              {loading
                ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                : <Save size={15} />}
              {loading ? "Guardando..." : esEdicion ? "Guardar cambios" : "Registrar receta"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
