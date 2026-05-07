/**
 * api/pacientes.js — Llamadas al módulo de pacientes del backend.
 */
import axiosClient from "../lib/axiosClient";

// GET /pacientes
export const listarPacientes = async ({ pagina = 1, porPagina = 20, soloActivos = true, claveCnis = null } = {}) => {
  const params = { pagina, por_pagina: porPagina, solo_activos: soloActivos };
  if (claveCnis) params.clave_cnis = claveCnis;
  const { data } = await axiosClient.get("/pacientes", { params });
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

// GET /pacientes/buscar?curp=xxx — Búsqueda nacional sin filtro RBAC
export const buscarPacientePorCurp = async (curp) => {
  const { data } = await axiosClient.get("/pacientes/buscar", {
    params: { curp: curp.trim().toUpperCase() },
  });
  return data; // { existe, id_paciente, nombre_completo, clues_unidad_adscripcion, nombre_unidad, total_registros }
};

// GET /pacientes/{curp}/registros — Todas las prescripciones del paciente, sin filtro de unidad
export const listarRegistrosDePaciente = async (curp, soloActivos = false) => {
  const { data } = await axiosClient.get(`/pacientes/${curp}/registros`, {
    params: { solo_activos: soloActivos },
  });
  return data; // RegistroListResponse
};
