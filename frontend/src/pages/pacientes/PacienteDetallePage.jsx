/**
 * PacienteDetallePage.jsx — Detalle completo de un paciente con sus prescripciones.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { ArrowLeft, Pencil, ClipboardList } from "lucide-react";
import { toast } from "sonner";

import { obtenerPaciente } from "../../api/pacientes";
import { listarRegistros } from "../../api/registros";
import useAuthStore from "../../store/authStore";

const ROLES_PUEDEN_EDITAR = ["SUPER_ADMIN", "RESPONSABLE_UNIDAD"];

export default function PacienteDetallePage() {
  const { curp } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { rolNombre } = useAuthStore();

  const [paciente, setPaciente] = useState(null);
  const [registros, setRegistros] = useState([]);
  const [loading, setLoading] = useState(true);

  // Detecta si llegamos desde el formulario de prescripción
  const vieneDelFormulario = location.state?.from === "registro-form";

  useEffect(() => {
    const cargar = async () => {
      try {
        const [p, r] = await Promise.all([
          obtenerPaciente(curp),
          listarRegistros({ soloActivos: false, porPagina: 500 }),
        ]);
        setPaciente(p);
        setRegistros(r.resultados.filter((reg) => reg.id_paciente === p.id_paciente));
      } catch {
        toast.error("Error al cargar el paciente.");
        navigate("/pacientes");
      } finally {
        setLoading(false);
      }
    };
    cargar();
  }, [curp]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!paciente) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => vieneDelFormulario ? navigate(-1) : navigate("/pacientes")}
            className="p-2 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h2 className="text-xl font-semibold text-neutral-black">{paciente.nombre_completo}</h2>
            <p className="text-sm font-mono text-neutral-gray">{paciente.curp_paciente}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {vieneDelFormulario && (
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 border border-primary text-primary hover:bg-primary/5
                text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              <ArrowLeft size={15} />
              Regresar al formulario
            </button>
          )}
          {ROLES_PUEDEN_EDITAR.includes(rolNombre) && paciente.es_activo && (
            <button
              onClick={() => navigate(`/pacientes/${curp}/editar`)}
              className="flex items-center gap-2 bg-primary hover:bg-primary-dark text-white
                text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              <Pencil size={15} />
              Editar
            </button>
          )}
        </div>
      </div>

      {/* Datos del paciente */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 p-6 grid grid-cols-2 gap-6">
        <Campo label="Estado" valor={
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
            ${paciente.es_activo ? "bg-secondary/10 text-secondary" : "bg-neutral-gray/10 text-neutral-gray"}`}>
            {paciente.es_activo ? "Activo" : "Baja"}
          </span>
        } />
        <Campo label="Unidad de adscripción" valor={paciente.clues_unidad_adscripcion} />
        <Campo label="Fecha de registro" valor={new Date(paciente.fecha_registro).toLocaleDateString("es-MX", {
          year: "numeric", month: "long", day: "numeric"
        })} />
        <Campo label="Adherencia" valor={
          paciente.dias_adherencia != null
            ? <span className="text-secondary font-semibold">{paciente.dias_adherencia} días</span>
            : "Sin prescripción activa"
        } />
        <div className="col-span-2">
          <Campo label="Diagnóstico actual" valor={paciente.diagnostico_actual ?? "—"} />
        </div>
      </div>

      {/* Historial de prescripciones */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-gray/10">
          <div className="flex items-center gap-2">
            <ClipboardList size={18} className="text-primary" />
            <h3 className="font-semibold text-neutral-black">Historial de Prescripciones</h3>
          </div>
          <span className="text-xs text-neutral-gray">{registros.length} prescripción(es)</span>
        </div>

        {registros.length === 0 ? (
          <p className="text-center text-neutral-gray py-10 text-sm">
            Este paciente no tiene prescripciones registradas.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-neutral-light border-b border-neutral-gray/10">
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">ID</th>
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Medicamento</th>
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Médico</th>
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Inicio</th>
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Fin</th>
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Dosis</th>
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Estado</th>
                </tr>
              </thead>
              <tbody>
                {registros.map((r) => (
                  <tr key={r.id_registro} className="border-b border-neutral-gray/10 hover:bg-neutral-light/50">
                    <td className="px-4 py-3 font-mono text-xs text-neutral-gray">#{r.id_registro}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-neutral-black text-xs">{r.clave_cnis}</p>
                      <p className="text-neutral-gray text-xs truncate max-w-xs">
                        {r.medicamento?.descripcion ?? "—"}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-neutral-gray text-xs">
                      {r.medico?.nombre_medico ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-neutral-gray text-xs">
                      {r.fecha_inicio_tratamiento ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-neutral-gray text-xs">
                      {r.fecha_fin_tratamiento ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-neutral-gray text-xs">
                      {r.dosis_administrada ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                        ${r.es_activo ? "bg-secondary/10 text-secondary" : "bg-neutral-gray/10 text-neutral-gray"}`}>
                        {r.es_activo ? "Activa" : "Anulada"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function Campo({ label, valor }) {
  return (
    <div>
      <p className="text-xs text-neutral-gray uppercase tracking-wide mb-1">{label}</p>
      <div className="text-sm text-neutral-black font-medium">{valor}</div>
    </div>
  );
}
