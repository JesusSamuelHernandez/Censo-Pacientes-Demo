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

// GET /pacientes/buscar-por-nombre?q=...&limite=15 — Búsqueda nacional por nombre, sin filtro RBAC
export const buscarPacientesPorNombre = async (q, limite = 15) => {
  const { data } = await axiosClient.get("/pacientes/buscar-por-nombre", {
    params: { q, limite },
  });
  return data; // { resultados: [...] }
};

// GET /pacientes/{curp}/registros — Todas las prescripciones del paciente, sin filtro de unidad
export const listarRegistrosDePaciente = async (curp, soloActivos = false) => {
  const { data } = await axiosClient.get(`/pacientes/${curp}/registros`, {
    params: { solo_activos: soloActivos },
  });
  return data; // RegistroListResponse
};

// GET /pacientes/{curp}/expedientes — Lista todos los expedientes del paciente por unidad
export const listarExpedientesPaciente = async (curp) => {
  const { data } = await axiosClient.get(`/pacientes/${curp}/expedientes`);
  return data; // list[ExpedienteResponse]
};

// POST /pacientes/{curp}/expedientes — Upsert: crea o actualiza expediente en una unidad
export const guardarExpediente = async (curp, clues, numeroExpediente) => {
  const { data } = await axiosClient.post(`/pacientes/${curp}/expedientes`, {
    clues,
    numero_expediente: numeroExpediente,
  });
  return data; // ExpedienteResponse
};

// GET /pacientes/{identificador}/reacciones-adversas — Lista reacciones adversas del paciente
export const obtenerReaccionesAdversas = async (identificador) => {
  const { data } = await axiosClient.get(`/pacientes/${identificador}/reacciones-adversas`);
  return data; // list[ReaccionAdversaResponse]
};

// POST /pacientes/{identificador}/reacciones-adversas — Registra una reacción adversa
export const agregarReaccionAdversa = async (identificador, payload) => {
  const { data } = await axiosClient.post(
    `/pacientes/${identificador}/reacciones-adversas`,
    payload // { clave_cnis, comentario }
  );
  return data; // ReaccionAdversaResponse
};
