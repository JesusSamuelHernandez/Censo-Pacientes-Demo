/**
 * api/recetas.js — Llamadas al módulo de recetas del backend.
 */
import axiosClient from "../lib/axiosClient";

// GET /recetas
export const listarRecetas = async ({ pagina = 1, porPagina = 100, soloActivos = true } = {}) => {
  const { data } = await axiosClient.get("/recetas", {
    params: { pagina, por_pagina: porPagina, solo_activos: soloActivos },
  });
  return data;
};

// GET /recetas/{id_receta}
export const obtenerReceta = async (idReceta) => {
  const { data } = await axiosClient.get(`/recetas/${idReceta}`);
  return data;
};

// POST /recetas
export const crearReceta = async (payload) => {
  const { data } = await axiosClient.post("/recetas", payload);
  return data;
};

// PATCH /recetas/{id_receta}
export const actualizarReceta = async (idReceta, payload) => {
  const { data } = await axiosClient.patch(`/recetas/${idReceta}`, payload);
  return data;
};

// DELETE /recetas/{id_receta} — Soft Delete
export const anularReceta = async (idReceta) => {
  const { data } = await axiosClient.delete(`/recetas/${idReceta}`);
  return data;
};
