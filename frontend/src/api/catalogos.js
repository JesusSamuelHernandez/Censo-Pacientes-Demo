/**
 * api/catalogos.js — Llamadas a catálogos (unidades y medicamentos).
 */
import axiosClient from "../lib/axiosClient";

// ── Medicamentos ──────────────────────────────────────────────────────────────

export const listarMedicamentos = async (soloActivos = true) => {
  const { data } = await axiosClient.get("/catalogos/medicamentos", {
    params: { solo_activos: soloActivos },
  });
  return data;
};

export const crearMedicamento = async (payload) => {
  const { data } = await axiosClient.post("/catalogos/medicamentos", payload);
  return data;
};

export const actualizarMedicamento = async (claveCnis, payload) => {
  const { data } = await axiosClient.patch(
    `/catalogos/medicamentos/${claveCnis}`,
    payload
  );
  return data;
};

// ── Unidades Médicas ──────────────────────────────────────────────────────────

export const listarUnidades = async (idEntidad = null) => {
  const params = {};
  if (idEntidad) params.id_entidad = idEntidad;
  const { data } = await axiosClient.get("/catalogos/unidades", { params });
  return data;
};

export const crearUnidad = async (payload) => {
  const { data } = await axiosClient.post("/catalogos/unidades", payload);
  return data;
};

export const actualizarUnidad = async (clues, payload) => {
  const { data } = await axiosClient.patch(
    `/catalogos/unidades/${clues}`,
    payload
  );
  return data;
};
