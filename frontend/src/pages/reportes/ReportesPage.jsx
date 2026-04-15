/**
 * ReportesPage.jsx — Reportes con dos pestañas: Detallado y Estatal.
 * Incluye exportación a Excel desde el cliente con la librería xlsx.
 */
import { useEffect, useState } from "react";
import { Download, RefreshCw, BarChart2, ClipboardList } from "lucide-react";
import { toast } from "sonner";
import * as XLSX from "xlsx";

import { getReporteDetallado, getReporteEstatal } from "../../api/reportes";
import useAuthStore from "../../store/authStore";

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
      </div>

      {tab === "detallado" && <ReporteDetallado />}
      {tab === "estatal" && ROLES_ESTATAL.includes(rolNombre) && <ReporteEstatal />}
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
      "Folio Receta": r.id_receta,
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
      "Dosis": r.dosis_administrada,
      "Fecha Inicio Tratamiento": r.fecha_inicio_tratamiento,
      "Fecha Primera Adm.": r.fecha_primera_admin,
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
                {["Folio", "Paciente", "CURP", "Diagnóstico", "Unidad", "Médico", "Días Adh.", "Medicamento", "Dosis", "Inicio Trat."].map((h) => (
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
                  <tr key={r.id_receta} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-3 py-2 font-mono text-neutral-gray">{r.id_receta}</td>
                    <td className="px-3 py-2 font-medium text-neutral-black max-w-[160px] truncate">{r.nombre_paciente}</td>
                    <td className="px-3 py-2 font-mono text-neutral-gray">{r.curp_paciente}</td>
                    <td className="px-3 py-2 text-neutral-gray max-w-[160px] truncate">{r.diagnostico ?? "—"}</td>
                    <td className="px-3 py-2 font-mono text-neutral-gray">{r.clues_unidad}</td>
                    <td className="px-3 py-2 text-neutral-black max-w-[140px] truncate">{r.medico ?? "—"}</td>
                    <td className="px-3 py-2 text-center">
                      {r.dias_adherencia != null
                        ? <span className="text-secondary font-semibold">{r.dias_adherencia}</span>
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-neutral-gray max-w-[180px] truncate">{r.descripcion_medicamento ?? r.clave_cnis}</td>
                    <td className="px-3 py-2 text-neutral-gray">{r.dosis_administrada ?? "—"}</td>
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
      "Total Recetas Activas": u.total_recetas_activas,
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
                <th className="text-center px-4 py-3 font-semibold text-neutral-black">Recetas Activas</th>
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
                        {u.total_recetas_activas}
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
