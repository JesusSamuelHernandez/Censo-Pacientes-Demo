/**
 * api/registros.js — Llamadas al módulo de registros (prescripciones) del backend.
 */
import axiosClient from "../lib/axiosClient";

// GET /registros
export const listarRegistros = async ({ pagina = 1, porPagina = 100, soloActivos = true } = {}) => {
  const { data } = await axiosClient.get("/registros", {
    params: { pagina, por_pagina: porPagina, solo_activos: soloActivos },
  });
  return data;
};

// GET /registros/{id_registro}
export const obtenerRegistro = async (idRegistro) => {
  const { data } = await axiosClient.get(`/registros/${idRegistro}`);
  return data;
};

// POST /registros
export const crearRegistro = async (payload) => {
  const { data } = await axiosClient.post("/registros", payload);
  return data;
};

// PATCH /registros/{id_registro}
export const actualizarRegistro = async (idRegistro, payload) => {
  const { data } = await axiosClient.patch(`/registros/${idRegistro}`, payload);
  return data;
};

// DELETE /registros/{id_registro} — Soft Delete
export const anularRegistro = async (idRegistro) => {
  const { data } = await axiosClient.delete(`/registros/${idRegistro}`);
  return data;
};

// POST /registros/completo — Registrar paciente nuevo (o existente) + prescripción en una llamada
export const crearRegistroCompleto = async (payload) => {
  const { data } = await axiosClient.post("/registros/completo", payload);
  return data;
};

// PATCH /registros/{id}/validar-continuidad — Reactivar y extender fecha de fin
// Si el registro tiene posología guardada, el backend calcula la fecha desde hoy (payload vacío).
// Si no tiene (legacy), se pasa nueva_fecha_fin_tratamiento manualmente.
export const validarContinuidad = async (idRegistro, nuevaFechaFin = null) => {
  const payload = nuevaFechaFin ? { nueva_fecha_fin_tratamiento: nuevaFechaFin } : {};
  const { data } = await axiosClient.patch(
    `/registros/${idRegistro}/validar-continuidad`,
    payload
  );
  return data;
};

// POST /registros/{id}/reemplazar — Crea nueva prescripción con cambios, anula la original
export const reemplazarRegistro = async (idRegistro, payload) => {
  const { data } = await axiosClient.post(`/registros/${idRegistro}/reemplazar`, payload);
  return data;
};

// ── Órdenes de Suministro ──────────────────────────────────────────────────

// GET /registros/{id}/ordenes-suministro
export const listarOrdenesSuministro = async (idRegistro) => {
  const { data } = await axiosClient.get(`/registros/${idRegistro}/ordenes-suministro`);
  return data;
};

// POST /registros/{id}/ordenes-suministro
export const crearOrdenSuministro = async (idRegistro, payload) => {
  const { data } = await axiosClient.post(`/registros/${idRegistro}/ordenes-suministro`, payload);
  return data;
};

// DELETE /registros/{id}/ordenes-suministro/{id_orden}
export const eliminarOrdenSuministro = async (idRegistro, idOrden) => {
  await axiosClient.delete(`/registros/${idRegistro}/ordenes-suministro/${idOrden}`);
};

// ── Órdenes de Remisión ───────────────────────────────────────────────────

// GET /registros/{id}/ordenes-remision
export const listarOrdenesRemision = async (idRegistro) => {
  const { data } = await axiosClient.get(`/registros/${idRegistro}/ordenes-remision`);
  return data;
};

// POST /registros/{id}/ordenes-remision
export const crearOrdenRemision = async (idRegistro, payload) => {
  const { data } = await axiosClient.post(`/registros/${idRegistro}/ordenes-remision`, payload);
  return data;
};

// DELETE /registros/{id}/ordenes-remision/{id_orden}
export const eliminarOrdenRemision = async (idRegistro, idOrden) => {
  await axiosClient.delete(`/registros/${idRegistro}/ordenes-remision/${idOrden}`);
};
