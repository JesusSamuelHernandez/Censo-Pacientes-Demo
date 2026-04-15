/**
 * api/auth.js — Llamadas al módulo de autenticación del backend.
 */
import axiosClient from "../lib/axiosClient";

// POST /auth/login — devuelve { access_token, token_type, rol_nombre, id_usuario, debe_cambiar_password }
export const login = async (email, password) => {
  // El backend usa OAuth2PasswordRequestForm: espera form-data con 'username' y 'password'
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const { data } = await axiosClient.post("/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
};

// POST /usuarios/me/cambiar-password
export const cambiarPassword = async ({ password_actual, password_nueva }) => {
  const { data } = await axiosClient.post("/usuarios/me/cambiar-password", {
    password_actual,
    password_nueva,
  });
  return data;
};
