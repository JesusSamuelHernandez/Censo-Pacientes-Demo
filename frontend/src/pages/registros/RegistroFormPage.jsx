/**
 * RegistroFormPage.jsx — Formulario combinado: registra paciente + prescripción en una sola operación.
 * - Si la CURP ya existe en el sistema: reutiliza el paciente y crea solo la prescripción.
 * - Si la CURP no existe: captura datos del paciente nuevo y crea ambos en una sola llamada.
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Save, Search, X, UserCheck, UserX, ExternalLink } from "lucide-react";
import { toast } from "sonner";

import { crearRegistroCompleto, actualizarRegistro, reemplazarRegistro, obtenerRegistro } from "../../api/registros";
import { buscarPacientePorCurp } from "../../api/pacientes";
import { listarMedicos } from "../../api/medicos";
import { listarMedicamentos, listarDiagnosticos } from "../../api/catalogos";
import UnidadCombobox from "../../components/shared/UnidadCombobox";

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------
const CURP_REGEX = /^[A-Z]{4}\d{6}[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$/;

const ESTATUS_OPTIONS = ["confirmado", "por confirmar"];

const CONFIRMADO_POR_OPTIONS = [
  "Consulta Externa",
  "Farmacia Hospitalaria",
  "Comité de Medicamentos",
  "Dirección Médica",
  "Trabajo Social",
];

// Campos opcionales compartidos entre crear y editar
const camposOpcionales = {
  estatus_diagnostico: z.string().optional().or(z.literal("")),
  confirmado_por: z.string().optional().or(z.literal("")),
  fecha_inicio_tratamiento: z.string().optional().or(z.literal("")),
  fecha_primera_administracion: z.string().optional().or(z.literal("")),
  dosis_administrada: z.string().max(100).optional().or(z.literal("")),
  peso: z.string().optional().or(z.literal("")),
  talla: z.string().optional().or(z.literal("")),
  // Posología
  dosis: z.string().optional().or(z.literal("")),
  cantidad: z.string().optional().or(z.literal("")),
  frecuencia: z.string().optional().or(z.literal("")),
  unidad_tiempo: z.string().optional().or(z.literal("")),
  duracion: z.string().optional().or(z.literal("")),
  id_diagnostico: z.string().optional().or(z.literal("")),
};

const schemaCrear = z.object({
  // Campos de paciente nuevo (validación adicional en onSubmit)
  nombre_completo: z.string().optional().or(z.literal("")),
  // Datos de prescripción obligatorios
  id_medico: z.number({ invalid_type_error: "Selecciona un médico." }).int().positive(),
  clave_cnis: z.string().min(1, "Selecciona un medicamento."),
  clues: z.string().min(1, "Selecciona una unidad."),
  ...camposOpcionales,
});

const schemaEditar = z.object({ ...camposOpcionales });

// ---------------------------------------------------------------------------
// Componente buscador genérico (para médicos)
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------
export default function RegistroFormPage() {
  const { id } = useParams();
  const esEdicion = Boolean(id);
  const navigate = useNavigate();
  const location = useLocation();
  const modoReemplazar = location.state?.modo === "reemplazar";

  const [medicos, setMedicos] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);
  const [diagnosticos, setDiagnosticos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [unidadMedicamentoEdicion, setUnidadMedicamentoEdicion] = useState(null);
  const [unidadDeMedidaEdicion, setUnidadDeMedidaEdicion] = useState(null);

  // Estado del widget de búsqueda por CURP
  const [curpBusqueda, setCurpBusqueda] = useState("");
  const [busquedaEstado, setBusquedaEstado] = useState(null); // null | "buscando" | "encontrado" | "no_encontrado" | "error"
  const [resultadoBusqueda, setResultadoBusqueda] = useState(null);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm({ resolver: zodResolver(esEdicion ? schemaEditar : schemaCrear) });

  const cluesSeleccionada = watch("clues");
  const claveCnisSeleccionada = watch("clave_cnis");

  // Unidad del medicamento seleccionado (para etiqueta dinámica en posología)
  const medSeleccionado = medicamentos.find((m) => m.clave_cnis === claveCnisSeleccionada);
  const unidadMedicamento = esEdicion
    ? unidadMedicamentoEdicion
    : (medSeleccionado?.unidad ?? null);
  const unidadDeMedida = esEdicion
    ? unidadDeMedidaEdicion
    : (medSeleccionado?.unidad_de_medida ?? null);

  // Watch de campos de posología para el preview en tiempo real
  const dosisVal            = watch("dosis");
  const cantidadVal         = watch("cantidad");
  const frecuenciaVal       = watch("frecuencia");
  const duracionVal         = watch("duracion");
  const unidadTiempoVal     = watch("unidad_tiempo");
  const fechaPrimeraAdminVal = watch("fecha_primera_administracion");

  // Calcula el preview de prescripción en el cliente (espejo de la lógica del backend)
  const previewPrescripcion = (() => {
    const d   = parseFloat(dosisVal);
    const f   = parseInt(frecuenciaVal, 10);
    const dur = parseInt(duracionVal, 10);
    const ut  = unidadTiempoVal;
    if (!d || !f || !dur || !ut) return null;

    const factor = { días: 1, semanas: 7, meses: 30 }[ut] ?? 1;
    const total  = Math.round(d * (24 / f) * dur * factor * 100) / 100;

    const pluralizar = (u, cant) => {
      if (!u) return "unidad(es)";
      if (cant === 1) return u;
      const ul = u.toLowerCase();
      if (["ml", "mg", "mcg", "g", "ui", "dosis"].includes(ul)) return u;
      if (ul.endsWith("ón")) return u.slice(0, -2) + "ones";
      if ("aeiouáéíóú".includes(ul[ul.length - 1])) return u + "s";
      return u + "es";
    };

    const unidadTxt = pluralizar(unidadMedicamento, d);
    const cant = parseFloat(cantidadVal);
    const textoCantidad = (cant && unidadDeMedida) ? ` de ${cant} ${unidadDeMedida}` : "";
    const texto = `${d % 1 === 0 ? d : d} ${unidadTxt}${textoCantidad}, cada ${f} horas, por ${dur} ${ut}`;

    // Calcular fecha fin estimada (último día de tratamiento, inclusive)
    // fecha_fin_tratamiento en BD es exclusiva (inicio + duracion),
    // así que mostramos inicio + duracion - 1 como último día real.
    let fechaFinTexto = null;
    if (fechaPrimeraAdminVal) {
      const fechaBase = new Date(fechaPrimeraAdminVal + "T12:00:00");
      fechaBase.setDate(fechaBase.getDate() + dur * factor - 1);
      fechaFinTexto = fechaBase.toLocaleDateString("es-MX", { dateStyle: "long" });
    }

    return { texto, total, unidadTxt, fechaFinTexto };
  })();

  // Búsqueda nacional al completar CURP válida
  useEffect(() => {
    const curp = curpBusqueda.trim().toUpperCase();
    if (!CURP_REGEX.test(curp)) {
      setBusquedaEstado(null);
      setResultadoBusqueda(null);
      return;
    }
    setBusquedaEstado("buscando");
    buscarPacientePorCurp(curp)
      .then((res) => {
        setResultadoBusqueda(res);
        setBusquedaEstado(res.existe ? "encontrado" : "no_encontrado");
      })
      .catch(() => setBusquedaEstado("error"));
  }, [curpBusqueda]);

  // Pre-carga la CURP cuando se regresa desde el historial del paciente
  useEffect(() => {
    if (location.state?.curpPreCargado) {
      setCurpBusqueda(location.state.curpPreCargado);
    }
  }, []);

  // Carga inicial de catálogos y datos de edición
  useEffect(() => {
    Promise.all([listarMedicos(), listarMedicamentos(), listarDiagnosticos()])
      .then(([m, med, diags]) => { setMedicos(m); setMedicamentos(med); setDiagnosticos(diags); })
      .catch(() => toast.error("Error al cargar datos del formulario."));

    if (esEdicion) {
      obtenerRegistro(id).then((r) => {
        setUnidadMedicamentoEdicion(r.medicamento?.unidad ?? null);
        setUnidadDeMedidaEdicion(r.medicamento?.unidad_de_medida ?? null);
        reset({
          estatus_diagnostico: r.estatus_diagnostico ?? "",
          confirmado_por: r.confirmado_por ?? "",
          fecha_inicio_tratamiento: r.fecha_inicio_tratamiento ?? "",
          fecha_primera_administracion: r.fecha_primera_administracion ?? "",
          id_diagnostico: r.id_diagnostico != null ? String(r.id_diagnostico) : "",
          dosis_administrada: r.dosis_administrada ?? "",
          peso: r.peso != null ? String(r.peso) : "",
          talla: r.talla != null ? String(r.talla) : "",
          dosis: r.dosis != null ? String(r.dosis) : "",
          cantidad: r.cantidad != null ? String(r.cantidad) : "",
          frecuencia: r.frecuencia != null ? String(r.frecuencia) : "",
          unidad_tiempo: r.unidad_tiempo ?? "",
          duracion: r.duracion != null ? String(r.duracion) : "",
        });
      }).catch(() => toast.error("Error al cargar la prescripción."));
    }
  }, [id]);

  // Convierte strings vacíos a undefined y parsea números
  const _prepararPayload = (values) => {
    // fecha_fin_tratamiento ya no se envía: el backend la calcula
    const { fecha_fin_tratamiento: _descartado, ...resto } = values;
    const payload = Object.fromEntries(
      Object.entries(resto).filter(([, v]) => v !== "" && v !== undefined && v !== null)
    );
    if (payload.peso !== undefined) payload.peso = parseFloat(payload.peso);
    if (payload.talla !== undefined) payload.talla = parseFloat(payload.talla);
    if (payload.dosis !== undefined) payload.dosis = parseFloat(payload.dosis);
    if (payload.cantidad !== undefined) payload.cantidad = parseFloat(payload.cantidad);
    if (payload.frecuencia !== undefined) payload.frecuencia = parseInt(payload.frecuencia, 10);
    if (payload.duracion !== undefined) payload.duracion = parseInt(payload.duracion, 10);
    if (payload.id_diagnostico !== undefined) payload.id_diagnostico = parseInt(payload.id_diagnostico, 10);
    return payload;
  };

  const onSubmit = async (values) => {
    if (!esEdicion) {
      // Validar que hay CURP antes de enviar
      const curp = curpBusqueda.trim().toUpperCase();
      if (!CURP_REGEX.test(curp)) {
        toast.error("Ingresa una CURP válida para identificar al paciente.");
        return;
      }
      // Si el paciente no existe, el nombre es obligatorio
      if (busquedaEstado === "no_encontrado" && !values.nombre_completo?.trim()) {
        toast.error("El nombre completo del paciente es requerido.");
        return;
      }
    }

    // Validar: si hay posología, fecha_primera_administracion es obligatoria
    const hayPosologia = [values.dosis, values.frecuencia, values.duracion, values.unidad_tiempo]
      .some((v) => v && v !== "");
    if (hayPosologia && !values.fecha_primera_administracion) {
      toast.error("La fecha de primera administración es obligatoria cuando se indica posología.");
      return;
    }

    setLoading(true);
    try {
      const camposBase = _prepararPayload(values);

      if (modoReemplazar) {
        await reemplazarRegistro(id, camposBase);
        toast.success("Nueva prescripción creada. La anterior ha quedado anulada.");
        navigate("/notificaciones");
        return;
      } else if (esEdicion) {
        await actualizarRegistro(id, camposBase);
        toast.success("Prescripción actualizada correctamente.");
      } else {
        const payload = {
          ...camposBase,
          curp_paciente: curpBusqueda.trim().toUpperCase(),
        };
        const resultado = await crearRegistroCompleto(payload);
        const msg = resultado.paciente_creado
          ? "Paciente y prescripción registrados correctamente."
          : "Prescripción registrada correctamente.";
        toast.success(msg);
      }
      navigate("/registros");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al guardar la prescripción.");
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate("/registros")}
          className="p-2 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">
            {modoReemplazar
              ? `Editar y validar prescripción #${id}`
              : esEdicion ? `Editar prescripción #${id}` : "Registrar Paciente"}
          </h2>
          <p className="text-sm text-neutral-gray">
            {modoReemplazar
              ? "Los cambios crearán una nueva prescripción activa y anularán la actual."
              : esEdicion
                ? "Puedes modificar fechas, dosis y datos clínicos."
                : "Busca al paciente por CURP y completa la prescripción."}
          </p>
        </div>
      </div>

      {modoReemplazar && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-3 flex items-start gap-3">
          <span className="text-amber-600 mt-0.5 flex-shrink-0 text-base">⚠</span>
          <div>
            <p className="text-sm font-medium text-amber-800">Modo: Editar y validar</p>
            <p className="text-xs text-amber-700 mt-0.5">
              Al guardar se creará una nueva prescripción activa y la prescripción #{id} quedará anulada.
              Ambas quedarán visibles en el historial del paciente.
            </p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-neutral-gray/20 p-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

          {/* ── Sección: Identificación del paciente (solo en creación) ── */}
          {!esEdicion && (
            <div className="space-y-4">
              <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-2">
                1. Identificación del paciente
              </p>

              {/* Widget de verificación CURP */}
              <div className="rounded-xl border border-neutral-gray/20 bg-neutral-light/50 p-4 space-y-3">
                <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-white text-sm">
                  <Search size={14} className="text-neutral-gray flex-shrink-0" />
                  <input
                    type="text"
                    placeholder="Escribe la CURP completa (18 caracteres)..."
                    value={curpBusqueda}
                    onChange={(e) => setCurpBusqueda(e.target.value.toUpperCase())}
                    maxLength={18}
                    className="flex-1 bg-transparent outline-none text-neutral-black placeholder:text-neutral-gray font-mono"
                  />
                  {curpBusqueda && (
                    <button type="button"
                      onClick={() => { setCurpBusqueda(""); setBusquedaEstado(null); setResultadoBusqueda(null); }}
                      className="text-neutral-gray hover:text-neutral-black">
                      <X size={14} />
                    </button>
                  )}
                  <span className={`text-xs font-mono ${curpBusqueda.length === 18 ? "text-secondary" : "text-neutral-gray/50"}`}>
                    {curpBusqueda.length}/18
                  </span>
                </div>

                {busquedaEstado === "buscando" && (
                  <div className="flex items-center gap-2 text-sm text-neutral-gray">
                    <span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin inline-block" />
                    Buscando en el sistema...
                  </div>
                )}

                {busquedaEstado === "encontrado" && resultadoBusqueda && (
                  <div className="flex items-start justify-between gap-3 bg-secondary/5 border border-secondary/20 rounded-lg px-4 py-3">
                    <div className="flex items-start gap-2">
                      <UserCheck size={16} className="text-secondary mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-semibold text-neutral-black">{resultadoBusqueda.nombre_completo}</p>
                        <p className="text-xs text-neutral-gray mt-0.5">
                          Unidad: <span className="font-medium">{resultadoBusqueda.nombre_unidad ?? resultadoBusqueda.clues_unidad_adscripcion}</span>
                        </p>
                        <p className="text-xs text-neutral-gray">
                          Prescripciones registradas: <span className="font-medium">{resultadoBusqueda.total_registros}</span>
                        </p>
                        <p className="text-xs text-secondary mt-1">Paciente identificado — continúa llenando la prescripción.</p>
                      </div>
                    </div>
                    <button type="button"
                      onClick={() => navigate(`/pacientes/${curpBusqueda}`, {
                        state: { from: "registro-form", curpOrigen: curpBusqueda }
                      })}
                      className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary-dark
                        border border-primary/30 hover:border-primary px-3 py-1.5 rounded-lg transition flex-shrink-0">
                      <ExternalLink size={12} />
                      Ver historial
                    </button>
                  </div>
                )}

                {busquedaEstado === "no_encontrado" && (
                  <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                    <UserX size={16} className="text-amber-600 flex-shrink-0" />
                    <p className="text-sm text-amber-700">
                      Paciente no encontrado. Completa los datos a continuación para registrarlo.
                    </p>
                  </div>
                )}

                {busquedaEstado === "error" && (
                  <p className="text-sm text-red-500">Error al buscar. Intenta de nuevo.</p>
                )}
              </div>

              {/* Campos del paciente nuevo — solo si no fue encontrado */}
              {busquedaEstado === "no_encontrado" && (
                <div className="space-y-4 rounded-xl border border-amber-200 bg-amber-50/30 p-4">
                  <p className="text-xs font-medium text-amber-700">Datos del paciente nuevo</p>

                  <div>
                    <label className="block text-sm font-medium text-neutral-black mb-1">
                      Nombre completo <span className="text-primary">*</span>
                    </label>
                    <input type="text" placeholder="Apellido Apellido Nombre"
                      className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                        focus:ring-2 focus:ring-primary/20 focus:border-primary
                        ${errors.nombre_completo ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-white"}`}
                      {...register("nombre_completo")} />
                    {errors.nombre_completo && <p className="text-red-500 text-xs mt-1">{errors.nombre_completo.message}</p>}
                  </div>

                </div>
              )}
            </div>
          )}

          {/* ── Sección: Datos de la prescripción ── */}
          <div className="space-y-4">
            {!esEdicion && (
              <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-2">
                2. Datos de la prescripción
              </p>
            )}

            {/* Médico */}
            {!esEdicion && (
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
            )}

            {/* Medicamento */}
            {!esEdicion && (
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
            )}

            {/* Unidad */}
            {!esEdicion && (
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Unidad donde se genera la prescripción <span className="text-primary">*</span>
                </label>
                <UnidadCombobox
                  value={cluesSeleccionada}
                  onChange={(clues) => setValue("clues", clues, { shouldValidate: true })}
                  error={errors.clues}
                />
                {errors.clues && <p className="text-red-500 text-xs mt-1">{errors.clues.message}</p>}
              </div>
            )}

            {/* Diagnóstico */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Diagnóstico
                <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
              </label>
              <select
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                {...register("id_diagnostico")}
              >
                <option value="">— Selecciona un diagnóstico —</option>
                {diagnosticos.map((d) => (
                  <option key={d.id_diagnostico} value={String(d.id_diagnostico)}>
                    {d.codigo_cie10 ? `${d.codigo_cie10} — ` : ""}{d.nombre}
                  </option>
                ))}
              </select>
            </div>

            {/* Estatus del diagnóstico */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Estatus del diagnóstico
                <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
              </label>
              <select
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                {...register("estatus_diagnostico")}
              >
                <option value="">— Selecciona un estatus —</option>
                {ESTATUS_OPTIONS.map((op) => (
                  <option key={op} value={op}>{op}</option>
                ))}
              </select>
            </div>

            {/* Confirmado por */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Confirmado por
                <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
              </label>
              <select
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                {...register("confirmado_por")}
              >
                <option value="">— Selecciona un área —</option>
                {CONFIRMADO_POR_OPTIONS.map((op) => (
                  <option key={op} value={op}>{op}</option>
                ))}
              </select>
            </div>

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


            {/* Peso y Talla */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Peso <span className="text-neutral-gray font-normal">(kg, opcional)</span>
                </label>
                <input type="number" step="0.01" min="0" max="999.99" placeholder="ej. 75.50"
                  className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                    text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                  {...register("peso")} />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Talla <span className="text-neutral-gray font-normal">(cm, opcional)</span>
                </label>
                <input type="number" step="0.01" min="0" max="999.99" placeholder="ej. 165.00"
                  className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                    text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                  {...register("talla")} />
              </div>
            </div>
          </div>

          {/* ── Sección: Posología ── */}
          <div className="space-y-4">
            <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-2">
              {esEdicion ? "Posología" : "3. Posología"}
              <span className="normal-case font-normal ml-2">
                (opcional — calcula el total de medicamento requerido)
              </span>
            </p>

            {/* Fecha de primera administración — obligatoria con posología */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Fecha de primera administración
                <span className="text-primary ml-1">*</span>
                <span className="text-neutral-gray font-normal ml-1">(requerida con posología)</span>
              </label>
              <input type="date"
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                {...register("fecha_primera_administracion")} />
              <p className="text-xs text-neutral-gray mt-1">
                La fecha de fin se calculará automáticamente a partir de esta fecha y la duración.
              </p>
            </div>

            {/* Dosis por toma + Cantidad */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Dosis por toma
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    placeholder="ej. 2"
                    className="w-24 px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                      text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                    {...register("dosis")}
                  />
                  <span className="text-sm text-neutral-gray">
                    {unidadMedicamento ? `${unidadMedicamento}(s)` : "unidad(es)"}
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Cantidad por unidad
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="ej. 10"
                    className="w-24 px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                      text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                    {...register("cantidad")}
                  />
                  <span className="text-sm text-neutral-gray">
                    {unidadDeMedida ?? "mg/ml"}
                  </span>
                </div>
              </div>
            </div>

            {/* Frecuencia */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Frecuencia
              </label>
              <div className="flex items-center gap-3">
                <span className="text-sm text-neutral-gray">Cada</span>
                <select
                  className="px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                    text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                  {...register("frecuencia")}
                >
                  <option value="">— —</option>
                  <option value="1">1 hora</option>
                  <option value="2">2 horas</option>
                  <option value="4">4 horas</option>
                  <option value="6">6 horas</option>
                  <option value="8">8 horas</option>
                  <option value="12">12 horas</option>
                  <option value="24">24 horas</option>
                  <option value="48">48 horas</option>
                  <option value="72">72 horas</option>
                  <option value="96">96 horas</option>
                  <option value="168">168 horas</option>
                </select>
              </div>
            </div>

            {/* Duración */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Duración del tratamiento
              </label>
              <div className="flex items-center gap-3">
                <span className="text-sm text-neutral-gray">Por</span>
                <input
                  type="number"
                  min="1"
                  placeholder="7"
                  className="w-24 px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                    text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                  {...register("duracion")}
                />
                <select
                  className="px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                    text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                  {...register("unidad_tiempo")}
                >
                  <option value="">— Unidad —</option>
                  <option value="días">Días</option>
                  <option value="semanas">Semanas</option>
                  <option value="meses">Meses</option>
                </select>
              </div>
            </div>

            {previewPrescripcion ? (
              <div className="bg-secondary/5 border border-secondary/20 rounded-lg px-4 py-3 space-y-1.5">
                <p className="text-xs text-neutral-gray uppercase tracking-wide font-semibold">Prescripción generada</p>
                <p className="text-sm font-medium text-neutral-black">{previewPrescripcion.texto}</p>
                <div className="flex flex-wrap gap-x-6 gap-y-1">
                  <p className="text-xs text-neutral-gray">
                    Total:{" "}
                    <span className="font-semibold text-secondary">
                      {previewPrescripcion.total % 1 === 0
                        ? previewPrescripcion.total
                        : previewPrescripcion.total.toFixed(2)}{" "}
                      {previewPrescripcion.unidadTxt}
                    </span>
                  </p>
                  {previewPrescripcion.fechaFinTexto && (
                    <p className="text-xs text-neutral-gray">
                      Fin estimado:{" "}
                      <span className="font-semibold text-neutral-black">
                        {previewPrescripcion.fechaFinTexto}
                      </span>
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-xs text-neutral-gray/60 bg-neutral-light/80 rounded-lg px-3 py-2">
                Completa los campos de posología para ver la prescripción calculada.
              </p>
            )}
          </div>

          {/* Botones */}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => navigate("/registros")}
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
              {loading ? "Guardando..." : esEdicion ? "Guardar cambios" : "Registrar"}
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}
