/**
 * authStore.js — Estado global de autenticación con Zustand.
 *
 * Persiste en localStorage para sobrevivir recargas de página.
 * Campos almacenados:
 *   token                : JWT para adjuntar en requests.
 *   rolNombre            : SUPER_ADMIN | ADMIN_ESTATAL | RESPONSABLE_UNIDAD
 *   idUsuario            : PK del usuario en la BD.
 *   debeCambiarPassword  : si true, el usuario debe cambiar su contraseña temporal.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      rolNombre: null,
      idUsuario: null,
      debeCambiarPassword: false,

      // Llamado después de un login exitoso
      login: ({ access_token, rol_nombre, id_usuario, debe_cambiar_password }) => {
        localStorage.setItem("access_token", access_token);
        set({
          token: access_token,
          rolNombre: rol_nombre,
          idUsuario: id_usuario,
          debeCambiarPassword: debe_cambiar_password,
        });
      },

      // Actualiza la bandera una vez que el usuario cambia su contraseña
      marcarPasswordCambiado: () => {
        set({ debeCambiarPassword: false });
      },

      // Cierra sesión y limpia todo
      logout: () => {
        localStorage.removeItem("access_token");
        set({
          token: null,
          rolNombre: null,
          idUsuario: null,
          debeCambiarPassword: false,
        });
      },

      // Helpers de rol — evitan comparar strings sueltos en los componentes
      esSuperAdmin: () => useAuthStore.getState().rolNombre === "SUPER_ADMIN",
      esAdminEstatal: () => useAuthStore.getState().rolNombre === "ADMIN_ESTATAL",
      esResponsableUnidad: () => useAuthStore.getState().rolNombre === "RESPONSABLE_UNIDAD",
    }),
    {
      name: "auth_store", // clave en localStorage
      partialize: (state) => ({
        token: state.token,
        rolNombre: state.rolNombre,
        idUsuario: state.idUsuario,
        debeCambiarPassword: state.debeCambiarPassword,
      }),
    }
  )
);

export default useAuthStore;
