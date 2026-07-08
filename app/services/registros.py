"""Lógica de negocio para registros de prescripción: posología, serialización y vencimientos."""
from datetime import date, timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session


from app.models import Registro
from app.schemas import DiagnosticoResponse, MedicamentoResponse, RegistroResponse
from app.services.medicos import _medico_to_response


def _pluralizar_unidad(unidad: str, cantidad: float) -> str:
    """Pluraliza la unidad del medicamento según cantidad. Ej: "tableta" → "tabletas"."""
    if cantidad == 1:
        return unidad
    u = unidad.lower()
    if u in {"ml", "mg", "mcg", "g", "ui", "dosis"}:
        return unidad
    if u.endswith("ón"):
        return unidad[:-2] + "ones"
    if u[-1] in "aeiouáéíóú":
        return unidad + "s"
    return unidad + "es"


def _calcular_prescripcion_y_total(
    dosis: float,
    frecuencia: int,
    duracion: int,
    unidad_tiempo: str,
    unidad: str,
    cantidad: float | None = None,
    unidad_de_medida: str | None = None,
) -> tuple[str, float]:
    """Retorna (texto_prescripcion, total_medicamento) a partir de los campos de posología."""
    factor = {"días": 1, "semanas": 7, "meses": 30}.get(unidad_tiempo, 1)
    duracion_dias = duracion * factor
    total = dosis * (24 / frecuencia) * duracion_dias
    unidad_txt = _pluralizar_unidad(unidad, dosis)
    if cantidad and unidad_de_medida:
        texto = (
            f"{dosis:g} {unidad_txt} de {cantidad:g} {unidad_de_medida}, "
            f"cada {frecuencia} horas, por {duracion} {unidad_tiempo}"
        )
    else:
        texto = f"{dosis:g} {unidad_txt}, cada {frecuencia} horas, por {duracion} {unidad_tiempo}"
    return texto, round(total, 2)


def _aplicar_posologia(
    registro: Registro,
    unidad_medicamento: str | None,
    unidad_de_medida: str | None = None,
) -> None:
    """Calcula prescripcion, total_medicamento y fecha_fin_tratamiento si la posología está completa."""
    if not (registro.dosis and registro.frecuencia and registro.duracion and registro.unidad_tiempo):
        return
    unidad = unidad_medicamento or "unidad"
    texto, total = _calcular_prescripcion_y_total(
        registro.dosis, registro.frecuencia, registro.duracion,
        registro.unidad_tiempo, unidad,
        cantidad=registro.cantidad,
        unidad_de_medida=unidad_de_medida,
    )
    registro.prescripcion = texto
    registro.total_medicamento = total
    if registro.fecha_primera_administracion:
        factor = {"días": 1, "semanas": 7, "meses": 30}.get(registro.unidad_tiempo, 1)
        registro.fecha_fin_tratamiento = (
            registro.fecha_primera_administracion + timedelta(days=registro.duracion * factor)
        )


def _registro_to_response(r: Registro) -> RegistroResponse:
    """Construye RegistroResponse descifrando los campos del médico y paciente embebidos."""
    return RegistroResponse(
        id_registro=r.id_registro,
        id_medico=r.id_medico,
        id_paciente=r.id_paciente,
        clave_cnis=r.clave_cnis,
        clues=r.clues,
        fecha_inicio_tratamiento=r.fecha_inicio_tratamiento,
        fecha_primera_administracion=r.fecha_primera_administracion,
        fecha_fin_tratamiento=r.fecha_fin_tratamiento,
        dosis_administrada=r.dosis_administrada,
        peso=r.peso,
        talla=r.talla,
        estatus_diagnostico=r.estatus_diagnostico,
        confirmado_por=r.confirmado_por,
        confirmado_mediante=r.confirmado_mediante,
        tratamiento_amparo=r.tratamiento_amparo,
        queja_derechos_humanos=r.queja_derechos_humanos,
        prescripcion=r.prescripcion,
        dosis=r.dosis,
        cantidad=r.cantidad,
        frecuencia=r.frecuencia,
        unidad_tiempo=r.unidad_tiempo,
        duracion=r.duracion,
        total_medicamento=r.total_medicamento,
        id_registro_origen=r.id_registro_origen,
        es_activo=r.es_activo,
        fecha_registro_sistema=r.fecha_registro_sistema,
        id_usuario_registro=r.id_usuario_registro,
        nombre_paciente=r.paciente.nombre_completo if r.paciente else None,
        curp_paciente=r.paciente.curp_paciente if r.paciente else None,
        id_diagnostico=r.id_diagnostico,
        medicamento=MedicamentoResponse.model_validate(r.medicamento) if r.medicamento else None,
        medico=_medico_to_response(r.medico) if r.medico else None,
        diagnostico=DiagnosticoResponse.model_validate(r.diagnostico) if r.diagnostico else None,
    )


def marcar_registros_vencidos(db: Session) -> int:
    """
    Marca es_activo=False en todos los registros activos cuyo plazo de continuidad
    ya venció: fecha_fin_tratamiento + 30 días <= hoy.
    Retorna el número de registros marcados. Se llama al inicio de los endpoints
    de lectura relevantes (lazy marking — sin scheduler externo).
    """
    fecha_limite = date.today() - timedelta(days=30)
    resultado = db.execute(
        update(Registro)
        .where(
            Registro.es_activo == True,
            Registro.fecha_fin_tratamiento.isnot(None),
            Registro.fecha_fin_tratamiento <= fecha_limite,
        )
        .values(es_activo=False)
    )
    db.commit()
    return resultado.rowcount
