"""Router de notificaciones: alertas de vencimiento y traslados entre unidades."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth import UsuarioActivo, apply_rbac_filter, require_password_cambiado

from app.database import get_db
from app.models import NotificacionTransferencia, Paciente, Registro, UnidadMedica
from app.schemas import (
    NotificacionListResponse,
    NotificacionResponse,
    NotificacionTransferenciaListResponse,
    NotificacionTransferenciaResponse,
)
from app.services.registros import marcar_registros_vencidos

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


@router.get(
    "",
    response_model=NotificacionListResponse,
    summary="Registros que requieren validación de continuidad (vencidos o por vencer en 7 días).",
)
def listar_notificaciones(
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    marcar_registros_vencidos(db)

    # Ventana de alerta: registros cuyo plazo de continuidad vence en los próximos 7 días
    # fecha_fin + 30 días <= hoy + 7  →  fecha_fin <= hoy - 23
    fecha_alerta = date.today() - timedelta(days=23)
    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(Registro)
        .options(
            joinedload(Registro.paciente),
            joinedload(Registro.medicamento),
        )
        .filter(
            Registro.fecha_fin_tratamiento.isnot(None),
            Registro.fecha_fin_tratamiento <= fecha_alerta,
            Registro.paciente.has(Paciente.es_activo == True),
        )
    )

    if filtro.filtrar_por_clues:
        # Filtra por la unidad donde el paciente está AHORA (no donde se hizo la prescripción),
        # para que las alertas de revalidación sigan al paciente tras un traslado.
        query = query.filter(
            Registro.paciente.has(
                Paciente.clues_unidad_adscripcion == filtro.valor_clues
            )
        )
    elif filtro.filtrar_por_entidad:
        # Mismo criterio para el nivel estatal: unidad actual del paciente dentro de la entidad.
        clues_en_entidad = (
            db.query(UnidadMedica.clues)
            .filter(UnidadMedica.id_entidad == filtro.valor_entidad)
        )
        query = query.filter(
            Registro.paciente.has(
                Paciente.clues_unidad_adscripcion.in_(clues_en_entidad)
            )
        )

    registros = query.order_by(Registro.fecha_fin_tratamiento.asc()).all()

    resultados = []
    for r in registros:
        fecha_limite = r.fecha_fin_tratamiento + timedelta(days=30)
        dias_restantes = (fecha_limite - date.today()).days
        resultados.append(NotificacionResponse(
            id_registro=r.id_registro,
            id_paciente=r.id_paciente,
            nombre_paciente=r.paciente.nombre_completo if r.paciente else "—",
            clave_cnis=r.clave_cnis,
            descripcion_medicamento=r.medicamento.descripcion if r.medicamento else None,
            clues=r.clues,
            fecha_fin_tratamiento=r.fecha_fin_tratamiento,
            fecha_limite=fecha_limite,
            dias_restantes=dias_restantes,
            es_activo=r.es_activo,
            fecha_inicio_tratamiento=r.fecha_inicio_tratamiento,
            dosis_administrada=r.dosis_administrada,
            peso=r.peso,
            talla=r.talla,
            prescripcion=r.prescripcion,
            duracion=r.duracion,
            unidad_tiempo=r.unidad_tiempo,
        ))

    return NotificacionListResponse(total=len(resultados), resultados=resultados)


@router.get(
    "/transferencias",
    response_model=NotificacionTransferenciaListResponse,
    summary="Traslados de pacientes pendientes de aceptar (RESPONSABLE_UNIDAD y SUPER_ADMIN).",
)
def listar_notificaciones_transferencia(
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no tiene notificaciones de traslado.",
        )

    query = (
        db.query(NotificacionTransferencia)
        .options(
            joinedload(NotificacionTransferencia.paciente),
            joinedload(NotificacionTransferencia.unidad_origen),
            joinedload(NotificacionTransferencia.unidad_destino),
            joinedload(NotificacionTransferencia.usuario_traslado),
        )
        .filter(NotificacionTransferencia.leida == False)
    )

    if current_user.es_responsable_unidad:
        # La unidad ve la notificación si es origen (pierde al paciente) O destino (lo recibe).
        query = query.filter(
            or_(
                NotificacionTransferencia.clues_unidad_origen == current_user.clues_unidad_asignada,
                NotificacionTransferencia.clues_unidad_destino == current_user.clues_unidad_asignada,
            )
        )

    notifs = query.order_by(NotificacionTransferencia.fecha_traslado.desc()).all()

    resultados = [
        NotificacionTransferenciaResponse(
            id=n.id,
            id_paciente=n.id_paciente,
            nombre_paciente=n.paciente.nombre_completo if n.paciente else "—",
            curp_paciente=n.paciente.curp_paciente if n.paciente else None,
            clues_unidad_origen=n.clues_unidad_origen,
            nombre_unidad_origen=n.unidad_origen.nombre_de_la_unidad if n.unidad_origen else None,
            clues_unidad_destino=n.clues_unidad_destino,
            nombre_unidad_destino=n.unidad_destino.nombre_de_la_unidad if n.unidad_destino else None,
            nombre_usuario_traslado=n.usuario_traslado.nombre_usuario if n.usuario_traslado else None,
            fecha_traslado=n.fecha_traslado,
        )
        for n in notifs
    ]

    return NotificacionTransferenciaListResponse(total=len(resultados), resultados=resultados)


@router.patch(
    "/transferencias/{id_notificacion}/leer",
    summary="Marcar traslado como leído por la unidad de origen.",
)
def marcar_traslado_leido(
    id_notificacion: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso.")

    notif = db.query(NotificacionTransferencia).filter(
        NotificacionTransferencia.id == id_notificacion
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada.")

    if current_user.es_responsable_unidad and notif.clues_unidad_origen != current_user.clues_unidad_asignada:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo la unidad de origen puede aceptar este traslado.",
        )

    notif.leida = True
    notif.id_usuario_leida = current_user.id_usuario
    notif.fecha_leida = datetime.now(timezone.utc)
    db.commit()

    return {"ok": True}
