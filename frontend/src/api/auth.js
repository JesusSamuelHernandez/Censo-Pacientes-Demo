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

// POST /usuarios/me/cambiar-password — nombre_usuario es requerido solo si la
// cuenta aún no tiene uno (autoservicio por correo o alta vía "Nuevo usuario")
export const cambiarPassword = async ({ password_actual, password_nueva, nombre_usuario }) => {
  const payload = { password_actual, password_nueva };
  if (nombre_usuario) payload.nombre_usuario = nombre_usuario;

  const { data } = await axiosClient.post("/usuarios/me/cambiar-password", payload);
  return data;
};

// POST /auth/solicitar-acceso — autoservicio desde la pantalla de login.
// Siempre responde el mismo mensaje genérico, sin importar el caso.
export const solicitarAcceso = async (email) => {
  const { data } = await axiosClient.post("/auth/solicitar-acceso", { email });
  return data; // { mensaje }
};

// POST /auth/activar — enlace de un solo uso del correo de alta/autoservicio.
// Establece la contraseña definitiva y deja la sesión iniciada (mismo shape
// que /auth/login: access_token, rol_nombre, etc.)
export const activarCuenta = async ({ token, password_nueva, nombre_usuario }) => {
  const payload = { token, password_nueva };
  if (nombre_usuario) payload.nombre_usuario = nombre_usuario;

  const { data } = await axiosClient.post("/auth/activar", payload);
  return data;
};

// POST /auth/logout — invalida en el servidor todos los tokens de la cuenta
// (token_version). Best-effort: si falla (p. ej. sin red), igual se limpia
// la sesión local en el llamador para no dejar a la persona sin poder salir.
export const cerrarSesion = async () => {
  await axiosClient.post("/auth/logout");
};
