/**
 * PacienteDetallePage.jsx — Detalle completo de un paciente con sus prescripciones.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { ArrowLeft, Pencil, ClipboardList, X, Eye } from "lucide-react";
import { toast } from "sonner";

import { obtenerPaciente, listarRegistrosDePaciente } from "../../api/pacientes";
import useAuthStore from "../../store/authStore";
import ReaccionAdversaIcon from "../../components/shared/ReaccionAdversaIcon";
import { REACCIONES_ADVERSAS_HABILITADO } from "../../config/featureFlags";

function getEstadoRegistro(r) {
  if (r.es_activo) {
    if (r.id_registro_origen) return { label: "Validada", classes: "bg-blue-100 text-blue-700" };
    return { label: "Activa", classes: "bg-secondary/10 text-secondary" };
  }
  if (r.fecha_fin_tratamiento) {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const limite = new Date(r.fecha_fin_tratamiento);
    limite.setDate(limite.getDate() + 30);
    limite.setHours(0, 0, 0, 0);
    if (limite <= hoy) return { label: "Vencida", classes: "bg-red-100 text-red-700" };
  }
  return { label: "Anulada", classes: "bg-neutral-gray/10 text-neutral-gray" };
}

const ROLES_PUEDEN_EDITAR = ["SUPER_ADMIN", "RESPONSABLE_UNIDAD"];

export default function PacienteDetallePage() {
  const { curp } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { rolNombre } = useAuthStore();

  const [paciente, setPaciente] = useState(null);
  const [registros, setRegistros] = useState([]);
  const [loading, setLoading] = useState(true);
  const [registroSeleccionado, setRegistroSeleccionado] = useState(null);

  const vieneDelFormulario = location.state?.from === "registro-form";
  const vieneDeLista = location.state?.from === "registros-list";

  useEffect(() => {
    const cargar = async () => {
      try {
        const [p, r] = await Promise.all([
          obtenerPaciente(curp),
          listarRegistrosDePaciente(curp),
        ]);
        setPaciente(p);
        setRegistros(r.resultados);
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
            onClick={() => {
              if (vieneDelFormulario) navigate("/registros/nuevo", { state: { curpPreCargado: location.state?.curpOrigen } });
              else if (vieneDeLista) navigate(-1);
              else navigate("/pacientes");
            }}
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
              onClick={() => navigate("/registros/nuevo", {
                state: { curpPreCargado: location.state?.curpOrigen }
              })}
              className="flex items-center gap-2 border border-primary text-primary hover:bg-primary/5
                text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              <ArrowLeft size={15} />
              Regresar al formulario
            </button>
          )}
          {vieneDeLista && (
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 border border-neutral-gray/30 text-neutral-gray
                hover:bg-neutral-light text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              <ArrowLeft size={15} />
              Regresar a la lista
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
          <Campo label="Diagnóstico(s)" valor={
            paciente.diagnosticos_activos?.length
              ? paciente.diagnosticos_activos.join(" · ")
              : "—"
          } />
        </div>
        {REACCIONES_ADVERSAS_HABILITADO && paciente.tiene_reaccion_adversa && (
          <div className="col-span-2">
            <Campo
              label="Alertas"
              valor={
                <ReaccionAdversaIcon
                  identificador={curp}
                  modoDetalle
                />
              }
            />
          </div>
        )}
      </div>

      {/* Modal de detalle de prescripción */}
      {registroSeleccionado && (
        <ModalDetallePrescripcion
          registro={registroSeleccionado}
          onClose={() => setRegistroSeleccionado(null)}
        />
      )}

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
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Prescripción</th>
                  <th className="text-left px-4 py-3 font-semibold text-neutral-black">Estado</th>
                  <th className="px-4 py-3 w-8" />
                </tr>
              </thead>
              <tbody>
                {registros.map((r) => (
                  <tr
                    key={r.id_registro}
                    onClick={() => setRegistroSeleccionado(r)}
                    className="border-b border-neutral-gray/10 hover:bg-neutral-light/50 cursor-pointer"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-neutral-gray">
                      #{r.id_registro}
                      {r.id_registro_origen && (
                        <span className="ml-1 text-blue-600" title={`Reemplaza a #${r.id_registro_origen}`}>↑</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-neutral-black text-xs">{r.clave_cnis}</p>
                      <p
                        title={r.medicamento?.descripcion}
                        className="text-neutral-gray text-xs truncate max-w-xs"
                      >
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
                    <td className="px-4 py-3 text-neutral-gray text-xs" title={r.prescripcion ?? undefined}>
                      {r.prescripcion ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      {(() => { const e = getEstadoRegistro(r); return (
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${e.classes}`}>
                          {e.label}
                        </span>
                      ); })()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Eye size={14} className="text-neutral-gray/50 group-hover:text-primary" />
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
  if (valor === null || valor === undefined || valor === "") return null;
  return (
    <div>
      <p className="text-xs text-neutral-gray uppercase tracking-wide mb-1">{label}</p>
      <div className="text-sm text-neutral-black font-medium">{valor}</div>
    </div>
  );
}

function ModalDetallePrescripcion({ registro: r, onClose }) {
  const estado = getEstadoRegistro(r);

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-neutral-gray/10 sticky top-0 bg-white z-10">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-neutral-black">
                Prescripción #{r.id_registro}
              </h3>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${estado.classes}`}>
                {estado.label}
              </span>
              {r.id_registro_origen && (
                <span className="text-xs text-blue-600 font-medium">
                  Reemplaza a #{r.id_registro_origen}
                </span>
              )}
            </div>
            <p className="text-xs font-mono text-neutral-gray mt-0.5">{r.clave_cnis}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-neutral-gray hover:text-neutral-black hover:bg-neutral-light transition flex-shrink-0"
          >
            <X size={16} />
          </button>
        </div>

        {/* Contenido */}
        <div className="p-6 space-y-6">

          {/* Medicamento y unidad */}
          <section className="space-y-3">
            <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide">
              Medicamento y unidad
            </p>
            <div className="grid grid-cols-2 gap-4">
              <Campo label="Descripción" valor={r.medicamento?.descripcion} />
              <Campo label="Médico" valor={r.medico?.nombre_medico} />
              <Campo label="Unidad (CLUES)" valor={r.clues} />
            </div>
          </section>

          {/* Posología y prescripción */}
          {(r.prescripcion || r.dosis || r.frecuencia) && (
            <section className="space-y-3">
              <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide">
                Posología
              </p>
              {r.prescripcion && (
                <div className="bg-secondary/5 border border-secondary/20 rounded-lg px-4 py-3">
                  <p className="text-xs text-neutral-gray uppercase tracking-wide font-semibold mb-1">
                    Prescripción generada
                  </p>
                  <p className="text-sm font-medium text-neutral-black">{r.prescripcion}</p>
                  {r.total_medicamento != null && (
                    <p className="text-xs text-neutral-gray mt-1">
                      Total del tratamiento:{" "}
                      <span className="font-semibold text-secondary">{r.total_medicamento}</span>
                    </p>
                  )}
                </div>
              )}
              <div className="grid grid-cols-3 gap-4">
                <Campo label="Dosis" valor={r.dosis != null ? `${r.dosis} ${r.medicamento?.unidad ?? "unidad(es)"}` : null} />
                <Campo label="Cantidad por unidad" valor={r.cantidad != null ? `${r.cantidad} ${r.medicamento?.unidad_de_medida ?? ""}`.trim() : null} />
                <Campo label="Frecuencia" valor={r.frecuencia != null ? `Cada ${r.frecuencia} horas` : null} />
                <Campo label="Duración" valor={r.duracion != null ? `${r.duracion} ${r.unidad_tiempo}` : null} />
              </div>
            </section>
          )}

          {/* Fechas */}
          <section className="space-y-3">
            <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide">
              Fechas
            </p>
            <div className="grid grid-cols-2 gap-4">
              <Campo label="Inicio de tratamiento" valor={r.fecha_inicio_tratamiento} />
              <Campo label="Primera administración" valor={r.fecha_primera_administracion} />
              <Campo label="Fin de tratamiento" valor={r.fecha_fin_tratamiento} />
              <Campo label="Fecha de registro" valor={r.fecha_registro_sistema
                ? new Date(r.fecha_registro_sistema).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" })
                : null} />
            </div>
          </section>

          {/* Datos clínicos */}
          {(r.diagnostico || r.estatus_diagnostico || r.confirmado_por || r.peso || r.talla || r.dosis_administrada) && (
            <section className="space-y-3">
              <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide">
                Datos clínicos
              </p>
              <div className="grid grid-cols-2 gap-4">
                {r.diagnostico && (
                  <div className="col-span-2">
                    <Campo label="Diagnóstico" valor={r.diagnostico.nombre} />
                  </div>
                )}
                <Campo label="Estatus del diagnóstico" valor={r.estatus_diagnostico} />
                <Campo label="Confirmado por" valor={r.confirmado_por} />
                <Campo label="Peso" valor={r.peso != null ? `${r.peso} kg` : null} />
                <Campo label="Talla" valor={r.talla != null ? `${r.talla} cm` : null} />
                <Campo label="Dosis administrada" valor={r.dosis_administrada} />
              </div>
            </section>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-gray/10 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-lg border border-neutral-gray/30
              text-sm text-neutral-gray hover:bg-neutral-light transition"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
