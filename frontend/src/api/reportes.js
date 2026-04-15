/**
 * api/reportes.js — Llamadas al módulo de reportes del backend.
 */
import axiosClient from "../lib/axiosClient";

// GET /reportes/resumen-detallado
export const getReporteDetallado = async ({ fechaInicio, fechaFin, soloActivos = true } = {}) => {
  const params = { solo_activos: soloActivos };
  if (fechaInicio) params.fecha_inicio = fechaInicio;
  if (fechaFin) params.fecha_fin = fechaFin;
  const { data } = await axiosClient.get("/reportes/resumen-detallado", { params });
  return data;
};

// GET /reportes/estatal
export const getReporteEstatal = async () => {
  const { data } = await axiosClient.get("/reportes/estatal");
  return data;
};
