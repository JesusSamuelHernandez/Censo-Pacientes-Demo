/**
 * axiosClient.js — Instancia Axios preconfigurada para toda la app.
 *
 * Interceptor de request: adjunta automáticamente el JWT en cada petición.
 * Interceptor de response: si el backend devuelve 401, limpia la sesión y
 *   redirige al login sin que ninguna página tenga que manejarlo manualmente.
 */
import axios from "axios";

const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request interceptor: adjunta el token JWT ────────────────────────────────
axiosClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor: maneja errores 401 globalmente ─────────────────────
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expirado o inválido — limpiar sesión y redirigir al login
      localStorage.removeItem("access_token");
      localStorage.removeItem("auth_store");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default axiosClient;
