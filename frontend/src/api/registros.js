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
