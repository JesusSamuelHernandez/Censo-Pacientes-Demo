/**
 * api/usuarios.js — Llamadas al módulo de usuarios (Solo SUPER_ADMIN).
 */
import axiosClient from "../lib/axiosClient";

export const listarUsuarios = async () => {
  const { data } = await axiosClient.get("/usuarios");
  return data;
};

export const crearUsuario = async (payload) => {
  const { data } = await axiosClient.post("/usuarios", payload);
  return data; // incluye password_temporal
};

export const actualizarUsuario = async (id, payload) => {
  const { data } = await axiosClient.patch(`/usuarios/${id}`, payload);
  return data;
};

export const eliminarUsuario = async (id) => {
  await axiosClient.delete(`/usuarios/${id}`);
};
