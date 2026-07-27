/**
 * api/pacientes.js — Llamadas al módulo de pacientes del backend.
 * El identificador de ruta preferido es id_paciente (numérico) para no
 * exponer la CURP en URLs, logs ni historial del navegador.
 */
import axiosClient from "../lib/axiosClient";

// GET /pacientes
export const listarPacientes = async ({ pagina = 1, porPagina = 20, soloActivos = true, claveCnis = null } = {}) => {
  const params = { pagina, por_pagina: porPagina, solo_activos: soloActivos };
  if (claveCnis) params.clave_cnis = claveCnis;
  const { data } = await axiosClient.get("/pacientes", { params });
  return data; // { total, pagina, por_pagina, resultados }
};

// GET /pacientes/{identificador}
export const obtenerPaciente = async (identificador) => {
  const { data } = await axiosClient.get(`/pacientes/${identificador}`);
  return data;
};

// POST /pacientes
export const crearPaciente = async (payload) => {
  const { data } = await axiosClient.post("/pacientes", payload);
  return data;
};

// PATCH /pacientes/{identificador}
export const actualizarPaciente = async (identificador, payload) => {
  const { data } = await axiosClient.patch(`/pacientes/${identificador}`, payload);
  return data;
};

// DELETE /pacientes/{identificador} — Soft Delete (es_activo = false), requiere uno o más motivos de baja
export const darBajaPaciente = async (identificador, motivosBaja) => {
  const { data } = await axiosClient.delete(`/pacientes/${identificador}`, {
    data: { motivo_baja: motivosBaja },
  });
  return data;
};

// POST /pacientes/buscar — Búsqueda nacional por CURP (body JSON, sin filtro RBAC)
export const buscarPacientePorCurp = async (curp) => {
  const { data } = await axiosClient.post("/pacientes/buscar", {
    curp: curp.trim().toUpperCase(),
  });
  return data; // { existe, id_paciente, nombre_completo, clues_unidad_adscripcion, nombre_unidad, total_registros }
};

// GET /pacientes/buscar-por-nombre?q=...&limite=15 — Búsqueda por nombre filtrada por rol
export const buscarPacientesPorNombre = async (q, limite = 15) => {
  const { data } = await axiosClient.get("/pacientes/buscar-por-nombre", {
    params: { q, limite },
  });
  return data; // { resultados: [...] }
};

// GET /pacientes/{identificador}/registros — Todas las prescripciones del paciente, sin filtro de unidad
export const listarRegistrosDePaciente = async (identificador, soloActivos = false) => {
  const { data } = await axiosClient.get(`/pacientes/${identificador}/registros`, {
    params: { solo_activos: soloActivos },
  });
  return data; // RegistroListResponse
};

// GET /pacientes/{identificador}/expedientes — Lista todos los expedientes del paciente por unidad
export const listarExpedientesPaciente = async (identificador) => {
  const { data } = await axiosClient.get(`/pacientes/${identificador}/expedientes`);
  return data; // list[ExpedienteResponse]
};

// POST /pacientes/{identificador}/expedientes — Upsert: crea o actualiza expediente en una unidad
export const guardarExpediente = async (identificador, clues, numeroExpediente) => {
  const { data } = await axiosClient.post(`/pacientes/${identificador}/expedientes`, {
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
