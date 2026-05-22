/**
 * ReportesPage.jsx — Reportes con dos pestañas: Detallado y Estatal.
 * Incluye exportación a Excel desde el cliente con la librería xlsx.
 */
import { useEffect, useState } from "react";
import { Download, RefreshCw, BarChart2, ClipboardList, TrendingUp } from "lucide-react";
import { toast } from "sonner";
import * as XLSX from "xlsx";

import { getReporteDetallado, getReporteEstatal, getRtm } from "../../api/reportes";
import { listarUnidades } from "../../api/catalogos";
import useAuthStore from "../../store/authStore";
import useRtmStore from "../../store/rtmStore";

const ROLES_ESTATAL = ["SUPER_ADMIN", "ADMIN_ESTATAL"];

export default function ReportesPage() {
  const { rolNombre } = useAuthStore();
  const [tab, setTab] = useState("detallado");

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-neutral-black">Reportes</h2>
        <p className="text-sm text-neutral-gray mt-0.5">Consulta y exporta información del censo.</p>
      </div>

      {/* Pestañas */}
      <div className="flex gap-1 bg-white border border-neutral-gray/20 rounded-xl p-1 w-fit">
        <TabBtn activo={tab === "detallado"} onClick={() => setTab("detallado")} icon={ClipboardList}>
          Reporte Detallado
        </TabBtn>
        {ROLES_ESTATAL.includes(rolNombre) && (
          <TabBtn activo={tab === "estatal"} onClick={() => setTab("estatal")} icon={BarChart2}>
            Reporte Estatal
          </TabBtn>
        )}
        {rolNombre === "SUPER_ADMIN" && (
          <TabBtn activo={tab === "rtm"} onClick={() => setTab("rtm")} icon={TrendingUp}>
            RTM
          </TabBtn>
        )}
      </div>

      {tab === "detallado" && <ReporteDetallado />}
      {tab === "estatal" && ROLES_ESTATAL.includes(rolNombre) && <ReporteEstatal />}
      {tab === "rtm" && rolNombre === "SUPER_ADMIN" && <ReporteRTM />}
    </div>
  );
}

// ── Botón de pestaña ──────────────────────────────────────────────────────────
function TabBtn({ activo, onClick, icon: Icon, children }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition
        ${activo ? "bg-primary text-white" : "text-neutral-gray hover:text-neutral-black hover:bg-neutral-light"}`}
    >
      <Icon size={15} />
      {children}
    </button>
  );
}

// ── Reporte Detallado ─────────────────────────────────────────────────────────
function ReporteDetallado() {
  const [datos, setDatos] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [soloActivos, setSoloActivos] = useState(true);

  const cargar = async () => {
    setLoading(true);
    try {
      const res = await getReporteDetallado({ fechaInicio, fechaFin, soloActivos });
      setDatos(res.datos);
      setMeta(res);
    } catch {
      toast.error("Error al cargar el reporte.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, []);

  const exportarExcel = () => {
    if (datos.length === 0) { toast.error("No hay datos para exportar."); return; }

    const filas = datos.map((r) => ({
      "ID Registro": r.id_registro,
      "ID Paciente": r.id_paciente,
      "CURP": r.curp_paciente,
      "Nombre Paciente": r.nombre_paciente,
      "Diagnóstico": r.diagnostico,
      "CLUES Unidad": r.clues_unidad,
      "Médico": r.medico,
      "Cédula Médico": r.cedula_medico,
      "Días Adherencia": r.dias_adherencia,
      "Clave CNIS": r.clave_cnis,
      "Medicamento": r.descripcion_medicamento,
      "Prescripción": r.prescripcion,
      "Fecha Inicio Tratamiento": r.fecha_inicio_tratamiento,
      "Fecha Primera Adm.": r.fecha_primera_administracion,
      "Fecha Registro": r.fecha_registro_sistema,
      "Activo": r.es_activo ? "Sí" : "No",
    }));

    const ws = XLSX.utils.json_to_sheet(filas);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Reporte Detallado");
    XLSX.writeFile(wb, `reporte_detallado_${new Date().toISOString().slice(0, 10)}.xlsx`);
    toast.success("Archivo Excel generado.");
  };

  return (
    <div className="space-y-4">
      {/* Filtros */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 px-4 py-3 flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs font-medium text-neutral-gray mb-1">Fecha inicio</label>
          <input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)}
            className="px-3 py-2 rounded-lg border border-neutral-gray/30 bg-neutral-light text-sm outline-none
              focus:ring-2 focus:ring-primary/20 focus:border-primary" />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-gray mb-1">Fecha fin</label>
          <input type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)}
            className="px-3 py-2 rounded-lg border border-neutral-gray/30 bg-neutral-light text-sm outline-none
              focus:ring-2 focus:ring-primary/20 focus:border-primary" />
        </div>
        <label className="flex items-center gap-2 text-sm text-neutral-gray cursor-pointer pb-1">
          <input type="checkbox" checked={soloActivos} onChange={(e) => setSoloActivos(e.target.checked)}
            className="accent-primary w-4 h-4" />
          Solo activos
        </label>
        <button onClick={cargar}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-neutral-light hover:bg-neutral-gray/20
            text-sm text-neutral-black border border-neutral-gray/30 transition">
          <RefreshCw size={14} />
          Aplicar filtros
        </button>
        <button onClick={exportarExcel}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary hover:bg-secondary-dark
            text-white text-sm font-medium transition ml-auto">
          <Download size={14} />
          Exportar Excel
        </button>
      </div>

      {/* Contador */}
      {meta && (
        <p className="text-xs text-neutral-gray">
          {meta.total_registros} registro(s) — generado el {new Date(meta.generado_en).toLocaleString("es-MX")}
        </p>
      )}

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-neutral-light border-b border-neutral-gray/20">
                {["Folio", "Paciente", "CURP", "Diagnóstico", "Unidad", "Médico", "Días Adh.", "Medicamento", "Prescripción", "Inicio Trat."].map((h) => (
                  <th key={h} className="text-left px-3 py-3 font-semibold text-neutral-black whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={10} className="text-center py-12">
                  <div className="flex justify-center">
                    <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  </div>
                </td></tr>
              ) : datos.length === 0 ? (
                <tr><td colSpan={10} className="text-center py-12 text-neutral-gray">Sin registros.</td></tr>
              ) : (
                datos.map((r) => (
                  <tr key={r.id_registro} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-3 py-2 font-mono text-neutral-gray">#{r.id_registro}</td>
                    <td className="px-3 py-2 font-medium text-neutral-black max-w-[160px] truncate" title={r.nombre_paciente}>{r.nombre_paciente}</td>
                    <td className="px-3 py-2 font-mono text-neutral-gray">{r.curp_paciente}</td>
                    <td className="px-3 py-2 text-neutral-gray max-w-[160px] truncate" title={r.diagnostico ?? undefined}>{r.diagnostico ?? "—"}</td>
                    <td className="px-3 py-2 font-mono text-neutral-gray">{r.clues_unidad}</td>
                    <td className="px-3 py-2 text-neutral-black max-w-[140px] truncate" title={r.medico ?? undefined}>{r.medico ?? "—"}</td>
                    <td className="px-3 py-2 text-center">
                      {r.dias_adherencia != null
                        ? <span className="text-secondary font-semibold">{r.dias_adherencia}</span>
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-neutral-gray max-w-[180px] truncate" title={r.descripcion_medicamento ?? r.clave_cnis}>{r.descripcion_medicamento ?? r.clave_cnis}</td>
                    <td className="px-3 py-2 text-neutral-gray max-w-[200px] truncate" title={r.prescripcion ?? undefined}>{r.prescripcion ?? "—"}</td>
                    <td className="px-3 py-2 text-neutral-gray">{r.fecha_inicio_tratamiento ?? "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const ENTIDADES_RTM = [
  "AGUASCALIENTES","BAJA CALIFORNIA","BAJA CALIFORNIA SUR","CAMPECHE","CHIAPAS",
  "CHIHUAHUA","CIUDAD DE MEXICO","COAHUILA","COLIMA","DURANGO","MEXICO",
  "GUANAJUATO","GUERRERO","HIDALGO","JALISCO","MICHOACAN DE OCAMPO","MORELOS",
  "NAYARIT","NUEVO LEON","OAXACA","PUEBLA","QUERETARO","QUINTANA ROO",
  "SAN LUIS POTOSI","SINALOA","SONORA","TABASCO","TAMAULIPAS","TLAXCALA",
  "VERACRUZ DE IGNACIO DE LA LLAVE","YUCATAN","ZACATECAS",
];

// ── Reporte RTM ───────────────────────────────────────────────────────────────
function ReporteRTM() {
  const { entidad, unidadSeleccionada, setEntidad, setUnidadSeleccionada, limpiarUnidad } = useRtmStore();
  const [busqueda, setBusqueda] = useState("");
  const [unidades, setUnidades] = useState([]);
  const [loadingUnidades, setLoadingUnidades] = useState(false);
  const [datos, setDatos] = useState(null);
  const [loading, setLoading] = useState(false);

  const MES_ACTUAL_IDX = 0;

  // Carga la lista de unidades cuando cambia la entidad.
  // Nunca limpia unidadSeleccionada aquí: esa responsabilidad está en el handler
  // del <select>, de modo que la restauración del store no provoque limpiezas.
  useEffect(() => {
    if (!entidad) { setUnidades([]); return; }
    setLoadingUnidades(true);
    listarUnidades(entidad)
      .then(setUnidades)
      .catch(() => toast.error("Error al cargar unidades."))
      .finally(() => setLoadingUnidades(false));
  }, [entidad]);

  // Genera el RTM al seleccionar una unidad (también al restaurar del store al montar)
  useEffect(() => {
    if (!unidadSeleccionada) { setDatos(null); return; }
    setLoading(true);
    getRtm(unidadSeleccionada.clues)
      .then(setDatos)
      .catch(() => toast.error("Error al generar el reporte RTM."))
      .finally(() => setLoading(false));
  }, [unidadSeleccionada]);

  const filtradas = busqueda.length < 2
    ? unidades
    : unidades.filter((u) =>
        u.clues.toLowerCase().includes(busqueda.toLowerCase()) ||
        u.nombre_de_la_unidad.toLowerCase().includes(busqueda.toLowerCase())
      );

  const exportarExcel = () => {
    if (!datos || datos.filas.length === 0) { toast.error("No hay datos para exportar."); return; }
    const filas = datos.filas.map((f) => {
      const row = {
        "Clave CNIS": f.clave_cnis,
        "Descripción": f.descripcion,
        "Grupo": f.grupo ?? "—",
        "U. Medida": f.unidad_de_medida ?? "—",
      };
      f.meses.forEach((m) => { row[m.etiqueta] = m.cantidad > 0 ? m.cantidad : 0; });
      return row;
    });
    const ws = XLSX.utils.json_to_sheet(filas);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "RTM");
    XLSX.writeFile(wb, `rtm_${unidadSeleccionada.clues}_${new Date().toISOString().slice(0, 7)}.xlsx`);
    toast.success("Archivo Excel generado.");
  };

  return (
    <div className="space-y-4">
      {/* Filtros: entidad + buscador */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 px-4 py-3 flex flex-wrap items-center gap-3">
        <select
          value={entidad}
          onChange={(e) => {
            setBusqueda("");
            limpiarUnidad();
            setDatos(null);
            setEntidad(e.target.value);
          }}
          className="px-3 py-2 rounded-lg border border-neutral-gray/30 bg-neutral-light
            text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
        >
          <option value="">— Selecciona una entidad —</option>
          {ENTIDADES_RTM.map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Buscar por CLUES o nombre..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          disabled={!entidad}
          className="flex-1 min-w-[220px] px-4 py-2 rounded-lg border border-neutral-gray/30 bg-neutral-light
            text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition
            disabled:opacity-50 disabled:cursor-not-allowed"
        />
        {entidad && (
          <span className="text-xs text-neutral-gray ml-auto">
            {loadingUnidades ? "Cargando..." : `${filtradas.length} unidad(es)`}
          </span>
        )}
      </div>

      {/* Lista de unidades filtradas (solo si no hay unidad seleccionada o hay búsqueda activa) */}
      {entidad && !unidadSeleccionada && (
        <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
          {loadingUnidades ? (
            <div className="flex justify-center py-10">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : filtradas.length === 0 ? (
            <p className="text-center text-neutral-gray text-sm py-10">Sin resultados.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-neutral-light border-b border-neutral-gray/20">
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black whitespace-nowrap">CLUES</th>
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Nombre de la Unidad</th>
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Categoría Gerencial</th>
                </tr>
              </thead>
              <tbody>
                {filtradas.map((u) => (
                  <tr
                    key={u.clues}
                    onClick={() => setUnidadSeleccionada(u)}
                    className="border-b border-neutral-gray/10 hover:bg-primary/5 cursor-pointer transition"
                  >
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-neutral-black whitespace-nowrap">
                      {u.clues}
                    </td>
                    <td className="px-4 py-3 font-medium text-neutral-black">{u.nombre_de_la_unidad}</td>
                    <td className="px-4 py-3 text-neutral-gray text-xs">{u.categoria_gerencial ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Encabezado del reporte con la unidad seleccionada */}
      {unidadSeleccionada && (
        <div className="flex items-center justify-between bg-white rounded-xl border border-neutral-gray/20 px-4 py-3">
          <div>
            <span className="text-xs text-neutral-gray">Unidad seleccionada</span>
            <p className="font-semibold text-neutral-black">{unidadSeleccionada.nombre_de_la_unidad}</p>
            <p className="text-xs font-mono text-neutral-gray">{unidadSeleccionada.clues}</p>
          </div>
          <div className="flex items-center gap-2">
            {datos && datos.filas.length > 0 && (
              <button
                onClick={exportarExcel}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary hover:bg-secondary-dark
                  text-white text-sm font-medium transition"
              >
                <Download size={14} />
                Exportar Excel
              </button>
            )}
            <button
              onClick={() => { limpiarUnidad(); setDatos(null); }}
              className="px-3 py-2 rounded-lg border border-neutral-gray/30 text-sm text-neutral-gray
                hover:bg-neutral-light transition"
            >
              Cambiar unidad
            </button>
          </div>
        </div>
      )}

      {/* Metadata */}
      {datos && unidadSeleccionada && (
        <p className="text-xs text-neutral-gray">
          Generado el {new Date(datos.generado_en).toLocaleString("es-MX")}
          {" · "}Solo prescripciones activas con posología completa
        </p>
      )}

      {/* Estados: placeholder / cargando RTM / sin datos / tabla */}
      {!unidadSeleccionada ? (
        !entidad ? (
          <div className="bg-white rounded-xl border border-neutral-gray/20 p-16 flex flex-col items-center gap-3">
            <TrendingUp size={40} className="text-neutral-gray/30" />
            <p className="text-sm text-neutral-gray">Selecciona una entidad y luego una unidad para generar el RTM.</p>
          </div>
        ) : null
      ) : loading ? (
        <div className="flex justify-center items-center h-48">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : datos && datos.filas.length === 0 ? (
        <div className="bg-white rounded-xl border border-neutral-gray/20 p-16 flex flex-col items-center gap-3">
          <TrendingUp size={40} className="text-neutral-gray/30" />
          <p className="text-sm text-neutral-gray">No hay prescripciones activas con posología en esta unidad.</p>
        </div>
      ) : datos ? (
        <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-neutral-light border-b border-neutral-gray/20">
                  <th className="text-left px-3 py-3 font-semibold text-neutral-black whitespace-nowrap sticky left-0 bg-neutral-light z-10">
                    Clave CNIS
                  </th>
                  <th className="text-left px-3 py-3 font-semibold text-neutral-black min-w-[220px]">
                    Descripción
                  </th>
                  <th className="text-left px-3 py-3 font-semibold text-neutral-black whitespace-nowrap">
                    Grupo
                  </th>
                  <th className="text-center px-3 py-3 font-semibold text-neutral-black whitespace-nowrap">
                    U. Medida
                  </th>
                  {datos.cabeceras.map((cab, idx) => (
                    <th
                      key={cab}
                      className={`text-center px-3 py-3 font-semibold whitespace-nowrap
                        ${idx === MES_ACTUAL_IDX
                          ? "text-primary bg-primary/5 border-x border-primary/20"
                          : "text-neutral-black"}`}
                    >
                      {idx === MES_ACTUAL_IDX && (
                        <span className="block text-[10px] text-primary/70 font-normal leading-none mb-0.5">
                          Mes actual
                        </span>
                      )}
                      {cab}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {datos.filas.map((f) => (
                  <tr key={f.clave_cnis} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-3 py-2.5 font-mono font-semibold text-neutral-black whitespace-nowrap sticky left-0 bg-white z-10">
                      {f.clave_cnis}
                    </td>
                    <td className="px-3 py-2.5 text-neutral-gray max-w-[240px]" title={f.descripcion}>
                      <span className="line-clamp-2">{f.descripcion}</span>
                    </td>
                    <td className="px-3 py-2.5 text-neutral-gray whitespace-nowrap">
                      {f.grupo ?? <span className="text-neutral-gray/40">—</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {f.unidad_de_medida ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-amber-100 text-amber-700 font-medium">
                          {f.unidad_de_medida}
                        </span>
                      ) : (
                        <span className="text-neutral-gray/40">—</span>
                      )}
                    </td>
                    {f.meses.map((m, idx) => (
                      <td
                        key={m.etiqueta}
                        className={`px-3 py-2.5 text-center whitespace-nowrap
                          ${idx === MES_ACTUAL_IDX ? "bg-primary/5 border-x border-primary/20" : ""}`}
                      >
                        {m.cantidad > 0 ? (
                          <span className={`font-semibold ${idx === MES_ACTUAL_IDX ? "text-primary" : "text-neutral-black"}`}>
                            {m.cantidad % 1 === 0 ? m.cantidad : m.cantidad.toFixed(2)}
                          </span>
                        ) : (
                          <span className="text-neutral-gray/40">—</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}

// ── Reporte Estatal ───────────────────────────────────────────────────────────
function ReporteEstatal() {
  const [datos, setDatos] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getReporteEstatal()
      .then((res) => { setDatos(res.unidades); setMeta(res); })
      .catch(() => toast.error("Error al cargar el reporte estatal."))
      .finally(() => setLoading(false));
  }, []);

  const exportarExcel = () => {
    if (datos.length === 0) { toast.error("No hay datos para exportar."); return; }

    const filas = datos.map((u) => ({
      "CLUES": u.clues,
      "Nombre Unidad": u.nombre_de_la_unidad,
      "Entidad": u.id_entidad,
      "Total Pacientes Activos": u.total_pacientes_activos,
      "Total Prescripciones Activas": u.total_registros_activos,
    }));

    const ws = XLSX.utils.json_to_sheet(filas);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Reporte Estatal");
    XLSX.writeFile(wb, `reporte_estatal_${new Date().toISOString().slice(0, 10)}.xlsx`);
    toast.success("Archivo Excel generado.");
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between bg-white rounded-xl border border-neutral-gray/20 px-4 py-3">
        {meta && (
          <p className="text-xs text-neutral-gray">
            Ámbito: <span className="font-medium text-neutral-black">{meta.ambito}</span>
            {" · "}{meta.total_unidades} unidad(es) — {new Date(meta.generado_en).toLocaleString("es-MX")}
          </p>
        )}
        <button onClick={exportarExcel}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary hover:bg-secondary-dark
            text-white text-sm font-medium transition">
          <Download size={14} />
          Exportar Excel
        </button>
      </div>

      <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-light border-b border-neutral-gray/20">
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">CLUES</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Unidad Médica</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Entidad</th>
                <th className="text-center px-4 py-3 font-semibold text-neutral-black">Pacientes Activos</th>
                <th className="text-center px-4 py-3 font-semibold text-neutral-black">Prescripciones Activas</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="text-center py-12">
                  <div className="flex justify-center">
                    <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  </div>
                </td></tr>
              ) : datos.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-12 text-neutral-gray">Sin datos.</td></tr>
              ) : (
                datos.map((u) => (
                  <tr key={u.clues} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-4 py-3 font-mono text-xs text-neutral-gray">{u.clues}</td>
                    <td className="px-4 py-3 font-medium text-neutral-black">{u.nombre_de_la_unidad}</td>
                    <td className="px-4 py-3 text-neutral-gray">{u.id_entidad}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center justify-center w-10 h-7 rounded-lg
                        bg-primary/10 text-primary font-semibold text-sm">
                        {u.total_pacientes_activos}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center justify-center w-10 h-7 rounded-lg
                        bg-secondary/10 text-secondary font-semibold text-sm">
                        {u.total_registros_activos}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
