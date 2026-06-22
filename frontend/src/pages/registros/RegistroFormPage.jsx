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
import { ArrowLeft, Save, Search, X, UserCheck, UserX, ExternalLink, Eye, ChevronLeft, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

import { crearRegistroCompleto, actualizarRegistro, reemplazarRegistro, obtenerRegistro } from "../../api/registros";
import { buscarPacientePorCurp, buscarPacientesPorNombre } from "../../api/pacientes";
import { listarMedicos } from "../../api/medicos";
import { listarMedicamentos, listarDiagnosticos } from "../../api/catalogos";
import UnidadCombobox from "../../components/shared/UnidadCombobox";
import useAuthStore from "../../store/authStore";

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------
const CURP_REGEX = /^[A-Z]{4}\d{6}[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$/;

const ESTATUS_OPTIONS = ["confirmado", "por confirmar"];

// Valor fijo actual del campo "Confirmado por". Las demás opciones se
// conservan en CONFIRMADO_POR_OPTIONS por si se reactivan más adelante.
const CONFIRMADO_POR_FIJO = "Médico tratante";

const CONFIRMADO_POR_OPTIONS = [
  CONFIRMADO_POR_FIJO,
  "Consulta Externa",
  "Farmacia Hospitalaria",
  "Comité de Medicamentos",
  "Dirección Médica",
  "Trabajo Social",
];

// Campos del formulario (requeridos en creación y edición)
const camposFormulario = {
  // Sin UI — hardcodeados o no visibles en el form
  estatus_diagnostico: z.string().optional().or(z.literal("")),
  dosis_administrada: z.string().max(100).optional().or(z.literal("")),
  // Requeridos
  id_diagnostico: z.string().min(1, "Selecciona un diagnóstico."),
  confirmado_por: z.string().min(1, "Selecciona quién confirmó."),
  confirmado_mediante: z.string().min(1, "Indica mediante qué se confirmó el diagnóstico.").max(200),
  fecha_inicio_tratamiento: z.string().min(1, "Selecciona la fecha de inicio de tratamiento."),
  fecha_primera_administracion: z.string().min(1, "Indica la fecha de primera administración."),
  peso: z.string().min(1, "Indica el peso del paciente (kg)."),
  talla: z.string().min(1, "Indica la talla del paciente (cm)."),
  dosis: z.string().min(1, "Indica la dosis por toma."),
  cantidad: z.string().min(1, "Indica la cantidad por unidad."),
  frecuencia: z.string().min(1, "Selecciona la frecuencia."),
  unidad_tiempo: z.string().min(1, "Selecciona la unidad de tiempo."),
  duracion: z.string().min(1, "Indica la duración del tratamiento."),
};

const schemaCrear = z.object({
  // Campos de paciente nuevo (validación adicional en onSubmit)
  nombre_completo: z.string().optional().or(z.literal("")),
  // Datos de prescripción obligatorios
  id_medico: z.number({ invalid_type_error: "Selecciona un médico." }).int().positive(),
  clave_cnis: z.string().min(1, "Selecciona un medicamento."),
  clues: z.string().min(1, "Selecciona una unidad."),
  ...camposFormulario,
});

const schemaEditar = z.object({ ...camposFormulario });

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const formatFecha = (iso) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
};

const formatFechaCorta = (iso) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y.slice(2)}`;
};

function FilaPreview({ label, valor, mono = false, span2 = false }) {
  return (
    <div className={span2 ? "col-span-2" : ""}>
      <p className="text-xs text-neutral-gray mb-0.5">{label}</p>
      <p className={`text-sm font-medium text-neutral-black ${mono ? "font-mono" : ""}`}>
        {valor || "—"}
      </p>
    </div>
  );
}

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
// Tarjeta de paciente identificado (por CURP o por nombre)
// ---------------------------------------------------------------------------
function PacienteEncontradoCard({ data, historialId, navigate, onQuitar }) {
  return (
    <div className="flex items-start justify-between gap-3 bg-secondary/5 border border-secondary/20 rounded-lg px-4 py-3">
      <div className="flex items-start gap-2">
        <UserCheck size={16} className="text-secondary mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-sm font-semibold text-neutral-black">{data.nombre_completo}</p>
          <p className="text-xs text-neutral-gray mt-0.5">
            Unidad: <span className="font-medium">{data.nombre_unidad ?? data.clues_unidad_adscripcion}</span>
          </p>
          <p className="text-xs text-neutral-gray">
            Prescripciones registradas: <span className="font-medium">{data.total_registros}</span>
          </p>
          {data.fecha_nacimiento && (
            <p className="text-xs text-neutral-gray">
              Fecha de nacimiento: <span className="font-medium">{formatFecha(data.fecha_nacimiento)}</span>
            </p>
          )}
          <p className="text-xs text-secondary mt-1">Paciente identificado — continúa llenando la prescripción.</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <button type="button"
          onClick={() => navigate(`/pacientes/${historialId}`, {
            state: { from: "registro-form", curpOrigen: typeof historialId === "string" ? historialId : null }
          })}
          className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary-dark
            border border-primary/30 hover:border-primary px-3 py-1.5 rounded-lg transition">
          <ExternalLink size={12} />
          Ver historial
        </button>
        {onQuitar && (
          <button type="button" onClick={onQuitar}
            className="text-neutral-gray hover:text-neutral-black p-1.5">
            <X size={14} />
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Buscador "as you type" de pacientes por nombre (para pacientes sin CURP)
// ---------------------------------------------------------------------------
function BuscadorPacientePorNombre({ onSelect }) {
  const [query, setQuery] = useState("");
  const [resultados, setResultados] = useState([]);
  const [estado, setEstado] = useState(null); // null | "buscando" | "resultados" | "sin_resultados" | "error"
  const [abierto, setAbierto] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setAbierto(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 3) {
      return;
    }
    const timeoutId = setTimeout(() => {
      setEstado("buscando");
      buscarPacientesPorNombre(q)
        .then((res) => {
          setResultados(res.resultados);
          setEstado(res.resultados.length > 0 ? "resultados" : "sin_resultados");
        })
        .catch(() => setEstado("error"));
    }, 350);
    return () => clearTimeout(timeoutId);
  }, [query]);

  const limpiar = () => { setQuery(""); setResultados([]); setEstado(null); };

  // El estado de búsqueda solo es relevante si el query sigue cumpliendo el mínimo
  const estadoVisible = query.trim().length >= 3 ? estado : null;

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-white text-sm">
        <Search size={14} className="text-neutral-gray flex-shrink-0" />
        <input
          type="text"
          placeholder="Escribe el nombre del paciente (apellidos o nombre, mín. 3 letras)..."
          value={query}
          onChange={(e) => { setQuery(e.target.value); setAbierto(true); }}
          onFocus={() => { if (resultados.length > 0) setAbierto(true); }}
          className="flex-1 bg-transparent outline-none text-neutral-black placeholder:text-neutral-gray"
        />
        {query && (
          <button type="button" onClick={limpiar} className="text-neutral-gray hover:text-neutral-black">
            <X size={14} />
          </button>
        )}
      </div>

      {estadoVisible === "buscando" && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-gray/20 rounded-lg
          shadow-lg px-4 py-3 text-sm text-neutral-gray flex items-center gap-2">
          <span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin inline-block" />
          Buscando...
        </div>
      )}

      {abierto && estadoVisible === "resultados" && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-neutral-gray/20 rounded-lg
          shadow-lg max-h-64 overflow-y-auto">
          {resultados.map((item) => (
            <li key={item.id_paciente}
              onMouseDown={() => { onSelect(item); limpiar(); setAbierto(false); }}
              className="px-4 py-2.5 cursor-pointer hover:bg-primary/5 text-sm">
              <p className="font-medium text-neutral-black">{item.nombre_completo}</p>
              <p className="text-xs text-neutral-gray">
                Nac. {formatFechaCorta(item.fecha_nacimiento)} — {item.nombre_unidad ?? item.clues_unidad_adscripcion}
              </p>
            </li>
          ))}
        </ul>
      )}

      {estadoVisible === "sin_resultados" && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-gray/20 rounded-lg
          shadow-lg px-4 py-3 text-sm text-neutral-gray">
          No se encontraron pacientes con ese nombre.
        </div>
      )}

      {estadoVisible === "error" && (
        <p className="text-sm text-red-500 mt-1">Error al buscar. Intenta de nuevo.</p>
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

  const { rolNombre, cluesUnidadAsignada, nombreUnidad } = useAuthStore();

  const [medicos, setMedicos] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);
  const [diagnosticos, setDiagnosticos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [enVistaPrevia, setEnVistaPrevia] = useState(false);
  const [nombreUnidadSeleccionada, setNombreUnidadSeleccionada] = useState("");
  const [unidadMedicamentoEdicion, setUnidadMedicamentoEdicion] = useState(null);
  const [unidadDeMedidaEdicion, setUnidadDeMedidaEdicion] = useState(null);
  // Datos de paciente nuevo
  const [fechaNacimientoNuevo, setFechaNacimientoNuevo] = useState("");
  // Expediente
  const [numeroExpediente, setNumeroExpediente] = useState("");

  // Estado del widget de búsqueda por CURP
  const [curpBusqueda, setCurpBusqueda] = useState("");
  const [busquedaEstado, setBusquedaEstado] = useState(null); // null | "buscando" | "encontrado" | "no_encontrado" | "error"
  const [resultadoBusqueda, setResultadoBusqueda] = useState(null);

  // Paciente identificado por búsqueda de nombre (pacientes sin CURP)
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState(null);
  // CURP opcional al registrar un paciente nuevo sin identificar previamente
  const [curpPacienteNuevo, setCurpPacienteNuevo] = useState("");

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    trigger,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esEdicion ? schemaEditar : schemaCrear),
    defaultValues: !esEdicion ? { confirmado_por: CONFIRMADO_POR_FIJO } : undefined,
  });

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
    setPacienteSeleccionado(null);
    setBusquedaEstado("buscando");
    buscarPacientePorCurp(curp)
      .then((res) => {
        setResultadoBusqueda(res);
        setBusquedaEstado(res.existe ? "encontrado" : "no_encontrado");
      })
      .catch(() => setBusquedaEstado("error"));
  }, [curpBusqueda]);

  // Paciente identificado (por CURP o por nombre) — fuente única para la tarjeta y los payloads
  const pacienteEncontrado = busquedaEstado === "encontrado" ? resultadoBusqueda : pacienteSeleccionado;

  // Pre-carga la CURP cuando se regresa desde el historial del paciente
  useEffect(() => {
    if (location.state?.curpPreCargado) {
      setCurpBusqueda(location.state.curpPreCargado);
    }
  }, []);

  // Para RESPONSABLE_UNIDAD en creación: pre-establecer su unidad
  useEffect(() => {
    if (!esEdicion && rolNombre === "RESPONSABLE_UNIDAD" && cluesUnidadAsignada) {
      setValue("clues", cluesUnidadAsignada, { shouldValidate: false });
      setNombreUnidadSeleccionada(nombreUnidad ?? cluesUnidadAsignada);
    }
  }, []);

  // Carga de medicamentos cuando cambia la unidad seleccionada (solo en creación)
  const prevCluesRef = useRef(null);
  useEffect(() => {
    if (esEdicion || !cluesSeleccionada) {
      if (!esEdicion) setMedicamentos([]);
      return;
    }
    // Si la unidad cambió (no es la primera carga), limpiar el medicamento elegido
    if (prevCluesRef.current !== null && prevCluesRef.current !== cluesSeleccionada) {
      setValue("clave_cnis", "", { shouldValidate: false });
    }
    prevCluesRef.current = cluesSeleccionada;

    listarMedicamentos(cluesSeleccionada)
      .then(setMedicamentos)
      .catch(() => toast.error("Error al cargar medicamentos de la unidad."));
  }, [cluesSeleccionada]);

  // Carga inicial de catálogos y datos de edición
  useEffect(() => {
    Promise.all([listarMedicos(), listarDiagnosticos()])
      .then(([m, diags]) => { setMedicos(m); setDiagnosticos(diags); })
      .catch(() => toast.error("Error al cargar datos del formulario."));

    if (esEdicion) {
      obtenerRegistro(id).then((r) => {
        setUnidadMedicamentoEdicion(r.medicamento?.unidad ?? null);
        setUnidadDeMedidaEdicion(r.medicamento?.unidad_de_medida ?? null);
        reset({
          estatus_diagnostico: r.estatus_diagnostico ?? "",
          confirmado_por: r.confirmado_por ?? "",
          confirmado_mediante: r.confirmado_mediante ?? "",
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
    payload.estatus_diagnostico = "confirmado";
    return payload;
  };

  // Valida la identificación del paciente (solo en creación): paciente ya
  // identificado (por CURP o por nombre), o datos mínimos para uno nuevo.
  const _validarIdentificacionPaciente = (values) => {
    if (pacienteEncontrado) return true;

    const curp = curpBusqueda.trim().toUpperCase();
    if (CURP_REGEX.test(curp)) {
      if (busquedaEstado === "no_encontrado" && !values.nombre_completo?.trim()) {
        toast.error("El nombre completo del paciente es requerido.");
        return false;
      }
      return true;
    }

    // Sin CURP y sin paciente identificado: se registrará un paciente nuevo
    if (!values.nombre_completo?.trim()) {
      toast.error("El nombre completo del paciente es requerido.");
      return false;
    }
    if (curpPacienteNuevo.trim() && !CURP_REGEX.test(curpPacienteNuevo.trim().toUpperCase())) {
      toast.error("La CURP del paciente nuevo no es válida.");
      return false;
    }
    return true;
  };

  const handleVistaPrevia = async () => {
    if (!esEdicion && !_validarIdentificacionPaciente(watch())) return;
    const valido = await trigger();
    if (!valido) {
      toast.error("Completa todos los campos antes de continuar.");
      return;
    }
    setEnVistaPrevia(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const onSubmit = async (values) => {
    if (!esEdicion && !_validarIdentificacionPaciente(values)) return;

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
          ...(numeroExpediente.trim() && { numero_expediente: numeroExpediente.trim() }),
        };

        if (pacienteSeleccionado) {
          payload.id_paciente = pacienteSeleccionado.id_paciente;
        } else {
          const curp = curpBusqueda.trim().toUpperCase();
          if (CURP_REGEX.test(curp)) {
            payload.curp_paciente = curp;
            if (busquedaEstado === "no_encontrado" && fechaNacimientoNuevo) {
              payload.fecha_nacimiento = fechaNacimientoNuevo;
            }
          } else {
            if (fechaNacimientoNuevo) payload.fecha_nacimiento = fechaNacimientoNuevo;
            const curpNueva = curpPacienteNuevo.trim().toUpperCase();
            if (curpNueva) payload.curp_paciente = curpNueva;
          }
        }

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

      <div className={`bg-white rounded-xl border border-neutral-gray/20 p-6 ${enVistaPrevia ? "hidden" : ""}`}>
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
                  <PacienteEncontradoCard data={resultadoBusqueda} historialId={curpBusqueda} navigate={navigate} />
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

              {/* Buscador por nombre — alternativa para pacientes sin CURP */}
              {busquedaEstado !== "encontrado" && (
                <div className="rounded-xl border border-neutral-gray/20 bg-neutral-light/50 p-4 space-y-3">
                  <p className="text-xs font-medium text-neutral-gray">
                    Buscar por nombre <span className="font-normal text-neutral-gray/70">(si el paciente no tiene CURP)</span>
                  </p>
                  {pacienteSeleccionado ? (
                    <PacienteEncontradoCard
                      data={pacienteSeleccionado}
                      historialId={pacienteSeleccionado.curp_paciente ?? pacienteSeleccionado.id_paciente}
                      navigate={navigate}
                      onQuitar={() => setPacienteSeleccionado(null)}
                    />
                  ) : (
                    <BuscadorPacientePorNombre onSelect={setPacienteSeleccionado} />
                  )}
                </div>
              )}

              {/* Campos del paciente nuevo — solo si no se identificó un paciente existente */}
              {!pacienteEncontrado && (
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

                  <div>
                    <label className="block text-sm font-medium text-neutral-black mb-1">
                      Fecha de nacimiento
                      <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
                    </label>
                    <input
                      type="date"
                      value={fechaNacimientoNuevo}
                      onChange={(e) => setFechaNacimientoNuevo(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-white
                        text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                    />
                  </div>

                  {!CURP_REGEX.test(curpBusqueda.trim().toUpperCase()) && (
                    <div>
                      <label className="block text-sm font-medium text-neutral-black mb-1">
                        CURP
                        <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
                      </label>
                      <input
                        type="text"
                        placeholder="Si el paciente cuenta con CURP, captúrala aquí"
                        value={curpPacienteNuevo}
                        onChange={(e) => setCurpPacienteNuevo(e.target.value.toUpperCase())}
                        maxLength={18}
                        className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-white
                          text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition font-mono"
                      />
                    </div>
                  )}
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

            {/* Unidad */}
            {!esEdicion && (
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Unidad donde se genera la prescripción <span className="text-primary">*</span>
                </label>
                {rolNombre === "RESPONSABLE_UNIDAD" ? (
                  <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-neutral-gray/20
                    bg-neutral-gray/10 text-sm text-neutral-black cursor-not-allowed">
                    <span className="font-mono text-xs text-neutral-gray">{cluesUnidadAsignada}</span>
                    <span>{nombreUnidad ?? "—"}</span>
                  </div>
                ) : (
                  <UnidadCombobox
                    value={cluesSeleccionada}
                    onChange={(clues, nombre) => {
                      setValue("clues", clues, { shouldValidate: true });
                      setNombreUnidadSeleccionada(nombre ?? "");
                    }}
                    error={errors.clues}
                  />
                )}
                {errors.clues && <p className="text-red-500 text-xs mt-1">{errors.clues.message}</p>}
              </div>
            )}

            {/* Número de expediente — solo en creación */}
            {!esEdicion && (
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Número de expediente
                  <span className="text-neutral-gray font-normal ml-1">(opcional)</span>
                </label>
                <input
                  type="text"
                  placeholder="ej. EXP-2024-001"
                  maxLength={100}
                  value={numeroExpediente}
                  onChange={(e) => setNumeroExpediente(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                    text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                />
                <p className="text-xs text-neutral-gray mt-1">
                  Se registra para esta unidad. Cambia si el paciente se transfiere.
                </p>
              </div>
            )}

            {/* Medicamento — se carga según la unidad seleccionada */}
            {!esEdicion && (
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Medicamento (clave CNIS) <span className="text-primary">*</span>
                </label>
                <select
                  disabled={!cluesSeleccionada}
                  className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                    focus:ring-2 focus:ring-primary/20 focus:border-primary
                    disabled:opacity-50 disabled:cursor-not-allowed
                    ${errors.clave_cnis ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                  {...register("clave_cnis")}
                >
                  <option value="">
                    {!cluesSeleccionada
                      ? "— Selecciona primero una unidad —"
                      : medicamentos.length === 0
                        ? "— Sin medicamentos asignados a esta unidad —"
                        : "— Selecciona un medicamento —"}
                  </option>
                  {medicamentos.map((m) => (
                    <option key={m.clave_cnis} value={m.clave_cnis}>
                      {m.clave_cnis} — {m.descripcion.slice(0, 70)}
                    </option>
                  ))}
                </select>
                {errors.clave_cnis && <p className="text-red-500 text-xs mt-1">{errors.clave_cnis.message}</p>}
                {medSeleccionado && (
                  <div className="mt-2 px-3 py-2 rounded-lg bg-primary/5 border border-primary/15 text-xs text-neutral-black leading-relaxed">
                    <span className="font-mono text-neutral-gray mr-1">{medSeleccionado.clave_cnis}</span>
                    {medSeleccionado.descripcion}
                  </div>
                )}
              </div>
            )}

            {/* Diagnóstico */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Diagnóstico <span className="text-primary">*</span>
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
              {errors.id_diagnostico && <p className="text-red-500 text-xs mt-1">{errors.id_diagnostico.message}</p>}
            </div>

            {/* Confirmado por */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Confirmado por <span className="text-primary">*</span>
              </label>
              <select
                disabled
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition
                  disabled:opacity-70 disabled:cursor-not-allowed"
                {...register("confirmado_por")}
              >
                <option value="">— Selecciona un área —</option>
                {CONFIRMADO_POR_OPTIONS.map((op) => (
                  <option key={op} value={op}>{op}</option>
                ))}
              </select>
              <p className="text-xs text-neutral-gray mt-1">Por el momento este campo queda fijo en "{CONFIRMADO_POR_FIJO}".</p>
              {errors.confirmado_por && <p className="text-red-500 text-xs mt-1">{errors.confirmado_por.message}</p>}
            </div>

            {/* Confirmado mediante */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Confirmado mediante <span className="text-primary">*</span>
              </label>
              <input type="text" maxLength={200} placeholder="ej. Estudio de gabinete, biopsia, laboratorio..."
                className={`w-full px-4 py-2.5 rounded-lg border bg-neutral-light text-sm outline-none transition
                  focus:ring-2 focus:ring-primary/20 focus:border-primary
                  ${errors.confirmado_mediante ? "border-red-400 bg-red-50" : "border-neutral-gray/30"}`}
                {...register("confirmado_mediante")} />
              {errors.confirmado_mediante && <p className="text-red-500 text-xs mt-1">{errors.confirmado_mediante.message}</p>}
            </div>

            {/* Fecha inicio tratamiento */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Fecha inicio de tratamiento <span className="text-primary">*</span>
              </label>
              <input type="date"
                className={`w-full px-4 py-2.5 rounded-lg border bg-neutral-light text-sm outline-none transition
                  focus:ring-2 focus:ring-primary/20 focus:border-primary
                  ${errors.fecha_inicio_tratamiento ? "border-red-400 bg-red-50" : "border-neutral-gray/30"}`}
                {...register("fecha_inicio_tratamiento")} />
              {errors.fecha_inicio_tratamiento && <p className="text-red-500 text-xs mt-1">{errors.fecha_inicio_tratamiento.message}</p>}
            </div>

            {/* Peso y Talla */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Peso <span className="text-neutral-gray font-normal">(kg)</span> <span className="text-primary">*</span>
                </label>
                <input type="number" step="0.01" min="0" max="999.99" placeholder="ej. 75.50"
                  className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                    focus:ring-2 focus:ring-primary/20 focus:border-primary
                    ${errors.peso ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                  {...register("peso")} />
                {errors.peso && <p className="text-red-500 text-xs mt-1">{errors.peso.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Talla <span className="text-neutral-gray font-normal">(cm)</span> <span className="text-primary">*</span>
                </label>
                <input type="number" step="0.01" min="0" max="999.99" placeholder="ej. 165.00"
                  className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                    focus:ring-2 focus:ring-primary/20 focus:border-primary
                    ${errors.talla ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                  {...register("talla")} />
                {errors.talla && <p className="text-red-500 text-xs mt-1">{errors.talla.message}</p>}
              </div>
            </div>
          </div>

          {/* ── Sección: Posología ── */}
          <div className="space-y-4">
            <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-2">
              {esEdicion ? "Posología" : "3. Posología"}
            </p>

            {/* Fecha de primera administración */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Fecha de primera administración <span className="text-primary">*</span>
              </label>
              <input type="date"
                className={`w-full px-4 py-2.5 rounded-lg border bg-neutral-light text-sm outline-none transition
                  focus:ring-2 focus:ring-primary/20 focus:border-primary
                  ${errors.fecha_primera_administracion ? "border-red-400 bg-red-50" : "border-neutral-gray/30"}`}
                {...register("fecha_primera_administracion")} />
              {errors.fecha_primera_administracion
                ? <p className="text-red-500 text-xs mt-1">{errors.fecha_primera_administracion.message}</p>
                : <p className="text-xs text-neutral-gray mt-1">La fecha de fin se calculará automáticamente.</p>
              }
            </div>

            {/* Dosis por toma + Cantidad */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Dosis por toma <span className="text-primary">*</span>
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    placeholder="ej. 2"
                    className={`w-24 px-4 py-2.5 rounded-lg border text-sm outline-none transition
                      focus:ring-2 focus:ring-primary/20 focus:border-primary
                      ${errors.dosis ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                    {...register("dosis")}
                  />
                  <span className="text-sm text-neutral-gray">
                    {unidadMedicamento ? `${unidadMedicamento}(s)` : "unidad(es)"}
                  </span>
                </div>
                {errors.dosis && <p className="text-red-500 text-xs mt-1">{errors.dosis.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-black mb-1">
                  Cantidad por unidad <span className="text-primary">*</span>
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="ej. 10"
                    className={`w-24 px-4 py-2.5 rounded-lg border text-sm outline-none transition
                      focus:ring-2 focus:ring-primary/20 focus:border-primary
                      ${errors.cantidad ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                    {...register("cantidad")}
                  />
                  <span className="text-sm text-neutral-gray">
                    {unidadDeMedida ?? "mg/ml"}
                  </span>
                </div>
                {errors.cantidad && <p className="text-red-500 text-xs mt-1">{errors.cantidad.message}</p>}
              </div>
            </div>

            {/* Frecuencia */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Frecuencia <span className="text-primary">*</span>
              </label>
              <div className="flex items-center gap-3">
                <span className="text-sm text-neutral-gray">Cada</span>
                <select
                  className={`px-4 py-2.5 rounded-lg border text-sm outline-none transition
                    focus:ring-2 focus:ring-primary/20 focus:border-primary
                    ${errors.frecuencia ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
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
              {errors.frecuencia && <p className="text-red-500 text-xs mt-1">{errors.frecuencia.message}</p>}
            </div>

            {/* Duración */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Duración del tratamiento <span className="text-primary">*</span>
              </label>
              <div className="flex items-center gap-3">
                <span className="text-sm text-neutral-gray">Por</span>
                <input
                  type="number"
                  min="1"
                  placeholder="7"
                  className={`w-24 px-4 py-2.5 rounded-lg border text-sm outline-none transition
                    focus:ring-2 focus:ring-primary/20 focus:border-primary
                    ${errors.duracion ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                  {...register("duracion")}
                />
                <select
                  className={`px-4 py-2.5 rounded-lg border text-sm outline-none transition
                    focus:ring-2 focus:ring-primary/20 focus:border-primary
                    ${errors.unidad_tiempo ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                  {...register("unidad_tiempo")}
                >
                  <option value="">— Unidad —</option>
                  <option value="días">Días</option>
                  <option value="semanas">Semanas</option>
                  <option value="meses">Meses</option>
                </select>
              </div>
              {(errors.duracion || errors.unidad_tiempo) && (
                <p className="text-red-500 text-xs mt-1">
                  {errors.duracion?.message || errors.unidad_tiempo?.message}
                </p>
              )}
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
            {esEdicion ? (
              <button type="submit" disabled={loading}
                className="flex-1 flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark
                  text-white text-sm font-medium py-2.5 rounded-lg transition
                  disabled:opacity-60 disabled:cursor-not-allowed">
                {loading
                  ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <Save size={15} />}
                {loading ? "Guardando..." : "Guardar cambios"}
              </button>
            ) : (
              <button type="button" onClick={handleVistaPrevia}
                className="flex-1 flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark
                  text-white text-sm font-medium py-2.5 rounded-lg transition">
                <Eye size={15} />
                Vista previa
              </button>
            )}
          </div>

        </form>
      </div>

      {/* ── Vista previa ── */}
      {enVistaPrevia && (() => {
        const vals = watch();
        const medicoPreview   = medicos.find((m) => m.id_medico === vals.id_medico);
        const medPreview      = medicamentos.find((m) => m.clave_cnis === vals.clave_cnis);
        const diagPreview     = diagnosticos.find((d) => String(d.id_diagnostico) === String(vals.id_diagnostico));
        const unidadDisplay   = rolNombre === "RESPONSABLE_UNIDAD"
          ? `${cluesUnidadAsignada} — ${nombreUnidad ?? ""}`
          : nombreUnidadSeleccionada
            ? `${vals.clues} — ${nombreUnidadSeleccionada}`
            : vals.clues;

        return (
          <div className="bg-white rounded-xl border border-neutral-gray/20 p-6 space-y-6">
            {/* Encabezado */}
            <div className="flex items-center gap-2">
              <CheckCircle2 size={20} className="text-secondary flex-shrink-0" />
              <div>
                <h3 className="text-base font-semibold text-neutral-black">Confirma los datos</h3>
                <p className="text-xs text-neutral-gray mt-0.5">Revisa la información antes de registrar la prescripción.</p>
              </div>
            </div>

            {/* Paciente */}
            {!esEdicion && (
              <section>
                <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-1.5 mb-3">
                  Paciente
                </p>
                <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                  <FilaPreview
                    label="CURP"
                    valor={pacienteEncontrado?.curp_paciente || curpBusqueda || curpPacienteNuevo.trim().toUpperCase()}
                    mono
                  />
                  <FilaPreview label="Nombre" valor={pacienteEncontrado ? pacienteEncontrado.nombre_completo : vals.nombre_completo} />
                  <FilaPreview
                    label="Estado"
                    valor={pacienteEncontrado ? "Paciente existente" : "Paciente nuevo"}
                  />
                  {pacienteEncontrado?.fecha_nacimiento && (
                    <FilaPreview label="Fecha de nacimiento" valor={formatFecha(pacienteEncontrado.fecha_nacimiento)} />
                  )}
                  {!pacienteEncontrado && fechaNacimientoNuevo && (
                    <FilaPreview label="Fecha de nacimiento" valor={formatFecha(fechaNacimientoNuevo)} />
                  )}
                </div>
              </section>
            )}

            {/* Prescripción */}
            <section>
              <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-1.5 mb-3">
                Prescripción
              </p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                {!esEdicion && (
                  <>
                    <FilaPreview label="Médico" valor={medicoPreview?.nombre_medico} span2 />
                    <FilaPreview label="Medicamento" valor={medPreview ? `${medPreview.clave_cnis} — ${medPreview.descripcion}` : "—"} span2 />
                    <FilaPreview label="Unidad" valor={unidadDisplay} span2 />
                  </>
                )}
                <FilaPreview label="Diagnóstico" valor={diagPreview?.nombre} span2 />
                <FilaPreview label="Confirmado por" valor={vals.confirmado_por} />
                <FilaPreview label="Confirmado mediante" valor={vals.confirmado_mediante} />
                <FilaPreview label="Fecha inicio tratamiento" valor={formatFecha(vals.fecha_inicio_tratamiento)} />
                <FilaPreview label="Peso" valor={vals.peso ? `${vals.peso} kg` : "—"} />
                <FilaPreview label="Talla" valor={vals.talla ? `${vals.talla} cm` : "—"} />
                {!esEdicion && numeroExpediente.trim() && (
                  <FilaPreview label="Número de expediente" valor={numeroExpediente.trim()} />
                )}
              </div>
            </section>

            {/* Posología */}
            {previewPrescripcion && (
              <section>
                <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-1.5 mb-3">
                  Posología
                </p>
                <div className="bg-secondary/5 border border-secondary/20 rounded-lg px-4 py-3 space-y-2">
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
                    <p className="text-xs text-neutral-gray">
                      Primera administración:{" "}
                      <span className="font-semibold text-neutral-black">
                        {formatFecha(vals.fecha_primera_administracion)}
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
              </section>
            )}

            {/* Botones de confirmación */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setEnVistaPrevia(false)}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg
                  border border-neutral-gray/30 text-sm text-neutral-gray hover:bg-neutral-light transition"
              >
                <ChevronLeft size={15} />
                Volver a editar
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={handleSubmit(onSubmit)}
                className="flex-1 flex items-center justify-center gap-2 bg-secondary hover:bg-secondary/90
                  text-white text-sm font-medium py-2.5 rounded-lg transition
                  disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading
                  ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <Save size={15} />}
                {loading ? "Registrando..." : "Confirmar y registrar"}
              </button>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
