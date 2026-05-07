/**
 * api/notificaciones.js — Llamadas al módulo de notificaciones del backend.
 */
import axiosClient from "../lib/axiosClient";

// GET /notificaciones — Registros que requieren validación de continuidad
export const listarNotificaciones = async () => {
  const { data } = await axiosClient.get("/notificaciones");
  return data; // { total, resultados }
};

// GET /notificaciones/transferencias — Traslados de pacientes pendientes de aceptar
export const listarNotificacionesTraslados = async () => {
  const { data } = await axiosClient.get("/notificaciones/transferencias");
  return data; // { total, resultados }
};

// PATCH /notificaciones/transferencias/{id}/leer — Marcar traslado como leído por la unidad
export const marcarTrasladoLeido = async (id) => {
  const { data } = await axiosClient.patch(`/notificaciones/transferencias/${id}/leer`);
  return data;
};
