/**
 * RegistroDetallePage.jsx — Vista completa de una prescripción.
 * Accesible desde la lista de notificaciones o de prescripciones.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { ArrowLeft, RefreshCw, Pencil, CheckCircle } from "lucide-react";
import { toast } from "sonner";

import { obtenerRegistro, validarContinuidad } from "../../api/registros";
import useAuthStore from "../../store/authStore";

// Calcula la nueva fecha fin desde hoy usando la duración guardada
function calcularNuevaFechaFin(registro) {
  if (!registro.duracion || !registro.unidad_tiempo) return null;
  const factor = { días: 1, semanas: 7, meses: 30 }[registro.unidad_tiempo] ?? 1;
  const fecha = new Date();
  fecha.setDate(fecha.getDate() + registro.duracion * factor);
  return fecha.toLocaleDateString("es-MX", { dateStyle: "long" });
}

const ROLES_PUEDEN_VALIDAR = ["SUPER_ADMIN", "RESPONSABLE_UNIDAD"];

function Campo({ label, valor }) {
  if (valor === null || valor === undefined || valor === "") return null;
  return (
    <div>
      <p className="text-xs text-neutral-gray uppercase tracking-wide mb-0.5">{label}</p>
      <div className="text-sm text-neutral-black font-medium">{valor}</div>
    </div>
  );
}

function getEstadoRegistro(r) {
  if (r.es_activo) return { label: "Activa", classes: "bg-secondary/10 text-secondary" };
  if (r.fecha_fin_tratamiento) {
    const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
    const limite = new Date(r.fecha_fin_tratamiento);
    limite.setDate(limite.getDate() + 30); limite.setHours(0, 0, 0, 0);
    if (limite <= hoy) return { label: "Vencida", classes: "bg-red-100 text-red-700" };
  }
  return { label: "Anulada", classes: "bg-neutral-gray/10 text-neutral-gray" };
}

export default function RegistroDetallePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { rolNombre } = useAuthStore();

  const [registro, setRegistro] = useState(null);
  const [loading, setLoading] = useState(true);

  // Modal validación
  const [modalValidar, setModalValidar] = useState(false);
  const [nuevaFecha, setNuevaFecha] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    obtenerRegistro(id)
      .then(setRegistro)
      .catch(() => { toast.error("Error al cargar la prescripción."); navigate(-1); })
      .finally(() => setLoading(false));
  }, [id]);

  const tienePosologia = registro?.duracion && registro?.unidad_tiempo;

  const handleValidar = async () => {
    // Si no tiene posología guardada, requiere fecha manual
    if (!tienePosologia && !nuevaFecha) return;
    setGuardando(true);
    try {
      await validarContinuidad(id, tienePosologia ? null : nuevaFecha);
      toast.success("Continuidad validada. Prescripción reactivada.");
      setModalValidar(false);
      setNuevaFecha("");
      const actualizado = await obtenerRegistro(id);
      setRegistro(actualizado);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al validar.");
    } finally {
      setGuardando(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!registro) return null;

  const estado = getEstadoRegistro(registro);
  const esVencida = estado.label === "Vencida";
  const desdeNotificaciones = location.state?.from === "notificaciones";

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h2 className="text-xl font-semibold text-neutral-black">
              Prescripción #{registro.id_registro}
            </h2>
            <p className="text-sm text-neutral-gray">
              {registro.nombre_paciente ?? `Paciente #${registro.id_paciente}`}
              {registro.curp_paciente && (
                <span className="font-mono ml-2">{registro.curp_paciente}</span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${estado.classes}`}>
            {estado.label}
          </span>
          {ROLES_PUEDEN_VALIDAR.includes(rolNombre) && esVencida && (
            <button
              onClick={() => { setModalValidar(true); setNuevaFecha(""); }}
              className="flex items-center gap-2 bg-secondary hover:bg-secondary-dark text-white
                text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              <RefreshCw size={15} />
              Validar continuidad
            </button>
          )}
          {ROLES_PUEDEN_VALIDAR.includes(rolNombre) && desdeNotificaciones && esVencida && (
            <button
              onClick={() => navigate(`/registros/${id}/editar`, {
                state: { ...location.state, modo: "reemplazar" }
              })}
              className="flex items-center gap-2 bg-primary hover:bg-primary-dark text-white
                text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              <Pencil size={15} />
              Editar y validar
            </button>
          )}
        </div>
      </div>

      {/* Datos de la prescripción */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 p-6 space-y-5">
        <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-2">
          Información del medicamento y unidad
        </p>
        <div className="grid grid-cols-2 gap-5">
          <Campo label="Clave CNIS" valor={registro.clave_cnis} />
          <Campo label="Medicamento" valor={registro.medicamento?.descripcion} />
          <Campo label="Unidad (CLUES)" valor={registro.clues} />
          <Campo label="Médico" valor={registro.medico?.nombre_medico} />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-neutral-gray/20 p-6 space-y-5">
        <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-2">
          Fechas y dosis
        </p>
        <div className="grid grid-cols-2 gap-5">
          <Campo label="Inicio de tratamiento" valor={registro.fecha_inicio_tratamiento ?? "—"} />
          <Campo label="Fin de tratamiento" valor={registro.fecha_fin_tratamiento ?? "—"} />
          <Campo label="Primera administración" valor={registro.fecha_primera_administracion ?? "—"} />
          <Campo label="Dosis administrada" valor={registro.dosis_administrada ?? "—"} />
        </div>
      </div>

      {(registro.estatus_diagnostico || registro.confirmado_por || registro.peso || registro.talla || registro.prescripcion) && (
        <div className="bg-white rounded-xl border border-neutral-gray/20 p-6 space-y-5">
          <p className="text-xs font-semibold text-neutral-gray uppercase tracking-wide border-b border-neutral-gray/10 pb-2">
            Datos clínicos
          </p>
          <div className="grid grid-cols-2 gap-5">
            <Campo label="Estatus del diagnóstico" valor={registro.estatus_diagnostico} />
            <Campo label="Confirmado por" valor={registro.confirmado_por} />
            <Campo label="Peso" valor={registro.peso != null ? `${registro.peso} kg` : null} />
            <Campo label="Talla" valor={registro.talla != null ? `${registro.talla} cm` : null} />
          </div>
          {registro.prescripcion && (
            <div>
              <p className="text-xs text-neutral-gray uppercase tracking-wide mb-1">Prescripción</p>
              <p className="text-sm text-neutral-black bg-neutral-light border border-neutral-gray/20
                rounded-lg px-4 py-3 whitespace-pre-wrap">
                {registro.prescripcion}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Modal de validación */}
      {modalValidar && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 space-y-4">
            <div>
              <h3 className="text-base font-semibold text-neutral-black">Validar continuidad</h3>
              <p className="text-sm font-medium text-neutral-black mt-1">
                {registro.nombre_paciente ?? `Paciente #${registro.id_paciente}`}
              </p>
              <p className="text-sm text-neutral-gray mt-0.5">
                {registro.medicamento?.descripcion ?? registro.clave_cnis}
              </p>
            </div>

            {tienePosologia ? (
              <div className="bg-secondary/5 border border-secondary/20 rounded-lg px-4 py-3 space-y-1">
                <p className="text-xs text-neutral-gray uppercase tracking-wide font-semibold">
                  Duración del tratamiento
                </p>
                <p className="text-sm font-medium text-neutral-black">
                  {registro.duracion} {registro.unidad_tiempo}
                </p>
                <p className="text-xs text-neutral-gray">
                  Nueva fecha de fin estimada:{" "}
                  <span className="font-semibold text-neutral-black">
                    {calcularNuevaFechaFin(registro)}
                  </span>
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm text-neutral-gray mb-3">
                  Este registro no tiene posología guardada. Indica manualmente la nueva fecha de fin.
                </p>
                <label className="block text-xs font-medium text-neutral-gray mb-1">
                  Nueva fecha de fin <span className="text-primary">*</span>
                </label>
                <input
                  type="date"
                  value={nuevaFecha}
                  onChange={(e) => setNuevaFecha(e.target.value)}
                  min={new Date().toISOString().slice(0, 10)}
                  className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                    text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>
            )}

            <div className="flex gap-3 pt-1">
              <button
                onClick={() => { setModalValidar(false); setNuevaFecha(""); }}
                className="flex-1 px-4 py-2 rounded-lg border border-neutral-gray/30
                  text-sm text-neutral-gray hover:bg-neutral-light transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleValidar}
                disabled={(!tienePosologia && !nuevaFecha) || guardando}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg
                  bg-secondary hover:bg-secondary-dark text-white text-sm font-medium transition
                  disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {guardando
                  ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <CheckCircle size={14} />}
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
