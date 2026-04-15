/**
 * api/pacientes.js — Llamadas al módulo de pacientes del backend.
 */
import axiosClient from "../lib/axiosClient";

// GET /pacientes
export const listarPacientes = async ({ pagina = 1, porPagina = 20, soloActivos = true } = {}) => {
  const { data } = await axiosClient.get("/pacientes", {
    params: { pagina, por_pagina: porPagina, solo_activos: soloActivos },
  });
  return data; // { total, pagina, por_pagina, resultados }
};

// GET /pacientes/{curp}
export const obtenerPaciente = async (curp) => {
  const { data } = await axiosClient.get(`/pacientes/${curp}`);
  return data;
};

// POST /pacientes
export const crearPaciente = async (payload) => {
  const { data } = await axiosClient.post("/pacientes", payload);
  return data;
};

// PATCH /pacientes/{curp}
export const actualizarPaciente = async (curp, payload) => {
  const { data } = await axiosClient.patch(`/pacientes/${curp}`, payload);
  return data;
};

// DELETE /pacientes/{curp} — Soft Delete (es_activo = false)
export const darBajaPaciente = async (curp) => {
  const { data } = await axiosClient.delete(`/pacientes/${curp}`);
  return data;
};
