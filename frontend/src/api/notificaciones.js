/**
 * api/notificaciones.js — Llamadas al módulo de notificaciones del backend.
 */
import axiosClient from "../lib/axiosClient";

// GET /notificaciones — Registros que requieren validación de continuidad
export const listarNotificaciones = async () => {
  const { data } = await axiosClient.get("/notificaciones");
  return data; // { total, resultados }
};
