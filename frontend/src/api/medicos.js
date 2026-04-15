/**
 * api/medicos.js — Llamadas al módulo de médicos del backend.
 */
import axiosClient from "../lib/axiosClient";

// GET /medicos
export const listarMedicos = async () => {
  const { data } = await axiosClient.get("/medicos");
  return data;
};

// GET /medicos/{id_medico}
export const obtenerMedico = async (idMedico) => {
  const { data } = await axiosClient.get(`/medicos/${idMedico}`);
  return data;
};

// POST /medicos
export const crearMedico = async (payload) => {
  const { data } = await axiosClient.post("/medicos", payload);
  return data;
};

// PATCH /medicos/{id_medico}
export const actualizarMedico = async (idMedico, payload) => {
  const { data } = await axiosClient.patch(`/medicos/${idMedico}`, payload);
  return data;
};
